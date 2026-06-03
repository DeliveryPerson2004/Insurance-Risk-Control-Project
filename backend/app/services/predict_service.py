"""单条预测编排 — 校验 → 变换 → 推理 → 持久化."""

import logging
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
        is_synthetic=True,
    )
    db.add(policy)
    await db.flush()  # 获取 policy_id 但等后续统一 commit

    claim = AccidentClaim(
        policy_id=synthetic_policy_id,
        is_synthetic=True,
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

    # 从已加载的预处理参数中读取类别特征可选值（无需重复读取 JSON）
    cat_options: dict[str, list[str]] = feature_transform._params.get("cat_options", {})
    cat_cols = feature_transform._params["cat_cols"]

    groups_order = ["诊断信息", "金额信息", "保单信息", "时间特征", "被保险人画像", "医院信息"]

    # 中文标签映射（覆盖 ICD-10 等英文选项）
    ICD10_CN: dict[str, str] = {
        "BLOOD": "血液及造血器官疾病",
        "CIRCULATORY": "循环系统疾病",
        "CONGENITAL": "先天性畸形",
        "DIGESTIVE": "消化系统疾病",
        "ENDOCRINE": "内分泌疾病",
        "EYE_EAR": "眼及附器疾病",
        "FACTORS": "影响健康因素",
        "GENITOURINARY": "泌尿生殖系统疾病",
        "INFECTIOUS": "传染病",
        "INJURY": "损伤中毒",
        "MENTAL": "精神行为障碍",
        "MUSCULOSKELETAL": "肌肉骨骼系统疾病",
        "NEOPLASM": "肿瘤",
        "NERVOUS": "神经系统疾病",
        "OTHER": "其他",
        "PERINATAL": "围生期疾病",
        "PREGNANCY": "妊娠分娩",
        "RESPIRATORY": "呼吸系统疾病",
        "SKIN": "皮肤皮下组织疾病",
        "SYMPTOMS": "症状体征",
    }
    MBR_TYPE_CN: dict[str, str] = {
        "APPLICANT": "主申请人",
        "CHILD": "子女",
        "PARENTS": "父母",
        "SPOUSE": "配偶",
    }
    BH_CATEGORY_CN: dict[str, str] = {
        "CJF": "常见病", "CLF": "慢性病", "CWF": "大病",
        "GHF": "高额病", "JCF": "基础病", "YPF": "药品费",
        "ZFYP": "政府药品", "ZLF": "诊疗费", "ZYF": "中药费",
        "OTHER": "其他",
    }
    BH_PREFIX_CN: dict[str, str] = {
        "100PCT": "100%报销", "NF": "非基金", "NON_SOCIAL": "非社保",
        "NS": "非标准", "OTHER": "其他", "SOCIAL": "社保",
    }
    BEN_TYPE_CN: dict[str, str] = {
        "BENEFIT_TYPE_DBIP": "门诊住院(DBIP)",
        "BENEFIT_TYPE_DBOP": "门诊(DBOP)",
        "BENEFIT_TYPE_DT": "牙科(DT)",
        "BENEFIT_TYPE_GGIP": "大病住院(GGIP)",
        "BENEFIT_TYPE_IP": "住院(IP)",
        "BENEFIT_TYPE_IPCASB": "住院日额(IPCASB)",
        "BENEFIT_TYPE_JWOP": "境外门诊(JWOP)",
        "BENEFIT_TYPE_MA": "医疗援助(MA)",
        "BENEFIT_TYPE_MAIP": "医疗援助住院(MAIP)",
        "BENEFIT_TYPE_MAOP": "医疗援助门诊(MAOP)",
        "BENEFIT_TYPE_MEMR": "医疗急诊(MEMR)",
        "BENEFIT_TYPE_MT": "生育(MT)",
        "BENEFIT_TYPE_OP": "门诊(OP)",
        "BENEFIT_TYPE_PA": "个人意外(PA)",
        "BENEFIT_TYPE_VS": "视力(VS)",
        "BENEFIT_TYPE_YWIP": "域外住院(YWIP)",
        "BENEFIT_TYPE_YWOP": "域外门诊(YWOP)",
    }

    # 字段名 → (中文标签映射, 是否过滤乱码)
    SELECT_LABEL_MAPS: dict[str, dict[str, str]] = {
        "ICD10_CHAPTER": ICD10_CN,
        "MBR_TYPE": MBR_TYPE_CN,
        "BH_CATEGORY": BH_CATEGORY_CN,
        "BH_PREFIX": BH_PREFIX_CN,
        "BEN_TYPE": BEN_TYPE_CN,
    }

    # 二进制字段：直接提供 否/是 选项，不再让用户猜 0/1
    BINARY_SELECT_FIELDS: dict[str, str] = {
        "IS_INPATIENT": "是否住院",
        "INCUR_IS_WEEKEND": "是否周末就诊",
        "IS_NEW_INSURED": "是否新保户",
        "IS_LONGTERM_INSURED": "是否长期保户",
    }

    # 枚举型数值字段改为 Select（训练数据中仅有限个取值）
    ENUM_NUMBER_FIELDS: dict[str, list[tuple[int, str]]] = {
        "PROV_LEVEL_ORDINAL": [
            (0, "未评级"),
            (1, "一级"),
            (2, "二级"),
            (3, "三级"),
            (4, "特需"),
            (10, "医保"),
            (11, "非医保"),
        ],
    }

    # 数值字段的 max 约束
    NUMERIC_MAX: dict[str, int] = {
        "INCUR_MONTH": 12,
        "INCUR_DAYOFWEEK": 6,
        "INCUR_QUARTER": 4,
    }

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
        "POCY_PLAN_DESC": ("保单信息", "保单计划", "text"),
        "NO_OF_YR": ("保单信息", "投保年限", "number"),
        "POLICY_CNT": ("保单信息", "保单数", "number"),
        "INVOICE_CNT": ("保单信息", "发票数", "number"),
        # 时间特征
        "DAYS_INCUR_TO_PAY": ("时间特征", "就诊到赔付天数", "number"),
        "DAYS_RCV_TO_CLOSE": ("时间特征", "收件到结案天数", "number"),
        "DAYS_HOSPITALIZATION": ("时间特征", "住院天数", "number"),
        "DAYS_RCV_TO_PAY": ("时间特征", "收件到赔付天数", "number"),
        "IS_INPATIENT": ("时间特征", "是否住院", "binary"),
        "INCUR_MONTH": ("时间特征", "就诊月份", "number"),
        "INCUR_DAYOFWEEK": ("时间特征", "就诊星期几", "number"),
        "INCUR_QUARTER": ("时间特征", "就诊季度", "number"),
        "INCUR_IS_WEEKEND": ("时间特征", "是否周末就诊", "binary"),
        # 被保险人画像
        "MBR_TYPE": ("被保险人画像", "成员类型", "select"),
        "IS_NEW_INSURED": ("被保险人画像", "是否新保户", "binary"),
        "IS_LONGTERM_INSURED": ("被保险人画像", "是否长期保户", "binary"),
        # 医院信息
        "PROV_LEVEL_ORDINAL": ("医院信息", "医院等级", "enum_number"),
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
            "type": "select" if ftype in ("binary", "enum_number") else ftype,
            "group": group,
            "required": True,
        }

        if ftype == "select":
            raw_opts = cat_options.get(name, [])
            # 过滤乱码选项（含 U+FFFD 的不可用选项）
            clean_opts = [o for o in raw_opts if "�" not in o]
            if len(clean_opts) < len(raw_opts):
                logger.warning(
                    "字段 '%s' 有 %d 个乱码选项已过滤，剩余 %d 个",
                    name, len(raw_opts) - len(clean_opts), len(clean_opts),
                )
            # 应用中文标签映射
            label_map = SELECT_LABEL_MAPS.get(name, {})
            if label_map:
                option["options"] = [
                    {"value": o, "label": label_map.get(o, o)}
                    for o in clean_opts
                ]
            else:
                option["options"] = [{"value": o, "label": o} for o in clean_opts]

        elif ftype == "binary":
            option["options"] = [
                {"value": 0, "label": "否"},
                {"value": 1, "label": "是"},
            ]

        elif ftype == "enum_number":
            option["options"] = [
                {"value": v, "label": l} for v, l in ENUM_NUMBER_FIELDS[name]
            ]

        elif ftype == "text":
            option["placeholder"] = f"请输入{label}"
            # POCY_PLAN_DESC 有 606 个全部乱码的选项，提供输入提示
            raw_opts = cat_options.get(name, [])
            clean_opts = [o for o in raw_opts if "�" not in o]
            if clean_opts:
                option["hint"] = f"可用值示例: {', '.join(clean_opts[:5])}"

        else:  # number
            option["min"] = 0
            option["step"] = 0.01 if name not in {
                "IS_INPATIENT", "INCUR_MONTH", "INCUR_DAYOFWEEK", "INCUR_QUARTER",
                "INCUR_IS_WEEKEND", "PROV_LEVEL_ORDINAL", "IS_NEW_INSURED",
                "IS_LONGTERM_INSURED", "NO_OF_YR", "POLICY_CNT", "INVOICE_CNT",
            } else 1
            if name in NUMERIC_MAX:
                option["max"] = NUMERIC_MAX[name]
            option["placeholder"] = f"请输入{label}"

        fields.append(option)

    _field_options_cache = {"fields": fields, "groups": groups_order}
    return _field_options_cache
