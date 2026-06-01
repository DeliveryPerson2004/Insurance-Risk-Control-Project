"""单条预测编排 — 校验 → 变换 → 推理 → 持久化."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.insuree import Insuree
from backend.app.models.model_info import ModelInfo
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.schemas.predict import (
    PredictSingleRequest,
    PredictSingleResponse,
    ShapItem,
)
from backend.app.services import model_service
from backend.app.services import feature_transform
from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


async def get_field_options() -> dict:
    """构建前端表单字段配置（模块级缓存，首次请求时生成）."""
    return _build_field_options()


async def predict_single(
    db: AsyncSession, req: PredictSingleRequest
) -> PredictSingleResponse:
    """单条预测完整流程."""
    # 确保惰性参数已加载
    feature_transform._load_params()

    # 1. 校验 insuree
    insuree_result = await db.execute(
        select(Insuree).where(Insuree.insuree_id == req.insuree_id)
    )
    insuree = insuree_result.scalar_one_or_none()
    if insuree is None:
        raise AppException(f"被保险人 {req.insuree_id} 不存在", status_code=400)

    # 2. 计算成员聚合
    mbr_agg = await feature_transform.compute_member_aggregates(db, req.insuree_id)

    # 3. 合并 35 特征
    feature_dict = req.model_dump()
    del feature_dict["insuree_id"]
    # 3 个成员聚合
    feature_dict["MBR_CLAIM_COUNT"] = mbr_agg["MBR_CLAIM_COUNT"]
    feature_dict["MBR_AVG_SUB_AMT"] = mbr_agg["MBR_AVG_SUB_AMT"]
    feature_dict["MBR_UNIQUE_HOSPITALS"] = mbr_agg["MBR_UNIQUE_HOSPITALS"]

    # 4. 变换
    import pandas as pd
    X = feature_transform.transform_single(feature_dict)

    # 5. 推理
    result = model_service.predict(X)

    # 6. 获取活跃 model_id
    model_result = await db.execute(
        select(ModelInfo.model_id).where(ModelInfo.is_active == True).limit(1)
    )
    model_id = model_result.scalar_one_or_none()
    if model_id is None:
        raise AppException("没有活跃的模型", status_code=503)

    # 7. FK 落库 — 自动生成合成骨
    synthetic_policy_id = f"PRED-{uuid.uuid4().hex[:8]}"
    policy = Policy(
        policy_id=synthetic_policy_id,
        insuree_id=req.insuree_id,
    )
    db.add(policy)
    await db.flush()  # 获取 policy_id 但等后续统一 commit

    claim = AccidentClaim(
        policy_id=synthetic_policy_id,
    )
    db.add(claim)
    await db.flush()

    # 8. 写入检测结果
    detect_time = datetime.now(timezone.utc)
    thresholds = model_service.get_threshold()

    record = FraudDetectResult(
        policy_id=synthetic_policy_id,
        accident_claim_id=claim.id,
        model_id=model_id,
        fraud_prob=result["fraud_prob"],
        raw_prob=result["raw_prob"],
        risk_level=result["risk_level"],
        threshold_used=thresholds,
        feature_values=feature_dict,
        shap_values=result["shap_values"],
        detect_time=detect_time,
    )
    db.add(record)
    await db.flush()

    # 构造响应
    shap_items = []
    for item in result["shap_values"]:
        shap_items.append(ShapItem(
            feature=item["feature"],
            value=item["value"],
            shap_value=item["shap_value"],
            direction="+" if item["shap_value"] > 0 else "-",
        ))

    return PredictSingleResponse(
        id=record.id,
        fraud_prob=result["fraud_prob"],
        raw_prob=result["raw_prob"],
        risk_level=result["risk_level"],
        threshold_used=thresholds,
        feature_values=feature_dict,
        shap_top10=shap_items,
        detect_time=detect_time,
    )


# ---- field-options 构建（模块级缓存）----

_field_options_cache: dict | None = None


def _build_field_options() -> dict:
    """构建 field-options 响应，含分组和字段 meta."""
    global _field_options_cache
    if _field_options_cache is not None:
        return _field_options_cache

    # 确保惰性参数已加载（CONT_COLS 在 visible_cont_cols 计算中需要）
    feature_transform._load_params()

    # 从烘焙的预处理参数中读取类别特征的可选值（Docker 无需 data/ 目录）
    _params_path = os.path.join(os.path.dirname(__file__), "preprocess_params.json")
    with open(_params_path, "r", encoding="utf-8") as f:
        _baked_params = json.load(f)
    cat_options: dict[str, list[str]] = _baked_params.get("cat_options", {})
    cat_cols = _baked_params["cat_cols"]

    groups_order = ["诊断信息", "金额信息", "保单信息", "时间特征", "被保险人画像", "医院信息"]

    # 字段 → 分组 + label 映射
    field_meta_map = {
        # 诊断信息
        "ICD10_CHAPTER": ("诊断信息", "ICD-10 诊断大类", "select"),
        "BH_PREFIX": ("诊断信息", "受益前缀", "select"),
        "BH_CATEGORY": ("诊断信息", "受益类别", "select"),
        "BEN_TYPE": ("诊断信息", "受益类型", "select"),
        # 金额信息
        "SUB_AMT": ("金额信息", "理赔申请金额", "number"),
        "TOTAL_RECEIPT_AMT": ("金额信息", "发票总金额", "number"),
        "ORG_PRES_AMT_VALUE": ("金额信息", "处方金额", "number"),
        "COPAY_PCT": ("金额信息", "共付比例(%)", "number"),
        "RECEIPT_TO_SUB_RATIO": ("金额信息", "发票/申请比", "number"),
        # 保单信息
        "KIND_CODE": ("保单信息", "险种代码", "select"),
        "POCY_PLAN_DESC": ("保单信息", "保单计划", "select"),
        "NO_OF_YR": ("保单信息", "投保年限", "number"),
        "POLICY_CNT": ("保单信息", "保单数", "number"),
        "INVOICE_CNT": ("保单信息", "发票数", "number"),
        # 时间特征
        "DAYS_INCUR_TO_PAY": ("时间特征", "就诊到赔付天数", "number"),
        "DAYS_RCV_TO_CLOSE": ("时间特征", "收件到结案天数", "number"),
        "DAYS_HOSPITALIZATION": ("时间特征", "住院天数", "number"),
        "DAYS_RCV_TO_PAY": ("时间特征", "收件到赔付天数", "number"),
        "IS_INPATIENT": ("时间特征", "是否住院", "number"),
        "INCUR_MONTH": ("时间特征", "就诊月份", "number"),
        "INCUR_DAYOFWEEK": ("时间特征", "就诊星期几", "number"),
        "INCUR_QUARTER": ("时间特征", "就诊季度", "number"),
        "INCUR_IS_WEEKEND": ("时间特征", "是否周末就诊", "number"),
        # 被保险人画像
        "MBR_TYPE": ("被保险人画像", "成员类型", "select"),
        "IS_NEW_INSURED": ("被保险人画像", "是否新保户", "number"),
        "IS_LONGTERM_INSURED": ("被保险人画像", "是否长期保户", "number"),
        # 医院信息
        "PROV_LEVEL_ORDINAL": ("医院信息", "医院等级", "number"),
    }

    fields = []
    visible_cont_cols = [
        c for c in feature_transform.CONT_COLS
        if c not in {"MBR_CLAIM_COUNT", "MBR_AVG_SUB_AMT", "MBR_UNIQUE_HOSPITALS"}
    ]
    for name in cat_cols + visible_cont_cols:
        if name not in field_meta_map:
            continue
        group, label, ftype = field_meta_map[name]
        option: dict = {
            "name": name,
            "label": label,
            "type": ftype,
            "group": group,
            "required": True,
        }
        if ftype == "select":
            option["options"] = cat_options.get(name, [])
        else:
            option["min"] = 0
            option["step"] = 0.01 if name not in {
                "IS_INPATIENT", "INCUR_MONTH", "INCUR_DAYOFWEEK", "INCUR_QUARTER",
                "INCUR_IS_WEEKEND", "PROV_LEVEL_ORDINAL", "IS_NEW_INSURED",
                "IS_LONGTERM_INSURED", "NO_OF_YR", "POLICY_CNT", "INVOICE_CNT",
            } else 1
            option["placeholder"] = f"请输入{label}"
        fields.append(option)

    _field_options_cache = {"fields": fields, "groups": groups_order}
    return _field_options_cache
