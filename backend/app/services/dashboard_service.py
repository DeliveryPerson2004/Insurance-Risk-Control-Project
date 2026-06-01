"""仪表盘聚合查询."""

from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.case_history import CaseHistory


async def get_stats(db: AsyncSession) -> dict:
    """今日待审、今日高风险、今日已处理、累计总量."""
    today = date.today()

    # 今日待审：今日产生且 manual_result IS NULL
    pending_result = await db.execute(
        select(func.count(FraudDetectResult.id)).where(
            FraudDetectResult.detect_time >= today,
            FraudDetectResult.manual_result == None,
        )
    )
    today_pending = pending_result.scalar() or 0

    # 今日高风险
    high_risk_result = await db.execute(
        select(func.count(FraudDetectResult.id)).where(
            FraudDetectResult.detect_time >= today,
            FraudDetectResult.risk_level == "high",
        )
    )
    today_high_risk = high_risk_result.scalar() or 0

    # 今日已处理
    processed_result = await db.execute(
        select(func.count(CaseHistory.id)).where(
            CaseHistory.operate_time >= today,
        )
    )
    today_processed = processed_result.scalar() or 0

    # 累计
    total_result = await db.execute(
        select(func.count(FraudDetectResult.id))
    )
    total_detected = total_result.scalar() or 0

    return {
        "today_pending": today_pending,
        "today_high_risk": today_high_risk,
        "today_processed": today_processed,
        "total_detected": total_detected,
    }


async def get_trend(db: AsyncSession, days: int = 30) -> list[dict]:
    """每日检测量 + 欺诈率."""
    since = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(FraudDetectResult.detect_time).label("d"),
            func.count(FraudDetectResult.id).label("total"),
            func.count().filter(FraudDetectResult.risk_level == "high").label("high_cnt"),
        )
        .where(FraudDetectResult.detect_time >= since)
        .group_by("d")
        .order_by("d")
    )
    rows = result.all()
    trend = []
    for row in rows:
        trend.append({
            "date": str(row.d),
            "total": row.total,
            "fraud_rate": round(row.high_cnt / row.total, 4) if row.total > 0 else 0.0,
        })
    return trend


async def get_high_risk(db: AsyncSession, limit: int = 5) -> list[dict]:
    """高风险 Top N."""
    result = await db.execute(
        select(
            FraudDetectResult.id,
            FraudDetectResult.policy_id,
            FraudDetectResult.fraud_prob,
            FraudDetectResult.risk_level,
            AccidentClaim.claim_amount,
            FraudDetectResult.detect_time,
        )
        .join(AccidentClaim, FraudDetectResult.accident_claim_id == AccidentClaim.id)
        .where(FraudDetectResult.risk_level == "high")
        .order_by(FraudDetectResult.fraud_prob.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": row.id,
            "policy_id": row.policy_id,
            "fraud_prob": row.fraud_prob,
            "risk_level": row.risk_level,
            "claim_amount": row.claim_amount,
            "detect_time": row.detect_time,
        }
        for row in rows
    ]
