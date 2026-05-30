"""
购物车数据模型
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============ 请求模型 ============

class CartItemAdd(BaseModel):
    """添加购物车项"""
    product_id: int = Field(..., description="商品ID")
    quantity: int = Field(1, ge=1, description="数量")


class CartItemUpdate(BaseModel):
    """更新购物车项"""
    quantity: Optional[int] = Field(None, ge=1, description="数量")
    selected: Optional[bool] = Field(None, description="是否选中")


# ============ 响应模型 ============

class CartItemResponse(BaseModel):
    """购物车项响应"""
    id: int
    user_id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    product_price: float
    product_platform: str
    product_stock: int
    quantity: int
    selected: bool
    subtotal: float
    created_at: datetime
    updated_at: Optional[datetime] = None


class CartResponse(BaseModel):
    """购物车响应"""
    items: List[CartItemResponse]
    total_items: int
    total_amount: float
    selected_amount: float
    selected_count: int
