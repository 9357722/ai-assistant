"""
健康检查和版本端点测试
"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查端点"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


@pytest.mark.asyncio
async def test_version_info(client):
    """测试版本信息端点"""
    response = await client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "git_commit" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_metrics_requires_auth(client):
    """测试 metrics 端点需要认证"""
    response = await client.get("/metrics")
    # 应该返回 403 或 401
    assert response.status_code in [401, 403]
