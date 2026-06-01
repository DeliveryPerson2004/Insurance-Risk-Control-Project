# Phase 2: 核心功能 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现模型推理、单条预测（API + 前端）、仪表盘（API + 前端），端到端贯通 Phase 2 全部核心功能。

**Architecture:** 4 个大步骤，每个独立可验证。先后端再前端，每个 API 开发完立即 `curl` 验证；前端组件写完立即在浏览器点一点。遵循现有代码模式：router 薄层 → service 业务逻辑 → schema Pydantic v2；前端 API module → component → page。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + XGBoost + SHAP + React 18 + TypeScript + Ant Design 5 + @ant-design/charts

---

## 步骤 2.1: 模型服务 + 特征变换

### Task 1: 创建 `model_service.py`

**Files:**
- Create: `backend/app/services/model_service.py`

- [x] **Step 1: 写入模块代码**

```python
"""模型加载 + 3 步推理 + SHAP 解释（模块级单例）."""

import os
import logging

import numpy as np
import pandas as pd
import joblib
import shap

from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "modeling/xgb_fraud_model.pkl")

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

    # Step 1: 原始概率
    raw_prob = float(_model_bundle["base_model"].predict_proba(X)[:, 1][0])

    # Step 2: 校准
    fraud_prob = float(_model_bundle["calibrator"].predict(np.array([raw_prob]))[0])
    fraud_prob = max(0.0, min(1.0, fraud_prob))

    # Step 3: 风险等级
    threshold = _model_bundle["threshold"]
    if fraud_prob >= 0.7:
        risk_level = "high"
    elif fraud_prob >= threshold:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Step 4: SHAP
    shap_vals = _explainer.shap_values(X)
    feature_names = _model_bundle["feature_cols"]
    items = []
    for i, name in enumerate(feature_names):
        items.append({
            "feature": name,
            "value": float(X.iloc[0][name]),
            "shap_value": float(shap_vals[0][i]),
        })
    items.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    shap_top10 = items[:10]

    return {
        "fraud_prob": round(fraud_prob, 4),
        "raw_prob": round(raw_prob, 4),
        "risk_level": risk_level,
        "shap_values": shap_top10,
    }
```

- [x] **Step 2: 验证模型可加载**

```bash
uv run python -c "
from backend.app.services.model_service import _load_model, get_threshold, get_feature_cols
_load_model()
print('threshold:', get_threshold())
print('features:', len(get_feature_cols()))
"
```

Expected: 输出 `threshold: 0.36` 和 `features: 35`

- [x] **Step 3: 用训练集已知样本验证推理正确性**

```bash
uv run python -c "
import pandas as pd
from backend.app.services.model_service import predict

train = pd.read_csv('data/train_eval_test/train.csv')
X_sample = train.drop(columns=['FRAUD']).iloc[[0]]
# 确保类别特征 dtype
cat_cols = ['ICD10_CHAPTER','BH_PREFIX','BH_CATEGORY','MBR_TYPE','BEN_TYPE','KIND_CODE','POCY_PLAN_DESC']
for c in cat_cols:
    if c in X_sample.columns:
        X_sample[c] = X_sample[c].astype('category')

result = predict(X_sample)
print('fraud_prob:', result['fraud_prob'])
print('risk_level:', result['risk_level'])
print('top SHAP:', result['shap_values'][0])
"
```

Expected: 输出 fraud_prob 值、risk_level 不为空、shap_values 有数据

- [x] **Step 4: Commit**

```bash
git add backend/app/services/model_service.py
git commit -m "feat: add model_service — model loading, 3-step inference, SHAP"
```

---

### Task 2: 创建 `feature_transform.py`

**Files:**
- Create: `backend/app/services/feature_transform.py`
- Read: `backend/app/services/preprocess_params.json`

- [x] **Step 1: 写入模块代码**

```python
"""单条/批次输入 → 35 特征 DataFrame（与训练时变换一致）."""

import json
import os
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

_PARAMS_PATH = os.path.join(os.path.dirname(__file__), "preprocess_params.json")

with open(_PARAMS_PATH, "r") as f:
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

    # 1) 类别特征 → category dtype
    for col in CAT_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).astype("category")

    # 2) 连续特征填充缺失
    for col in CONT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            med = FILL_VALUES.get(col, 0)
            df[col] = df[col].fillna(med)

    # 3) 缺失标记（用户已传 0/1，这里仅兜底）
    for col in MISSING_COLS:
        if col not in df.columns:
            base_col = col.replace("_MISSING", "")
            df[col] = df[base_col].isnull().astype(int) if base_col in df.columns else 0

    # 4) Winsor
    for col in CONT_COLS:
        if col in SKIP_WINSOR or col not in df.columns:
            continue
        if col in WINSOR_BOUNDS:
            lo, hi = WINSOR_BOUNDS[col]
            df[col] = df[col].clip(lo, hi)

    # 5) log1p
    for col, lp in LOG_PARAMS.items():
        if col in df.columns:
            mn = lp["min"]
            df[col] = np.log1p(df[col].clip(lower=mn) - mn + 1)

    # 6) StandardScaler
    for col, sp in SCALER_PARAMS.items():
        if col in df.columns:
            mean = sp["mean"]
            std = sp["std"]
            if std > 0:
                df[col] = (df[col] - mean) / std

    # 7) 确保 final 列序
    existing = [c for c in FEATURE_COLS if c in df.columns]
    return df[existing]
```

- [x] **Step 2: 验证变换管线**

