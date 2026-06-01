"""仪表盘 Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel


class DashboardStats(BaseModel):
    today_pending: int
    today_high_risk: int
    today_processed: int
    total_detected: int


class TrendItem(BaseModel):
    date: str
    total: int
    fraud_rate: float


class TrendResponse(BaseModel):
    trend: list[TrendItem]


class HighRiskItem(BaseModel):
    id: int
    policy_id: str
    fraud_prob: float
    risk_level: str
    claim_amount: float | None
    detect_time: datetime


class HighRiskResponse(BaseModel):
    items: list[HighRiskItem]
