"""
购物车和订单模块测试脚本
"""
import asyncio
import aiomysql
import json

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "108045",
    "db": "product_db",
    "charset": "utf8mb4",
}


async def test_cart_operations():
    """测试购物车操作"""
    print("\n=== 测试购物车操作 ===")

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

            # 获取测试商品
            await cur.execute("SELECT id, name, price FROM products WHERE status = 'on_sale' LIMIT 2")
            products = await cur.fetchall()
            if len(products) < 2:
                print("  商品不足")
                return

            product1 = products[0]
            product2 = products[1]

            # 测试1: 添加商品到购物车
            print("\n1. 添加商品到购物车:")
            for product in [product1, product2]:
                # 检查是否已在购物车
                await cur.execute(
                    "SELECT id, quantity FROM cart_items WHERE user_id = %s AND product_id = %s",
                    (user_id, product["id"])
                )
                existing = await cur.fetchone()

                if existing:
                    # 更新数量
                    new_qty = existing["quantity"] + 1
                    await cur.execute(
                        "UPDATE cart_items SET quantity = %s WHERE id = %s",
                        (new_qty, existing["id"])
                    )
                    print(f"  ✓ 更新 {product['name']} 数量为 {new_qty}")
                else:
                    # 新增
                    await cur.execute(
                        "INSERT INTO cart_items (user_id, product_id, quantity, selected) VALUES (%s, %s, 1, TRUE)",
                        (user_id, product["id"])
                    )
                    print(f"  ✓ 添加 {product['name']} 到购物车")

            await conn.commit()

            # 测试2: 查询购物车
            print("\n2. 查询购物车:")
            await cur.execute("""
                SELECT ci.*, p.name as product_name, p.price as product_price
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = %s
            """, (user_id,))
            cart_items = await cur.fetchall()

            total_amount = 0
            for item in cart_items:
                subtotal = float(item["product_price"]) * item["quantity"]
                total_amount += subtotal
                print(f"  - {item['product_name']}: ¥{item['product_price']} x {item['quantity']} = ¥{subtotal}")

            print(f"  总计: ¥{total_amount}")

            # 测试3: 更新购物车项（修改数量）
            print("\n3. 更新购物车项:")
            if cart_items:
                item = cart_items[0]
                new_quantity = 3
                await cur.execute(
                    "UPDATE cart_items SET quantity = %s WHERE id = %s",
                    (new_quantity, item["id"])
                )
                await conn.commit()
                print(f"  ✓ 更新 {item['product_name']} 数量为 {new_quantity}")

            # 测试4: 更新选中状态
            print("\n4. 更新选中状态:")
            if cart_items:
                item = cart_items[0]
                await cur.execute(
                    "UPDATE cart_items SET selected = FALSE WHERE id = %s",
                    (item["id"],)
                )
                await conn.commit()
                print(f"  ✓ 取消选中 {item['product_name']}")

            # 测试5: 删除购物车项
            print("\n5. 删除购物车项:")
            await cur.execute(
                "DELETE FROM cart_items WHERE user_id = %s AND product_id = %s",
                (user_id, product2["id"])
            )
            await conn.commit()
            print(f"  ✓ 删除 {product2['name']}")

    pool.close()
    await pool.wait_closed()


