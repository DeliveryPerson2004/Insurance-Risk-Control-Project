"""accident_claim_info — 事故理赔."""

from datetime import datetime, date

from sqlalchemy import (
    String, Float, Integer, Boolean, Date, DateTime, ForeignKey, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class AccidentClaim(Base):
    __tablename__ = "accident_claim_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_info.policy_id"), nullable=False, index=True
    )
    accident_date: Mapped[date | None] = mapped_column(Date)
    accident_type: Mapped[str | None] = mapped_column(String(64))
    has_witness: Mapped[bool | None] = mapped_column(Boolean)
    claim_amount: Mapped[float | None] = mapped_column(Float)
    claim_date: Mapped[date | None] = mapped_column(Date)
    is_paid: Mapped[bool | None] = mapped_column(Boolean)
    paid_amount: Mapped[float | None] = mapped_column(Float)
    # 仅回填脚本写入真实标签，运行时新案件为 NULL
    is_fraud: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped["Policy"] = relationship("Policy", lazy="selectin")
