"""
用户数据模型
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ============ 请求模型 ============

class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None


class PasswordChange(BaseModel):
    """密码修改请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class AddressCreate(BaseModel):
    """创建地址请求"""
    name: str = Field(..., max_length=50, description="收件人姓名")
    phone: str = Field(..., max_length=20, description="手机号")
    province: Optional[str] = Field(None, max_length=50, description="省份")
    city: Optional[str] = Field(None, max_length=50, description="城市")
    district: Optional[str] = Field(None, max_length=50, description="区/县")
    detail: str = Field(..., max_length=200, description="详细地址")
    is_default: bool = Field(False, description="是否默认地址")


# ============ 响应模型 ============

class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserLoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AddressResponse(BaseModel):
    """地址响应"""
    id: int
    user_id: int
    name: str
    phone: str
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    detail: str
    is_default: bool
    created_at: datetime


class UserListResponse(BaseModel):
    """用户列表响应（分页）"""
    total: int
    page: int
    page_size: int
    items: List[UserResponse]
