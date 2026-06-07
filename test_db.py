# -*- coding: utf-8 -*-
"""快速测试 DB 连接和用户登录接口"""
import asyncio
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

import config

async def test_db():
    print(f"DB_HOST: {config.DB_HOST}")
    print(f"DB_PORT: {config.DB_PORT}")
    print(f"DB_USER: {config.DB_USER}")
    print(f"DB_PASSWORD: {'***' if config.DB_PASSWORD else '(empty!)'}")
    print(f"DB_NAME: {config.DB_NAME}")

    import aiomysql
    try:
        pool = await aiomysql.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_NAME,
            charset="utf8mb4",
        )
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM users")
                row = await cur.fetchone()
                print(f"DB OK - users count: {row[0]}")
        pool.close()
        await pool.wait_closed()
    except Exception as e:
        print(f"DB FAIL: {e}")

asyncio.run(test_db())
