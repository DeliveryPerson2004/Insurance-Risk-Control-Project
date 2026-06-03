"""预测相关 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class FieldOption(BaseModel):
    """field-options 响应中的单个字段 meta."""
    name: str
    label: str
    type: str  # "select" | "number"
    group: str
    required: bool
    # select 专属
    options: list[str] | None = None
    # number 专属
    min: float | None = None
    step: float | None = None
    placeholder: str | None = None


class FieldOptionsResponse(BaseModel):
    fields: list[FieldOption]
    groups: list[str]


class PredictSingleRequest(BaseModel):
    """27 个可见字段 + insuree_id."""
    insuree_id: str = Field(..., min_length=1, max_length=64)

    # 7 个类别特征
    ICD10_CHAPTER: str
    BH_PREFIX: str
    BH_CATEGORY: str
    MBR_TYPE: str
    BEN_TYPE: str
    KIND_CODE: str
    POCY_PLAN_DESC: str

    # 20 个普通连续特征
    SUB_AMT: float
    TOTAL_RECEIPT_AMT: float
    ORG_PRES_AMT_VALUE: float
    COPAY_PCT: float
    NO_OF_YR: float
    POLICY_CNT: float
    INVOICE_CNT: float
    DAYS_INCUR_TO_PAY: float
    DAYS_RCV_TO_CLOSE: float
    DAYS_HOSPITALIZATION: float
    DAYS_RCV_TO_PAY: float
    IS_INPATIENT: int
    INCUR_MONTH: int
    INCUR_DAYOFWEEK: int
    INCUR_QUARTER: int
    INCUR_IS_WEEKEND: int
    PROV_LEVEL_ORDINAL: int
    RECEIPT_TO_SUB_RATIO: float
    IS_NEW_INSURED: int
    IS_LONGTERM_INSURED: int


class ShapItem(BaseModel):
    feature: str
    value: float | str  # 类别特征的值为字符串（如 "BLOOD"），连续特征为 float
    shap_value: float
    direction: str  # "+" 或 "-"


class PredictSingleResponse(BaseModel):
    id: int
    policy_id: str
    fraud_prob: float
    raw_prob: float
    risk_level: str
    threshold_used: float
    feature_values: dict
    shap_top10: list[ShapItem]
    detect_time: datetime
