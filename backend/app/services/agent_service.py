"""Agent 业务逻辑 — 生成/缓存/降级."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.agent.interface import CaseContext
from backend.app.agent.deepseek_agent import get_agent
from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


async def analyze_case(
    db: AsyncSession,
    case_id: int,
    force_refresh: bool = False,
) -> dict:
    """为指定案件生成/返回 AI 分析报告."""
    result = await db.execute(
        select(FraudDetectResult)
        .options(selectinload(FraudDetectResult.accident_claim))
        .where(FraudDetectResult.id == case_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise AppException(f"案件 {case_id} 不存在", status_code=404)

    # Check cache
    if not force_refresh and record.agent_report is not None:
        ar = record.agent_report
        return {
            "report": ar.get("report_text"),
            "model_used": ar.get("model_used"),
            "cached": True,
            "fallback": False,
            "error": None,
        }

    # Build CaseContext
    shap_top10 = _extract_shap_top10(record)
    claim = record.accident_claim

    ctx = CaseContext(
        case_id=record.id,
        fraud_prob=record.fraud_prob,
        risk_level=record.risk_level,
        threshold_used=record.threshold_used or 0.36,
        claim_amount=claim.claim_amount if claim else None,
        icd10_chapter=_get_feature_val(record, "ICD10_CHAPTER"),
        shap_top10=shap_top10,
    )

    # Call agent (with fallback)
    try:
        agent = get_agent()
        report = await agent.generate_report(ctx)

        # Write cache
        record.agent_report = {
            "report_text": report.report_text,
            "model_used": report.model_used,
            "tokens_used": report.tokens_used,
            "generated_at": report.generated_at,
        }
        await db.commit()

        return {
            "report": report.report_text,
            "model_used": report.model_used,
            "cached": False,
            "fallback": False,
            "error": None,
        }

    except Exception as e:
        logger.exception("Agent failed for case %d", case_id)
        return {
            "report": None,
            "model_used": None,
            "cached": False,
            "fallback": True,
            "error": "Agent service unavailable",
        }


async def check_health() -> dict:
    """Agent 健康检查."""
    try:
        agent = get_agent()
        available = await agent.health_check()
    except Exception:
        available = False
    return {"available": available}


def _extract_shap_top10(record: FraudDetectResult) -> list[dict]:
    """从 shap_values JSONB 提取 Top 10 SHAP 特征."""
    sv = record.shap_values or {}
    fv = record.feature_values or {}
    items = []
    for feature, shap_val in sv.items():
        items.append({
            "feature": feature,
            "value": fv.get(feature, "N/A"),
            "shap_value": shap_val,
            "direction": "+" if shap_val > 0 else "-",
        })
    items.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return items[:10]


def _get_feature_val(record: FraudDetectResult, key: str) -> str | None:
    fv = record.feature_values or {}
    val = fv.get(key)
    return str(val) if val is not None else None
