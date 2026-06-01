"""FastAPI 依赖注入 — 认证 + 权限."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.utils.security import decode_token
from backend.app.utils.exceptions import AppException

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT 解析当前用户，返回 ORM 对象."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise AppException("token 无效或已过期", code=401, status_code=401)

    if payload.get("type") != "access":
        raise AppException("token 类型错误，请使用 access token", code=401, status_code=401)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AppException("用户不存在或已停用", code=401, status_code=401)

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """仅允许 admin 角色."""
    if current_user.user_role != "admin":
        raise AppException("需要管理员权限", code=403, status_code=403)
    return current_user
