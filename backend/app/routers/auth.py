"""认证路由 — POST /api/auth/*."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
)
from backend.app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


def ok(data):
    """统一成功响应."""
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.register(db, req)
    return ok(result.model_dump(mode="json"))


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.login(db, req.username, req.password)
    return ok(result.model_dump(mode="json"))


@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.refresh_access_token(db, req.refresh_token)
    return ok(result.model_dump(mode="json"))


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    result = UserResponse.model_validate(current_user)
    return ok(result.model_dump(mode="json"))
