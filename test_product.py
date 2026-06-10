"""
商品模块测试脚本
测试商品查询、创建、更新、删除、评价等功能
"""
import asyncio
import aiomysql
import json
from db_config import get_aiomysql_config

# 数据库配置
DB_CONFIG = get_aiomysql_config()


async def test_product_operations():
    """测试商品操作"""
    print("\n=== 测试商品操作 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 测试1: 查询商品列表
            print("\n1. 查询商品列表:")
            await cur.execute("""
                SELECT p.*, c.name as category_name,
                       COALESCE(AVG(r.rating), 0) as rating,
                       COUNT(DISTINCT r.id) as review_count
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_reviews r ON p.id = r.product_id
                WHERE p.status = 'on_sale'
                GROUP BY p.id
                LIMIT 5
            """)
            products = await cur.fetchall()
            for p in products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

            # 测试2: 查询分类列表
            print("\n2. 查询分类列表:")
            await cur.execute("SELECT * FROM categories ORDER BY sort_order")
            categories = await cur.fetchall()
            for c in categories:
                print(f"  - {c['name']} (ID: {c['id']})")

            # 测试3: 创建新商品（模拟管理员操作）
            print("\n3. 创建新商品:")
            test_product = {
                "name": "测试商品-蓝牙音箱",
                "price": 299.00,
                "platform": "京东",
                "category_id": 2,  # 耳机分类
                "description": "高品质蓝牙音箱，支持蓝牙5.0",
                "stock": 100,
                "status": "on_sale",
            }

            # 检查是否已存在
            await cur.execute("SELECT id FROM products WHERE name = %s", (test_product["name"],))
            existing = await cur.fetchone()

            if existing:
                print(f"  商品 '{test_product['name']}' 已存在，ID: {existing['id']}")
                product_id = existing["id"]
            else:
                await cur.execute(
                    """INSERT INTO products (name, price, platform, category_id, description, stock, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        test_product["name"],
                        test_product["price"],
                        test_product["platform"],
                        test_product["category_id"],
                        test_product["description"],
                        test_product["stock"],
                        test_product["status"],
                    )
                )
                await conn.commit()
                product_id = cur.lastrowid
                print(f"  ✓ 商品创建成功，ID: {product_id}")

            # 测试4: 更新商品价格
            print("\n4. 更新商品价格:")
            new_price = 259.00
            await cur.execute(
                "UPDATE products SET price = %s WHERE id = %s",
                (new_price, product_id)
            )
            await conn.commit()
            print(f"  ✓ 价格更新为: ¥{new_price}")

            # 测试5: 查询商品详情
            print("\n5. 查询商品详情:")
            await cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            product = await cur.fetchone()
            if product:
                print(f"  名称: {product['name']}")
                print(f"  价格: ¥{product['price']}")
                print(f"  平台: {product['platform']}")
                print(f"  库存: {product['stock']}")
                print(f"  状态: {product['status']}")

    pool.close()
    await pool.wait_closed()


async def test_review_operations():
    """测试评价操作"""
    print("\n=== 测试评价操作 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取测试用户
            await cur.execute("SELECT id FROM users WHERE username = 'testuser'")
            user = await cur.fetchone()
            if not user:
                print("  测试用户不存在，跳过评价测试")
                return
            user_id = user["id"]

            # 获取测试商品
            await cur.execute("SELECT id FROM products LIMIT 1")
            product = await cur.fetchone()
            if not product:
                print("  没有商品，跳过评价测试")
                return
            product_id = product["id"]

            # 测试1: 创建评价
            print("\n1. 创建评价:")
            test_review = {
                "product_id": product_id,
                "user_id": user_id,
                "rating": 5,
                "content": "非常好的商品，质量很棒！",
                "images": json.dumps(["http://example.com/img1.jpg"]),
            }

            # 检查是否已评价
            await cur.execute(
                "SELECT id FROM product_reviews WHERE product_id = %s AND user_id = %s",
                (product_id, user_id)
            )
            existing = await cur.fetchone()

            if existing:
                print(f"  用户已评价过该商品，评价ID: {existing['id']}")
            else:
                await cur.execute(
                    "INSERT INTO product_reviews (product_id, user_id, rating, content, images) VALUES (%s, %s, %s, %s, %s)",
                    (test_review["product_id"], test_review["user_id"], test_review["rating"],
                     test_review["content"], test_review["images"])
                )
                await conn.commit()
                print(f"  ✓ 评价创建成功，ID: {cur.lastrowid}")

            # 测试2: 查询商品评价
            print("\n2. 查询商品评价:")
            await cur.execute("""
                SELECT r.*, u.username
                FROM product_reviews r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE r.product_id = %s
                ORDER BY r.created_at DESC
                LIMIT 5
            """, (product_id,))
            reviews = await cur.fetchall()
            for r in reviews:
                print(f"  - {r['username']}: {'★' * r['rating']} - {r['content']}")

            # 测试3: 查询商品平均评分
            print("\n3. 查询商品平均评分:")
            await cur.execute(
                "SELECT AVG(rating) as avg_rating, COUNT(*) as count FROM product_reviews WHERE product_id = %s",
                (product_id,)
            )
            stats = await cur.fetchone()
            avg_rating = round(float(stats["avg_rating"]), 1) if stats["avg_rating"] else 0
            print(f"  平均评分: {avg_rating} ({stats['count']}条评价)")

    pool.close()
    await pool.wait_closed()


async def test_search_operations():
    """测试搜索操作"""
    print("\n=== 测试搜索操作 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 测试1: 关键词搜索
            print("\n1. 关键词搜索 '手机':")
            await cur.execute(
                "SELECT * FROM products WHERE name LIKE %s AND status = 'on_sale' LIMIT 5",
                ("%手机%",)
            )
            products = await cur.fetchall()
            for p in products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

            # 测试2: 价格区间搜索
            print("\n2. 价格区间搜索 (1000-5000):")
            await cur.execute(
                "SELECT * FROM products WHERE price BETWEEN %s AND %s AND status = 'on_sale' LIMIT 5",
                (1000, 5000)
            )
            products = await cur.fetchall()
            for p in products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

            # 测试3: 分类搜索
            print("\n3. 分类搜索 (手机):")
            await cur.execute("""
                SELECT p.* FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE c.name = '手机' AND p.status = 'on_sale'
                LIMIT 5
            """)
            products = await cur.fetchall()
            for p in products:
                print(f"  - {p['name']}: ¥{p['price']} ({p['platform']})")

    pool.close()
    await pool.wait_closed()


async def main():
    """运行所有测试"""
    print("开始测试商品模块...")

    await test_product_operations()
    await test_review_operations()
    await test_search_operations()

    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
