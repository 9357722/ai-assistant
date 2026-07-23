"""
Redis 连接管理
提供全局 Redis 连接池
"""
import logging
import redis.asyncio as redis
from typing import Optional

import config

logger = logging.getLogger(__name__)

# 全局 Redis 连接池
_redis_pool: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """初始化 Redis 连接"""
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            await _redis_pool.ping()
            logger.info(f"Redis connected to {config.REDIS_HOST}:{config.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Memory caching will be disabled.")
            _redis_pool = None
    return _redis_pool


async def get_redis() -> Optional[redis.Redis]:
    """获取 Redis 连接"""
    global _redis_pool
    if _redis_pool is None:
        await init_redis()
    return _redis_pool


async def close_redis():
    """关闭 Redis 连接"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection closed")
