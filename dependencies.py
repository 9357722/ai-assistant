# -*- coding: utf-8 -*-
"""
公共依赖模块
提供数据库连接池等共享依赖
"""
from db import get_pool


async def get_db():
    """获取全局连接池"""
    return get_pool()
