"""
AI 路由模块
提供智能推荐、AI客服等接口
"""
import aiomysql
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import config
from auth import get_current_user, get_optional_user, TokenData
from services.recommendation import RecommendationEngine
from services.ai_customer_service import AICustomerService

router = APIRouter(prefix="/api/ai", tags=["AI 模块"])


# ============ 数据库连接 ============

async def get_db():
    """获取数据库连接池"""
    pool = await aiomysql.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        db=config.DB_NAME,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        yield pool
    finally:
        pool.close()
        await pool.wait_closed()


# ============ 请求模型 ============

class RecommendationRequest(BaseModel):
    """推荐请求"""
    budget: Optional[float] = Field(None, description="预算")
    category: Optional[str] = Field(None, description="商品分类")
    prefer_brand: Optional[str] = Field(None, description="偏好品牌")
    limit: int = Field(10, ge=1, le=50, description="推荐数量")


class ChatRequest(BaseModel):
    """AI客服对话请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    history: Optional[List[dict]] = Field(None, description="对话历史")


class AIRecommendationRequest(BaseModel):
    """AI推荐请求"""
    query: str = Field(..., min_length=1, description="需求描述")
    budget: Optional[float] = Field(None, description="预算")


# ============ 个性化推荐 ============

@router.get("/recommendations")
async def get_personalized_recommendations(
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取个性化推荐（需要登录）"""
    engine = RecommendationEngine(pool)
    recommendations = await engine.get_personalized_recommendations(
        user_id=current_user.user_id,
        limit=limit,
    )
    return {
        "user_id": current_user.user_id,
        "count": len(recommendations),
        "recommendations": recommendations,
    }


# ============ 预算推荐 ============

@router.post("/recommendations/budget")
async def get_budget_recommendations(
    request: RecommendationRequest,
    pool=Depends(get_db),
):
    """基于预算的推荐"""
    engine = RecommendationEngine(pool)
    recommendations = await engine.get_recommendation_by_budget(
        budget=request.budget,
        category=request.category,
        prefer_brand=request.prefer_brand,
        limit=request.limit,
    )
    return {
        "budget": request.budget,
        "count": len(recommendations),
        "recommendations": recommendations,
    }


# ============ 相似商品推荐 ============

@router.get("/recommendations/similar/{product_id}")
async def get_similar_products(
    product_id: int,
    limit: int = Query(5, ge=1, le=20, description="推荐数量"),
    pool=Depends(get_db),
):
    """获取相似商品推荐"""
    engine = RecommendationEngine(pool)
    recommendations = await engine.get_similar_products(
        product_id=product_id,
        limit=limit,
    )
    return {
        "product_id": product_id,
        "count": len(recommendations),
        "recommendations": recommendations,
    }


# ============ AI 智能推荐 ============

@router.post("/recommendations/ai")
async def get_ai_recommendation(
    request: AIRecommendationRequest,
    pool=Depends(get_db),
):
    """AI 智能推荐（生成推荐文案）"""
    engine = RecommendationEngine(pool)
    recommendation = await engine.generate_ai_recommendation(
        user_query=request.query,
        budget=request.budget,
    )
    return {
        "query": request.query,
        "budget": request.budget,
        "recommendation": recommendation,
    }


# ============ AI 客服对话 ============

@router.post("/chat")
async def ai_customer_service_chat(
    request: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """AI 客服对话"""
    service = AICustomerService(pool)
    reply = await service.chat(
        user_id=current_user.user_id,
        message=request.message,
        history=request.history,
    )
    return {
        "user_id": current_user.user_id,
        "message": request.message,
        "reply": reply,
    }


# ============ 快捷回复 ============

@router.get("/quick-replies")
async def get_quick_replies(
    current_user: TokenData = Depends(get_current_user),
    pool=Depends(get_db),
):
    """获取快捷回复建议"""
    service = AICustomerService(pool)
    replies = await service.get_quick_replies(current_user.user_id)
    return {
        "user_id": current_user.user_id,
        "quick_replies": replies,
    }
