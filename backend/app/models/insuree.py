"""insuree_info — 被保险人."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Insuree(Base):
    __tablename__ = "insuree_info"

    insuree_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(16))
    occupation: Mapped[str | None] = mapped_column(String(128))
    marital_status: Mapped[str | None] = mapped_column(String(32))
    claim_times: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