```bash
uv run python -c "
import pandas as pd
from backend.app.services.feature_transform import transform_single

# 用 train.csv 第一行测试完整的 35 特征 roundtrip
train = pd.read_csv('data/train_eval_test/train.csv')
row = train.drop(columns=['FRAUD']).iloc[0].to_dict()
df = transform_single(row)
print('output shape:', df.shape)
print('columns:', list(df.columns[:5]), '...')
"
```

Expected: `output shape: (1, 35)`

- [x] **Step 3: Commit**

```bash
git add backend/app/services/feature_transform.py
git commit -m "feat: add feature_transform — winsor/log/scale pipeline for single input"
```

---

## 步骤 2.2: 单条预测 API

### Task 3: 创建 `schemas/predict.py`

**Files:**
- Create: `backend/app/schemas/predict.py`

- [x] **Step 1: 写入 schema 模块**

```python
"""预测相关 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class FieldOption(BaseModel):
    """field-options 响应中的单个字段 meta."""
    name: str
    label: str
    type: str  # "select" | "number"
    group: str
    required: bool
    # select 专属
    options: list[str] | None = None
    # number 专属
    min: float | None = None
    step: float | None = None
    placeholder: str | None = None


class FieldOptionsResponse(BaseModel):
    fields: list[FieldOption]
    groups: list[str]


class PredictSingleRequest(BaseModel):
    """27 个可见字段 + insuree_id."""
    insuree_id: str = Field(..., min_length=1, max_length=64)

    # 7 个类别特征
    ICD10_CHAPTER: str
    BH_PREFIX: str
    BH_CATEGORY: str
    MBR_TYPE: str
    BEN_TYPE: str
    KIND_CODE: str
    POCY_PLAN_DESC: str

    # 20 个普通连续特征
    SUB_AMT: float
    TOTAL_RECEIPT_AMT: float
    ORG_PRES_AMT_VALUE: float
    COPAY_PCT: float
    NO_OF_YR: float
    POLICY_CNT: float
    INVOICE_CNT: float
    DAYS_INCUR_TO_PAY: float
    DAYS_RCV_TO_CLOSE: float
    DAYS_HOSPITALIZATION: float
    DAYS_RCV_TO_PAY: float
    IS_INPATIENT: int
    INCUR_MONTH: int
    INCUR_DAYOFWEEK: int
    INCUR_QUARTER: int
    INCUR_IS_WEEKEND: int
    PROV_LEVEL_ORDINAL: int
    RECEIPT_TO_SUB_RATIO: float
    IS_NEW_INSURED: int
    IS_LONGTERM_INSURED: int


class ShapItem(BaseModel):
    feature: str
    value: float
    shap_value: float
    direction: str  # "+" 或 "-"


class PredictSingleResponse(BaseModel):
    id: int
    fraud_prob: float
    raw_prob: float
    risk_level: str
    threshold_used: float
    feature_values: dict
    shap_top10: list[ShapItem]
    detect_time: datetime
```

- [x] **Step 2: Commit**

```bash
git add backend/app/schemas/predict.py
git commit -m "feat: add predict schemas — field-options, single predict request/response"
```

---

### Task 4: 创建 `predict_service.py`

**Files:**
- Create: `backend/app/services/predict_service.py`

- [x] **Step 1: 写入服务模块**

```python
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
from backend.app.services.feature_transform import (
    compute_member_aggregates,
    transform_single,
    CONT_COLS,
    MISSING_COLS,
)
from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


async def get_field_options() -> dict:
    """构建前端表单字段配置（模块级缓存，首次请求时生成）."""
    return _build_field_options()


async def predict_single(
    db: AsyncSession, req: PredictSingleRequest
) -> PredictSingleResponse:
    """单条预测完整流程."""
    # 1. 校验 insuree
    insuree_result = await db.execute(
        select(Insuree).where(Insuree.insuree_id == req.insuree_id)
    )
    insuree = insuree_result.scalar_one_or_none()
    if insuree is None:
        raise AppException(f"被保险人 {req.insuree_id} 不存在", status_code=400)

    # 2. 计算成员聚合
    mbr_agg = await compute_member_aggregates(db, req.insuree_id)

    # 3. 合并 35 特征
    feature_dict = req.model_dump()
    del feature_dict["insuree_id"]
    # 5 个缺失标记
    for mc in MISSING_COLS:
        base_col = mc.replace("_MISSING", "")
        feature_dict[mc] = 1 if base_col in feature_dict and feature_dict[base_col] is None else 0
    # 3 个成员聚合
    feature_dict["MBR_CLAIM_COUNT"] = mbr_agg["MBR_CLAIM_COUNT"]
    feature_dict["MBR_AVG_SUB_AMT"] = mbr_agg["MBR_AVG_SUB_AMT"]
    feature_dict["MBR_UNIQUE_HOSPITALS"] = mbr_agg["MBR_UNIQUE_HOSPITALS"]

    # 4. 变换
    import pandas as pd
    X = transform_single(feature_dict)

    # 5. 推理
    result = model_service.predict(X)

    # 6. 获取活跃 model_id
    model_result = await db.execute(
        select(ModelInfo.model_id).where(ModelInfo.is_active == True).limit(1)
    )
    model_id = model_result.scalar_one_or_none()

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

    import pandas as pd

    # 从训练集提取类别特征的可选值
    train = pd.read_csv("data/train_eval_test/train.csv")
    cat_cols = [
        "ICD10_CHAPTER", "BH_PREFIX", "BH_CATEGORY",
        "MBR_TYPE", "BEN_TYPE", "KIND_CODE", "POCY_PLAN_DESC",
    ]

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
    for name in cat_cols + [c for c in CONT_COLS if c not in {"MBR_CLAIM_COUNT", "MBR_AVG_SUB_AMT", "MBR_UNIQUE_HOSPITALS"}]:
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
            if name in train.columns:
                vals = train[name].dropna().unique().tolist()
                option["options"] = sorted([str(v) for v in vals])
            else:
                option["options"] = []
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
```