async def test_order_operations():
    """测试订单操作"""
    print("\n=== 测试订单操作 ===")

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

            # 获取测试地址
            await cur.execute("SELECT id FROM user_addresses WHERE user_id = %s LIMIT 1", (user_id,))
            address = await cur.fetchone()
            if not address:
                # 创建测试地址
                await cur.execute(
                    """INSERT INTO user_addresses (user_id, name, phone, province, city, district, detail, is_default)
                       VALUES (%s, '测试用户', '13800138000', '浙江省', '杭州市', '西湖区', '文三路123号', TRUE)""",
                    (user_id,)
                )
                await conn.commit()
                address_id = cur.lastrowid
                print(f"  ✓ 创建测试地址，ID: {address_id}")
            else:
                address_id = address["id"]

            # 获取购物车中选中的商品
            await cur.execute("""
                SELECT ci.*, p.name as product_name, p.main_image as product_image,
                       p.price as product_price, p.stock as product_stock
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = %s AND ci.selected = TRUE AND p.status = 'on_sale'
            """, (user_id,))
            cart_items = await cur.fetchall()

            if not cart_items:
                print("  购物车中没有选中的商品，跳过订单测试")
                return

            # 测试1: 创建订单
            print("\n1. 创建订单:")
            import time
            order_no = f"ORD{int(time.time() * 1000)}"

            # 计算总金额
            total_amount = sum(float(item["product_price"]) * item["quantity"] for item in cart_items)

            # 地址快照
            await cur.execute("SELECT * FROM user_addresses WHERE id = %s", (address_id,))
            address_data = await cur.fetchone()
            address_snapshot = json.dumps({
                "name": address_data["name"],
                "phone": address_data["phone"],
                "province": address_data["province"],
                "city": address_data["city"],
                "district": address_data["district"],
                "detail": address_data["detail"],
            }, ensure_ascii=False)

            # 创建订单
            await cur.execute(
                """INSERT INTO orders (order_no, user_id, total_amount, pay_amount, status, address_snapshot)
                   VALUES (%s, %s, %s, %s, 'pending', %s)""",
                (order_no, user_id, total_amount, total_amount, address_snapshot)
            )
            order_id = cur.lastrowid

            # 创建订单项
            for item in cart_items:
                await cur.execute(
                    """INSERT INTO order_items (order_id, product_id, product_name, product_image, price, quantity)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (order_id, item["product_id"], item["product_name"], item["product_image"],
                     item["product_price"], item["quantity"])
                )

                # 扣减库存
                await cur.execute(
                    "UPDATE products SET stock = stock - %s, sales = sales + %s WHERE id = %s",
                    (item["quantity"], item["quantity"], item["product_id"])
                )

            # 清理购物车
            await cur.execute(
                "DELETE FROM cart_items WHERE user_id = %s AND selected = TRUE",
                (user_id,)
            )

            await conn.commit()
            print(f"  ✓ 订单创建成功，订单号: {order_no}")
            print(f"  ✓ 订单金额: ¥{total_amount}")

            # 测试2: 查询订单详情
            print("\n2. 查询订单详情:")
            await cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = await cur.fetchone()
            print(f"  订单号: {order['order_no']}")
            print(f"  状态: {order['status']}")
            print(f"  金额: ¥{order['total_amount']}")

            await cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
            items = await cur.fetchall()
            print(f"  商品数: {len(items)}")
            for item in items:
                print(f"    - {item['product_name']}: ¥{item['price']} x {item['quantity']}")

            # 测试3: 模拟支付
            print("\n3. 模拟支付:")
            await cur.execute(
                "UPDATE orders SET status = 'paid', paid_at = NOW() WHERE id = %s",
                (order_id,)
            )
            await conn.commit()
            print(f"  ✓ 订单已支付")

            # 测试4: 模拟发货
            print("\n4. 模拟发货:")
            await cur.execute(
                "UPDATE orders SET status = 'shipped', shipped_at = NOW() WHERE id = %s",
                (order_id,)
            )
            await conn.commit()
            print(f"  ✓ 订单已发货")

            # 测试5: 确认收货
            print("\n5. 确认收货:")
            await cur.execute(
                "UPDATE orders SET status = 'completed', completed_at = NOW() WHERE id = %s",
                (order_id,)
            )
            await conn.commit()
            print(f"  ✓ 订单已完成")

            # 测试6: 查询订单列表
            print("\n6. 查询订单列表:")
            await cur.execute(
                "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 5",
                (user_id,)
            )
            orders = await cur.fetchall()
            for o in orders:
                print(f"  - {o['order_no']}: {o['status']} - ¥{o['total_amount']}")

    pool.close()
    await pool.wait_closed()


async def test_cancel_order():
    """测试取消订单"""
    print("\n=== 测试取消订单 ===")

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

            # 创建一个待支付的测试订单
            import time
            order_no = f"ORD{int(time.time() * 1000)}"

            await cur.execute(
                """INSERT INTO orders (order_no, user_id, total_amount, pay_amount, status)
                   VALUES (%s, %s, 100.00, 100.00, 'pending')""",
                (order_no, user_id)
            )
            order_id = cur.lastrowid
            print(f"  创建测试订单: {order_no}")

            # 取消订单
            await cur.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = %s AND status = 'pending'",
                (order_id,)
            )
            await conn.commit()
            print(f"  ✓ 订单已取消")

            # 验证状态
            await cur.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
            order = await cur.fetchone()
            print(f"  订单状态: {order['status']}")

    pool.close()
    await pool.wait_closed()


async def main():
    """运行所有测试"""
    print("开始测试购物车和订单模块...")

    await test_cart_operations()
    await test_order_operations()
    await test_cancel_order()

    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
