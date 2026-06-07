# -*- coding: utf-8 -*-
"""直接测试 login 接口"""
import sys, asyncio
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from db import init_pool

async def main():
    await init_pool()
    from starlette.testclient import TestClient
    from api_server import app

    client = TestClient(app)
    try:
        resp = client.post("/api/user/login", json={
            "username": "admin",
            "password": "admin123"
        })
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:500]}")
    except Exception as e:
        import traceback
        print(f"ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()

asyncio.run(main())