- [x] **Step 2: Commit**

```bash
git add backend/app/services/predict_service.py
git commit -m "feat: add predict_service — orchestrate validation, transform, inference, persist"
```

---

### Task 5: 创建 `routers/predict.py`

**Files:**
- Create: `backend/app/routers/predict.py`
- Modify: `backend/app/main.py` (注册路由)

- [x] **Step 1: 写入路由模块**

```python
"""预测路由 — GET /api/predict/field-options, POST /api/predict/single."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.predict import PredictSingleRequest
from backend.app.services import predict_service

router = APIRouter(prefix="/api/predict", tags=["predict"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/field-options")
async def field_options(current_user: User = Depends(get_current_user)):
    result = await predict_service.get_field_options()
    return ok(result)


@router.post("/single")
async def single_predict(
    req: PredictSingleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await predict_service.predict_single(db, req)
    return ok(result.model_dump(mode="json"))
```

- [x] **Step 2: 在 main.py 注册 predict 路由**

在 `backend/app/main.py` 的 `create_app()` 函数中，auth 路由注册之后添加：

```python
    from backend.app.routers.predict import router as predict_router
    app.include_router(predict_router)
```

- [x] **Step 3: 重启后端并验证 API**

```bash
# 启动后端
uv run uvicorn backend.app.main:app --reload --port 8000 &
sleep 2

# 先登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

# 测试 field-options
curl -s http://localhost:8000/api/predict/field-options \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print(len(d['data']['fields']), 'fields,', len(d['data']['groups']), 'groups')"
```

Expected: `27 fields, 6 groups`

- [x] **Step 4: 测试 POST /single（需要已有 insuree）**

先确保数据库有 insuree 记录（或跳过，留到 seed 后验证）.

- [x] **Step 5: Commit**

```bash
git add backend/app/routers/predict.py backend/app/main.py
git commit -m "feat: add predict router — /field-options + /single"
```

---

## 步骤 2.3: 单条预测前端

### Task 6: 创建前端类型和 API 模块

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/predict.ts`

- [x] **Step 1: 在 types/index.ts 末尾追加预测相关类型**

```typescript
// ---- 预测 ----
export interface FieldOption {
  name: string;
  label: string;
  type: 'select' | 'number';
  group: string;
  required: boolean;
  options?: string[];
  min?: number;
  step?: number;
  placeholder?: string;
}

export interface FieldOptionsResponse {
  fields: FieldOption[];
  groups: string[];
}

export interface PredictSingleRequest {
  insuree_id: string;
  ICD10_CHAPTER: string;
  BH_PREFIX: string;
  BH_CATEGORY: string;
  MBR_TYPE: string;
  BEN_TYPE: string;
  KIND_CODE: string;
  POCY_PLAN_DESC: string;
  SUB_AMT: number;
  TOTAL_RECEIPT_AMT: number;
  ORG_PRES_AMT_VALUE: number;
  COPAY_PCT: number;
  NO_OF_YR: number;
  POLICY_CNT: number;
  INVOICE_CNT: number;
  DAYS_INCUR_TO_PAY: number;
  DAYS_RCV_TO_CLOSE: number;
  DAYS_HOSPITALIZATION: number;
  DAYS_RCV_TO_PAY: number;
  IS_INPATIENT: number;
  INCUR_MONTH: number;
  INCUR_DAYOFWEEK: number;
  INCUR_QUARTER: number;
  INCUR_IS_WEEKEND: number;
  PROV_LEVEL_ORDINAL: number;
  RECEIPT_TO_SUB_RATIO: number;
  IS_NEW_INSURED: number;
  IS_LONGTERM_INSURED: number;
}

export interface ShapItem {
  feature: string;
  value: number;
  shap_value: number;
  direction: string;
}

export interface PredictSingleResponse {
  id: number;
  fraud_prob: number;
  raw_prob: number;
  risk_level: 'high' | 'medium' | 'low';
  threshold_used: number;
  feature_values: Record<string, number>;
  shap_top10: ShapItem[];
  detect_time: string;
}
```

- [x] **Step 2: 创建 `frontend/src/api/predict.ts`**

```typescript
import client from './client';
import type { ApiResponse, FieldOptionsResponse, PredictSingleRequest, PredictSingleResponse } from '../types';

export async function getFieldOptions(): Promise<FieldOptionsResponse> {
  const res = await client.get<ApiResponse<FieldOptionsResponse>>('/predict/field-options');
  return res.data.data;
}

export async function postSinglePredict(data: PredictSingleRequest): Promise<PredictSingleResponse> {
  const res = await client.post<ApiResponse<PredictSingleResponse>>('/predict/single', data);
  return res.data.data;
}
```

- [x] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/predict.ts
git commit -m "feat: add predict types and API module"
```

---

### Task 7: 创建 `RiskGauge` 组件

**Files:**
- Create: `frontend/src/components/predict/RiskGauge.tsx`

- [x] **Step 1: 写入组件**

