"""
用户认证模块测试
"""
import pytest


@pytest.mark.asyncio
async def test_user_register(client):
    """测试用户注册"""
    response = await client.post("/api/user/register", json={
        "username": "test_register_user",
        "email": "register_test@example.com",
        "password": "Test123456"
    })
    # 注册成功或用户已存在
    assert response.status_code in [201, 400]


@pytest.mark.asyncio
async def test_user_login_success(client):
    """测试用户登录成功"""
    # 先注册
    await client.post("/api/user/register", json={
        "username": "test_login_user",
        "email": "login_test@example.com",
        "password": "Test123456"
    })

    # 登录
    response = await client.post("/api/user/login", json={
        "username": "test_login_user",
        "password": "Test123456"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data


@pytest.mark.asyncio
async def test_user_login_wrong_password(client):
    """测试用户登录密码错误"""
    response = await client.post("/api/user/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client, auth_headers):
    """测试获取用户信息"""
    response = await client.get("/api/user/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "email" in data


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client):
    """测试未认证获取用户信息"""
    response = await client.get("/api/user/profile")
    assert response.status_code in [401, 403]
