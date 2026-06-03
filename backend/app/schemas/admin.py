"""管理面板相关 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel

from backend.app.models.user import UserRole


class UpdateUserRequest(BaseModel):
    user_role: UserRole
    is_active: bool


# 注意: UserOut 与 auth.UserResponse 字段相似但语义独立。
# UserResponse 用于认证响应，UserOut 用于管理面板用户列表。
# 随着 Phase 4 推进，管理视图可能需要额外字段（如 updated_at），
# 两者分开定义以便独立演化。


class UserOut(BaseModel):
    user_id: str
    username: str
    display_name: str
    user_role: str
    email: str | None
    phone: str | None
    is_active: bool
    last_login: datetime | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int
