"""批量预测异步任务."""

import logging
import os
import uuid as _uuid
from datetime import datetime as _dt, timezone as _tz

import pandas as pd
from sqlalchemy import select

from backend.app.tasks.celery_app import celery_app
from backend.app.config import settings

logger = logging.getLogger(__name__)

RESULT_DIR = settings.BATCH_RESULT_DIR
os.makedirs(RESULT_DIR, exist_ok=True)


def _update_progress(task_id: str, **kwargs):
    """Update task progress in Redis."""
    from backend.app.utils.redis_utils import redis_get, redis_set
    key = f"batch_task:{task_id}"
    current = redis_get(key) or {}
    current.update(kwargs)
    redis_set(key, current)


@celery_app.task(bind=True, max_retries=0)
def process_batch(self, task_id: str, filepath: str, filename: str):
    """处理批量预测文件."""
    try:
        _update_progress(task_id, status="processing")

        # 1. Parse file
        if filename.endswith(".csv"):
            df = pd.read_csv(filepath)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f"不支持的文件格式: {filename}")

        total = len(df)
        _update_progress(task_id, total=total, processed=0)

        # 2. Process rows
        import asyncio
        from backend.app.database import engine

        async def _run():
            await engine.dispose()
            return await _process_rows(df, task_id, total)

        results = asyncio.run(_run())

        # 3. Generate result CSV
        result_df = pd.DataFrame(results)
        result_filename = f"{task_id}_result.csv"
        result_path = f"{RESULT_DIR}/{result_filename}"
        result_df.to_csv(result_path, index=False)

        _update_progress(
            task_id,
            status="completed",
            result_filename=result_filename,
            completed_at=_dt.now().isoformat(),
        )

    except Exception as e:
        logger.exception("Batch task %s failed", task_id)
        _update_progress(
            task_id,
            status="failed",
            error_message=str(e),
            completed_at=_dt.now().isoformat(),
        )
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


async def _process_rows(df: pd.DataFrame, task_id: str, total: int) -> list[dict]:
    """逐行处理：特征变换 → 推理 → 持久化."""
    from backend.app.database import async_session
    from backend.app.models.insuree import Insuree
    from backend.app.models.policy import Policy
    from backend.app.models.accident_claim import AccidentClaim
    from backend.app.models.fraud_detect_result import FraudDetectResult
    from backend.app.models.model_info import ModelInfo
    from backend.app.services import model_service, feature_transform

    feature_transform._load_params()
    feature_cols = model_service.get_feature_cols()
    cat_cols = feature_transform.CAT_COLS

    results = []
    success = 0
    failed = 0

    async with async_session() as db:
        model_result = await db.execute(
            select(ModelInfo.model_id).where(ModelInfo.is_active == True).limit(1)
        )
        model_id = model_result.scalar_one_or_none()

        if model_id is None:
            _update_progress(task_id, status="failed", error_message="No active model")
            return []

        for idx, (_, row) in enumerate(df.iterrows()):
            try:
                # Build feature dict from row
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
                        if col == "MBR_CLAIM_COUNT":
                            feature_dict[col] = 0.0
                        elif col == "MBR_AVG_SUB_AMT":
                            feature_dict[col] = 0.0
                        elif col == "MBR_UNIQUE_HOSPITALS":
                            feature_dict[col] = 0.0
                        elif col.endswith("_MISSING"):
                            feature_dict[col] = 0
                        elif col in cat_cols:
                            feature_dict[col] = "UNKNOWN"
                        else:
                            feature_dict[col] = 0.0

                # Run 7-step pipeline
                X = feature_transform.transform_single(feature_dict)
                result = model_service.predict(X)

                # Persist
                insuree_id = _uuid.uuid4().hex
                policy_id = _uuid.uuid4().hex

                insuree = Insuree(insuree_id=insuree_id)
                db.add(insuree)
                await db.flush()

                policy = Policy(policy_id=policy_id, insuree_id=insuree_id, is_synthetic=False)
                db.add(policy)
                await db.flush()

                claim = AccidentClaim(policy_id=policy_id, is_synthetic=False)
                db.add(claim)
                await db.flush()

                now = _dt.now(_tz.utc)
                record = FraudDetectResult(
                    policy_id=policy_id,
                    accident_claim_id=claim.id,
                    model_id=model_id,
                    fraud_prob=result["fraud_prob"],
                    raw_prob=result["raw_prob"],
                    risk_level=result["risk_level"],
                    threshold_used=model_service.get_threshold(),
                    feature_values=feature_dict,
                    shap_values={
                        item["feature"]: item["shap_value"]
                        for item in result["shap_values"]
                    },
                    detect_time=now,
                )
                db.add(record)
                await db.flush()

                out_row = row.to_dict()
                out_row["fraud_prob"] = result["fraud_prob"]
                out_row["risk_level"] = result["risk_level"]
                out_row["shap_top_features"] = ",".join(
                    item["feature"] for item in result["shap_values"][:5]
                )
                results.append(out_row)
                success += 1

            except Exception as e:
                logger.warning("Row %d failed: %s", idx, str(e))
                out_row = row.to_dict()
                out_row["fraud_prob"] = None
                out_row["risk_level"] = "error"
                out_row["shap_top_features"] = ""
                out_row["_error"] = str(e)
                results.append(out_row)
                failed += 1

            if (idx + 1) % 50 == 0:
                await db.commit()
                _update_progress(
                    task_id,
                    processed=idx + 1,
                    success=success,
                    failed=failed,
                )

        await db.commit()
        _update_progress(task_id, processed=total, success=success, failed=failed)

    return results
