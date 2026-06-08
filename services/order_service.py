# -*- coding: utf-8 -*-
"""
订单服务层
处理订单创建、支付、取消等核心业务逻辑
"""
import logging
import uuid
from typing import List, Optional, Dict, Any

import aiomysql

logger = logging.getLogger(__name__)


def generate_order_no() -> str:
    """生成订单号（UUID，不可预测）"""
    return f"ORD{uuid.uuid4().hex[:16].upper()}"


async def create_order_from_cart(
    conn: aiomysql.Connection,
    user_id: int,
    cart_item_ids: Optional[List[int]],
    address_id: int,
    remark: Optional[str],
    idempotency_key: Optional[str],
) -> Dict[str, Any]:
    """
    从购物车创建订单

    Args:
        conn: 数据库连接（已在事务中）
        user_id: 用户ID
        cart_item_ids: 购物车项ID列表（None则使用选中的商品）
        address_id: 收货地址ID
        remark: 订单备注
        idempotency_key: 幂等键

    Returns:
        订单信息字典
    """
    async with conn.cursor(aiomysql.DictCursor) as cur:
        # 幂等性校验
        if idempotency_key:
            await cur.execute(
                "SELECT id, order_no FROM orders WHERE idempotency_key = %s AND user_id = %s",
                (idempotency_key, user_id)
            )
            existing_order = await cur.fetchone()
            if existing_order:
                raise ValueError(f"订单已存在: {existing_order['order_no']}")

        # 获取收货地址
        await cur.execute(
            "SELECT * FROM user_addresses WHERE id = %s AND user_id = %s",
            (address_id, user_id)
        )
        address = await cur.fetchone()
        if not address:
            raise ValueError("收货地址不存在")

        # 获取购物车项
        if cart_item_ids:
            placeholders = ",".join(["%s"] * len(cart_item_ids))
            sql = f"""
                SELECT ci.*, p.name as product_name, p.main_image as product_image,
                       p.price as product_price, p.stock as product_stock
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.id IN ({placeholders}) AND ci.user_id = %s AND p.status = 'on_sale'
            """
            params = cart_item_ids + [user_id]
        else:
            sql = """
                SELECT ci.*, p.name as product_name, p.main_image as product_image,
                       p.price as product_price, p.stock as product_stock
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = %s AND ci.selected = TRUE AND p.status = 'on_sale'
            """
            params = [user_id]

        await cur.execute(sql, params)
        cart_items = await cur.fetchall()

        if not cart_items:
            raise ValueError("没有选中的商品")

        # 锁定商品行，防止并发扣减
        product_ids = [item["product_id"] for item in cart_items]
        placeholders = ",".join(["%s"] * len(product_ids))
        await cur.execute(
            f"SELECT id, stock FROM products WHERE id IN ({placeholders}) FOR UPDATE",
            product_ids
        )

        # 验证库存
        for item in cart_items:
            if item["product_stock"] < item["quantity"]:
                raise ValueError(f"商品 '{item['product_name']}' 库存不足")

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
            (order_no, user_id, total_amount, total_amount,
             json.dumps(address_snapshot, ensure_ascii=False), remark, idempotency_key)
        )
        order_id = cur.lastrowid

        # 创建订单项
        order_items = []
        for item in cart_items:
            await cur.execute(
                """INSERT INTO order_items (order_id, product_id, product_name, product_image, price, quantity)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (order_id, item["product_id"], item["product_name"],
                 item["product_image"], item["product_price"], item["quantity"])
            )
            order_items.append({
                "id": cur.lastrowid,
                "order_id": order_id,
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "product_image": item["product_image"],
                "price": float(item["product_price"]),
                "quantity": item["quantity"],
                "subtotal": float(item["product_price"]) * item["quantity"],
            })

            # 扣减库存
            await cur.execute(
                "UPDATE products SET stock = stock - %s, sales = sales + %s WHERE id = %s",
                (item["quantity"], item["quantity"], item["product_id"])
            )

        # 清理购物车
        cart_ids = [item["id"] for item in cart_items]
        placeholders = ",".join(["%s"] * len(cart_ids))
        await cur.execute(
            f"DELETE FROM cart_items WHERE id IN ({placeholders}) AND user_id = %s",
            cart_ids + [user_id]
        )

        logger.info(f"Order created: order_no={order_no}, user_id={user_id}, amount={total_amount}, items={len(order_items)}")

        return {
            "id": order_id,
            "order_no": order_no,
            "user_id": user_id,
            "total_amount": total_amount,
            "pay_amount": total_amount,
            "status": "pending",
            "address_snapshot": address_snapshot,
            "remark": remark,
            "items": order_items,
        }


import json
