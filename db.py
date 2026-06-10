# -*- coding: utf-8 -*-
"""
全局数据库连接池
应用启动时创建，所有路由共享
"""
import os
import logging
import time
import aiomysql
import config

logger = logging.getLogger(__name__)
_pool: aiomysql.Pool = None

# 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0"))

SENSITIVE_PARAM_MARKER = "***"


def _summarize_params(params):
    """Return a safe, shape-only representation for query parameters."""
    if params is None:
        return None
    if isinstance(params, dict):
        return {key: SENSITIVE_PARAM_MARKER for key in params.keys()}
    if isinstance(params, (list, tuple)):
        return [SENSITIVE_PARAM_MARKER for _ in params]
    return SENSITIVE_PARAM_MARKER


class SlowQueryLogger:
    """慢查询日志记录器"""

    @staticmethod
    def log_if_slow(query: str, duration: float, params=None):
        """记录慢查询"""
        if duration > SLOW_QUERY_THRESHOLD:
            safe_params = _summarize_params(params)
            logger.warning(
                f"Slow query ({duration:.3f}s): {query[:200]}"
                + (f" | params: {safe_params}" if safe_params else "")
            )


async def init_pool():
    """应用启动时调用，创建全局连接池"""
    global _pool
    _pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        db=config.DB_NAME,
        charset="utf8mb4",
        autocommit=False,
        minsize=2,
        maxsize=20,
        pool_recycle=3600,
    )
    logger.info("Database pool initialized")


def get_pool() -> aiomysql.Pool:
    """获取全局连接池（必须在 init_pool 之后调用）"""
    if _pool is None:
        raise RuntimeError("DB pool not initialized - did you forget to call init_pool()?")
    return _pool


async def close_pool():
    """应用关闭时调用，释放连接池"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        logger.info("Database pool closed")
