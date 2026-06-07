# -*- coding: utf-8 -*-
"""
Redis 缓存服务
"""
import json
import redis
import config
import logging

logger = logging.getLogger(__name__)

# Redis 连接
_redis_client = None
_redis_available = True  # 标记 Redis 是否可用

def get_redis() -> redis.Redis:
    """获取 Redis 客户端"""
    global _redis_client, _redis_available
    if not _redis_available:
        return None
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            _redis_available = False
            return None
    return _redis_client

def get_cache(key: str):
    """获取缓存"""
    try:
        r = get_redis()
        if r is None:
            return None
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None

def set_cache(key: str, value, expire: int = 300):
    """设置缓存，默认5分钟过期"""
    try:
        r = get_redis()
        if r is None:
            return
        r.setex(key, expire, json.dumps(value, default=str))
    except Exception:
        pass

def delete_cache(pattern: str):
    """删除匹配的缓存（使用 SCAN 避免阻塞）"""
    try:
        r = get_redis()
        if r is None:
            return
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            if keys:
                r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass
