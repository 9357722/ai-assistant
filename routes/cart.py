"""
购物车路由模块
提供购物车增删改查接口
"""
import aiomysql

from fastapi import APIRouter, Depends, HTTPException, status

import config
from auth import get_current_user, TokenData
from models.cart import (
    CartItemAdd,
    CartItemUpdate,
    CartItemResponse,
    CartResponse,
)

router = APIRouter(prefix="/api/cart", tags=["购物车模块"])


# ============ 数据库连接 ============

async def get_db():
    """获取数据库连接池"""
    pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        db=config.DB_NAME,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        yield pool
    finally:
        pool.close()
        await pool.wait_closed()


# ============ 获取购物车 ============

@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取当前用户的购物车"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查询购物车项（关联商品信息）
            sql = """
                SELECT ci.*, p.name as product_name, p.main_image as product_image,
                       p.price as product_price, p.platform as product_platform,
                       p.stock as product_stock
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = %s AND p.status = 'on_sale'
                ORDER BY ci.created_at DESC
            """
            await cur.execute(sql, (current_user.user_id,))
            items = await cur.fetchall()

            # 计算小计和总计
            cart_items = []
            total_amount = 0
            selected_amount = 0
            selected_count = 0

            for item in items:
                subtotal = item["product_price"] * item["quantity"]
                total_amount += subtotal

                if item["selected"]:
                    selected_amount += subtotal
                    selected_count += 1

                cart_items.append(CartItemResponse(
                    id=item["id"],
                    user_id=item["user_id"],
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    product_image=item["product_image"],
                    product_price=float(item["product_price"]),
                    product_platform=item["product_platform"],
                    product_stock=item["product_stock"],
                    quantity=item["quantity"],
                    selected=bool(item["selected"]),
                    subtotal=subtotal,
                    created_at=item["created_at"],
                    updated_at=item.get("updated_at"),
                ))

            return CartResponse(
                items=cart_items,
                total_items=len(cart_items),
                total_amount=total_amount,
                selected_amount=selected_amount,
                selected_count=selected_count,
            )


# ============ 添加到购物车 ============

@router.post("/add", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item_data: CartItemAdd,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """添加商品到购物车"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 检查商品是否存在且在售
            await cur.execute(
                "SELECT id, name, main_image, price, platform, stock FROM products WHERE id = %s AND status = 'on_sale'",
                (item_data.product_id,)
            )
            product = await cur.fetchone()
            if not product:
                raise HTTPException(status_code=404, detail="商品不存在或已下架")

            # 检查库存
            if product["stock"] < item_data.quantity:
                raise HTTPException(status_code=400, detail="库存不足")

            # 检查购物车中是否已有该商品
            await cur.execute(
                "SELECT id, quantity FROM cart_items WHERE user_id = %s AND product_id = %s",
                (current_user.user_id, item_data.product_id)
            )
            existing = await cur.fetchone()

            if existing:
                # 更新数量
                new_quantity = existing["quantity"] + item_data.quantity
                if new_quantity > product["stock"]:
                    raise HTTPException(status_code=400, detail="超出库存限制")

                await cur.execute(
                    "UPDATE cart_items SET quantity = %s WHERE id = %s",
                    (new_quantity, existing["id"])
                )
                await conn.commit()

                return CartItemResponse(
                    id=existing["id"],
                    user_id=current_user.user_id,
                    product_id=item_data.product_id,
                    product_name=product["name"],
                    product_image=product["main_image"],
                    product_price=float(product["price"]),
                    product_platform=product["platform"],
                    product_stock=product["stock"],
                    quantity=new_quantity,
                    selected=True,
                    subtotal=float(product["price"]) * new_quantity,
                    created_at=existing.get("created_at"),
                )
            else:
                # 新增购物车项
                await cur.execute(
                    "INSERT INTO cart_items (user_id, product_id, quantity, selected) VALUES (%s, %s, %s, TRUE)",
                    (current_user.user_id, item_data.product_id, item_data.quantity)
                )
                await conn.commit()
                cart_item_id = cur.lastrowid

                return CartItemResponse(
                    id=cart_item_id,
                    user_id=current_user.user_id,
                    product_id=item_data.product_id,
                    product_name=product["name"],
                    product_image=product["main_image"],
                    product_price=float(product["price"]),
                    product_platform=product["platform"],
                    product_stock=product["stock"],
                    quantity=item_data.quantity,
                    selected=True,
                    subtotal=float(product["price"]) * item_data.quantity,
                    created_at=None,
                )


# ============ 更新购物车项 ============

@router.put("/{cart_item_id}", response_model=CartItemResponse)
async def update_cart_item(
    cart_item_id: int,
    item_data: CartItemUpdate,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """更新购物车项（数量、选中状态）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 检查购物车项是否存在且属于当前用户
            await cur.execute(
                """SELECT ci.*, p.name as product_name, p.main_image as product_image,
                          p.price as product_price, p.platform as product_platform, p.stock as product_stock
                   FROM cart_items ci
                   JOIN products p ON ci.product_id = p.id
                   WHERE ci.id = %s AND ci.user_id = %s""",
                (cart_item_id, current_user.user_id)
            )
            item = await cur.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="购物车项不存在")

            # 更新字段
            update_fields = []
            update_values = []

            if item_data.quantity is not None:
                if item_data.quantity > item["product_stock"]:
                    raise HTTPException(status_code=400, detail="超出库存限制")
                update_fields.append("quantity = %s")
                update_values.append(item_data.quantity)

            if item_data.selected is not None:
                update_fields.append("selected = %s")
                update_values.append(item_data.selected)

            if not update_fields:
                raise HTTPException(status_code=400, detail="没有要更新的内容")

            update_values.append(cart_item_id)
            sql = f"UPDATE cart_items SET {', '.join(update_fields)} WHERE id = %s"
            await cur.execute(sql, update_values)
            await conn.commit()

            # 返回更新后的数据
            quantity = item_data.quantity if item_data.quantity is not None else item["quantity"]
            selected = item_data.selected if item_data.selected is not None else item["selected"]

            return CartItemResponse(
                id=cart_item_id,
                user_id=current_user.user_id,
                product_id=item["product_id"],
                product_name=item["product_name"],
                product_image=item["product_image"],
                product_price=float(item["product_price"]),
                product_platform=item["product_platform"],
                product_stock=item["product_stock"],
                quantity=quantity,
                selected=selected,
                subtotal=float(item["product_price"]) * quantity,
                created_at=item["created_at"],
                updated_at=item.get("updated_at"),
            )


# ============ 删除购物车项 ============

@router.delete("/{cart_item_id}")
async def delete_cart_item(
    cart_item_id: int,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """删除购物车项"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM cart_items WHERE id = %s AND user_id = %s",
                (cart_item_id, current_user.user_id)
            )
            await conn.commit()

            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="购物车项不存在")

            return {"message": "已从购物车移除"}


# ============ 清空购物车 ============

@router.delete("")
async def clear_cart(
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """清空购物车"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM cart_items WHERE user_id = %s",
                (current_user.user_id,)
            )
            await conn.commit()

            return {"message": f"已清空购物车，删除 {cur.rowcount} 件商品"}
