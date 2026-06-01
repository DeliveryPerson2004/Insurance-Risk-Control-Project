"""单条/批次输入 → 35 特征 DataFrame（与训练时变换一致）."""

import json
import os
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

_PARAMS_PATH = os.path.join(os.path.dirname(__file__), "preprocess_params.json")

with open(_PARAMS_PATH, "r", encoding="utf-8") as f:
    _params = json.load(f)

CAT_COLS: list[str] = _params["cat_cols"]
CONT_COLS: list[str] = _params["cont_cols"]  # 23 个（含 3 个 MBR_*）
FEATURE_COLS: list[str] = _params["feature_cols"]  # 35 个最终列
MISSING_COLS: list[str] = _params["missing_cols"]  # 5 个 *_MISSING
FILL_VALUES: dict[str, float] = _params["fill_values"]
WINSOR_BOUNDS: dict[str, list[float]] = _params["winsor_bounds"]
LOG_PARAMS: dict[str, dict] = _params["log_params"]
SKIP_WINSOR: list[str] = _params["skip_winsor"]
SCALER_PARAMS: dict[str, dict] = _params["scaler_params"]

# 用户可见字段 = 7 类别 + (23 连续 - 3 MBR_*) = 27
MBR_AGG_FEATURES = {"MBR_CLAIM_COUNT", "MBR_AVG_SUB_AMT", "MBR_UNIQUE_HOSPITALS"}


async def compute_member_aggregates(
    db: AsyncSession, insuree_id: str
) -> dict[str, float]:
    """从数据库动态计算当前 insuree 的成员聚合特征.

    Returns:
        {"MBR_CLAIM_COUNT": int, "MBR_AVG_SUB_AMT": float, "MBR_UNIQUE_HOSPITALS": int}
        新 insuree（无历史记录）返回全 0.
    """
    from backend.app.models.accident_claim import AccidentClaim
    from backend.app.models.policy import Policy

    # NOTE: Training used PROV_CODE for unique hospitals, but DB schema lacks this field.
    # Using distinct policy_id as a proxy (each claim typically maps to one provider interaction).
    result = await db.execute(
        select(
            func.count(AccidentClaim.id).label("claim_count"),
            func.coalesce(func.avg(AccidentClaim.claim_amount), 0).label("avg_claim"),
            func.count(func.distinct(Policy.policy_id)).label("unique_hospitals"),
        )
        .join(Policy, AccidentClaim.policy_id == Policy.policy_id)
        .where(Policy.insuree_id == insuree_id)
    )
    row = result.one_or_none()
    if row is None or row.claim_count == 0:
        return {"MBR_CLAIM_COUNT": 0.0, "MBR_AVG_SUB_AMT": 0.0, "MBR_UNIQUE_HOSPITALS": 0.0}

    return {
        "MBR_CLAIM_COUNT": float(row.claim_count),
        "MBR_AVG_SUB_AMT": float(row.avg_claim),
        "MBR_UNIQUE_HOSPITALS": float(row.unique_hospitals),
    }


def transform_single(feature_dict: dict[str, Any]) -> pd.DataFrame:
    """将 35 特征 dict 变换为 (1, 35) DataFrame.

    feature_dict 必须包含全部 35 个字段: 27 用户输入 + 3 MBR_* + 5 *_MISSING.
    """
    df = pd.DataFrame([feature_dict])

    # 0) 缺失标记 — 必须在任何 fill 之前生成，否则 isnull() 恒为假
    for col in MISSING_COLS:
        if col not in df.columns:
            base_col = col.replace("_MISSING", "")
            df[col] = df[base_col].isnull().astype(int) if base_col in df.columns else 0

    # 1) 类别特征 → category dtype（NaN 先用 'UNKNOWN' 填充，与训练一致）
    for col in CAT_COLS:
        if col in df.columns:
            df[col] = df[col].fillna('UNKNOWN').astype(str).astype("category")

    # 2) 连续特征填充缺失
    for col in CONT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            med = FILL_VALUES.get(col, 0)
            df[col] = df[col].fillna(med)

    # 3) Winsor
    for col in CONT_COLS:
        if col in SKIP_WINSOR or col not in df.columns:
            continue
        if col in WINSOR_BOUNDS:
            lo, hi = WINSOR_BOUNDS[col]
            df[col] = df[col].clip(lo, hi)

    # 4) log1p
    for col, lp in LOG_PARAMS.items():
        if col in df.columns:
            mn = lp["min"]
            df[col] = np.log1p(df[col].clip(lower=mn) - mn + 1)

    # 5) StandardScaler
    for col, sp in SCALER_PARAMS.items():
        if col in df.columns:
            mean = sp["mean"]
            std = sp["std"]
            if std > 0:
                df[col] = (df[col] - mean) / std

    # 6) 确保 final 列序
    existing = [c for c in FEATURE_COLS if c in df.columns]
    return df[existing]
