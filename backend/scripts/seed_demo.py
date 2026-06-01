"""Seed ~100 demo prediction records for Phase 2 dashboard development."""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.app.database import async_session
from backend.app.models.insuree import Insuree
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.model_info import ModelInfo
from backend.app.models.case_history import CaseHistory
from backend.app.models.user import User


async def seed() -> None:
    async with async_session() as db:
        # 1. Ensure active model
        model_result = await db.execute(
            select(ModelInfo).where(ModelInfo.is_active == True).limit(1)
        )
        model = model_result.scalar_one_or_none()
        if model is None:
            print("No active model found — skipping seed")
            return

        # 2. Ensure insuree
        insuree_result = await db.execute(select(Insuree).limit(1))
        insuree = insuree_result.scalar_one_or_none()
        if insuree is None:
            insuree = Insuree(
                insuree_id="DEMO-001",
                age=35,
                gender="M",
            )
            db.add(insuree)
            await db.flush()
            insuree_id = "DEMO-001"
        else:
            insuree_id = insuree.insuree_id

        # 3. Find a reviewer user (needed for CaseHistory FK)
        user_result = await db.execute(select(User).limit(1))
        reviewer = user_result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        risk_levels = ["high"] * 15 + ["medium"] * 30 + ["low"] * 55

        for i in range(100):
            # Synthetic policy
            policy_id = f"SEED-{uuid.uuid4().hex[:8]}"
            policy = Policy(
                policy_id=policy_id,
                insuree_id=insuree_id,
                is_synthetic=True,
            )
            db.add(policy)
            await db.flush()

            # Synthetic accident claim
            claim = AccidentClaim(
                policy_id=policy_id,
                claim_amount=round(random.uniform(100, 20_000), 2),
                is_synthetic=True,
            )
            db.add(claim)
            await db.flush()

            # Random detect time (past 30 days)
            days_ago = random.randint(0, 30)
            detect_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))

            risk_level = random.choice(risk_levels)
            if risk_level == "high":
                fraud_prob = round(random.uniform(0.7, 0.99), 4)
            elif risk_level == "medium":
                fraud_prob = round(random.uniform(0.36, 0.7), 4)
            else:
                fraud_prob = round(random.uniform(0.01, 0.36), 4)

            record = FraudDetectResult(
                policy_id=policy_id,
                accident_claim_id=claim.id,
                model_id=model.model_id,
                fraud_prob=fraud_prob,
                raw_prob=round(fraud_prob - random.uniform(-0.05, 0.05), 4),
                risk_level=risk_level,
                threshold_used=0.36,
                feature_values={},
                shap_values={},
                detect_time=detect_time,
            )
            db.add(record)

            # ~30% of records get a review history (only if a reviewer user exists)
            if reviewer is not None and random.random() < 0.3:
                await db.flush()
                case = CaseHistory(
                    policy_id=policy_id,
                    detect_result_id=record.id,
                    user_id=reviewer.user_id,
                    operate_time=detect_time + timedelta(hours=random.randint(1, 48)),
                    manual_result=random.choice(["pass", "reject", "investigate"]),
                    remark="Demo review record",
                )
                db.add(case)

        await db.commit()
        print("Seed: inserted 100 fraud_detect_result records + companion policy/claim rows")


if __name__ == "__main__":
    asyncio.run(seed())
