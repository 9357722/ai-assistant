# -*- coding: utf-8 -*-
"""
商家端路由
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os
import uuid

from auth import get_current_user, TokenData
from db import get_pool

router = APIRouter(prefix="/api/merchant", tags=["商家端"])


async def get_db():
    return get_pool()


# ================================================================
# 请求模型
# ================================================================

class MerchantCreate(BaseModel):
    shop_name: str
    shop_description: Optional[str] = ""
    contact_phone: Optional[str] = ""
    contact_email: Optional[str] = ""
    address: Optional[str] = ""


class ProductCreate(BaseModel):
    name: str
    price: float
    category_id: Optional[int] = None
    description: Optional[str] = ""
    main_image: Optional[str] = ""
    stock: Optional[int] = 100


class CouponCreate(BaseModel):
    name: str
    type: str  # fixed 或 percent
    value: float
    min_amount: Optional[float] = 0
    max_uses: Optional[int] = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class MerchantInfoUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    shop_logo: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None


# ================================================================
# 商家信息接口
# ================================================================

@router.get("/info")
async def get_merchant_info(user=Depends(get_current_user), db=Depends(get_db)):
    """获取当前用户的商家信息"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Getting merchant info for user_id={user.user_id}")

    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    logger.info(f"Merchant result: {merchant}")

    if not merchant:
        return {"is_merchant": False}
    if merchant.get('created_at'):
        merchant['created_at'] = merchant['created_at'].isoformat()
    if merchant.get('updated_at'):
        merchant['updated_at'] = merchant['updated_at'].isoformat()
    return {"is_merchant": True, "merchant": merchant}


@router.post("/register")
async def register_merchant(data: MerchantCreate, user=Depends(get_current_user), db=Depends(get_db)):
    """注册成为商家"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)

    # 检查是否已是商家
    existing = await service.get_merchant_by_user_id(user.user_id)
    if existing:
        raise HTTPException(status_code=400, detail="您已经是商家了")

    merchant_id = await service.create_merchant(
        user_id=user.user_id,
        shop_name=data.shop_name,
        shop_description=data.shop_description,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email,
        address=data.address
    )
    return {"message": "商家注册成功", "merchant_id": merchant_id}


@router.put("/info")
async def update_merchant_info(data: MerchantInfoUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    """更新商家信息"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="商家不存在")

    # 只更新非None字段
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if update_data:
        await service.update_merchant(merchant['id'], **update_data)
    return {"message": "更新成功"}


# ================================================================
# 商品管理接口
# ================================================================

@router.get("/products")
async def get_merchant_products(page: int = 1, page_size: int = 20,
                                user=Depends(get_current_user), db=Depends(get_db)):
    """获取商家商品列表"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    return await service.get_merchant_products(merchant['id'], page, page_size)


@router.post("/products")
async def add_product(data: ProductCreate, user=Depends(get_current_user), db=Depends(get_db)):
    """添加商品"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    product_id = await service.add_product_to_merchant(merchant['id'], data.dict())
    return {"message": "商品添加成功", "product_id": product_id}


@router.put("/products/{product_id}")
async def update_product(product_id: int, data: dict, user=Depends(get_current_user), db=Depends(get_db)):
    """更新商品"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    success = await service.update_merchant_product(merchant['id'], product_id, **data)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在或无权修改")
    return {"message": "更新成功"}


@router.delete("/products/{product_id}")
async def delete_product(product_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    """删除商品"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    success = await service.delete_merchant_product(merchant['id'], product_id)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在或无权删除")
    return {"message": "删除成功"}


