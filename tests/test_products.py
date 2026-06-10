"""
商品模块测试
"""
import pytest


@pytest.mark.asyncio
async def test_get_products(client):
    """测试获取商品列表"""
    response = await client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_products_with_pagination(client):
    """测试分页"""
    response = await client.get("/api/products?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_get_product_detail(client):
    """测试获取商品详情"""
    # 先获取列表
    response = await client.get("/api/products?page_size=1")
    if response.json()["total"] > 0:
        product_id = response.json()["items"][0]["id"]
        response = await client.get(f"/api/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "price" in data


@pytest.mark.asyncio
async def test_product_search(client):
    """测试商品搜索"""
    response = await client.get("/api/products?keyword=手机")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_categories(client):
    """测试获取分类列表"""
    response = await client.get("/api/products/categories/list")
    assert response.status_code == 200
