"""批量预测 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class BatchTaskStatus(BaseModel):
    """GET /batch/{task_id}/status 响应."""
    task_id: str
    status: str  # pending / processing / completed / failed
    total: int
    processed: int
    success: int
    failed: int
    result_filename: str | None = None
    error_message: str | None = None


class BatchTaskItem(BaseModel):
    """GET /batch 列表项."""
    task_id: str
    filename: str
    status: str
    total: int | None = None
    processed: int | None = None
    created_at: str
    completed_at: str | None = None


class BatchTaskListResponse(BaseModel):
    items: list[BatchTaskItem]
    total: int
    page: int
    size: int
