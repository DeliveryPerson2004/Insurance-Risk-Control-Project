"""管理面板相关 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class UpdateUserRequest(BaseModel):
    user_role: str = Field(..., pattern="^(admin|reviewer)$")
    is_active: bool


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
