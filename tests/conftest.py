"""
pytest 配置和公共 fixtures
使用方法: pytest tests/ -v
"""
import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# 设置测试环境
os.environ["ENV"] = "testing"
os.environ["DB_HOST"] = os.getenv("TEST_DB_HOST", "localhost")
os.environ["DB_NAME"] = os.getenv("TEST_DB_NAME", "product_db_test")
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def app():
    """获取 FastAPI 应用实例"""
    from api_server import app as fastapi_app
    yield fastapi_app


@pytest_asyncio.fixture(scope="session")
async def client(app):
    """创建异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_pool():
    """获取数据库连接池"""
    from db import init_pool, get_pool, close_pool
    await init_pool()
    pool = get_pool()
    yield pool
    await close_pool()


@pytest_asyncio.fixture
async def auth_headers(client):
    """获取认证 headers（使用测试用户）"""
    # 先尝试登录
    response = await client.post("/api/user/login", json={
        "username": "test_user",
        "password": "test_password123"
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # 如果登录失败，尝试注册
    await client.post("/api/user/register", json={
        "username": "test_user",
        "email": "test@example.com",
        "password": "test_password123"
    })
    response = await client.post("/api/user/login", json={
        "username": "test_user",
        "password": "test_password123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client):
    """获取管理员认证 headers"""
    response = await client.post("/api/user/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    pytest.skip("Admin login failed")
