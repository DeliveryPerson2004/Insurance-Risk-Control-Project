"""Agent 路由 — /api/agent/*."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.agent import AnalyzeRequest
from backend.app.services import agent_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/health")
async def agent_health(current_user: User = Depends(get_current_user)):
    result = await agent_service.check_health()
    return ok(result)


@router.post("/analyze")
async def analyze(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await agent_service.analyze_case(db, req.case_id, req.force_refresh)
    return ok(result)
