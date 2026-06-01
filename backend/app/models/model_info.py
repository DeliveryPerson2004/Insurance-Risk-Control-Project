"""model_info — 模型元数据."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ModelInfo(Base):
    __tablename__ = "model_info"

    model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_algorithm: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(32))
    model_auc: Mapped[float | None] = mapped_column(Float)
    model_f1: Mapped[float | None] = mapped_column(Float)
    model_precision: Mapped[float | None] = mapped_column(Float)
    model_recall: Mapped[float | None] = mapped_column(Float)
    pr_auc: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[float | None] = mapped_column(Float)
    feature_count: Mapped[int | None] = mapped_column(Integer)
    cv_f1_mean: Mapped[float | None] = mapped_column(Float)
    cv_f1_std: Mapped[float | None] = mapped_column(Float)
    param_config: Mapped[dict | None] = mapped_column(JSONB)
    train_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    model_file_path: Mapped[str | None] = mapped_column(String(256))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
