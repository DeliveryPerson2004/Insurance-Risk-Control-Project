"""预测路由 — GET /api/predict/field-options, POST /api/predict/single."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.predict import PredictSingleRequest
from backend.app.services import predict_service

router = APIRouter(prefix="/api/predict", tags=["predict"])


def ok(data):
    """统一成功响应."""
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/field-options")
async def field_options(current_user: User = Depends(get_current_user)):
    result = await predict_service.get_field_options()
    return ok(result)


@router.post("/single")
async def single_predict(
    req: PredictSingleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await predict_service.predict_single(db, req)
    return ok(result.model_dump(mode="json"))