```tsx
import { Typography } from 'antd';

const { Text, Title } = Typography;

interface Props {
  fraudProb: number;
  riskLevel: 'high' | 'medium' | 'low';
  threshold: number;
}

const LEVEL_CONFIG = {
  high: { color: '#ff4d4f', label: '高风险' },
  medium: { color: '#faad14', label: '中等风险' },
  low: { color: '#52c41a', label: '低风险' },
};

export default function RiskGauge({ fraudProb, riskLevel, threshold }: Props) {
  const pct = fraudProb; // 0-1
  const angle = -180 + pct * 180; // SVG 半圆：-180° → 0°
  const cfg = LEVEL_CONFIG[riskLevel];

  // 指针端点坐标
  const cx = 100, cy = 100, r = 80;
  const rad = (angle * Math.PI) / 180;
  const nx = cx + r * Math.cos(rad);
  const ny = cy + r * Math.sin(rad);

  return (
    <div style={{ textAlign: 'center', padding: '16px 0' }}>
      <svg width="220" height="120" viewBox="0 0 200 110">
        {/* 半圆背景色段 */}
        <defs>
          <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#52c41a" />
            <stop offset="36%" stopColor="#52c41a" />
            <stop offset="36%" stopColor="#faad14" />
            <stop offset="70%" stopColor="#faad14" />
            <stop offset="70%" stopColor="#ff4d4f" />
            <stop offset="100%" stopColor="#ff4d4f" />
          </linearGradient>
        </defs>
        <path
          d="M 10 100 A 90 90 0 0 1 190 100"
          fill="none"
          stroke="url(#gaugeGrad)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        {/* 指针 */}
        <line
          x1={cx}
          y1={cy}
          x2={nx}
          y2={ny}
          stroke="#333"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r="4" fill="#333" />
        {/* 刻度标签 */}
        <text x="10" y="112" fontSize="9" fill="#999" textAnchor="middle">0</text>
        <text x="55" y="112" fontSize="9" fill="#999" textAnchor="middle">{threshold.toFixed(2)}</text>
        <text x="100" y="112" fontSize="9" fill="#999" textAnchor="middle">0.5</text>
        <text x="145" y="112" fontSize="9" fill="#999" textAnchor="middle">0.7</text>
        <text x="190" y="112" fontSize="9" fill="#999" textAnchor="middle">1.0</text>
      </svg>
      <div style={{ marginTop: -8 }}>
        <Title level={3} style={{ color: cfg.color, marginBottom: 0 }}>
          {cfg.label}
        </Title>
        <Text strong style={{ fontSize: 20, color: cfg.color }}>
          {(fraudProb * 100).toFixed(1)}%
        </Text>
        <br />
        <Text type="secondary" style={{ fontSize: 11 }}>
          阈值 {threshold} | 校准后概率
        </Text>
      </div>
    </div>
  );
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/components/predict/RiskGauge.tsx
git commit -m "feat: add RiskGauge — SVG semi-circle gauge for fraud probability"
```

---

### Task 8: 创建 `ShapExplanation` 组件

**Files:**
- Create: `frontend/src/components/predict/ShapExplanation.tsx`

- [x] **Step 1: 写入组件**

```tsx
import type { ShapItem } from '../../types';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

interface Props {
  items: ShapItem[];
}

export default function ShapExplanation({ items }: Props) {
  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14, color: '#666' }}>
        关键疑点特征（Top 10 SHAP）
      </div>
      {items.map((item, i) => (
        <div
          key={item.feature}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '6px 0',
            borderBottom: i < items.length - 1 ? '1px solid #f0f0f0' : 'none',
            fontSize: 13,
          }}
        >
          <span style={{ flex: 1, fontWeight: 500 }}>{item.feature}</span>
          <span style={{ width: 60, textAlign: 'right', color: '#999' }}>
            {typeof item.value === 'number' ? item.value.toFixed(2) : item.value}
          </span>
          <span
            style={{
              width: 80,
              textAlign: 'right',
              fontWeight: 600,
              color: item.direction === '+' ? '#ff4d4f' : '#52c41a',
            }}
          >
            {item.direction === '+' ? (
              <ArrowUpOutlined style={{ marginRight: 2 }} />
            ) : (
              <ArrowDownOutlined style={{ marginRight: 2 }} />
            )}
            {item.shap_value.toFixed(3)}
          </span>
        </div>
      ))}
      <div style={{ marginTop: 8, fontSize: 11, color: '#999' }}>
        仅展示 Top 10 SHAP 特征，完整 35 特征值已存入数据库
      </div>
    </div>
  );
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/components/predict/ShapExplanation.tsx
git commit -m "feat: add ShapExplanation — top 10 SHAP list with color coding"
```

---

### Task 9: 创建 `PredictionForm` 组件

**Files:**
- Create: `frontend/src/components/predict/PredictionForm.tsx`

- [x] **Step 1: 写入组件**

