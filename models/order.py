"""
订单数据模型
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ============ 请求模型 ============

class OrderCreate(BaseModel):
    """创建订单请求"""
    address_id: int = Field(..., description="收货地址ID")
    remark: Optional[str] = Field(None, max_length=500, description="备注")
    cart_item_ids: Optional[List[int]] = Field(None, description="购物车项ID列表，为空则使用所有选中项")
    idempotency_key: Optional[str] = Field(None, max_length=64, description="幂等键，防止重复提交")


class OrderQuery(BaseModel):
    """订单查询参数"""
    status: Optional[str] = Field(None, description="订单状态")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# ============ 响应模型 ============

class OrderItemResponse(BaseModel):
    """订单项响应"""
    id: int
    order_id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    price: float
    quantity: int
    subtotal: float


class OrderResponse(BaseModel):
    """订单响应"""
    id: int
    order_no: str
    user_id: int
    total_amount: float
    pay_amount: Optional[float] = None
    status: str
    address_snapshot: Optional[dict] = None
    remark: Optional[str] = None
    items: List[OrderItemResponse] = []
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OrderListResponse(BaseModel):
    """订单列表响应（分页）"""
    total: int
    page: int
    page_size: int
    items: List[OrderResponse]