# ================================================================
# 图片上传接口
# ================================================================

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    """上传商品图片"""
    # 允许的扩展名
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']

    # 提取并验证扩展名
    original_filename = file.filename or "unknown.jpg"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="只支持 JPG、PNG、WebP 格式")

    # 检查文件大小 (5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    # 验证文件头 magic bytes
    if len(content) < 4:
        raise HTTPException(status_code=400, detail="无效的图片文件")

    # JPEG: FF D8 FF, PNG: 89 50 4E 47, WebP: 52 49 46 46
    valid_magic = {
        b'\xff\xd8\xff': '.jpg',
        b'\x89PNG': '.png',
        b'RIFF': '.webp',  # WebP以RIFF开头
    }
    magic_valid = False
    for magic, expected_ext in valid_magic.items():
        if content[:len(magic)] == magic:
            magic_valid = True
            break
    if not magic_valid:
        raise HTTPException(status_code=400, detail="无效的图片文件内容")

    # 生成安全文件名
    filename = f"product_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join("static/products", filename)

    # 保存文件
    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/static/products/{filename}", "filename": filename}


# ================================================================
# 订单管理接口
# ================================================================

@router.get("/orders")
async def get_merchant_orders(status: Optional[str] = None, page: int = 1, page_size: int = 20,
                              user=Depends(get_current_user), db=Depends(get_db)):
    """获取商家订单"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    return await service.get_merchant_orders(merchant['id'], status, page, page_size)


@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: int, data: dict, user=Depends(get_current_user), db=Depends(get_db)):
    """更新订单状态"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    status = data.get('status')
    if not status:
        raise HTTPException(status_code=400, detail="请提供状态")

    success, message = await service.update_order_status(merchant['id'], order_id, status)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


# ================================================================
# 数据统计接口
# ================================================================

@router.get("/dashboard")
async def get_dashboard(user=Depends(get_current_user), db=Depends(get_db)):
    """获取后台概览数据"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    return await service.get_dashboard_stats(merchant['id'])


# ================================================================
# 优惠券接口
# ================================================================

@router.get("/coupons")
async def get_coupons(user=Depends(get_current_user), db=Depends(get_db)):
    """获取优惠券列表"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    return await service.get_merchant_coupons(merchant['id'])


@router.post("/coupons")
async def create_coupon(data: CouponCreate, user=Depends(get_current_user), db=Depends(get_db)):
    """创建优惠券"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    coupon_id = await service.create_coupon(merchant['id'], data.dict())
    return {"message": "优惠券创建成功", "coupon_id": coupon_id}


# ================================================================
# 智能助手 Agent 接口
# ================================================================

class AgentChat(BaseModel):
    message: str
    context: Optional[list] = None


@router.post("/agent/chat")
async def agent_chat(data: AgentChat, user=Depends(get_current_user), db=Depends(get_db)):
    """与商家智能助手对话"""
    from services.merchant_service import MerchantService
    from services.merchant_agent import MerchantAgent

    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    agent = MerchantAgent(db)
    result = await agent.chat(merchant['id'], data.message, data.context)
    return result


@router.delete("/agent/chat/history")
async def clear_agent_history(user=Depends(get_current_user), db=Depends(get_db)):
    """清除商家智能助手对话历史"""
    from services.merchant_service import MerchantService
    from services.merchant_agent import MerchantAgent

    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    agent = MerchantAgent(db)
    agent.clear_history(merchant['id'])
    return {"message": "对话历史已清除"}


@router.post("/agent/generate-product")
async def agent_generate_product(data: dict, user=Depends(get_current_user), db=Depends(get_db)):
    """AI生成商品信息"""
    from services.merchant_service import MerchantService
    from services.merchant_agent import MerchantAgent

    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    name = data.get('name', '')
    price = data.get('price', 0)
    category = data.get('category', '')

    agent = MerchantAgent(db)
    product_info = await agent._generate_product_info({
        'name': name,
        'price': price,
        'category': category
    })
    return product_info


@router.post("/agent/confirm-product")
async def agent_confirm_product(data: ProductCreate, user=Depends(get_current_user), db=Depends(get_db)):
    """确认添加AI生成的商品"""
    from services.merchant_service import MerchantService
    service = MerchantService(db)
    merchant = await service.get_merchant_by_user_id(user.user_id)
    if not merchant:
        raise HTTPException(status_code=403, detail="您不是商家")

    product_id = await service.add_product_to_merchant(merchant['id'], data.dict())
    return {"message": "商品添加成功", "product_id": product_id}
