"""case_history — 人工审核历史."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class CaseHistory(Base):
    __tablename__ = "case_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_info.policy_id"), nullable=False, index=True
    )
    detect_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fraud_detect_result.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_info.user_id"), nullable=False
    )
    operate_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    manual_result: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped["Policy"] = relationship("Policy", lazy="selectin")
    detect_result: Mapped["FraudDetectResult"] = relationship(
        "FraudDetectResult", lazy="selectin"
    )
    reviewer: Mapped["User"] = relationship("User", lazy="selectin")