```tsx
import { useState, useEffect, useCallback } from 'react';
import {
  Form, Select, InputNumber, Input, Button, Collapse, Steps, Space, message, Spin,
} from 'antd';
import type { FieldOption } from '../../types';
import { getFieldOptions } from '../../api/predict';

interface Props {
  onResult: (result: any) => void;
  loading: boolean;
}

type ViewMode = 'collapse' | 'steps';

export default function PredictionForm({ onResult, loading }: Props) {
  const [form] = Form.useForm();
  const [fields, setFields] = useState<FieldOption[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('collapse');
  const [fetching, setFetching] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    getFieldOptions()
      .then((data) => {
        setFields(data.fields);
        setGroups(data.groups);
      })
      .catch(() => message.error('获取字段配置失败'))
      .finally(() => setFetching(false));
  }, []);

  const getFieldsByGroup = useCallback(
    (group: string) => fields.filter((f) => f.group === group),
    [fields],
  );

  const renderField = (field: FieldOption) => {
    if (field.type === 'select') {
      return (
        <Form.Item
          key={field.name}
          name={field.name}
          label={field.label}
          rules={[{ required: field.required, message: `请选择${field.label}` }]}
        >
          <Select
            showSearch
            placeholder={field.placeholder || `请选择${field.label}`}
            options={(field.options || []).map((o) => ({ value: o, label: o }))}
          />
        </Form.Item>
      );
    }
    return (
      <Form.Item
        key={field.name}
        name={field.name}
        label={field.label}
        rules={[{ required: field.required, message: `请输入${field.label}` }]}
      >
        <InputNumber
          style={{ width: '100%' }}
          min={field.min}
          step={field.step}
          placeholder={field.placeholder}
        />
      </Form.Item>
    );
  };

  if (fetching) {
    return <Spin tip="加载字段配置..." style={{ display: 'block', textAlign: 'center', padding: 48 }} />;
  }

  // 向导步骤
  const stepItems = [
    { title: '诊断+金额', groups: ['诊断信息', '金额信息'] },
    { title: '保单+时间', groups: ['保单信息', '时间特征'] },
    { title: '画像+医院', groups: ['被保险人画像', '医院信息'] },
    { title: '确认提交', groups: [] as string[] },
  ];

  return (
    <div>
      {/* 模式切换 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16, gap: 8 }}>
        <Button
          size="small"
          type={viewMode === 'collapse' ? 'primary' : 'default'}
          onClick={() => setViewMode('collapse')}
        >
          折叠面板
        </Button>
        <Button
          size="small"
          type={viewMode === 'steps' ? 'primary' : 'default'}
          onClick={() => setViewMode('steps')}
        >
          向导
        </Button>
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={(values) => onResult(values)}
      >
        {/* insuree_id 放在最前面 */}
        <Form.Item
          name="insuree_id"
          label="被保险人 ID"
          rules={[{ required: true, message: '请输入被保险人 ID' }]}
        >
          <Input placeholder="请输入被保险人 ID" />
        </Form.Item>

        {viewMode === 'collapse' ? (
          <Collapse
            defaultActiveKey={[groups[0]]}
            items={groups.map((group) => ({
              key: group,
              label: `${group} (${getFieldsByGroup(group).length} 字段)`,
              children: (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {getFieldsByGroup(group).map(renderField)}
                </div>
              ),
            }))}
          />
        ) : (
          <div>
            <Steps
              current={currentStep}
              size="small"
              style={{ marginBottom: 24 }}
              onChange={setCurrentStep}
              items={stepItems.map((s) => ({ title: s.title }))}
            />
            {currentStep < 3 ? (
              <>
                {stepItems[currentStep].groups.map((group) => (
                  <div key={group} style={{ marginBottom: 16 }}>
                    <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{group}</div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {getFieldsByGroup(group).map(renderField)}
                    </div>
                  </div>
                ))}
                <div style={{ textAlign: 'right', marginTop: 16 }}>
                  <Button type="primary" onClick={() => setCurrentStep((s) => Math.min(s + 1, 3))}>
                    下一步
                  </Button>
                </div>
              </>
            ) : (
              <div>
                <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>
                  确认提交 — 请检查所有已填写字段
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                  <Button onClick={() => setCurrentStep(2)}>上一步</Button>
                  <Button type="primary" htmlType="submit" loading={loading}>
                    提交预测
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {viewMode === 'collapse' && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
            <Button onClick={() => form.resetFields()}>重置</Button>
            <Button type="primary" htmlType="submit" loading={loading}>
              提交预测
            </Button>
          </div>
        )}
      </Form>
    </div>
  );
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/components/predict/PredictionForm.tsx
git commit -m "feat: add PredictionForm — 27-field form with collapse/steps mode"
```

---

### Task 10: 创建 `PredictionPage` + 注册路由

**Files:**
- Create: `frontend/src/pages/PredictionPage.tsx`
- Modify: `frontend/src/App.tsx`

- [x] **Step 1: 写入 PredictionPage**

```tsx
import { useState } from 'react';
import { message, Row, Col, Card, Button, Input } from 'antd';
import PredictionForm from '../components/predict/PredictionForm';
import RiskGauge from '../components/predict/RiskGauge';
import ShapExplanation from '../components/predict/ShapExplanation';
import { postSinglePredict } from '../api/predict';
import type { PredictSingleResponse } from '../types';

export default function PredictionPage() {
  const [result, setResult] = useState<PredictSingleResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: Record<string, any>) => {
    setLoading(true);
    try {
      const res = await postSinglePredict(values as any);
      setResult(res);
      message.success('预测完成');
    } catch {
      message.error('预测失败，请检查输入');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>单条预测</h2>
      <PredictionForm onResult={handleSubmit} loading={loading} />

      {result && (
        <Card style={{ marginTop: 24 }}>
          <Row gutter={24} align="top">
            <Col flex="240px">
              <RiskGauge
                fraudProb={result.fraud_prob}
                riskLevel={result.risk_level}
                threshold={result.threshold_used}
              />
            </Col>
            <Col flex="auto">
              <ShapExplanation items={result.shap_top10} />
            </Col>
            <Col flex="160px">
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontWeight: 600, marginBottom: 16, color: '#666' }}>审核判定</div>
                <Button
                  type="primary"
                  style={{ background: '#52c41a', borderColor: '#52c41a', width: '100%', marginBottom: 8 }}
                >
                  通过
                </Button>
                <Button
                  danger
                  style={{ width: '100%', marginBottom: 8 }}
                >
                  拒绝
                </Button>
                <Button
                  style={{ background: '#faad14', borderColor: '#faad14', color: '#fff', width: '100%', marginBottom: 12 }}
                >
                  待调查
                </Button>
                <Input.TextArea rows={3} placeholder="备注（可选）" />
              </div>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}
```

