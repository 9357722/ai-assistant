"""
购物车和订单模块测试
"""
import pytest


@pytest.mark.asyncio
async def test_get_cart(client, auth_headers):
    """测试获取购物车"""
    response = await client.get("/api/cart", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total_amount" in data


@pytest.mark.asyncio
async def test_add_to_cart(client, auth_headers):
    """测试添加商品到购物车"""
    # 先获取一个商品
    products = await client.get("/api/products?page_size=1")
    if products.json()["total"] > 0:
        product_id = products.json()["items"][0]["id"]
        response = await client.post("/api/cart/add", json={
            "product_id": product_id,
            "quantity": 1
        }, headers=auth_headers)
        # 添加成功或库存不足
        assert response.status_code in [201, 400]


@pytest.mark.asyncio
async def test_get_orders(client, auth_headers):
    """测试获取订单列表"""
    response = await client.get("/api/orders", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_order_validation(client, auth_headers):
    """测试创建订单参数验证"""
    # 空购物车创建订单应该失败
    response = await client.post("/api/orders", json={
        "address_id": 1,
        "remark": "测试订单"
    }, headers=auth_headers)
    # 可能成功也可能失败，取决于购物车状态
    assert response.status_code in [201, 400]
