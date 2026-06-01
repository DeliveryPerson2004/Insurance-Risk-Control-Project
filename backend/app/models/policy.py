"""policy_info — 保单."""

from datetime import datetime

from sqlalchemy import String, Float, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Policy(Base):
    __tablename__ = "policy_info"

    policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    insuree_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("insuree_info.insuree_id"), nullable=False, index=True
    )
    insurance_type: Mapped[str | None] = mapped_column(String(64))
    insurance_amount: Mapped[float | None] = mapped_column(Float)
    premium: Mapped[float | None] = mapped_column(Float)
    insure_date: Mapped[datetime | None] = mapped_column(Date)
    effect_date: Mapped[datetime | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    insuree: Mapped["Insuree"] = relationship("Insuree", lazy="selectin")