- [x] **Step 2: 更新 App.tsx 路由**

将 `frontend/src/App.tsx` 中的占位路由替换为真实组件。在文件顶部添加 import：

```typescript
import PredictionPage from './pages/PredictionPage';
```

将 `<Route path="predict/single" element={<div>单条预测（Phase 2）</div>} />` 替换为：

```typescript
<Route path="predict/single" element={<PredictionPage />} />
```

- [x] **Step 3: Commit**

```bash
git add frontend/src/pages/PredictionPage.tsx frontend/src/App.tsx
git commit -m "feat: add PredictionPage — form + gauge + SHAP layout, register route"
```

- [x] **Step 4: 前端类型检查验证**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无类型错误.

---

## 步骤 2.4: 仪表盘 API + 前端 + Seed

### Task 11: 创建 `schemas/dashboard.py`

**Files:**
- Create: `backend/app/schemas/dashboard.py`

- [x] **Step 1: 写入 schema**

```python
"""仪表盘 Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel


class DashboardStats(BaseModel):
    today_pending: int
    today_high_risk: int
    today_processed: int
    total_detected: int


class TrendItem(BaseModel):
    date: str
    total: int
    fraud_rate: float


class TrendResponse(BaseModel):
    trend: list[TrendItem]


class HighRiskItem(BaseModel):
    id: int
    policy_id: str
    fraud_prob: float
    risk_level: str
    claim_amount: float | None
    detect_time: datetime


class HighRiskResponse(BaseModel):
    items: list[HighRiskItem]
```

- [x] **Step 2: Commit**

```bash
git add backend/app/schemas/dashboard.py
git commit -m "feat: add dashboard schemas"
```

---

### Task 12: 创建 `dashboard_service.py` + `routers/dashboard.py`

**Files:**
- Create: `backend/app/services/dashboard_service.py`
- Create: `backend/app/routers/dashboard.py`
- Modify: `backend/app/main.py` (注册路由)

- [x] **Step 1: 写入 dashboard_service.py**

```python
"""仪表盘聚合查询."""

from datetime import date, timedelta

from sqlalchemy import select, func, and_
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
```

- [x] **Step 2: 写入 routers/dashboard.py**

```python
"""仪表盘路由."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def ok(data):
    return JSONResponse(content={"code": 0, "data": data, "message": "ok"})


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await dashboard_service.get_stats(db)
    return ok(data)


@router.get("/trend")
async def trend(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await dashboard_service.get_trend(db, days)
    return ok({"trend": data})


@router.get("/high-risk")
async def high_risk(
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await dashboard_service.get_high_risk(db, limit)
    return ok({"items": data})
```

- [x] **Step 3: 在 main.py 注册 dashboard 路由**

在 `backend/app/main.py` 的 `create_app()` 中 predict 路由注册之后添加：

```python
    from backend.app.routers.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
```

- [x] **Step 4: Commit**

```bash
git add backend/app/services/dashboard_service.py backend/app/routers/dashboard.py backend/app/main.py
git commit -m "feat: add dashboard API — stats, trend, high-risk endpoints"
```

---

### Task 13: 创建 Seed 演示数据脚本

**Files:**
- Create: `backend/scripts/seed_demo.py`

- [x] **Step 1: 写入 seed 脚本**

```python
"""Seed ~100 条演示预测记录，供 Phase 2 仪表盘开发和演示使用."""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session
from backend.app.models.insuree import Insuree
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.model_info import ModelInfo
from backend.app.models.case_history import CaseHistory


async def seed():
    async with async_session() as db:
        # 确保有活跃 model
        model_result = await db.execute(
            select(ModelInfo).where(ModelInfo.is_active == True).limit(1)
        )
        model = model_result.scalar_one_or_none()
        if model is None:
            print("无活跃模型，跳过 seed")
            return

        # 确保有 insuree
        insuree_result = await db.execute(select(Insuree).limit(1))
        insuree = insuree_result.scalar_one_or_none()
        if insuree is None:
            ensure = Insuree(
                insuree_id="DEMO-001",
                age=35,
                gender="M",
            )
            db.add(insuree)
            await db.flush()
            insuree_id = "DEMO-001"
        else:
            insuree_id = insuree.insuree_id

        now = datetime.now(timezone.utc)
        risk_levels = ["high"] * 15 + ["medium"] * 30 + ["low"] * 55

        for i in range(100):
            # 合成 policy
            policy_id = f"SEED-{uuid.uuid4().hex[:8]}"
            policy = Policy(
                policy_id=policy_id,
                insuree_id=insuree_id,
            )
            db.add(policy)
            await db.flush()

            # 合成 accident_claim
            claim = AccidentClaim(
                policy_id=policy_id,
                claim_amount=round(random.uniform(100, 20000), 2),
            )
            db.add(claim)
            await db.flush()

            # 随机检测时间（过去 30 天）
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
                shap_values=[],
                detect_time=detect_time,
            )
            db.add(record)

            # 部分记录添加审核历史
            if random.random() < 0.3:
                case = CaseHistory(
                    policy_id=policy_id,
                    detect_result_id=record.id,
                    user_id=uuid.uuid4().hex,  # 无真实用户的演示占位
                    operate_time=detect_time + timedelta(hours=random.randint(1, 48)),
                    manual_result=random.choice(["pass", "reject", "investigate"]),
                    remark="演示审核记录",
                )
                db.add(case)

        await db.commit()
        print(f"Seed: 插入 100 条 fraud_detect_result + 配套 policy/claim")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [x] **Step 2: 验证 seed 脚本可执行**

```bash
uv run python backend/scripts/seed_demo.py
```

Expected: `Seed: 插入 100 条 fraud_detect_result + 配套 policy/claim`

- [x] **Step 3: Commit**

```bash
git add backend/scripts/seed_demo.py
git commit -m "feat: add seed_demo — 100 demo prediction records for dashboard"
```

---

### Task 14: 创建仪表盘前端组件

**Files:**
- Create: `frontend/src/api/dashboard.ts`
- Create: `frontend/src/components/dashboard/StatsCards.tsx`
- Create: `frontend/src/components/dashboard/RiskTrendChart.tsx`
- Create: `frontend/src/components/dashboard/HighRiskTable.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [x] **Step 1: 在 types/index.ts 追加仪表盘类型**

