"""
管理后台和支付模块测试脚本
"""
import asyncio
import aiomysql
import json
from datetime import datetime
from db_config import get_aiomysql_config

# 数据库配置
DB_CONFIG = get_aiomysql_config()


async def test_statistics():
    """测试数据统计"""
    print("\n=== 测试数据统计 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 用户统计
            await cur.execute("SELECT COUNT(*) as total FROM users")
            total_users = (await cur.fetchone())["total"]

            await cur.execute("SELECT COUNT(*) as total FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
            new_users_week = (await cur.fetchone())["total"]

            print(f"  用户总数: {total_users}")
            print(f"  本周新增: {new_users_week}")

            # 商品统计
            await cur.execute("SELECT COUNT(*) as total FROM products WHERE status = 'on_sale'")
            total_products = (await cur.fetchone())["total"]
            print(f"  在售商品: {total_products}")

            # 订单统计
            await cur.execute("SELECT COUNT(*) as total FROM orders")
            total_orders = (await cur.fetchone())["total"]

            await cur.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'pending'")
            pending_orders = (await cur.fetchone())["total"]

            await cur.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'paid'")
            paid_orders = (await cur.fetchone())["total"]

            print(f"  订单总数: {total_orders}")
            print(f"  待支付: {pending_orders}")
            print(f"  已支付: {paid_orders}")

            # 销售额统计
            await cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM orders
                WHERE status IN ('paid', 'shipped', 'completed')
            """)
            total_sales = float((await cur.fetchone())["total"])

            await cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM orders
                WHERE status IN ('paid', 'shipped', 'completed')
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            sales_week = float((await cur.fetchone())["total"])

            print(f"  总销售额: ¥{total_sales}")
            print(f"  本周销售: ¥{sales_week}")

    pool.close()
    await pool.wait_closed()


async def test_product_management():
    """测试商品管理"""
    print("\n=== 测试商品管理 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查询商品列表
            print("\n1. 查询商品列表:")
            await cur.execute("""
                SELECT p.id, p.name, p.price, p.platform, p.stock, p.status, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.created_at DESC
                LIMIT 10
            """)
            products = await cur.fetchall()
            for p in products:
                status = "在售" if p["status"] == "on_sale" else "下架"
                print(f"  [{p['id']}] {p['name']}: ¥{p['price']} ({p['platform']}, {status})")

            # 创建商品
            print("\n2. 创建商品:")
            test_product = {
                "name": "管理后台测试商品",
                "price": 999.00,
                "platform": "京东",
                "category_id": 1,
                "description": "管理后台创建的测试商品",
                "stock": 50,
                "status": "on_sale",
            }

            await cur.execute(
                """INSERT INTO products (name, price, platform, category_id, description, stock, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (test_product["name"], test_product["price"], test_product["platform"],
                 test_product["category_id"], test_product["description"],
                 test_product["stock"], test_product["status"])
            )
            await conn.commit()
            product_id = cur.lastrowid
            print(f"  ✓ 商品创建成功，ID: {product_id}")

            # 更新商品
            print("\n3. 更新商品:")
            new_price = 899.00
            await cur.execute(
                "UPDATE products SET price = %s WHERE id = %s",
                (new_price, product_id)
            )
            await conn.commit()
            print(f"  ✓ 价格更新为: ¥{new_price}")

            # 下架商品
            print("\n4. 下架商品:")
            await cur.execute(
                "UPDATE products SET status = 'off_sale' WHERE id = %s",
                (product_id,)
            )
            await conn.commit()
            print(f"  ✓ 商品已下架")

            # 删除测试商品
            await cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            await conn.commit()
            print(f"  ✓ 测试商品已删除")

    pool.close()
    await pool.wait_closed()


async def test_order_management():
    """测试订单管理"""
    print("\n=== 测试订单管理 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查询订单列表
            print("\n1. 查询订单列表:")
            await cur.execute("""
                SELECT o.*, u.username
                FROM orders o
                JOIN users u ON o.user_id = u.id
                ORDER BY o.created_at DESC
                LIMIT 5
            """)
            orders = await cur.fetchall()

            status_map = {
                "pending": "待支付",
                "paid": "已支付",
                "shipped": "已发货",
                "completed": "已完成",
                "cancelled": "已取消",
            }

            for o in orders:
                status = status_map.get(o["status"], o["status"])
                print(f"  [{o['id']}] {o['order_no']}: {status} - ¥{o['total_amount']} ({o['username']})")

            # 测试订单状态更新
            print("\n2. 测试订单状态更新:")
            # 找一个已支付的订单
            await cur.execute(
                "SELECT id, order_no, status FROM orders WHERE status = 'paid' LIMIT 1"
            )
            paid_order = await cur.fetchone()

            if paid_order:
                print(f"  找到已支付订单: {paid_order['order_no']}")

                # 更新为已发货
                await cur.execute(
                    "UPDATE orders SET status = 'shipped', shipped_at = NOW() WHERE id = %s",
                    (paid_order["id"],)
                )
                await conn.commit()
                print(f"  ✓ 订单状态更新为: 已发货")

                # 更新为已完成
                await cur.execute(
                    "UPDATE orders SET status = 'completed', completed_at = NOW() WHERE id = %s",
                    (paid_order["id"],)
                )
                await conn.commit()
                print(f"  ✓ 订单状态更新为: 已完成")
            else:
                print("  没有已支付的订单")

    pool.close()
    await pool.wait_closed()


async def test_user_management():
    """测试用户管理"""
    print("\n=== 测试用户管理 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查询用户列表
            print("\n1. 查询用户列表:")
            await cur.execute("""
                SELECT id, username, email, role, is_active, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT 10
            """)
            users = await cur.fetchall()

            for u in users:
                status = "启用" if u["is_active"] else "禁用"
                print(f"  [{u['id']}] {u['username']}: {u['email']} ({u['role']}, {status})")

            # 测试用户状态更新
            print("\n2. 测试用户状态更新:")
            await cur.execute("SELECT id, username FROM users WHERE role = 'user' LIMIT 1")
            test_user = await cur.fetchone()

            if test_user:
                print(f"  测试用户: {test_user['username']}")

                # 禁用用户
                await cur.execute(
                    "UPDATE users SET is_active = FALSE WHERE id = %s",
                    (test_user["id"],)
                )
                await conn.commit()
                print(f"  ✓ 用户已禁用")

                # 启用用户
                await cur.execute(
                    "UPDATE users SET is_active = TRUE WHERE id = %s",
                    (test_user["id"],)
                )
                await conn.commit()
                print(f"  ✓ 用户已启用")
            else:
                print("  没有普通用户")

    pool.close()
    await pool.wait_closed()


async def test_category_management():
    """测试分类管理"""
    print("\n=== 测试分类管理 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查询分类列表
            print("\n1. 查询分类列表:")
            await cur.execute("SELECT * FROM categories ORDER BY sort_order, id")
            categories = await cur.fetchall()

            for c in categories:
                parent = f" (父ID: {c['parent_id']})" if c["parent_id"] else ""
                print(f"  [{c['id']}] {c['name']}{parent}")

            # 创建分类
            print("\n2. 创建分类:")
            await cur.execute(
                "INSERT INTO categories (name, sort_order) VALUES ('测试分类', 99)",
            )
            await conn.commit()
            category_id = cur.lastrowid
            print(f"  ✓ 分类创建成功，ID: {category_id}")

            # 删除测试分类
            await cur.execute("DELETE FROM categories WHERE id = %s", (category_id,))
            await conn.commit()
            print(f"  ✓ 测试分类已删除")

    pool.close()
    await pool.wait_closed()


async def test_payment_simulation():
    """测试支付模拟"""
    print("\n=== 测试支付模拟 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 创建测试订单
            import time
            order_no = f"ORD{int(time.time() * 1000)}"

            await cur.execute(
                """INSERT INTO orders (order_no, user_id, total_amount, pay_amount, status)
                   VALUES (%s, 1, 100.00, 100.00, 'pending')""",
                (order_no,)
            )
            order_id = cur.lastrowid
            print(f"  创建测试订单: {order_no}")

            # 模拟支付
            print("\n  模拟支付:")
            payment_no = f"PAY{int(time.time() * 1000)}"

            # 更新订单状态
            await cur.execute(
                "UPDATE orders SET status = 'paid', paid_at = NOW() WHERE id = %s",
                (order_id,)
            )
            await conn.commit()
            print(f"  ✓ 支付成功，支付单号: {payment_no}")

            # 查询支付状态
            print("\n  查询支付状态:")
            await cur.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
            order = await cur.fetchone()
            print(f"  订单状态: {order['status']}")

            # 模拟退款
            print("\n  模拟退款:")
            refund_no = f"REF{int(time.time() * 1000)}"

            await cur.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = %s",
                (order_id,)
            )
            await conn.commit()
            print(f"  ✓ 退款成功，退款单号: {refund_no}")

            # 清理测试数据
            await cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            await conn.commit()
            print(f"  ✓ 测试订单已删除")

    pool.close()
    await pool.wait_closed()


async def main():
    """运行所有测试"""
    print("开始测试管理后台和支付模块...")

    await test_statistics()
    await test_product_management()
    await test_order_management()
    await test_user_management()
    await test_category_management()
    await test_payment_simulation()

    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
