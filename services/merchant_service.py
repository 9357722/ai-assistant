# -*- coding: utf-8 -*-
"""
商家服务层
处理商家相关的业务逻辑
"""
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

import aiomysql


class MerchantService:
    """商家服务"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool

    # ================================================================
    # 商家信息管理
    # ================================================================

    async def get_merchant_by_user_id(self, user_id: int) -> Optional[Dict]:
        """根据用户ID获取商家信息"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM merchants WHERE user_id = %s
                """, (user_id,))
                return await cur.fetchone()

    async def create_merchant(self, user_id: int, shop_name: str, **kwargs) -> int:
        """创建商家"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO merchants (user_id, shop_name, shop_description, contact_phone, contact_email, address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    shop_name,
                    kwargs.get('shop_description', ''),
                    kwargs.get('contact_phone', ''),
                    kwargs.get('contact_email', ''),
                    kwargs.get('address', '')
                ))
                await conn.commit()
                return cur.lastrowid

    async def update_merchant(self, merchant_id: int, **kwargs) -> bool:
        """更新商家信息"""
        allowed_fields = ['shop_name', 'shop_description', 'shop_logo', 'contact_phone', 'contact_email', 'address']
        updates = []
        params = []
        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = %s")
                params.append(kwargs[field])
        if not updates:
            return False
        params.append(merchant_id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"""
                    UPDATE merchants SET {', '.join(updates)} WHERE id = %s
                """, params)
                await conn.commit()
                return cur.rowcount > 0

    # ================================================================
    # 商家商品管理
    # ================================================================

    async def get_merchant_products(self, merchant_id: int, page: int = 1, page_size: int = 20) -> Dict:
        """获取商家的商品列表"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取总数
                await cur.execute("""
                    SELECT COUNT(*) as total
                    FROM merchant_products mp
                    JOIN products p ON mp.product_id = p.id
                    WHERE mp.merchant_id = %s
                """, (merchant_id,))
                total = (await cur.fetchone())['total']

                # 获取商品列表
                offset = (page - 1) * page_size
                await cur.execute("""
                    SELECT p.*, c.name as category_name
                    FROM merchant_products mp
                    JOIN products p ON mp.product_id = p.id
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE mp.merchant_id = %s
                    ORDER BY p.created_at DESC
                    LIMIT %s OFFSET %s
                """, (merchant_id, page_size, offset))
                items = await cur.fetchall()

                # 转换 datetime 为字符串
                for item in items:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].isoformat()
                    if item.get('updated_at'):
                        item['updated_at'] = item['updated_at'].isoformat()

                return {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'items': items
                }

    async def add_product_to_merchant(self, merchant_id: int, product_data: Dict) -> int:
        """商家添加商品"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 插入商品
                await cur.execute("""
                    INSERT INTO products (name, price, category_id, description, main_image, stock, platform, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'on_sale')
                """, (
                    product_data['name'],
                    product_data['price'],
                    product_data.get('category_id'),
                    product_data.get('description', ''),
                    product_data.get('main_image', ''),
                    product_data.get('stock', 100),
                    product_data.get('platform', '自营')
                ))
                product_id = cur.lastrowid

                # 关联商家
                await cur.execute("""
                    INSERT INTO merchant_products (merchant_id, product_id)
                    VALUES (%s, %s)
                """, (merchant_id, product_id))

                await conn.commit()
                return product_id

    async def update_merchant_product(self, merchant_id: int, product_id: int, **kwargs) -> bool:
        """更新商家商品"""
        # 先验证商品归属
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id FROM merchant_products
                    WHERE merchant_id = %s AND product_id = %s
                """, (merchant_id, product_id))
                if not await cur.fetchone():
                    return False

                # 更新商品
                allowed_fields = ['name', 'price', 'category_id', 'description', 'main_image', 'stock', 'status']
                updates = []
                params = []
                for field in allowed_fields:
                    if field in kwargs:
                        updates.append(f"{field} = %s")
                        params.append(kwargs[field])
                if not updates:
                    return False
                params.append(product_id)

                await cur.execute(f"""
                    UPDATE products SET {', '.join(updates)} WHERE id = %s
                """, params)
                await conn.commit()
                return cur.rowcount > 0

    async def delete_merchant_product(self, merchant_id: int, product_id: int) -> bool:
        """删除商家商品"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 验证商品归属
                await cur.execute("""
                    SELECT id FROM merchant_products
                    WHERE merchant_id = %s AND product_id = %s
                """, (merchant_id, product_id))
                if not await cur.fetchone():
                    return False

                # 删除关联
                await cur.execute("""
                    DELETE FROM merchant_products WHERE merchant_id = %s AND product_id = %s
                """, (merchant_id, product_id))
                await conn.commit()
                return True

    # ================================================================
    # 订单管理
    # ================================================================

    # 订单状态机：定义合法的状态转换
    ORDER_STATUS_TRANSITIONS = {
        'pending': ['paid', 'cancelled'],      # 待付款 -> 已付款/已取消
        'paid': ['shipped', 'cancelled'],      # 已付款 -> 已发货/已取消
        'shipped': ['completed', 'returned'],  # 已发货 -> 已完成/已退货
        'completed': [],                       # 已完成 - 终态
        'cancelled': [],                       # 已取消 - 终态
        'returned': [],                        # 已退货 - 终态
    }

    async def get_merchant_orders(self, merchant_id: int, status: Optional[str] = None,
                                   page: int = 1, page_size: int = 20) -> Dict:
        """获取商家订单"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 构建查询
                where_conditions = ["oi.product_id IN (SELECT product_id FROM merchant_products WHERE merchant_id = %s)"]
                params = [merchant_id]

                if status:
                    where_conditions.append("o.status = %s")
                    params.append(status)

                where_clause = " AND ".join(where_conditions)

                # 获取总数
                await cur.execute(f"""
                    SELECT COUNT(DISTINCT o.id) as total
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    WHERE {where_clause}
                """, params)
                total = (await cur.fetchone())['total']

                # 获取订单列表（脱敏：只显示用户名前2位+***）
                offset = (page - 1) * page_size
                await cur.execute(f"""
                    SELECT DISTINCT o.*,
                           CONCAT(LEFT(u.username, 2), '***') as buyer_name
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    LEFT JOIN users u ON o.user_id = u.id
                    WHERE {where_clause}
                    ORDER BY o.created_at DESC
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                items = await cur.fetchall()

                # 转换 datetime
                for item in items:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].isoformat()

                return {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'items': items
                }

    async def update_order_status(self, merchant_id: int, order_id: int, new_status: str) -> tuple[bool, str]:
        """更新订单状态（带状态机校验）
        返回: (成功, 消息)
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取当前订单状态
                await cur.execute("""
                    SELECT o.id, o.status FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE o.id = %s AND mp.merchant_id = %s
                    LIMIT 1
                """, (order_id, merchant_id))
                order = await cur.fetchone()
                if not order:
                    return False, "订单不存在或无权操作"

                current_status = order['status']

                # 状态机校验
                allowed_transitions = self.ORDER_STATUS_TRANSITIONS.get(current_status, [])
                if new_status not in allowed_transitions:
                    return False, f"不允许从 {current_status} 转换到 {new_status}"

                # 更新状态
                await cur.execute("""
                    UPDATE orders SET status = %s WHERE id = %s
                """, (new_status, order_id))
                await conn.commit()
                return cur.rowcount > 0, "状态更新成功"

    # ================================================================
    # 数据统计
    # ================================================================

    async def get_dashboard_stats(self, merchant_id: int) -> Dict:
        """获取商家后台概览数据"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 商品数量
                await cur.execute("""
                    SELECT COUNT(*) as total_products
                    FROM merchant_products WHERE merchant_id = %s
                """, (merchant_id,))
                products = (await cur.fetchone())['total_products']

                # 今日订单和销售额
                await cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as today_orders,
                           COALESCE(SUM(oi.quantity * oi.price), 0) as today_sales
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s
                      AND DATE(o.created_at) = CURDATE()
                """, (merchant_id,))
                today = await cur.fetchone()

                # 待发货订单
                await cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as pending_orders
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s AND o.status = 'pending'
                """, (merchant_id,))
                pending = (await cur.fetchone())['pending_orders']

                return {
                    'total_products': products,
                    'today_orders': today['today_orders'],
                    'today_sales': float(today['today_sales']),
                    'pending_orders': pending
                }

    # ================================================================
    # 优惠券管理
    # ================================================================

    async def get_merchant_coupons(self, merchant_id: int) -> List[Dict]:
        """获取商家优惠券列表"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM coupons
                    WHERE merchant_id = %s
                    ORDER BY created_at DESC
                """, (merchant_id,))
                items = await cur.fetchall()
                for item in items:
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].isoformat()
                    if item.get('start_date'):
                        item['start_date'] = item['start_date'].isoformat()
                    if item.get('end_date'):
                        item['end_date'] = item['end_date'].isoformat()
                return items

    async def create_coupon(self, merchant_id: int, coupon_data: Dict) -> int:
        """创建优惠券"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO coupons (merchant_id, name, type, value, min_amount, max_uses, start_date, end_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    merchant_id,
                    coupon_data['name'],
                    coupon_data['type'],
                    coupon_data['value'],
                    coupon_data.get('min_amount', 0),
                    coupon_data.get('max_uses', 0),
                    coupon_data.get('start_date'),
                    coupon_data.get('end_date')
                ))
                await conn.commit()
                return cur.lastrowid
