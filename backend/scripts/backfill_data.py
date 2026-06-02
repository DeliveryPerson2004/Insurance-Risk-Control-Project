"""Seed ~1,000 demo records from training data for Phase 3 development.

Usage:
    docker compose exec backend uv run python backend/scripts/backfill_data.py
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select

from backend.app.database import async_session
from backend.app.models.insuree import Insuree
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.model_info import ModelInfo
from backend.app.models.case_history import CaseHistory
from backend.app.models.user import User
from backend.app.services import model_service, feature_transform

logger = logging.getLogger(__name__)

CSV_DIR = "data/train_eval_test"
CSV_FILES = ["train.csv", "eval.csv", "test.csv"]
MAX_ROWS = 1000  # Full backfill deferred to post-Phase 4


async def backfill():
    # 1. Load & merge CSVs
    dfs = []
    for fname in CSV_FILES:
        path = f"{CSV_DIR}/{fname}"
        df = pd.read_csv(path, nrows=MAX_ROWS // len(CSV_FILES) + 1)
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True).head(MAX_ROWS)

    # 2. Ensure active model_info (hardcoded metrics from training)
    async with async_session() as db:
        existing = await db.execute(
            select(ModelInfo).where(ModelInfo.is_active == True).limit(1)
        )
        model = existing.scalar_one_or_none()

        if model is None:
            model = ModelInfo(
                model_id=str(uuid.uuid4()),
                model_name="XGBoost Fraud Detection v1",
                model_algorithm="XGBoost + IsotonicRegression",
                model_version="1.0.0",
                model_auc=0.9934,
                model_f1=0.9187,
                threshold=0.36,
                feature_count=35,
                is_active=True,
                model_file_path="modeling/xgb_fraud_model.pkl",
            )
            db.add(model)
            await db.flush()
            print(f"Inserted model_info: {model.model_id}")

        model_id = model.model_id

        # Find a reviewer user for CaseHistory FK
        user_result = await db.execute(select(User).limit(1))
        reviewer = user_result.scalar_one_or_none()

        feature_cols = model_service.get_feature_cols()
        feature_transform._load_params()
        cat_cols = feature_transform.CAT_COLS
        now = datetime.now(timezone.utc)
        count = 0

        for _, row in df.iterrows():
            try:
                # 3. Generate IDs
                insuree_id = uuid.uuid4().hex
                policy_id = uuid.uuid4().hex

                # 4. Create insuree
                age_val = None
                gender_val = None
                if "age" in row.index:
                    age_val = int(row["age"]) if pd.notna(row["age"]) else None
                if "gender" in row.index:
                    gender_val = str(row["gender"]) if pd.notna(row["gender"]) else None

                insuree = Insuree(
                    insuree_id=insuree_id,
                    age=age_val,
                    gender=gender_val,
                )
                db.add(insuree)
                await db.flush()

                # 5. Create policy (is_synthetic=False — acts as demo data)
                policy = Policy(
                    policy_id=policy_id,
                    insuree_id=insuree_id,
                    is_synthetic=False,
                )
                db.add(policy)
                await db.flush()

                # 6. Create accident claim
                is_fraud = None
                if "FRAUD" in row.index:
                    is_fraud = int(row["FRAUD"]) if pd.notna(row["FRAUD"]) else None

                claim = AccidentClaim(
                    policy_id=policy_id,
                    is_fraud=is_fraud,
                    is_synthetic=False,
                )
                db.add(claim)
                await db.flush()

                # 7. Predict: CSV is already standardized → direct inference
                feature_dict = {}
                for col in feature_cols:
                    if col in row.index:
                        val = row[col]
                        if pd.isna(val):
                            feature_dict[col] = 0.0 if col not in cat_cols else "UNKNOWN"
                        elif col in cat_cols:
                            feature_dict[col] = str(val)
                        else:
                            feature_dict[col] = float(val)
                    else:
                        feature_dict[col] = 0.0 if col not in cat_cols else "UNKNOWN"

                X = pd.DataFrame([feature_dict])
                for c in cat_cols:
                    if c in X.columns:
                        X[c] = X[c].astype("category")
                X = X[feature_cols]

                result = model_service.predict(X)

                # 8. Random detect time (past 180 days)
                days_ago = random.randint(0, 180)
                detect_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))

                # 9. Write fraud_detect_result
                record = FraudDetectResult(
                    policy_id=policy_id,
                    accident_claim_id=claim.id,
                    model_id=model_id,
                    fraud_prob=result["fraud_prob"],
                    raw_prob=result["raw_prob"],
                    risk_level=result["risk_level"],
                    threshold_used=model_service.get_threshold(),
                    feature_values={k: v for k, v in feature_dict.items() if k in feature_cols},
                    shap_values={item["feature"]: item["shap_value"] for item in result["shap_values"]},
                    detect_time=detect_time,
                )
                db.add(record)
                await db.flush()

                # 10. ~20% get pre-made review history
                if reviewer is not None and random.random() < 0.2:
                    case = CaseHistory(
                        policy_id=policy_id,
                        detect_result_id=record.id,
                        user_id=reviewer.user_id,
                        operate_time=detect_time + timedelta(hours=random.randint(1, 72)),
                        manual_result=random.choices(
                            ["pass", "reject", "investigate"], weights=[0.6, 0.2, 0.2]
                        )[0],
                        remark="Backfill review record",
                    )
                    db.add(case)

            except Exception as e:
                logger.error("Row %d failed: %s", count, str(e))

            count += 1

            if count % 100 == 0:
                await db.commit()
                print(f"  ... {count}/{MAX_ROWS}")

        await db.commit()
        print(f"Backfill complete: {count} records inserted")


if __name__ == "__main__":
    asyncio.run(backfill())
