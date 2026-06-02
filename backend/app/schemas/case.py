"""案件管理 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class CaseListItem(BaseModel):
    """GET /cases 列表项."""
    id: int
    policy_id: str
    fraud_prob: float
    raw_prob: float | None = None
    risk_level: str
    claim_amount: float | None = None
    manual_result: str | None = None
    detect_time: datetime
    has_agent_report: bool = False


class CaseListResponse(BaseModel):
    items: list[CaseListItem]
    total: int
    page: int
    size: int


class CaseDetailInsuree(BaseModel):
    insuree_id: str
    age: int | None = None
    gender: str | None = None
    occupation: str | None = None


class CaseDetailPolicy(BaseModel):
    policy_id: str
    insurance_type: str | None = None
    insurance_amount: float | None = None
    premium: float | None = None


class CaseDetailClaim(BaseModel):
    id: int
    accident_date: str | None = None
    accident_type: str | None = None
    claim_amount: float | None = None
    claim_date: str | None = None
    is_fraud: int | None = None
    is_paid: int | None = None


class CaseHistoryItem(BaseModel):
    id: int
    manual_result: str | None = None
    remark: str | None = None
    operate_time: datetime
    reviewer_name: str | None = None


class CaseDetailResponse(BaseModel):
    """GET /cases/{id} 响应."""
    id: int
    policy_id: str
    fraud_prob: float
    raw_prob: float | None = None
    risk_level: str
    threshold_used: float | None = None
    feature_values: dict | None = None
    shap_values: dict | None = None
    agent_report: dict | None = None
    manual_result: str | None = None
    detect_time: datetime
    insuree: CaseDetailInsuree | None = None
    policy: CaseDetailPolicy | None = None
    accident_claim: CaseDetailClaim | None = None
    case_history: list[CaseHistoryItem] = []


class AdjudicateRequest(BaseModel):
    """PUT /cases/{id}/adjudicate."""
    manual_result: str = Field(..., pattern="^(pass|reject|investigate)$")
    remark: str | None = Field(None, max_length=512)


class CaseStatsSummary(BaseModel):
    """GET /cases/stats/summary."""
    total: int
    by_risk_level: dict[str, int]
    by_manual_result: dict[str, int]