```typescript
// ---- 仪表盘 ----
export interface DashboardStats {
  today_pending: number;
  today_high_risk: number;
  today_processed: number;
  total_detected: number;
}

export interface TrendItem {
  date: string;
  total: number;
  fraud_rate: number;
}

export interface HighRiskItem {
  id: number;
  policy_id: string;
  fraud_prob: number;
  risk_level: string;
  claim_amount: number | null;
  detect_time: string;
}
```

- [x] **Step 2: 创建 `frontend/src/api/dashboard.ts`**

```typescript
import client from './client';
import type { ApiResponse, DashboardStats, TrendItem, HighRiskItem } from '../types';

export async function fetchStats(): Promise<DashboardStats> {
  const res = await client.get<ApiResponse<DashboardStats>>('/dashboard/stats');
  return res.data.data;
}

export async function fetchTrend(days = 30): Promise<TrendItem[]> {
  const res = await client.get<ApiResponse<{ trend: TrendItem[] }>>('/dashboard/trend', { params: { days } });
  return res.data.data.trend;
}

export async function fetchHighRisk(limit = 5): Promise<HighRiskItem[]> {
  const res = await client.get<ApiResponse<{ items: HighRiskItem[] }>>('/dashboard/high-risk', { params: { limit } });
  return res.data.data.items;
}
```

- [x] **Step 3: 创建 StatsCards**

```tsx
import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import {
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { fetchStats } from '../../api/dashboard';
import type { DashboardStats } from '../../types';

export default function StatsCards() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    fetchStats().then(setStats).catch(() => {});

    const interval = setInterval(() => {
      fetchStats().then(setStats).catch(() => {});
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Row gutter={16}>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日待审核"
            value={stats?.today_pending ?? 0}
            prefix={<ClockCircleOutlined />}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日高风险"
            value={stats?.today_high_risk ?? 0}
            prefix={<WarningOutlined />}
            valueStyle={{ color: '#cf1322' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="今日已处理"
            value={stats?.today_processed ?? 0}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="累计检测量"
            value={stats?.total_detected ?? 0}
            prefix={<DatabaseOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
}
```

- [x] **Step 4: 创建 RiskTrendChart**

```tsx
import { useEffect, useState } from 'react';
import { Button, Space, Spin } from 'antd';
import { DualAxes } from '@ant-design/charts';
import { fetchTrend } from '../../api/dashboard';
import type { TrendItem } from '../../types';

export default function RiskTrendChart() {
  const [data, setData] = useState<TrendItem[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTrend(days)
      .then(setData)
      .finally(() => setLoading(false));
  }, [days]);

  const config = {
    data: [data, data],
    xField: 'date',
    yField: ['total', 'fraud_rate'],
    geometryOptions: [
      { geometry: 'column', color: '#1677ff' },
      {
        geometry: 'line',
        color: '#ff4d4f',
        lineStyle: { lineWidth: 2 },
        point: { size: 3 },
      },
    ],
    yAxis: {
      total: { title: { text: '检测量' } },
      fraud_rate: {
        title: { text: '欺诈率' },
        label: { formatter: (v: string) => `${(parseFloat(v) * 100).toFixed(0)}%` },
      },
    },
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: '#666' }}>检测量 & 欺诈率趋势</span>
        <Space>
          {[7, 30, 90].map((d) => (
            <Button
              key={d}
              size="small"
              type={days === d ? 'primary' : 'default'}
              onClick={() => setDays(d)}
            >
              {d}天
            </Button>
          ))}
        </Space>
      </div>
      {loading ? <Spin style={{ display: 'block', textAlign: 'center', padding: 48 }} /> : <DualAxes {...config} height={220} />}
    </div>
  );
}
```

- [x] **Step 5: 创建 HighRiskTable**

