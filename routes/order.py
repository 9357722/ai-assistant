"""
订单路由模块
提供订单创建、查询、支付、取消等接口
"""
import json
import time
import logging
import aiomysql

from fastapi import APIRouter, Depends, HTTPException, status, Query

import config
from db import get_pool
from auth import get_current_user, TokenData
from services.websocket_manager import ws_manager
from models.order import (
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["订单模块"])


# ============ 数据库连接 ============

async def get_db():
    """获取全局连接池"""
    return get_pool()


def generate_order_no() -> str:
    """生成订单号（UUID，不可预测）"""
    import uuid
    return f"ORD{uuid.uuid4().hex[:16].upper()}"


# ============ 创建订单 ============

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """
    创建订单

    1. 从购物车获取选中的商品
    2. 验证商品库存
    3. 创建订单和订单项
    4. 扣减库存
    5. 清理购物车
    """
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 开启事务：关闭 autocommit，保证扣库存+建订单+清购物车原子性
            await conn.begin()
            try:
                # 幂等性校验：如果提供了幂等键，检查是否已存在
                if order_data.idempotency_key:
                    await cur.execute(
                        "SELECT id, order_no FROM orders WHERE idempotency_key = %s AND user_id = %s",
                        (order_data.idempotency_key, current_user.user_id)
                    )
                    existing_order = await cur.fetchone()
                    if existing_order:
                        # 已存在，返回已有订单（幂等）
                        await conn.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_200_OK,
                            detail=f"订单已存在: {existing_order['order_no']}"
                        )

                # 获取收货地址
                await cur.execute(
                    "SELECT * FROM user_addresses WHERE id = %s AND user_id = %s",
                    (order_data.address_id, current_user.user_id)
                )
                address = await cur.fetchone()
                if not address:
                    raise HTTPException(status_code=404, detail="收货地址不存在")

                # 获取购物车项（使用 FOR UPDATE 行级锁，防止并发超卖）
                if order_data.cart_item_ids:
                    placeholders = ",".join(["%s"] * len(order_data.cart_item_ids))
                    sql = f"""
                        SELECT ci.*, p.name as product_name, p.main_image as product_image,
                               p.price as product_price, p.stock as product_stock
                        FROM cart_items ci
                        JOIN products p ON ci.product_id = p.id
                        WHERE ci.id IN ({placeholders}) AND ci.user_id = %s AND p.status = 'on_sale'
                    """
                    params = order_data.cart_item_ids + [current_user.user_id]
                else:
                    sql = """
                        SELECT ci.*, p.name as product_name, p.main_image as product_image,
                               p.price as product_price, p.stock as product_stock
                        FROM cart_items ci
                        JOIN products p ON ci.product_id = p.id
                        WHERE ci.user_id = %s AND ci.selected = TRUE AND p.status = 'on_sale'
                    """
                    params = [current_user.user_id]

                await cur.execute(sql, params)
                cart_items = await cur.fetchall()

                # 锁定商品行，防止并发扣减
                product_ids = [item["product_id"] for item in cart_items] if cart_items else []
                if product_ids:
                    placeholders = ",".join(["%s"] * len(product_ids))
                    await cur.execute(
                        f"SELECT id, stock FROM products WHERE id IN ({placeholders}) FOR UPDATE",
                        product_ids
                    )

                if not cart_items:
                    raise HTTPException(status_code=400, detail="没有选中的商品")

                # 验证库存（乐观锁：扣减时再校验一次）
                for item in cart_items:
                    if item["product_stock"] < item["quantity"]:
                        raise HTTPException(
                            status_code=400,
                            detail=f"商品 '{item['product_name']}' 库存不足"
                        )

                # 计算总金额
                total_amount = sum(float(item["product_price"]) * item["quantity"] for item in cart_items)

                # 生成订单号
                order_no = generate_order_no()

                # 地址快照
                address_snapshot = {
                    "name": address["name"],
                    "phone": address["phone"],
                    "province": address["province"],
                    "city": address["city"],
                    "district": address["district"],
                    "detail": address["detail"],
                }

                # 创建订单
                await cur.execute(
                    """INSERT INTO orders (order_no, user_id, total_amount, pay_amount, status, address_snapshot, remark, idempotency_key)
                       VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s)""",
                    (order_no, current_user.user_id, total_amount, total_amount,
                     json.dumps(address_snapshot, ensure_ascii=False), order_data.remark,
                     order_data.idempotency_key)
                )
                order_id = cur.lastrowid

                # 创建订单项并扣减库存（带乐观锁校验）
                order_items = []
                for item in cart_items:
                    await cur.execute(
                        """INSERT INTO order_items (order_id, product_id, product_name, product_image, price, quantity)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (order_id, item["product_id"], item["product_name"], item["product_image"],
                         item["product_price"], item["quantity"])
                    )

                    # 乐观锁扣库存：WHERE 库存 >= 购买量
                    await cur.execute(
                        "UPDATE products SET stock = stock - %s, sales = sales + %s WHERE id = %s AND stock >= %s",
                        (item["quantity"], item["quantity"], item["product_id"], item["quantity"])
                    )
                    if cur.rowcount == 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"商品 '{item['product_name']}' 库存扣减失败（并发冲突）"
                        )

                    order_items.append(OrderItemResponse(
                        id=cur.lastrowid,
                        order_id=order_id,
                        product_id=item["product_id"],
                        product_name=item["product_name"],
                        product_image=item["product_image"],
                        price=float(item["product_price"]),
                        quantity=item["quantity"],
                        subtotal=float(item["product_price"]) * item["quantity"],
                    ))

                # 清理购物车中的已购商品
                cart_item_ids = [item["id"] for item in cart_items]
                placeholders = ",".join(["%s"] * len(cart_item_ids))
                await cur.execute(
                    f"DELETE FROM cart_items WHERE id IN ({placeholders}) AND user_id = %s",
                    cart_item_ids + [current_user.user_id]
                )

                await conn.commit()

                logger.info(f"Order created: order_no={order_no}, user_id={current_user.user_id}, amount={total_amount}, items={len(order_items)}")

                return OrderResponse(
                    id=order_id,
                    order_no=order_no,
                    user_id=current_user.user_id,
                    total_amount=total_amount,
                    pay_amount=total_amount,
                    status="pending",
                    address_snapshot=address_snapshot,
                    remark=order_data.remark,
                    items=order_items,
                    created_at=None,
                )
            except HTTPException:
                await conn.rollback()
                raise
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=500, detail=f"订单创建失败: {str(e)}")


# ============ 订单列表 ============

@router.get("", response_model=OrderListResponse)
async def list_orders(
    status_filter: str = Query(None, alias="status", description="订单状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取当前用户的订单列表"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 构建查询条件
            where_clause = "o.user_id = %s"
            params = [current_user.user_id]

            if status_filter:
                where_clause += " AND o.status = %s"
                params.append(status_filter)

            # 获取总数
            count_sql = f"SELECT COUNT(*) as total FROM orders o WHERE {where_clause}"
            await cur.execute(count_sql, params)
            total = (await cur.fetchone())["total"]

            # 获取订单列表
            offset = (page - 1) * page_size
            order_sql = f"""
                SELECT o.* FROM orders o
                WHERE {where_clause}
                ORDER BY o.created_at DESC
                LIMIT %s OFFSET %s
            """
            await cur.execute(order_sql, params + [page_size, offset])
            orders = await cur.fetchall()

            # 批量获取订单项（避免 N+1 查询）
            order_ids = [order["id"] for order in orders]
            order_list = []
            items_map = {}

            if order_ids:
                placeholders = ",".join(["%s"] * len(order_ids))
                await cur.execute(
                    f"SELECT * FROM order_items WHERE order_id IN ({placeholders})",
                    order_ids
                )
                all_items = await cur.fetchall()
                for item in all_items:
                    items_map.setdefault(item["order_id"], []).append(item)

            for order in orders:
                items = items_map.get(order["id"], [])

                order_items = [
                    OrderItemResponse(
                        id=item["id"],
                        order_id=item["order_id"],
                        product_id=item["product_id"],
                        product_name=item["product_name"],
                        product_image=item["product_image"],
                        price=float(item["price"]),
                        quantity=item["quantity"],
                        subtotal=float(item["price"]) * item["quantity"],
                    )
                    for item in items
                ]

                # 解析地址快照
                address_snapshot = order.get("address_snapshot")
                if isinstance(address_snapshot, str):
                    address_snapshot = json.loads(address_snapshot)

                order_list.append(OrderResponse(
                    id=order["id"],
                    order_no=order["order_no"],
                    user_id=order["user_id"],
                    total_amount=float(order["total_amount"]),
                    pay_amount=float(order["pay_amount"]) if order["pay_amount"] else None,
                    status=order["status"],
                    address_snapshot=address_snapshot,
                    remark=order["remark"],
                    items=order_items,
                    paid_at=order["paid_at"],
                    shipped_at=order["shipped_at"],
                    completed_at=order["completed_at"],
                    created_at=order["created_at"],
                    updated_at=order.get("updated_at"),
                ))

            return OrderListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=order_list,
            )


# ============ 订单详情 ============

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取订单详情"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取订单
            await cur.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                (order_id, current_user.user_id)
            )
            order = await cur.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            # 获取订单项
            await cur.execute(
                "SELECT * FROM order_items WHERE order_id = %s",
                (order_id,)
            )
            items = await cur.fetchall()

            order_items = [
                OrderItemResponse(
                    id=item["id"],
                    order_id=item["order_id"],
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    product_image=item["product_image"],
                    price=float(item["price"]),
                    quantity=item["quantity"],
                    subtotal=float(item["price"]) * item["quantity"],
                )
                for item in items
            ]

            # 解析地址快照
            address_snapshot = order.get("address_snapshot")
            if isinstance(address_snapshot, str):
                address_snapshot = json.loads(address_snapshot)

            return OrderResponse(
                id=order["id"],
                order_no=order["order_no"],
                user_id=order["user_id"],
                total_amount=float(order["total_amount"]),
                pay_amount=float(order["pay_amount"]) if order["pay_amount"] else None,
                status=order["status"],
                address_snapshot=address_snapshot,
                remark=order["remark"],
                items=order_items,
                paid_at=order["paid_at"],
                shipped_at=order["shipped_at"],
                completed_at=order["completed_at"],
                created_at=order["created_at"],
                updated_at=order.get("updated_at"),
            )


# ============ 模拟支付 ============

@router.post("/{order_id}/pay")
async def pay_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """模拟支付订单"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取订单
            await cur.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                (order_id, current_user.user_id)
            )
            order = await cur.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            if order["status"] != "pending":
                raise HTTPException(status_code=400, detail=f"订单状态为 {order['status']}，无法支付")

            # 更新订单状态为已支付
            await cur.execute(
                "UPDATE orders SET status = 'paid', paid_at = NOW() WHERE id = %s",
                (order_id,)
            )
            await conn.commit()

            # 推送实时通知
            await ws_manager.notify_order_status(
                user_id=current_user.user_id,
                order_no=order["order_no"],
                status="paid",
                message=f"订单 {order['order_no']} 支付成功，金额 ¥{order['total_amount']}",
            )

            return {
                "message": "支付成功",
                "order_no": order["order_no"],
                "amount": float(order["total_amount"]),
            }


