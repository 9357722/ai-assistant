"""
用户认证模块测试脚本
测试用户注册、登录、JWT Token 生成功能
"""
import asyncio
import aiomysql
from auth import get_password_hash, verify_password, create_access_token, decode_token
from models.user import UserCreate, UserLogin

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "108045",
    "db": "product_db",
    "charset": "utf8mb4",
}


async def test_user_registration():
    """测试用户注册"""
    print("\n=== 测试用户注册 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 测试数据
            test_user = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "test123456",
                "phone": "13800138000",
            }

            # 检查用户是否已存在
            await cur.execute("SELECT id FROM users WHERE username = %s", (test_user["username"],))
            existing = await cur.fetchone()

            if existing:
                print(f"用户 {test_user['username']} 已存在，跳过注册测试")
            else:
                # 创建用户
                hashed_password = get_password_hash(test_user["password"])
                await cur.execute(
                    "INSERT INTO users (username, email, hashed_password, phone) VALUES (%s, %s, %s, %s)",
                    (test_user["username"], test_user["email"], hashed_password, test_user["phone"])
                )
                await conn.commit()
                print(f"✓ 用户 {test_user['username']} 注册成功")

            # 验证密码哈希
            await cur.execute("SELECT hashed_password FROM users WHERE username = %s", (test_user["username"],))
            user = await cur.fetchone()
            is_valid = verify_password(test_user["password"], user["hashed_password"])
            print(f"✓ 密码验证: {'通过' if is_valid else '失败'}")

    pool.close()
    await pool.wait_closed()


async def test_jwt_token():
    """测试 JWT Token 生成和验证"""
    print("\n=== 测试 JWT Token ===")

    # 创建 Token
    token_data = {
        "user_id": 1,
        "username": "testuser",
        "role": "user",
    }
    token = create_access_token(token_data)
    print(f"✓ Token 生成成功: {token[:50]}...")

    # 验证 Token
    decoded = decode_token(token)
    print(f"✓ Token 解码成功: user_id={decoded.user_id}, username={decoded.username}, role={decoded.role}")


async def test_user_login():
    """测试用户登录流程"""
    print("\n=== 测试用户登录 ===")

    pool = await aiomysql.create_pool(**DB_CONFIG)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 模拟登录
            login_data = {"username": "testuser", "password": "test123456"}

            await cur.execute(
                "SELECT * FROM users WHERE username = %s",
                (login_data["username"],)
            )
            user = await cur.fetchone()

            if user and verify_password(login_data["password"], user["hashed_password"]):
                token = create_access_token({
                    "user_id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                })
                print(f"✓ 登录成功，Token: {token[:50]}...")
            else:
                print("✗ 登录失败")

    pool.close()
    await pool.wait_closed()


async def main():
    """运行所有测试"""
    print("开始测试用户认证模块...")

    await test_user_registration()
    await test_jwt_token()
    await test_user_login()

    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
