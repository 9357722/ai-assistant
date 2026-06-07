"""
商品路由模块
提供商品查询、创建、更新、删除、评价等接口
"""
import aiomysql
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

import config
from db import get_pool
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
from services.cache import get_cache, set_cache, delete_cache

router = APIRouter(prefix="/api/products", tags=["商品模块"])


# ============ 数据库连接 ============

async def get_db():
    """获取全局连接池"""
    return get_pool()


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
    # 构建缓存 key（包含所有查询参数）
    cache_key = f"products:list:{keyword}:{category_id}:{min_price}:{max_price}:{platform}:{sort_by}:{sort_order}:{page}:{page_size}"
    cached = get_cache(cache_key)
    if cached:
        return cached

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
    result = await service.get_products(query)
    # 写入缓存，60秒过期（列表数据变化较快）
    set_cache(cache_key, result.model_dump(), expire=60)
    return result


# ============ 商品对比 ============

@router.get("/compare")
async def compare_products(
    ids: str = Query(..., description="商品ID列表，逗号分隔，最多4个"),
    pool=Depends(get_db),
):
    """
    商品对比接口

    支持 2-4 个商品同时对比，返回结构化对比数据
    包含：价格、销量、平台、分类等维度
    """
    try:
        product_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="商品ID格式错误")

    if len(product_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个商品进行对比")
    if len(product_ids) > 4:
        raise HTTPException(status_code=400, detail="最多支持4个商品对比")

    cache_key = f"products:compare:{','.join(map(str, sorted(product_ids)))}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            placeholders = ",".join(["%s"] * len(product_ids))
            await cur.execute(
                f"""SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.id IN ({placeholders}) AND p.status = 'on_sale'""",
                product_ids
            )
            products = list(await cur.fetchall())

    if len(products) < 2:
        raise HTTPException(status_code=400, detail="对比商品不足，请检查商品是否存在或已下架")

    comparison = {
        "products": [
            {
                "id": p["id"],
                "name": p["name"],
                "price": float(p["price"]),
                "platform": p["platform"],
                "category": p.get("category_name", ""),
                "sales": p.get("sales", 0),
                "stock": p.get("stock", 0),
                "main_image": p.get("main_image", ""),
                "description": p.get("description", ""),
            }
            for p in products
        ],
        "dimensions": {
            "cheapest": min(products, key=lambda x: float(x["price"]))["id"],
            "best_selling": max(products, key=lambda x: x.get("sales", 0))["id"],
            "most_stock": max(products, key=lambda x: x.get("stock", 0))["id"],
        },
    }

    set_cache(cache_key, comparison, expire=120)
    return comparison


# ============ 商品详情 ============

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int = Path(..., description="商品ID"),
    service: ProductService = Depends(get_product_service),
):
    """获取商品详情"""
    cache_key = f"products:detail:{product_id}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    product = await service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    set_cache(cache_key, product.model_dump(), expire=300)
    return product


# ============ 创建商品（管理员） ============

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: TokenData = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
):
    """创建商品（仅管理员）"""
    product = await service.create_product(product_data)
    delete_cache("products:list:*")
    return product


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
    delete_cache("products:list:*")
    delete_cache(f"products:detail:{product_id}")
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
    if success:
        delete_cache("products:list:*")
        delete_cache(f"products:detail:{product_id}")
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


# ============ 搜索自动补全 ============

@router.get("/search/suggest")
async def search_suggest(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(8, ge=1, le=20, description="返回数量"),
    pool=Depends(get_db),
):
    """
    搜索自动补全（Typeahead）

    基于 Redis 前缀树缓存 + 数据库模糊查询
    支持商品名、品牌名、分类名补全
    """
    from services.cache import get_cache, set_cache

    cache_key = f"search:suggest:{keyword}:{limit}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 商品名补全
            await cur.execute(
                """SELECT DISTINCT name as text, 'product' as type
                   FROM products WHERE name LIKE %s AND status = 'on_sale'
                   LIMIT %s""",
                (f"%{keyword}%", limit)
            )
            products = list(await cur.fetchall())

            # 分类名补全
            await cur.execute(
                """SELECT DISTINCT name as text, 'category' as type
                   FROM categories WHERE name LIKE %s
                   LIMIT %s""",
                (f"%{keyword}%", limit)
            )
            categories = list(await cur.fetchall())

            # 合并去重
            suggestions = []
            seen = set()
            for item in products + categories:
                if item["text"] not in seen:
                    seen.add(item["text"])
                    suggestions.append(item)

            result = {"keyword": keyword, "suggestions": suggestions[:limit]}
            set_cache(cache_key, result, expire=300)
            return result


# ============ 智能搜索（四棒搜索引擎） ============

@router.get("/search/ai")
async def ai_search(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    pool=Depends(get_db),
):
    """
    智能搜索（四棒搜索引擎）

    第1棒：意图解析（LLM纠错+语义理解）
    第2棒：多路召回（文本+分类+品牌）
    第3棒：精排打分（价格+销量+评分）
    第4棒：重排调整（多样性+业务规则）
    """
    from services.search_engine import SearchEngine
    engine = SearchEngine(pool)
    return await engine.search(query=keyword, page=page, page_size=page_size)
