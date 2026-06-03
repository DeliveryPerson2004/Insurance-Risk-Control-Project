"""单条/批次输入 → 35 特征 DataFrame（与训练时变换一致）."""

import json
import logging
import os
import threading
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)

_PARAMS_PATH = os.path.join(os.path.dirname(__file__), "preprocess_params.json")

# ---- 模块级惰性加载（仿 model_service.py 的 _load_model 模式） ----
_params: dict | None = None
CAT_COLS: list[str] = []
CONT_COLS: list[str] = []
FEATURE_COLS: list[str] = []
MISSING_COLS: list[str] = []
FILL_VALUES: dict[str, float] = {}
WINSOR_BOUNDS: dict[str, list[float]] = {}
LOG_PARAMS: dict[str, dict] = {}
SKIP_WINSOR: list[str] = []
SCALER_PARAMS: dict[str, dict] = {}

# 用户可见字段 = 7 类别 + (23 连续 - 3 MBR_*) = 27
MBR_AGG_FEATURES = {"MBR_CLAIM_COUNT", "MBR_AVG_SUB_AMT", "MBR_UNIQUE_HOSPITALS"}
_lock = threading.Lock()


def _load_params():
    """惰性加载预处理参数（首次调用时触发，后续复用单例）."""
    global _params, CAT_COLS, CONT_COLS, FEATURE_COLS
    global MISSING_COLS, FILL_VALUES, WINSOR_BOUNDS
    global LOG_PARAMS, SKIP_WINSOR, SCALER_PARAMS

    if _params is not None:
        return

    with _lock:
        if _params is not None:  # double-check
            return

        if not os.path.exists(_PARAMS_PATH):
            raise AppException(
                f"预处理参数文件不存在: {_PARAMS_PATH}", status_code=503
            )

        try:
            with open(_PARAMS_PATH, "r", encoding="utf-8") as f:
                _params = json.load(f)
        except json.JSONDecodeError as e:
            raise AppException(
                f"预处理参数文件格式错误: {e}", status_code=503
            )

        CAT_COLS = _params["cat_cols"]
        CONT_COLS = _params["cont_cols"]
        FEATURE_COLS = _params["feature_cols"]
        MISSING_COLS = _params["missing_cols"]
        FILL_VALUES = _params["fill_values"]
        WINSOR_BOUNDS = _params["winsor_bounds"]
        LOG_PARAMS = _params["log_params"]
        SKIP_WINSOR = _params["skip_winsor"]
        SCALER_PARAMS = _params["scaler_params"]

        logger.info(
            "预处理参数已加载: %d 特征, %d 类别, %d 连续",
            len(FEATURE_COLS), len(CAT_COLS), len(CONT_COLS),
        )
        logger.warning(
            "PROV_CODE 字段在数据库中不存在，unique_hospitals 使用 policy_id 作为代理"
        )


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
        .where(
            Policy.insuree_id == insuree_id,
            AccidentClaim.is_synthetic == False,
            Policy.is_synthetic == False,
        )
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
    _load_params()

    # 验证输入列完整性（惰性加载后 FEATURE_COLS 已知）
    missing = [c for c in FEATURE_COLS if c not in feature_dict]
    if missing:
        raise AppException(
            f"输入缺少 {len(missing)} 个必需字段: {missing}",
            status_code=400,
        )

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
            before_na = df[col].isna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            coerced = df[col].isna().sum() - before_na
            if coerced > 0:
                logger.warning(
                    "列 '%s' 中有 %d 个值被 pd.to_numeric 强制转换为 NaN",
                    col, coerced,
                )
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

    # 6) 确保 final 列序与模型期望一致（防御性对齐，防止 JSON 配置漂移）
    from backend.app.services import model_service
    model_cols = model_service.get_feature_cols()
    if list(df.columns) != model_cols:
        logger.warning(
            "transform_single: 列序与模型不一致，自动重排。"
            "请检查 preprocess_params.json 的 feature_cols。"
        )
        return df[model_cols]
    return df
