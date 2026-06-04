# -*- coding: utf-8 -*-
"""
全局数据库连接池
应用启动时创建，所有路由共享
"""
import logging
import aiomysql
import config

logger = logging.getLogger(__name__)
_pool: aiomysql.Pool = None


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
