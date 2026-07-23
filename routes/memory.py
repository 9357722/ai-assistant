"""
记忆管理路由
提供用户记忆画像、记忆查询、记忆搜索等接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user, TokenData
from services.ai_customer_service import AICustomerService
from db import get_pool

router = APIRouter(prefix="/api/memory", tags=["记忆管理"])


async def get_db():
    """获取数据库连接池"""
    return get_pool()


class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    query: str
    limit: int = Query(5, ge=1, le=50)


# ============ 用户记忆画像 ============

@router.get("/profile")
async def get_memory_profile(
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取用户记忆画像"""
    service = AICustomerService(pool)
    profile = await service.get_user_memory_profile(current_user.user_id)

    if not profile:
        return {
            "user_id": current_user.user_id,
            "message": "暂无记忆画像数据",
            "profile": None
        }

    return {
        "user_id": current_user.user_id,
        "profile": profile
    }


# ============ 用户记忆列表 ============

@router.get("/list")
async def get_memory_list(
    memory_type: Optional[str] = Query(None, description="记忆类型过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取用户记忆列表"""
    service = AICustomerService(pool)
    memories = await service.get_user_memories(
        current_user.user_id,
        memory_type=memory_type,
        limit=limit
    )

    return {
        "user_id": current_user.user_id,
        "count": len(memories),
        "memories": memories
    }


# ============ 记忆搜索 ============

@router.post("/search")
async def search_memories(
    request: MemorySearchRequest,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """搜索用户记忆"""
    service = AICustomerService(pool)
    results = await service.search_user_memories(
        current_user.user_id,
        query=request.query,
        limit=request.limit
    )

    return {
        "user_id": current_user.user_id,
        "query": request.query,
        "count": len(results),
        "results": results
    }


# ============ 清除记忆 ============

@router.delete("/clear")
async def clear_memories(
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """清除用户记忆"""
    service = AICustomerService(pool)
    await service.clear_user_memories(current_user.user_id)

    return {
        "user_id": current_user.user_id,
        "message": "记忆已清除"
    }


# ============ 记忆统计 ============

@router.get("/stats")
async def get_memory_stats(
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取记忆统计信息"""
    import aiomysql

    try:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 长期记忆数量
                await cur.execute(
                    "SELECT COUNT(*) as count FROM user_memory_vectors WHERE user_id = %s",
                    (current_user.user_id,)
                )
                long_term_count = (await cur.fetchone())["count"]

                # 记忆日志数量
                await cur.execute(
                    "SELECT COUNT(*) as count FROM memory_logs WHERE user_id = %s",
                    (current_user.user_id,)
                )
                log_count = (await cur.fetchone())["count"]

                # 按类型统计
                await cur.execute(
                    """SELECT memory_type, COUNT(*) as count
                       FROM user_memory_vectors
                       WHERE user_id = %s
                       GROUP BY memory_type""",
                    (current_user.user_id,)
                )
                by_type = {row["memory_type"]: row["count"] for row in await cur.fetchall()}

                return {
                    "user_id": current_user.user_id,
                    "long_term_memories": long_term_count,
                    "memory_logs": log_count,
                    "by_type": by_type
                }
    except Exception as e:
        return {
            "user_id": current_user.user_id,
            "error": str(e),
            "long_term_memories": 0,
            "memory_logs": 0,
            "by_type": {}
        }
