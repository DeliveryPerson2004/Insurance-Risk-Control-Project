"""仪表盘路由."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await dashboard_service.get_stats(db)
    return ok(data)


@router.get("/trend")
async def trend(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await dashboard_service.get_trend(db, days)
    return ok({"trend": data})


@router.get("/high-risk")
async def high_risk(
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await dashboard_service.get_high_risk(db, limit)
    return ok({"items": data})
