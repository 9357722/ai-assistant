"""
用户路由模块
提供用户注册、登录、个人信息管理、地址管理等接口
"""
import aiomysql
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request

import config
from db import get_pool
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_admin,
    decode_token_allow_expired,
    TokenData,
)
from models.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    PasswordChange,
    AddressCreate,
    AddressResponse,
    UserLoginResponse,
    UserListResponse,
)

router = APIRouter(prefix="/api/user", tags=["用户模块"])


# ============ 数据库连接 ============

async def get_db():
    """获取全局连接池"""
    return get_pool()


# ============ 用户注册 ============

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db=Depends(get_db)):
    """
    用户注册

    - 检查用户名和邮箱是否已存在
    - 创建新用户
    - 返回用户信息
    """
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 检查用户名是否已存在
            await cur.execute("SELECT id FROM users WHERE username = %s", (user_data.username,))
            if await cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已存在"
                )

            # 检查邮箱是否已存在
            await cur.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
            if await cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )

            # 创建用户
            hashed_password = get_password_hash(user_data.password)
            await cur.execute(
                """INSERT INTO users (username, email, hashed_password, phone)
                   VALUES (%s, %s, %s, %s)""",
                (user_data.username, user_data.email, hashed_password, user_data.phone)
            )
            user_id = cur.lastrowid
            await conn.commit()

            # 返回用户信息
            await cur.execute(
                "SELECT id, username, email, phone, avatar, role, is_active, created_at FROM users WHERE id = %s",
                (user_id,)
            )
            user = await cur.fetchone()
            return UserResponse(**user)


# ============ 登录限流（Redis 滑动窗口 + 内存降级） ============
_LOGIN_MAX_ATTEMPTS = 10
_LOGIN_WINDOW = 300  # 5 分钟
_login_memory: dict = {}  # {ip: [timestamp, ...]} — Redis 不可用时的降级方案

def _check_login_rate_limit(ip: str):
    """检查登录频率，超过限制抛出 429"""
    try:
        from services.cache import get_redis
        r = get_redis()
        if r is not None:
            key = f"login_limit:{ip}"
            now = time.time()
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - _LOGIN_WINDOW)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, _LOGIN_WINDOW)
            _, _, count, _ = pipe.execute()
            if count > _LOGIN_MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="登录尝试过于频繁，请稍后再试"
                )
            return
    except HTTPException:
        raise
    except Exception:
        pass

    # Redis 不可用，降级为内存限流
    now = time.time()
    timestamps = _login_memory.get(ip, [])
    timestamps = [t for t in timestamps if now - t < _LOGIN_WINDOW]
    timestamps.append(now)
    _login_memory[ip] = timestamps
    if len(timestamps) > _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录尝试过于频繁，请稍后再试"
        )

# ============ 用户登录 ============

@router.post("/login", response_model=UserLoginResponse)
async def login(login_data: UserLogin, request: Request, db=Depends(get_db)):
    """
    用户登录

    - 支持用户名或邮箱登录
    - 验证密码
    - 返回 JWT Token
    """
    import logging
    import hashlib
    logger = logging.getLogger(__name__)

    # 使用哈希值记录用户名，避免明文泄露
    username_hash = hashlib.md5(login_data.username.encode()).hexdigest()[:8]
    logger.info(f"LOGIN ATTEMPT: hash={username_hash}")

    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)

    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查找用户（支持用户名或邮箱）— 明确指定字段，避免 SELECT * 泄露 hash
            await cur.execute(
                "SELECT id, username, email, hashed_password, phone, avatar, role, is_active, created_at, updated_at FROM users WHERE username = %s OR email = %s",
                (login_data.username, login_data.username)
            )
            user = await cur.fetchone()

            if not user:
                logger.warning(f"Login failed: user not found, hash={username_hash}, ip={client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户名或密码错误",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            password_valid = verify_password(login_data.password, user["hashed_password"])

            if not password_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户名或密码错误",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="账号已被禁用"
                )

            # 生成 Token
            token = create_access_token({
                "user_id": user["id"],
                "username": user["username"],
                "role": user["role"],
            })

            return UserLoginResponse(
                access_token=token,
                user=UserResponse(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    phone=user["phone"],
                    avatar=user["avatar"],
                    role=user["role"],
                    is_active=user["is_active"],
                    created_at=user["created_at"],
                    updated_at=user.get("updated_at"),
                )
            )


# ============ Token 刷新 ============

@router.post("/refresh", response_model=UserLoginResponse)
async def refresh_token(
    request: Request,
    db=Depends(get_db),
):
    """
    刷新 Token

    - 接收当前 Token（即使已过期）
    - 验证用户仍然有效
    - 返回新 Token
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证凭据")

    old_token = auth_header[7:]
    token_data = decode_token_allow_expired(old_token)

    if not token_data.user_id:
        raise HTTPException(status_code=401, detail="无效的 Token")

    # 验证用户仍然存在且有效
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, username, email, phone, avatar, role, is_active, created_at, updated_at FROM users WHERE id = %s",
                (token_data.user_id,)
            )
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="用户不存在")
            if not user["is_active"]:
                raise HTTPException(status_code=403, detail="账号已被禁用")

    # 生成新 Token
    new_token = create_access_token({
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
    })

    return UserLoginResponse(
        access_token=new_token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            phone=user["phone"],
            avatar=user["avatar"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            updated_at=user.get("updated_at"),
        )
    )


# ============ 获取当前用户信息 ============

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """获取当前登录用户的个人信息"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, username, email, phone, avatar, role, is_active, created_at, updated_at FROM users WHERE id = %s",
                (current_user.user_id,)
            )
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            return UserResponse(**user)


