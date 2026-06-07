"""
JWT 认证模块
提供用户认证、Token 生成和验证功能
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel

import config

# Bearer Token 方案
security = HTTPBearer()


class TokenData(BaseModel):
    """Token 数据模型"""
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Token

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def decode_token_allow_expired(token: str) -> TokenData:
    """
    解码 JWT Token（允许过期，用于 Token 刷新）

    仅提取 user_id/username/role，不校验 exp
    """
    try:
        payload = jwt.decode(
            token, config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
            options={"verify_exp": False},
        )
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
            )
        return TokenData(user_id=user_id, username=username, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效",
        )


def decode_token(token: str) -> TokenData:
    """
    解码 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        TokenData 对象

    Raises:
        HTTPException: Token 无效或过期
    """
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(user_id=user_id, username=username, role=role)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    获取当前认证用户（FastAPI 依赖注入）

    使用方式:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    return decode_token(credentials.credentials)


async def get_current_admin(user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    获取当前管理员用户（需要 admin 角色）

    使用方式:
        @app.get("/admin-only")
        async def admin_route(user: TokenData = Depends(get_current_admin)):
            return {"message": "Admin access granted"}
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员角色",
        )
    return user


# ============ 可选认证（不强制要求登录） ============
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """
    获取可选用户（不强制要求登录）

    如果提供了有效的 Token，则返回用户信息；否则返回 None
    """
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials)
    except HTTPException:
        return None
