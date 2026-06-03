"""管理面板路由 — 用户管理."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import require_admin
from backend.app.models.user import User
from backend.app.schemas.admin import UpdateUserRequest, UserOut, UserListResponse
from backend.app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    username: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users, total = await admin_service.list_users(db, page, size, username)
    return ok(
        UserListResponse(
            items=[UserOut.model_validate(u) for u in users],
            total=total,
            page=page,
            size=size,
        ).model_dump()
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    updated = await admin_service.update_user(
        db, user_id, body.user_role, body.is_active, current_user.user_id
    )
    return ok(UserOut.model_validate(updated).model_dump())
