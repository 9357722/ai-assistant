"""
商品路由模块
提供商品查询、创建、更新、删除、评价等接口
"""
import aiomysql
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

import config
from auth import get_current_user, get_current_admin, get_optional_user, TokenData
from models.product import (
    ProductCreate,
    ProductUpdate,
    ProductQuery,
    ProductResponse,
    ProductListResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
    CategoryResponse,
    SearchResult,
)
from services.product_service import ProductService

router = APIRouter(prefix="/api/products", tags=["商品模块"])


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


async def get_product_service(pool=Depends(get_db)) -> ProductService:
    """获取商品服务实例"""
    return ProductService(pool)


# ============ 商品列表 ============

@router.get("", response_model=ProductListResponse)
async def list_products(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[int] = Query(None, description="分类ID"),
    min_price: Optional[float] = Query(None, ge=0, description="最低价格"),
    max_price: Optional[float] = Query(None, ge=0, description="最高价格"),
    platform: Optional[str] = Query(None, description="平台"),
    sort_by: str = Query("created_at", description="排序字段: created_at, price, sales, name"),
    sort_order: str = Query("desc", description="排序方式: asc, desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ProductService = Depends(get_product_service),
):
    """
    获取商品列表

    支持按关键词、分类、价格区间、平台筛选
    支持按创建时间、价格、销量、名称排序
    """
    query = ProductQuery(
        keyword=keyword,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        platform=platform,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return await service.get_products(query)


# ============ 商品详情 ============

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int = Path(..., description="商品ID"),
    service: ProductService = Depends(get_product_service),
):
    """获取商品详情"""
    product = await service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


# ============ 创建商品（管理员） ============

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: TokenData = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
):
    """创建商品（仅管理员）"""
    return await service.create_product(product_data)


# ============ 更新商品（管理员） ============

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: TokenData = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
):
    """更新商品（仅管理员）"""
    product = await service.update_product(product_id, product_data)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


# ============ 删除商品（管理员） ============

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: TokenData = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
):
    """删除商品（软删除，仅管理员）"""
    success = await service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"message": "商品已下架"}


# ============ 分类列表 ============

@router.get("/categories/list", response_model=list)
async def list_categories(
    service: ProductService = Depends(get_product_service),
):
    """获取商品分类列表（树形结构）"""
    return await service.get_categories()


# ============ 商品评价 ============

@router.get("/{product_id}/reviews", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ProductService = Depends(get_product_service),
):
    """获取商品评价列表"""
    return await service.get_product_reviews(product_id, page, page_size)


@router.post("/{product_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_product_review(
    product_id: int,
    review_data: ReviewCreate,
    current_user: TokenData = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    """创建商品评价（需要登录）"""
    try:
        return await service.create_review(product_id, current_user.user_id, review_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 智能搜索 ============

@router.get("/search/ai", response_model=SearchResult)
async def ai_search(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ProductService = Depends(get_product_service),
    pool=Depends(get_db),
):
    """
    智能搜索（结合向量检索 + 关键词匹配）

    返回搜索结果和 AI 总结
    """
    # 获取向量数据库集合
    vector_collection = None
    try:
        from utils import init_vector_db
        import os
        siliconflow_key = os.getenv("SILICONFLOW_API_KEY")
        if siliconflow_key:
            vector_collection = init_vector_db(api_key=siliconflow_key)
    except Exception:
        pass

    # 执行搜索
    products = await service.search_products_with_vector(
        keyword=keyword,
        vector_collection=vector_collection,
        n_results=page_size,
    )

    # 生成 AI 总结（可选）
    ai_summary = None
    if products:
        try:
            from openai import OpenAI
            import os
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if deepseek_key:
                client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
                product_list = "\n".join([f"- {p.name}: ¥{p.price} ({p.platform})" for p in products[:5]])
                response = client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": "你是商品搜索助手，用一句话总结搜索结果。"},
                        {"role": "user", "content": f"用户搜索: {keyword}\n搜索结果:\n{product_list}\n请用一句话总结。"}
                    ],
                    max_tokens=100,
                )
                ai_summary = response.choices[0].message.content
        except Exception:
            pass

    return SearchResult(
        keyword=keyword,
        total=len(products),
        items=products,
        ai_summary=ai_summary,
    )
