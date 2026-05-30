"""
商品数据模型
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============ 请求模型 ============

class ProductCreate(BaseModel):
    """创建商品请求"""
    name: str = Field(..., max_length=100, description="商品名称")
    price: float = Field(..., gt=0, description="价格")
    platform: str = Field(..., max_length=50, description="平台")
    category_id: Optional[int] = Field(None, description="分类ID")
    description: Optional[str] = Field(None, description="商品描述")
    main_image: Optional[str] = Field(None, description="主图URL")
    images: Optional[List[str]] = Field(None, description="图片列表")
    stock: int = Field(0, ge=0, description="库存")
    status: str = Field("on_sale", description="状态: on_sale, off_sale")


class ProductUpdate(BaseModel):
    """更新商品请求"""
    name: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    platform: Optional[str] = Field(None, max_length=50)
    category_id: Optional[int] = None
    description: Optional[str] = None
    main_image: Optional[str] = None
    images: Optional[List[str]] = None
    stock: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class ProductQuery(BaseModel):
    """商品查询参数"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    category_id: Optional[int] = Field(None, description="分类ID")
    min_price: Optional[float] = Field(None, ge=0, description="最低价格")
    max_price: Optional[float] = Field(None, ge=0, description="最高价格")
    platform: Optional[str] = Field(None, description="平台")
    status: Optional[str] = Field(None, description="状态")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方式: asc, desc")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class ReviewCreate(BaseModel):
    """创建评价请求"""
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    content: Optional[str] = Field(None, description="评价内容")
    images: Optional[List[str]] = Field(None, description="评价图片")


# ============ 响应模型 ============

class CategoryResponse(BaseModel):
    """分类响应"""
    id: int
    name: str
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: int = 0
    children: Optional[List["CategoryResponse"]] = None


class ProductResponse(BaseModel):
    """商品响应"""
    id: int
    name: str
    price: float
    platform: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    description: Optional[str] = None
    main_image: Optional[str] = None
    images: Optional[List[str]] = None
    stock: int = 0
    sales: int = 0
    status: str = "on_sale"
    rating: Optional[float] = None
    review_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProductListResponse(BaseModel):
    """商品列表响应（分页）"""
    total: int
    page: int
    page_size: int
    items: List[ProductResponse]


class ReviewResponse(BaseModel):
    """评价响应"""
    id: int
    product_id: int
    user_id: int
    username: Optional[str] = None
    rating: int
    content: Optional[str] = None
    images: Optional[List[str]] = None
    created_at: datetime


class ReviewListResponse(BaseModel):
    """评价列表响应"""
    total: int
    page: int
    page_size: int
    average_rating: float
    items: List[ReviewResponse]


class ProductRecommendation(BaseModel):
    """商品推荐"""
    product: ProductResponse
    score: float = Field(..., description="推荐分数")
    reason: str = Field(..., description="推荐理由")


class SearchResult(BaseModel):
    """搜索结果"""
    keyword: str
    total: int
    items: List[ProductResponse]
    ai_summary: Optional[str] = Field(None, description="AI 搜索总结")
