"""批量预测业务逻辑 — 上传解析 + 任务管理."""

import os
import uuid
import logging
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.utils.exceptions import AppException
from backend.app.utils.redis_utils import redis_get, redis_set, _get_redis
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Result files directory (mounted/shared with celery-worker)
RESULT_DIR = settings.BATCH_RESULT_DIR
os.makedirs(RESULT_DIR, exist_ok=True)


def _parse_task_key(task_id: str) -> str:
    """Redis key for batch task progress."""
    return f"batch_task:{task_id}"


async def create_batch_task(
    db: AsyncSession,
    filename: str,
    file_content: bytes,
    user_id: str,
) -> dict:
    """保存上传文件，创建 Celery 任务，返回 task_id."""
    task_id = uuid.uuid4().hex

    # Save uploaded file
    upload_dir = f"{RESULT_DIR}/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    filepath = f"{upload_dir}/{task_id}_{filename}"
    with open(filepath, "wb") as f:
        f.write(file_content)

    # Set initial progress in Redis
    key = _parse_task_key(task_id)
    redis_set(key, {
        "status": "pending",
        "total": 0,
        "processed": 0,
        "success": 0,
        "failed": 0,
        "filename": filename,
        "result_filename": None,
        "error_message": None,
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    })

    # Dispatch async task
    from backend.app.tasks.batch_tasks import process_batch
    process_batch.delay(task_id, filepath, filename)

    return {"task_id": task_id, "status": "pending"}


async def get_batch_status(task_id: str, user_id: str) -> dict:
    """查询批量任务进度."""
    key = _parse_task_key(task_id)
    data = redis_get(key)
    if data is None:
        raise AppException(f"任务 {task_id} 不存在", status_code=404)
    if data.get("user_id") != user_id:
        raise AppException("无权访问此任务", status_code=403)
    return data


async def list_batch_tasks(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    size: int = 20,
) -> dict:
    """当前用户历史批量任务列表（从 Redis 扫描实现）."""
    r = _get_redis()
    items = []
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor, match="batch_task:*", count=100)
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            data = redis_get(key_str)
            if data and data.get("user_id") == user_id:
                items.append({
                    "task_id": key_str.replace("batch_task:", ""),
                    "filename": data.get("filename", ""),
                    "status": data.get("status", "unknown"),
                    "total": data.get("total"),
                    "processed": data.get("processed"),
                    "created_at": data.get("created_at", ""),
                    "completed_at": data.get("completed_at"),
                })
        if cursor == 0:
            break

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total = len(items)
    start = (page - 1) * size
    end = start + size
    paged = items[start:end]

    return {"items": paged, "total": total, "page": page, "size": size}


def get_result_path(task_id: str, user_id: str) -> str | None:
    """获取结果文件路径."""
    key = _parse_task_key(task_id)
    data = redis_get(key)
    if data is None or data.get("result_filename") is None:
        return None
    if data.get("user_id") != user_id:
        return None
    return f"{RESULT_DIR}/{data['result_filename']}"
