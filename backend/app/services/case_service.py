"""案件管理业务逻辑 — 列表/详情/判定."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.policy import Policy
from backend.app.models.insuree import Insuree
from backend.app.models.case_history import CaseHistory
from backend.app.models.user import User
from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


async def list_cases(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    risk_level: str | None = None,
    manual_result: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    keyword: str | None = None,
) -> dict:
    """分页列表，支持多维筛选."""
    if date_from:
        date_from = datetime.fromisoformat(date_from)
    if date_to:
        date_to = datetime.fromisoformat(date_to)

    stmt = select(
        FraudDetectResult.id,
        FraudDetectResult.policy_id,
        FraudDetectResult.fraud_prob,
        FraudDetectResult.raw_prob,
        FraudDetectResult.risk_level,
        FraudDetectResult.manual_result,
        FraudDetectResult.detect_time,
        FraudDetectResult.agent_report,
        AccidentClaim.claim_amount,
    ).join(
        AccidentClaim, FraudDetectResult.accident_claim_id == AccidentClaim.id
    )

    conditions = []
    if risk_level:
        conditions.append(FraudDetectResult.risk_level == risk_level)
    if manual_result:
        if manual_result == "pending":
            conditions.append(FraudDetectResult.manual_result == None)
        else:
            conditions.append(FraudDetectResult.manual_result == manual_result)
    if date_from:
        conditions.append(FraudDetectResult.detect_time >= date_from)
    if date_to:
        conditions.append(FraudDetectResult.detect_time <= date_to)
    if keyword:
        keyword = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(FraudDetectResult.policy_id.ilike(f"%{keyword}%"))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate with ordering: high risk first, then by detect_time desc
    stmt = stmt.order_by(
        desc(FraudDetectResult.risk_level == "high"),
        desc(FraudDetectResult.detect_time),
    ).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        items.append({
            "id": row.id,
            "policy_id": row.policy_id,
            "fraud_prob": row.fraud_prob,
            "raw_prob": row.raw_prob,
            "risk_level": row.risk_level,
            "claim_amount": row.claim_amount,
            "manual_result": row.manual_result,
            "detect_time": row.detect_time,
            "has_agent_report": row.agent_report is not None,
        })

    return {"items": items, "total": total, "page": page, "size": size}


async def get_case_detail(db: AsyncSession, case_id: int) -> dict:
    """案件详情，含完整的关联查询."""
    result = await db.execute(
        select(FraudDetectResult)
        .options(
            selectinload(FraudDetectResult.policy).selectinload(Policy.insuree),
            selectinload(FraudDetectResult.accident_claim),
        )
        .where(FraudDetectResult.id == case_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise AppException(f"案件 {case_id} 不存在", status_code=404)

    # Get case history with reviewer names
    history_result = await db.execute(
        select(CaseHistory, User.display_name)
        .join(User, CaseHistory.user_id == User.user_id)
        .where(CaseHistory.detect_result_id == case_id)
        .order_by(CaseHistory.operate_time.desc())
    )
    history_rows = history_result.all()

    return _build_detail(record, history_rows)


def _build_detail(record, history_rows) -> dict:
    """组装 FullDetailCase 响应."""
    policy = record.policy
    insuree = policy.insuree if policy else None
    claim = record.accident_claim

    detail = {
        "id": record.id,
        "policy_id": record.policy_id,
        "fraud_prob": record.fraud_prob,
        "raw_prob": record.raw_prob,
        "risk_level": record.risk_level,
        "threshold_used": record.threshold_used,
        "feature_values": record.feature_values,
        "shap_values": record.shap_values,
        "agent_report": record.agent_report,
        "manual_result": record.manual_result,
        "detect_time": record.detect_time,
        "insuree": {
            "insuree_id": insuree.insuree_id,
            "age": insuree.age,
            "gender": insuree.gender,
            "occupation": insuree.occupation,
        } if insuree else None,
        "policy": {
            "policy_id": policy.policy_id,
            "insurance_type": policy.insurance_type,
            "insurance_amount": policy.insurance_amount,
            "premium": policy.premium,
        } if policy else None,
        "accident_claim": {
            "id": claim.id,
            "accident_date": claim.accident_date.isoformat() if claim and claim.accident_date else None,
            "accident_type": claim.accident_type,
            "claim_amount": claim.claim_amount,
            "claim_date": claim.claim_date.isoformat() if claim and claim.claim_date else None,
            "is_fraud": claim.is_fraud,
            "is_paid": claim.is_paid,
        } if claim else None,
        "case_history": [
            {
                "id": ch.id,
                "manual_result": ch.manual_result,
                "remark": ch.remark,
                "operate_time": ch.operate_time,
                "reviewer_name": reviewer_name,
            }
            for ch, reviewer_name in history_rows
        ],
    }
    return detail


async def adjudicate_case(
    db: AsyncSession,
    case_id: int,
    manual_result: str,
    remark: str | None,
    user_id: str,
) -> dict:
    """人工判定 — 更新 manual_result + 写入 case_history."""
    result = await db.execute(
        select(FraudDetectResult).where(FraudDetectResult.id == case_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise AppException(f"案件 {case_id} 不存在", status_code=404)

    record.manual_result = manual_result
    now = datetime.now(timezone.utc)
    record.updated_at = now

    history = CaseHistory(
        policy_id=record.policy_id,
        detect_result_id=record.id,
        user_id=user_id,
        manual_result=manual_result,
        remark=remark,
        operate_time=now,
    )
    db.add(history)
    await db.flush()

    return {"id": history.id, "manual_result": manual_result, "operate_time": now.isoformat()}


async def get_case_stats(db: AsyncSession) -> dict:
    """聚合统计."""
    risk_result = await db.execute(
        select(
            FraudDetectResult.risk_level,
            func.count(FraudDetectResult.id),
        ).group_by(FraudDetectResult.risk_level)
    )
    by_risk = {row.risk_level: row.count for row in risk_result.all()}
    for level in ("high", "medium", "low"):
        by_risk.setdefault(level, 0)

    mr_result = await db.execute(
        select(
            func.coalesce(FraudDetectResult.manual_result, "pending"),
            func.count(FraudDetectResult.id),
        ).group_by(FraudDetectResult.manual_result)
    )
    by_mr = {row[0]: row[1] for row in mr_result.all()}

    total_result = await db.execute(select(func.count(FraudDetectResult.id)))
    total = total_result.scalar() or 0

    return {
        "total": total,
        "by_risk_level": by_risk,
        "by_manual_result": by_mr,
    }
