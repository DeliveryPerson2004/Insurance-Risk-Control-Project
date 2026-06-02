"""案件管理路由 — /api/cases/*."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.case import AdjudicateRequest
from backend.app.services import case_service

router = APIRouter(prefix="/api/cases", tags=["cases"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("")
async def list_cases(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    risk_level: str | None = Query(default=None),
    manual_result: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await case_service.list_cases(
        db, page, size, risk_level, manual_result, date_from, date_to, keyword,
    )
    return ok(result)


@router.get("/stats/summary")
async def stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await case_service.get_case_stats(db)
    return ok(result)


@router.get("/{case_id}")
async def case_detail(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await case_service.get_case_detail(db, case_id)
    return ok(result)


@router.put("/{case_id}/adjudicate")
async def adjudicate(
    case_id: int,
    req: AdjudicateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await case_service.adjudicate_case(
        db, case_id, req.manual_result, req.remark, current_user.user_id,
    )
    await db.commit()
    return ok(result)
