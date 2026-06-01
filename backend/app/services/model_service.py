"""模型加载 + 3 步推理 + SHAP 解释（模块级单例）."""

import os
import logging

import numpy as np
import pandas as pd
import joblib
import shap

from backend.app.config import settings
from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)

MODEL_PATH = settings.MODEL_PATH

# ---- 模块级单例 ----
_model_bundle: dict | None = None
_explainer: shap.TreeExplainer | None = None


def _load_model():
    """惰性加载模型（首次调用时触发，后续复用单例）."""
    global _model_bundle, _explainer
    if _model_bundle is not None:
        return

    if not os.path.exists(MODEL_PATH):
        raise AppException(f"模型未部署: {MODEL_PATH} 不存在", status_code=503)

    logger.info("Loading model from %s ...", MODEL_PATH)
    _model_bundle = joblib.load(MODEL_PATH)
    _explainer = shap.TreeExplainer(_model_bundle["base_model"])
    logger.info(
        "Model loaded: %d features, threshold=%.2f",
        len(_model_bundle["feature_cols"]),
        _model_bundle["threshold"],
    )


def get_threshold() -> float:
    """返回决策阈值."""
    _load_model()
    return _model_bundle["threshold"]


def get_feature_cols() -> list[str]:
    """返回 35 特征列名（顺序一致）."""
    _load_model()
    return _model_bundle["feature_cols"]


def _safe_value(raw_val):
    """Convert feature value for JSON: numeric -> float, string -> str."""
    try:
        return float(raw_val)
    except (ValueError, TypeError):
        return str(raw_val)


def predict(X: pd.DataFrame) -> dict:
    """
    对 (1, 35) DataFrame 执行推理.

    Returns:
        {
            "fraud_prob": float,    # 校准后概率
            "raw_prob": float,      # 原始 XGBoost 概率
            "risk_level": str,      # high / medium / low
            "shap_values": list[dict],  # Top 10, 按 abs(shap_value) 降序
        }
    """
    _load_model()

    expected_cols = _model_bundle["feature_cols"]
    if X.shape[1] != len(expected_cols) or list(X.columns) != expected_cols:
        raise AppException(
            f"特征列不匹配: 期望 {len(expected_cols)} 列 {expected_cols}, "
            f"实际 {X.shape[1]} 列 {list(X.columns)}",
            status_code=400,
        )

    # Step 1: 原始概率
    raw_prob = float(_model_bundle["base_model"].predict_proba(X)[:, 1][0])

    # Step 2: 校准
    fraud_prob = float(_model_bundle["calibrator"].predict(np.array([raw_prob]))[0])
    fraud_prob = max(0.0, min(1.0, fraud_prob))

    # Step 3: 风险等级
    # 注意: 0.7 是业务决策阈值，高于最优二分类阈值 (threshold≈0.36)，
    # 用于将高风险案件标记为 "high" 以便人工优先审核
    threshold = _model_bundle["threshold"]
    if fraud_prob >= 0.7:
        risk_level = "high"
    elif fraud_prob >= threshold:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Step 4: SHAP（失败不影响主流程，回退为空列表）
    try:
        shap_vals = _explainer.shap_values(X)
        feature_names = expected_cols
        items = []
        for i, name in enumerate(feature_names):
            items.append({
                "feature": name,
                "value": _safe_value(X.iloc[0][name]),
                "shap_value": float(shap_vals[0][i]),
            })
        items.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        shap_top10 = items[:10]
    except Exception:
        logger.warning("SHAP 计算失败，返回空列表作为回退", exc_info=True)
        shap_top10 = []

    return {
        "fraud_prob": round(fraud_prob, 4),
        "raw_prob": round(raw_prob, 4),
        "risk_level": risk_level,
        "shap_values": shap_top10,
    }
