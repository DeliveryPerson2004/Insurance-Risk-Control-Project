"""认证业务逻辑."""

from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
    LoginResponse,
)
from backend.app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.utils.exceptions import AppException


async def register(db: AsyncSession, req: RegisterRequest) -> LoginResponse:
    """注册新用户。首个用户自动成为 admin."""
    # 检查用户名唯一
    existing = await db.execute(
        select(User).where(User.username == req.username)
    )
    if existing.scalar_one_or_none() is not None:
        raise AppException("用户名已存在", code=1001, status_code=409)

    # 检查是否为第一个用户
    count_result = await db.execute(select(User))
    is_first = count_result.first() is None

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.username,
        user_role="admin" if is_first else "reviewer",
        email=req.email,
        phone=req.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = _make_tokens(user)
    return LoginResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def login(db: AsyncSession, username: str, password: str) -> LoginResponse:
    """登录."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise AppException("用户名或密码错误", code=1002, status_code=401)

    if not user.is_active:
        raise AppException("账户已被停用", code=1003, status_code=403)

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    tokens = _make_tokens(user)
    return LoginResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """用 refresh token 换取新的 access token."""
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise AppException("无效的 refresh token", code=1004, status_code=401)

    if payload.get("type") != "refresh":
        raise AppException("token 类型错误", code=1005, status_code=401)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AppException("用户不存在或已停用", code=1006, status_code=401)

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.user_role),
        refresh_token=create_refresh_token(user.user_id),
    )


async def get_me(db: AsyncSession, user_id: str) -> UserResponse:
    """获取当前用户信息."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppException("用户不存在", code=1007, status_code=404)
    return UserResponse.model_validate(user)


def _make_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.user_id, user.user_role),
        refresh_token=create_refresh_token(user.user_id),
    )