# ============ 取消订单 ============

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """取消订单"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await conn.begin()
            try:
                # 获取订单
                await cur.execute(
                    "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                    (order_id, current_user.user_id)
                )
                order = await cur.fetchone()
                if not order:
                    raise HTTPException(status_code=404, detail="订单不存在")

                if order["status"] not in ["pending", "paid"]:
                    raise HTTPException(status_code=400, detail=f"订单状态为 {order['status']}，无法取消")

                # 恢复库存
                await cur.execute(
                    "SELECT * FROM order_items WHERE order_id = %s",
                    (order_id,)
                )
                items = await cur.fetchall()

                for item in items:
                    await cur.execute(
                        "UPDATE products SET stock = stock + %s, sales = sales - %s WHERE id = %s",
                        (item["quantity"], item["quantity"], item["product_id"])
                    )

                # 更新订单状态
                await cur.execute(
                    "UPDATE orders SET status = 'cancelled' WHERE id = %s",
                    (order_id,)
                )
                await conn.commit()

                # 推送实时通知
                await ws_manager.notify_order_status(
                    user_id=current_user.user_id,
                    order_no=order["order_no"],
                    status="cancelled",
                    message=f"订单 {order['order_no']} 已取消",
                )

                return {"message": "订单已取消"}
            except HTTPException:
                await conn.rollback()
                raise
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=500, detail=f"取消订单失败: {str(e)}")


# ============ 确认收货 ============

@router.post("/{order_id}/complete")
async def complete_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """确认收货"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取订单
            await cur.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                (order_id, current_user.user_id)
            )
            order = await cur.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            if order["status"] != "shipped":
                raise HTTPException(status_code=400, detail=f"订单状态为 {order['status']}，无法确认收货")

            # 更新订单状态
            await cur.execute(
                "UPDATE orders SET status = 'completed', completed_at = NOW() WHERE id = %s",
                (order_id,)
            )
            await conn.commit()

            # 推送实时通知
            await ws_manager.notify_order_status(
                user_id=current_user.user_id,
                order_no=order["order_no"],
                status="completed",
                message=f"订单 {order['order_no']} 已确认收货",
            )

            return {"message": "已确认收货"}
