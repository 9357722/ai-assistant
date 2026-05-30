"""
电商 Agent 工具集
为 LangGraph Agent 提供电商相关的工具函数
"""
import json
from typing import Optional, List

import aiomysql
from langchain_core.tools import tool

import config


# 数据库连接池（全局变量，由 main.py 初始化）
_pool = None


async def init_pool():
    """初始化数据库连接池"""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_NAME,
            charset="utf8mb4",
            autocommit=True,
        )


async def close_pool():
    """关闭数据库连接池"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


@tool
async def search_products(keyword: str, limit: int = 5) -> str:
    """
    搜索商品

    Args:
        keyword: 搜索关键词
        limit: 返回数量限制

    Returns:
        商品列表 JSON 字符串
    """
    await init_pool()

    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT id, name, price, platform, stock, sales
                FROM products
                WHERE (name LIKE %s OR description LIKE %s)
                AND status = 'on_sale'
                ORDER BY sales DESC
                LIMIT %s
            """, (f"%{keyword}%", f"%{keyword}%", limit))

            products = await cur.fetchall()

            if not products:
                return json.dumps({"message": f"未找到与'{keyword}'相关的商品"}, ensure_ascii=False)

            result = {
                "keyword": keyword,
                "count": len(products),
                "products": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "price": float(p["price"]),
                        "platform": p["platform"],
                        "stock": p["stock"],
                        "sales": p["sales"],
                    }
                    for p in products
                ],
            }

            return json.dumps(result, ensure_ascii=False)


@tool
async def get_product_detail(product_id: int) -> str:
    """
    获取商品详情

    Args:
        product_id: 商品ID

    Returns:
        商品详情 JSON 字符串
    """
    await init_pool()

    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
            """, (product_id,))

            product = await cur.fetchone()

            if not product:
                return json.dumps({"error": "商品不存在"}, ensure_ascii=False)

            # 获取评价统计
            await cur.execute("""
                SELECT COUNT(*) as count, AVG(rating) as avg_rating
                FROM product_reviews
                WHERE product_id = %s
            """, (product_id,))
            review_stats = await cur.fetchone()

            result = {
                "id": product["id"],
                "name": product["name"],
                "price": float(product["price"]),
                "platform": product["platform"],
                "category": product.get("category_name"),
                "description": product.get("description"),
                "stock": product["stock"],
                "sales": product["sales"],
                "review_count": review_stats["count"],
                "avg_rating": round(float(review_stats["avg_rating"]), 1) if review_stats["avg_rating"] else None,
            }

            return json.dumps(result, ensure_ascii=False)


@tool
async def get_order_status(order_no: str, user_id: int) -> str:
    """
    查询订单状态

    Args:
        order_no: 订单号
        user_id: 用户ID

    Returns:
        订单状态 JSON 字符串
    """
    await init_pool()

    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT order_no, status, total_amount, created_at, paid_at, shipped_at
                FROM orders
                WHERE order_no = %s AND user_id = %s
            """, (order_no, user_id))

            order = await cur.fetchone()

            if not order:
                return json.dumps({"error": "订单不存在"}, ensure_ascii=False)

            status_map = {
                "pending": "待支付",
                "paid": "已支付",
                "shipped": "已发货",
                "completed": "已完成",
                "cancelled": "已取消",
            }

            result = {
                "order_no": order["order_no"],
                "status": status_map.get(order["status"], order["status"]),
                "amount": float(order["total_amount"]),
                "created_at": str(order["created_at"]),
                "paid_at": str(order["paid_at"]) if order["paid_at"] else None,
                "shipped_at": str(order["shipped_at"]) if order["shipped_at"] else None,
            }

            return json.dumps(result, ensure_ascii=False)


@tool
async def get_user_orders(user_id: int, limit: int = 5) -> str:
    """
    获取用户订单列表

    Args:
        user_id: 用户ID
        limit: 返回数量限制

    Returns:
        订单列表 JSON 字符串
    """
    await init_pool()

    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT order_no, status, total_amount, created_at
                FROM orders
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))

            orders = await cur.fetchall()

            status_map = {
                "pending": "待支付",
                "paid": "已支付",
                "shipped": "已发货",
                "completed": "已完成",
                "cancelled": "已取消",
            }

            result = {
                "count": len(orders),
                "orders": [
                    {
                        "order_no": o["order_no"],
                        "status": status_map.get(o["status"], o["status"]),
                        "amount": float(o["total_amount"]),
                        "created_at": str(o["created_at"]),
                    }
                    for o in orders
                ],
            }

            return json.dumps(result, ensure_ascii=False)


@tool
async def compare_products(product_ids: str) -> str:
    """
    对比多个商品

    Args:
        product_ids: 商品ID列表，用逗号分隔

    Returns:
        商品对比结果 JSON 字符串
    """
    await init_pool()

    ids = [int(id.strip()) for id in product_ids.split(",") if id.strip()]
    if len(ids) < 2:
        return json.dumps({"error": "至少需要2个商品进行对比"}, ensure_ascii=False)

    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            placeholders = ",".join(["%s"] * len(ids))
            await cur.execute(f"""
                SELECT p.id, p.name, p.price, p.platform, p.stock, p.sales,
                       c.name as category_name,
                       COALESCE(AVG(r.rating), 0) as avg_rating
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_reviews r ON p.id = r.product_id
                WHERE p.id IN ({placeholders})
                GROUP BY p.id
            """, ids)

            products = await cur.fetchall()

            if not products:
                return json.dumps({"error": "未找到商品"}, ensure_ascii=False)

            result = {
                "count": len(products),
                "products": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "price": float(p["price"]),
                        "platform": p["platform"],
                        "category": p.get("category_name"),
                        "stock": p["stock"],
                        "sales": p["sales"],
                        "avg_rating": round(float(p["avg_rating"]), 1) if p["avg_rating"] else None,
                    }
                    for p in products
                ],
            }

            return json.dumps(result, ensure_ascii=False)


@tool
async def get_hot_products(category: str = "", limit: int = 5) -> str:
    """
    获取热门商品

    Args:
        category: 商品分类（可选）
        limit: 返回数量限制

    Returns:
        热门商品列表 JSON 字符串
    """
    await init_pool()

    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if category:
                await cur.execute("""
                    SELECT p.id, p.name, p.price, p.platform, p.sales
                    FROM products p
                    JOIN categories c ON p.category_id = c.id
                    WHERE c.name LIKE %s AND p.status = 'on_sale'
                    ORDER BY p.sales DESC
                    LIMIT %s
                """, (f"%{category}%", limit))
            else:
                await cur.execute("""
                    SELECT id, name, price, platform, sales
                    FROM products
                    WHERE status = 'on_sale'
                    ORDER BY sales DESC
                    LIMIT %s
                """, (limit,))

            products = await cur.fetchall()

            result = {
                "category": category or "全部",
                "count": len(products),
                "products": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "price": float(p["price"]),
                        "platform": p["platform"],
                        "sales": p["sales"],
                    }
                    for p in products
                ],
            }

            return json.dumps(result, ensure_ascii=False)


# 导出所有工具
ecommerce_tools = [
    search_products,
    get_product_detail,
    get_order_status,
    get_user_orders,
    compare_products,
    get_hot_products,
]
