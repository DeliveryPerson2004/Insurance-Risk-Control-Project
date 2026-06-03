"""管理面板路由 — 用户管理."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import require_admin
from backend.app.models.user import User
from backend.app.schemas.admin import UpdateUserRequest, UserOut, UserListResponse
from backend.app.services import admin_service
import uuid as _uuid
import os as _os
from fastapi import UploadFile, File
from backend.app.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

# 注: 暂复用 BATCH_RESULT_DIR 作为上传目录父路径。文件为临时存储，
# Celery 任务完成后自动清理，生产环境建议独立配置 DATA_UPLOAD_DIR。
UPLOAD_DIR = _os.path.join(settings.BATCH_RESULT_DIR, "uploads")
_os.makedirs(UPLOAD_DIR, exist_ok=True)


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
        ).model_dump(mode="json")
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
    return ok(UserOut.model_validate(updated).model_dump(mode="json"))


@router.post("/data/upload")
async def upload_data(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
):
    """上传原始 Excel，创建数据导入任务."""
    allowed_ext = (".xlsx", ".xls")
    if not file.filename or not file.filename.lower().endswith(allowed_ext):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "仅支持 Excel 文件 (.xlsx/.xls)"},
        )

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "文件大小不能超过 100MB"},
        )
    if len(content) == 0:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "文件为空"},
        )

    task_id = _uuid.uuid4().hex
    filepath = _os.path.join(UPLOAD_DIR, f"{task_id}.xlsx")
    with open(filepath, "wb") as f:
        f.write(content)

    from backend.app.utils.redis_utils import redis_set
    from datetime import datetime as _dt

    redis_set(
        f"data_task:{task_id}",
        {
            "filename": file.filename,
            "status": "pending",
            "created_at": _dt.now().isoformat(),
        },
    )

    from backend.app.tasks.data_tasks import process_data_import
    process_data_import.delay(task_id, filepath, file.filename)

    return ok({"task_id": task_id})


@router.get("/data/tasks")
async def list_data_tasks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_admin),
):
    """历史数据导入任务列表."""
    from backend.app.utils.redis_utils import _get_redis, redis_get

    r = _get_redis()
    keys = [k.decode() for k in r.scan_iter("data_task:*") if b":" in k]
    items = []
    for key in keys:
        data = redis_get(key)
        if data:
            data["task_id"] = key.split(":", 1)[1]
            items.append(data)

    # 按创建时间降序
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total = len(items)
    offset = (page - 1) * size
    paged = items[offset : offset + size]

    from backend.app.schemas.admin import DataTaskStatus, DataTaskListResponse
    return ok(
        DataTaskListResponse(
            items=[DataTaskStatus(**it) for it in paged],
            total=total,
            page=page,
            size=size,
        ).model_dump(mode="json")
    )


@router.get("/data/tasks/{task_id}/status")
async def data_task_status(
    task_id: str,
    current_user: User = Depends(require_admin),
):
    """查询数据导入任务进度."""
    from backend.app.services.admin_service import get_data_task_status
    data = await get_data_task_status(task_id)
    return ok(data)
