"""管理面板业务逻辑."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User, UserRole
from backend.app.utils.exceptions import AppException
from backend.app.utils.redis_utils import redis_get


async def list_users(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    username: str | None = None,
) -> tuple[list[User], int]:
    """分页查询用户列表，支持按 username 模糊搜索."""
    base = select(User)
    count_base = select(func.count(User.user_id))

    if username:
        pattern = f"%{username}%"
        base = base.where(User.username.ilike(pattern))
        count_base = count_base.where(User.username.ilike(pattern))

    # 总数
    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * size
    result = await db.execute(
        base.order_by(User.created_at.desc()).offset(offset).limit(size)
    )
    users = result.scalars().all()

    return users, total


async def update_user(
    db: AsyncSession,
    user_id: str,
    user_role: UserRole | None,
    is_active: bool | None,
    operated_by: str,
) -> User:
    """修改用户角色或状态。operated_by 为操作者 ID，禁止修改自己."""
    if user_id == operated_by:
        raise AppException("不能修改自己的角色或状态", status_code=400)

    if user_role is None and is_active is None:
        raise AppException("至少需要修改 role 或 is_active 中的一个", status_code=400)

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppException("用户不存在", status_code=404)

    if user_role is not None:
        user.user_role = user_role
    if is_active is not None:
        user.is_active = is_active

    await db.commit()
    await db.refresh(user)
    return user


async def get_data_task_status(task_id: str) -> dict:
    """从 Redis 查询数据导入任务进度."""
    data = redis_get(f"data_task:{task_id}")
    if data is None:
        raise AppException("任务不存在或已过期", status_code=404)
    data["task_id"] = task_id
    return data
