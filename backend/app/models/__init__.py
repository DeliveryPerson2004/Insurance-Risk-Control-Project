"""ORM 模型 — 导入全部模型供 Alembic 发现."""

from backend.app.database import Base

# 按依赖顺序导入（有外键的模型后导入），确保 Alembic autogenerate 能解析关系
from backend.app.models.user import User
from backend.app.models.model_info import ModelInfo
from backend.app.models.insuree import Insuree
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.case_history import CaseHistory

__all__ = [
    "Base",
    "User",
    "ModelInfo",
    "Insuree",
    "Policy",
    "AccidentClaim",
    "FraudDetectResult",
    "CaseHistory",
]
