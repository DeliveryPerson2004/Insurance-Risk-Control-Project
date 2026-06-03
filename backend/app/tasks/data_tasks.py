"""数据导入异步任务 — 预处理 + 推理 + 入库."""

import logging
import os
import uuid as _uuid
from datetime import datetime as _dt, timezone as _tz

import pandas as pd
from sqlalchemy import select

from backend.app.tasks.celery_app import celery_app
from backend.app.config import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(settings.BATCH_RESULT_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _update_progress(task_id: str, **kwargs):
    from backend.app.utils.redis_utils import redis_get, redis_set
    key = f"data_task:{task_id}"
    current = redis_get(key) or {}
    current.update(kwargs)
    redis_set(key, current)


@celery_app.task(bind=True, max_retries=0)
def process_data_import(self, task_id: str, filepath: str, filename: str):
    """处理数据导入: 预处理 → 特征变换 → 推理 → 入库."""
    try:
        _update_progress(task_id, status="processing")

        # 1. 解析 Excel
        if not filename.lower().endswith((".xlsx", ".xls")):
            raise ValueError(f"不支持的文件格式: {filename}")

        df = pd.read_excel(filepath, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        df = df.drop_duplicates()

        total = len(df)
        _update_progress(task_id, total=total, processed=0, step="preprocessing")

        # 2. 预处理: 108列 → 30特征 (raw)
        from backend.app.services.preprocess_service import preprocess_raw_excel
        feature_df = preprocess_raw_excel(df)
        feature_cols = list(feature_df.columns)
        del df

        _update_progress(task_id, step="inference")

        # 3. 逐行: 特征变换 → 推理 → 入库
        import asyncio
        results = asyncio.run(
            _process_rows(feature_df, feature_cols, task_id, total)
        )

        _update_progress(
            task_id,
            status="completed",
            completed_at=_dt.now().isoformat(),
        )
        return results

    except Exception as e:
        logger.exception("Data import task %s failed", task_id)
        _update_progress(
            task_id,
            status="failed",
            error_message=str(e),
            completed_at=_dt.now().isoformat(),
        )
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


async def _process_rows(
    feature_df: pd.DataFrame,
    feature_cols: list[str],
    task_id: str,
    total: int,
) -> dict:
    """逐行处理: 特征变换 → 推理 → 持久化.

    feature_df 有 30 列（preprocess_service 输出），需补齐 5 个 _MISSING
    标记列再传给 transform_single（它要求完整的 35 特征）。
    """
    from backend.app.database import async_session
    from backend.app.models.insuree import Insuree
    from backend.app.models.policy import Policy
    from backend.app.models.accident_claim import AccidentClaim
    from backend.app.models.fraud_detect_result import FraudDetectResult
    from backend.app.models.model_info import ModelInfo
    from backend.app.services import model_service, feature_transform

    feature_transform._load_params()
    cat_cols = feature_transform.CAT_COLS
    missing_cols = feature_transform.MISSING_COLS  # e.g. ['TOTAL_RECEIPT_AMT_MISSING', ...]

    success = 0
    failed = 0

    async with async_session() as db:
        model_result = await db.execute(
            select(ModelInfo.model_id).where(ModelInfo.is_active == True).limit(1)
        )
        model_id = model_result.scalar_one_or_none()

        if model_id is None:
            _update_progress(task_id, status="failed", error_message="No active model")
            return {"success": 0, "failed": 0}

        for idx, (_, row) in enumerate(feature_df.iterrows()):
            try:
                # Build feature dict from 30 preprocessed columns
                feature_dict = {}
                for col in feature_cols:
                    val = row[col]
                    if pd.isna(val):
                        feature_dict[col] = 0.0 if col not in cat_cols else "UNKNOWN"
                    elif col in cat_cols:
                        feature_dict[col] = str(val)
                    else:
                        feature_dict[col] = float(val)

                # 补齐 _MISSING 标记列（transform_single 要求完整 35 特征）
                for mc in missing_cols:
                    base_col = mc.replace("_MISSING", "")
                    if base_col in feature_dict:
                        feature_dict[mc] = 1 if pd.isna(row[base_col]) else 0
                    else:
                        feature_dict[mc] = 0

                # 7-step transform → model inference
                X = feature_transform.transform_single(feature_dict)
                result = model_service.predict(X)

                # Persist
                insuree = Insuree(
                    insuree_id=_uuid.uuid4().hex,
                )
                db.add(insuree)
                await db.flush()

                policy = Policy(
                    policy_id=_uuid.uuid4().hex,
                    insuree_id=insuree.insuree_id,
                    is_synthetic=False,
                )
                db.add(policy)
                await db.flush()

                claim = AccidentClaim(
                    policy_id=policy.policy_id,
                    is_synthetic=False,
                )
                db.add(claim)
                await db.flush()

                now = _dt.now(_tz.utc)
                record = FraudDetectResult(
                    policy_id=policy.policy_id,
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

                success += 1

            except Exception as e:
                logger.warning("Row %d failed: %s", idx, str(e))
                failed += 1

            if (idx + 1) % 100 == 0:
                await db.commit()
                _update_progress(
                    task_id,
                    processed=idx + 1,
                    success=success,
                    failed=failed,
                )

        await db.commit()
        _update_progress(
            task_id, processed=total, success=success, failed=failed
        )

    return {"success": success, "failed": failed}