# ============ 更新用户信息 ============

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """更新当前用户的个人信息"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 构建更新语句
            update_fields = []
            update_values = []

            if update_data.email is not None:
                # 检查邮箱是否已被使用
                await cur.execute(
                    "SELECT id FROM users WHERE email = %s AND id != %s",
                    (update_data.email, current_user.user_id)
                )
                if await cur.fetchone():
                    raise HTTPException(status_code=400, detail="邮箱已被使用")
                update_fields.append("email = %s")
                update_values.append(update_data.email)

            if update_data.phone is not None:
                update_fields.append("phone = %s")
                update_values.append(update_data.phone)

            if update_data.avatar is not None:
                update_fields.append("avatar = %s")
                update_values.append(update_data.avatar)

            if not update_fields:
                raise HTTPException(status_code=400, detail="没有要更新的内容")

            update_values.append(current_user.user_id)
            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            await cur.execute(sql, update_values)
            await conn.commit()

            # 返回更新后的用户信息
            await cur.execute(
                "SELECT id, username, email, phone, avatar, role, is_active, created_at, updated_at FROM users WHERE id = %s",
                (current_user.user_id,)
            )
            user = await cur.fetchone()
            return UserResponse(**user)


# ============ 修改密码 ============

@router.put("/password")
async def change_password(
    password_data: PasswordChange,
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """修改密码"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取当前密码
            await cur.execute("SELECT hashed_password FROM users WHERE id = %s", (current_user.user_id,))
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            # 验证旧密码
            if not verify_password(password_data.old_password, user["hashed_password"]):
                raise HTTPException(status_code=400, detail="旧密码错误")

            # 更新密码
            new_hashed = get_password_hash(password_data.new_password)
            await cur.execute(
                "UPDATE users SET hashed_password = %s WHERE id = %s",
                (new_hashed, current_user.user_id)
            )
            await conn.commit()

            return {"message": "密码修改成功"}


# ============ 地址管理 ============

@router.get("/addresses", response_model=list[AddressResponse])
async def get_addresses(
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """获取当前用户的所有地址"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM user_addresses WHERE user_id = %s ORDER BY is_default DESC, created_at DESC",
                (current_user.user_id,)
            )
            addresses = await cur.fetchall()
            return [AddressResponse(**addr) for addr in addresses]


@router.post("/addresses", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    address_data: AddressCreate,
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """创建新地址"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 如果设为默认地址，先取消其他默认
            if address_data.is_default:
                await cur.execute(
                    "UPDATE user_addresses SET is_default = FALSE WHERE user_id = %s",
                    (current_user.user_id,)
                )

            # 插入新地址
            await cur.execute(
                """INSERT INTO user_addresses (user_id, name, phone, province, city, district, detail, is_default)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    current_user.user_id,
                    address_data.name,
                    address_data.phone,
                    address_data.province,
                    address_data.city,
                    address_data.district,
                    address_data.detail,
                    address_data.is_default,
                )
            )
            address_id = cur.lastrowid
            await conn.commit()

            # 返回创建的地址
            await cur.execute("SELECT * FROM user_addresses WHERE id = %s", (address_id,))
            address = await cur.fetchone()
            return AddressResponse(**address)


@router.put("/addresses/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int,
    address_data: AddressCreate,
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """更新地址"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 检查地址是否存在且属于当前用户
            await cur.execute(
                "SELECT id FROM user_addresses WHERE id = %s AND user_id = %s",
                (address_id, current_user.user_id)
            )
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="地址不存在")

            # 如果设为默认地址，先取消其他默认
            if address_data.is_default:
                await cur.execute(
                    "UPDATE user_addresses SET is_default = FALSE WHERE user_id = %s AND id != %s",
                    (current_user.user_id, address_id)
                )

            # 更新地址
            await cur.execute(
                """UPDATE user_addresses
                   SET name=%s, phone=%s, province=%s, city=%s, district=%s, detail=%s, is_default=%s
                   WHERE id=%s AND user_id=%s""",
                (
                    address_data.name,
                    address_data.phone,
                    address_data.province,
                    address_data.city,
                    address_data.district,
                    address_data.detail,
                    address_data.is_default,
                    address_id,
                    current_user.user_id,
                )
            )
            await conn.commit()

            # 返回更新后的地址
            await cur.execute("SELECT * FROM user_addresses WHERE id = %s", (address_id,))
            address = await cur.fetchone()
            return AddressResponse(**address)


@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: int,
    current_user: TokenData = Depends(get_current_user),
    db=Depends(get_db)
):
    """删除地址"""
    async with db.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM user_addresses WHERE id = %s AND user_id = %s",
                (address_id, current_user.user_id)
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="地址不存在")
            await conn.commit()
            return {"message": "地址删除成功"}


# ============ 管理员接口 ============

@router.get("/list", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: TokenData = Depends(get_current_admin),
    db=Depends(get_db)
):
    """获取用户列表（仅管理员）"""
    async with db.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 获取总数
            await cur.execute("SELECT COUNT(*) as total FROM users")
            total = (await cur.fetchone())["total"]

            # 获取分页数据
            offset = (page - 1) * page_size
            await cur.execute(
                "SELECT id, username, email, phone, avatar, role, is_active, created_at FROM users ORDER BY id DESC LIMIT %s OFFSET %s",
                (page_size, offset)
            )
            users = await cur.fetchall()

            return UserListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[UserResponse(**user) for user in users]
            )
