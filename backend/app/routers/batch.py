"""批量预测路由 — /api/predict/batch/*."""

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.services import batch_service

router = APIRouter(prefix="/api/predict/batch", tags=["batch"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.post("")
async def upload_batch(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传 CSV/Excel 文件，创建批量预测任务."""
    allowed_ext = (".csv", ".xlsx", ".xls")
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in allowed_ext):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "仅支持 CSV 和 Excel 文件"},
        )

    content = await file.read()
    if len(content) == 0:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "文件为空"},
        )

    result = await batch_service.create_batch_task(
        db, file.filename, content, current_user.user_id
    )
    return ok(result)


@router.get("")
async def list_batch_tasks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户历史批量任务列表."""
    result = await batch_service.list_batch_tasks(db, current_user.user_id, page, size)
    return ok(result)


@router.get("/{task_id}/status")
async def batch_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """查询批量任务进度."""
    result = await batch_service.get_batch_status(task_id)
    return ok(result)


@router.get("/{task_id}/download")
async def batch_download(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """下载批量预测结果 CSV."""
    import os as _os
    path = batch_service.get_result_path(task_id)
    if path is None or not _os.path.exists(path):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "data": None, "message": "结果文件不存在或任务未完成"},
        )
    return FileResponse(path, filename=f"batch_result_{task_id}.csv")
