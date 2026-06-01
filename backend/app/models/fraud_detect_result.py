"""fraud_detect_result — AI 预测结果."""

from datetime import datetime

from sqlalchemy import (
    String, Float, Integer, DateTime, ForeignKey, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class FraudDetectResult(Base):
    __tablename__ = "fraud_detect_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_info.policy_id"), nullable=False, index=True
    )
    accident_claim_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accident_claim_info.id"),
        unique=True,
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("model_info.model_id"), nullable=False
    )
    fraud_prob: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    raw_prob: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    threshold_used: Mapped[float | None] = mapped_column(Float)
    feature_values: Mapped[dict | None] = mapped_column(JSONB)
    shap_values: Mapped[dict | None] = mapped_column(JSONB)
    agent_report: Mapped[dict | None] = mapped_column(JSONB)
    detect_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
    manual_result: Mapped[str | None] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped["Policy"] = relationship("Policy", lazy="selectin")
    accident_claim: Mapped["AccidentClaim"] = relationship(
        "AccidentClaim", lazy="selectin"
    )
    model: Mapped["ModelInfo"] = relationship("ModelInfo", lazy="selectin")
