"""
AI 模块测试脚本
测试推荐引擎和 AI 客服功能
"""
import asyncio
import aiomysql
import json
from db_config import get_aiomysql_config

# 数据库配置
DB_CONFIG = get_aiomysql_config()


async def test_recommendation_engine():
    """测试推荐引擎"""
    print("\n=== 测试推荐引擎 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 测试1: 获取热门商品
            print("\n1. 获取热门商品:")
            await cur.execute("""
                SELECT id, name, price, platform, sales
                FROM products
                WHERE status = 'on_sale'
                ORDER BY sales DESC
                LIMIT 5
            """)
            hot_products = await cur.fetchall()
            for p in hot_products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']}, 销量: {p['sales']})")

            # 测试2: 基于预算的推荐
            print("\n2. 基于预算的推荐 (¥5000):")
            budget = 5000
            await cur.execute("""
                SELECT id, name, price, platform
                FROM products
                WHERE price <= %s AND status = 'on_sale'
                ORDER BY price DESC
                LIMIT 5
            """, (budget,))
            budget_products = await cur.fetchall()
            for p in budget_products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

            # 测试3: 基于分类的推荐
            print("\n3. 基于分类的推荐 (手机):")
            await cur.execute("""
                SELECT p.id, p.name, p.price, p.platform
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE c.name = '手机' AND p.status = 'on_sale'
                ORDER BY p.sales DESC
                LIMIT 5
            """)
            category_products = await cur.fetchall()
            for p in category_products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

            # 测试4: 相似商品推荐
            print("\n4. 相似商品推荐:")
            if hot_products:
                product = hot_products[0]
                print(f"  基于商品: {product['name']}")

                # 获取同分类商品
                await cur.execute("""
                    SELECT p2.id, p2.name, p2.price, p2.platform
                    FROM products p1
                    JOIN products p2 ON p1.category_id = p2.category_id
                    WHERE p1.id = %s AND p2.id != %s AND p2.status = 'on_sale'
                    ORDER BY p2.sales DESC
                    LIMIT 3
                """, (product["id"], product["id"]))
                similar_products = await cur.fetchall()
                for p in similar_products:
                    print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

    pool.close()
    await pool.wait_closed()


async def test_ai_customer_service():
    """测试 AI 客服"""
    print("\n=== 测试 AI 客服 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取测试用户
            await cur.execute("SELECT id FROM users WHERE username = 'testuser'")
            user = await cur.fetchone()
            if not user:
                print("  测试用户不存在")
                return
            user_id = user["id"]

            # 测试1: 获取用户上下文
            print("\n1. 获取用户上下文:")
            await cur.execute(
                "SELECT username, email FROM users WHERE id = %s",
                (user_id,)
            )
            user_info = await cur.fetchone()
            print(f"  用户: {user_info['username']}")

            # 获取最近订单
            await cur.execute("""
                SELECT order_no, status, total_amount
                FROM orders
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 3
            """, (user_id,))
            orders = await cur.fetchall()
            print(f"  最近订单: {len(orders)} 个")
            for o in orders:
                print(f"    - {o['order_no']}: {o['status']} - ¥{o['total_amount']}")

            # 获取购物车
            await cur.execute(
                "SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s",
                (user_id,)
            )
            cart_count = (await cur.fetchone())["count"]
            print(f"  购物车: {cart_count} 件商品")

            # 测试2: 模拟工具调用
            print("\n2. 模拟工具调用:")

            # 查询订单
            print("  查询订单:")
            status_map = {
                "pending": "待支付",
                "paid": "已支付",
                "shipped": "已发货",
                "completed": "已完成",
                "cancelled": "已取消",
            }
            if orders:
                for o in orders:
                    status = status_map.get(o["status"], o["status"])
                    print(f"    订单 {o['order_no']}: {status}")
            else:
                print("    无订单记录")

            # 查询商品
            print("  查询商品 (手机):")
            await cur.execute("""
                SELECT name, price, platform
                FROM products
                WHERE name LIKE '%手机%' AND status = 'on_sale'
                LIMIT 3
            """)
            products = await cur.fetchall()
            for p in products:
                print(f"    - {p['name']}: ¥{p['price']} ({p['platform']})")

            # 测试3: 快捷回复
            print("\n3. 快捷回复建议:")
            quick_replies = ["查看热门商品", "商品推荐"]

            # 检查待支付订单
            await cur.execute(
                "SELECT COUNT(*) as count FROM orders WHERE user_id = %s AND status = 'pending'",
                (user_id,)
            )
            has_pending = (await cur.fetchone())["count"] > 0
            if has_pending:
                quick_replies.insert(0, "查看待支付订单")

            # 检查购物车
            if cart_count > 0:
                quick_replies.insert(0, "查看购物车")

            for reply in quick_replies:
                print(f"  - {reply}")

    pool.close()
    await pool.wait_closed()


async def test_ecommerce_tools():
    """测试电商工具"""
    print("\n=== 测试电商工具 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 测试1: 搜索商品
            print("\n1. 搜索商品 (手机):")
            await cur.execute("""
                SELECT id, name, price, platform, stock, sales
                FROM products
                WHERE name LIKE '%手机%' AND status = 'on_sale'
                ORDER BY sales DESC
                LIMIT 5
            """)
            products = await cur.fetchall()
            for p in products:
                print(f"  - [{p['id']}] {p['name']}: ¥{p['price']} (库存: {p['stock']}, 销量: {p['sales']})")

            # 测试2: 获取商品详情
            print("\n2. 获取商品详情:")
            if products:
                product_id = products[0]["id"]
                await cur.execute("""
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.id = %s
                """, (product_id,))
                product = await cur.fetchone()
                if product:
                    print(f"  名称: {product['name']}")
                    print(f"  价格: ¥{product['price']}")
                    print(f"  平台: {product['platform']}")
                    print(f"  分类: {product.get('category_name', '未分类')}")
                    print(f"  库存: {product['stock']}")
                    print(f"  销量: {product['sales']}")

            # 测试3: 对比商品
            print("\n3. 对比商品:")
            if len(products) >= 2:
                ids = [products[0]["id"], products[1]["id"]]
                placeholders = ",".join(["%s"] * len(ids))
                await cur.execute(f"""
                    SELECT id, name, price, platform
                    FROM products
                    WHERE id IN ({placeholders})
                """, ids)
                compare_products = await cur.fetchall()
                for p in compare_products:
                    print(f"  - [{p['id']}] {p['name']}: ¥{p['price']} ({p['platform']})")

    pool.close()
    await pool.wait_closed()


async def main():
    """运行所有测试"""
    print("开始测试 AI 模块...")

    await test_recommendation_engine()
    await test_ai_customer_service()
    await test_ecommerce_tools()

    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