```tsx
import { useEffect, useState } from 'react';
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { fetchHighRisk } from '../../api/dashboard';
import type { HighRiskItem } from '../../types';

const columns: ColumnsType<HighRiskItem> = [
  { title: '案件ID', dataIndex: 'policy_id', key: 'policy_id', width: 180 },
  {
    title: '欺诈概率',
    dataIndex: 'fraud_prob',
    key: 'fraud_prob',
    width: 100,
    render: (v: number) => (
      <span style={{ fontWeight: 600, color: v >= 0.7 ? '#ff4d4f' : '#faad14' }}>
        {(v * 100).toFixed(1)}%
      </span>
    ),
  },
  {
    title: '风险等级',
    dataIndex: 'risk_level',
    key: 'risk_level',
    width: 80,
    render: (v: string) => <Tag color={v === 'high' ? 'red' : 'orange'}>{v}</Tag>,
  },
  {
    title: '理赔金额',
    dataIndex: 'claim_amount',
    key: 'claim_amount',
    width: 100,
    render: (v: number | null) => (v != null ? v.toFixed(2) : '-'),
  },
];

export default function HighRiskTable() {
  const [items, setItems] = useState<HighRiskItem[]>([]);

  useEffect(() => {
    fetchHighRisk(5).then(setItems).catch(() => {});
  }, []);

  return (
    <div>
      <div style={{ fontWeight: 600, fontSize: 14, color: '#666', marginBottom: 12 }}>
        高风险案件 Top 5
      </div>
      <Table
        columns={columns}
        dataSource={items}
        rowKey="id"
        size="small"
        pagination={false}
      />
    </div>
  );
}
```

- [x] **Step 6: 更新 DashboardPage.tsx**

替换 `frontend/src/pages/DashboardPage.tsx` 为：

```tsx
import { Card, Col, Row } from 'antd';
import StatsCards from '../components/dashboard/StatsCards';
import RiskTrendChart from '../components/dashboard/RiskTrendChart';
import HighRiskTable from '../components/dashboard/HighRiskTable';

export default function DashboardPage() {
  return (
    <div>
      <h2>仪表盘</h2>
      <StatsCards />
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={15}>
          <Card>
            <RiskTrendChart />
          </Card>
        </Col>
        <Col span={9}>
          <Card>
            <HighRiskTable />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
```

- [x] **Step 7: 安装 @ant-design/charts**

```bash
cd frontend && npm install @ant-design/charts
```

- [x] **Step 8: TypeScript 类型检查**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无类型错误.

- [x] **Step 9: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/dashboard.ts \
  frontend/src/components/dashboard/StatsCards.tsx \
  frontend/src/components/dashboard/RiskTrendChart.tsx \
  frontend/src/components/dashboard/HighRiskTable.tsx \
  frontend/src/pages/DashboardPage.tsx \
  frontend/package.json frontend/package-lock.json
git commit -m "feat: add dashboard frontend — StatsCards, RiskTrendChart, HighRiskTable"
```

---

### Task 15: 清理 Vite 脚手架残留 + 添加 shap 依赖

**Files:**
- Delete: `frontend/src/App.css`
- Delete: `frontend/src/assets/hero.png`
- Delete: `frontend/src/assets/react.svg`
- Delete: `frontend/src/assets/vite.svg`
- Modify: `pyproject.toml` (add shap)
- Modify: `.claude/CLAUDE.md` (mark cleanup done)

- [x] **Step 1: 删除残留文件**

```bash
rm -f frontend/src/App.css
rm -f frontend/src/assets/hero.png
rm -f frontend/src/assets/react.svg
rm -f frontend/src/assets/vite.svg
```

- [x] **Step 2: 添加 shap 到依赖**

```bash
uv add --group ml shap
```

- [x] **Step 3: 更新 CLAUDE.md checklist**

将 `.claude/CLAUDE.md` 中 Phase 2 checklist 的 Vite 清理项标记为已完成 `[x]`.

- [x] **Step 4: Commit**

```bash
git add -u frontend/src/App.css frontend/src/assets/ pyproject.toml uv.lock
git commit -m "chore: clean up Vite boilerplate, add shap dependency"
```

---

### Task 16: 端到端验证

- [x] **Step 1: 启动后端并验证全部 API**

```bash
# 启动后端
uv run uvicorn backend.app.main:app --reload --port 8000 &
sleep 2

# 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

# health
curl -s http://localhost:8000/api/health | python -c "import sys,json; print(json.load(sys.stdin))"

# field-options
curl -s http://localhost:8000/api/predict/field-options \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin)['data']; print(len(d['fields']), 'fields')"

# dashboard stats
curl -s http://localhost:8000/api/dashboard/stats \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; print(json.load(sys.stdin)['data'])"

# dashboard trend
curl -s "http://localhost:8000/api/dashboard/trend?days=30" \
  -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; print(len(json.load(sys.stdin)['data']['trend']), 'days')"
```

Expected: 
- health: `{"code":0, ...}`
- field-options: `27 fields`
- dashboard stats: `{"today_pending": N, ...}`
- dashboard trend: `N days`

- [x] **Step 2: 前端 Dev 模式验证**

```bash
cd frontend && npm run dev
```

访问 `http://localhost:5173` → 
- 登录 → 仪表盘显示 seed 数据（统计卡片 + 趋势图 + 高风险表）
- 导航到"单条预测" → 表单渲染 → 填写 → 提交 → 结果区展示 RiskGauge + SHAP

- [x] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "chore: final verification — all Phase 2 APIs and frontend working"
```

---

## 任务依赖

```
Task 1 (model_service)  ──┐
                          ├──→ Task 4 (predict_service) ──→ Task 5 (predict router)
Task 2 (feature_transform)┘                                      │
                                                                  │
Task 3 (predict schemas) ────────────────────────────────────────┘
                                                                  │
Task 6 (predict api ts) ──→ Task 7 (RiskGauge) ──→ Task 9 (PredictionForm) ──→ Task 10 (PredictionPage)
                           Task 8 (ShapExplanation) ──┘

Task 11 (dashboard schemas) ──→ Task 12 (dashboard API) ──→ Task 13 (seed script)
                                                                    │
Task 14 (dashboard frontend) ──────────────────────────────────────┘

Task 15 (cleanup) ──→ Task 16 (e2e verify) 
```
