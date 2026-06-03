# Phase 4 模块 2: 数据管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理员上传原始 Excel（108 列），系统自动完成预处理（→35 特征）→ 推理 → 入库，结果可在案件管理中查看

**Architecture:** 三层管线：preprocess_service (108→35 raw) → feature_transform (35 raw→35 scaled) → model_service (推理) → 入库。Celery 异步执行预处理（全量 DataFrame）+ 逐行推理入库。进度追踪复用 Redis 模式。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Celery + Redis + pandas + React 18 + TypeScript + Ant Design 5

---

### Task 1: 新增预处理 Service

**Files:**
- Create: `backend/app/services/preprocess_service.py`

- [ ] **Step 1: 创建 108→35 预处理服务**

从 `data/preprocessing.py` 提取核心预处理逻辑，去掉 FRAUD 标签计算、train/test split、winsor/log/scaler（这些留给 feature_transform.py）。

```python
"""原始 Excel (108列) → 35 特征 DataFrame (原始值，未缩放).

从 data/preprocessing.py 提取核心逻辑，去掉：
  - FRAUD 标签计算
  - train/eval/test 切分
  - winsor / log1p / StandardScaler（feature_transform.py 负责）
  - category dtype 转换（feature_transform.py 负责）
"""

import logging
import pandas as pd
import numpy as np

from backend.app.utils.exceptions import AppException

logger = logging.getLogger(__name__)

# 35 特征列（与模型训练时的 FEATURE_COLS 一致）
CATEGORICAL = [
    'ICD10_CHAPTER', 'BH_PREFIX', 'BH_CATEGORY',
    'MBR_TYPE', 'BEN_TYPE', 'KIND_CODE', 'POCY_PLAN_DESC',
]
CONTINUOUS = [
    'SUB_AMT', 'TOTAL_RECEIPT_AMT', 'ORG_PRES_AMT_VALUE', 'COPAY_PCT',
    'NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT',
    'DAYS_INCUR_TO_PAY', 'DAYS_RCV_TO_CLOSE',
    'DAYS_HOSPITALIZATION', 'DAYS_RCV_TO_PAY',
    'IS_INPATIENT', 'INCUR_MONTH', 'INCUR_DAYOFWEEK',
    'INCUR_QUARTER', 'INCUR_IS_WEEKEND',
    'PROV_LEVEL_ORDINAL', 'RECEIPT_TO_SUB_RATIO',
    'IS_NEW_INSURED', 'IS_LONGTERM_INSURED',
    'MBR_CLAIM_COUNT', 'MBR_AVG_SUB_AMT', 'MBR_UNIQUE_HOSPITALS',
]

AMOUNT_COLS = [
    'APP_AMT', 'BEN_SPEND', 'SUB_AMT', 'TOTAL_RECEIPT_AMT',
    'CL_SOCIAL_PAY_AMT', 'CL_OWNER_PAY_AMT', 'CL_SELF_CAT_PAY_AMT',
    'DED_AMT', 'PAY_AMT_USD', 'CWF_AMT_DAY',
]


def preprocess_raw_excel(df: pd.DataFrame) -> pd.DataFrame:
    """将原始 108 列 DataFrame 转换为 35 特征 DataFrame.

    入参 df 由调用方从 Excel 读入，列名已标准化（strip + uppercase）。
    返回的 DataFrame 包含 35 个特征列，值为原始值（未经 winsor/log/scaler）。
    """

    # ---- 1. 金额列清洗 ----
    for col in AMOUNT_COLS:
        if col not in df.columns:
            continue
        s = df[col].astype(str).str.replace('RMB', '', case=False, regex=False)
        s = s.str.replace(',', '', regex=False).str.replace(' ', '', regex=False)
        s = s.str.strip().replace(['nan', 'NAN', 'None', '', 'NULL'], np.nan)
        df[col] = pd.to_numeric(s, errors='coerce')

    # ---- 2. 日期特征 ----
    date_cols_map = [
        ('INCUR_DATE_FROM', '_from'), ('INCUR_DATE_TO', '_to'),
        ('PAY_DATE', '_pay'), ('RCV_DATE', '_rcv'), ('FILE_CLOSE_DATE', '_close'),
    ]
    for col, name in date_cols_map:
        if col in df.columns:
            df[name] = pd.to_datetime(df[col], errors='coerce')

    if '_from' in df.columns and '_pay' in df.columns:
        df['DAYS_INCUR_TO_PAY'] = (df['_pay'] - df['_from']).dt.days
    if '_rcv' in df.columns and '_close' in df.columns:
        df['DAYS_RCV_TO_CLOSE'] = (df['_close'] - df['_rcv']).dt.days
    if '_to' in df.columns and '_from' in df.columns:
        df['DAYS_HOSPITALIZATION'] = (df['_to'] - df['_from']).dt.days
        df['IS_INPATIENT'] = (df['DAYS_HOSPITALIZATION'] > 0).astype(int)
    if '_from' in df.columns:
        df['INCUR_MONTH'] = df['_from'].dt.month.astype(int)
        df['INCUR_DAYOFWEEK'] = df['_from'].dt.dayofweek.astype(int)
        df['INCUR_QUARTER'] = df['_from'].dt.quarter.astype(int)
        df['INCUR_IS_WEEKEND'] = (df['INCUR_DAYOFWEEK'] >= 5).astype(int)
    if '_rcv' in df.columns and '_pay' in df.columns:
        df['DAYS_RCV_TO_PAY'] = (df['_pay'] - df['_rcv']).dt.days

    # 清理临时日期列
    for name in ['_from', '_to', '_pay', '_rcv', '_close']:
        if name in df.columns:
            del df[name]

    # ---- 3. ICD-10 章节映射 ----
    if 'DIAG_CODE' in df.columns:

        def _icd10_chapter(code):
            if pd.isna(code) or not isinstance(code, str):
                return 'UNKNOWN'
            c = code.strip().upper()[0]
            rest = code.strip().upper()[1:] if len(code) > 1 else ''

            if c in ('A', 'B'):    return 'INFECTIOUS'
            elif c == 'C':          return 'NEOPLASM'
            elif c == 'D':
                if rest and rest[0] in '01234': return 'NEOPLASM'
                return 'BLOOD'
            elif c == 'E':          return 'ENDOCRINE'
            elif c == 'F':          return 'MENTAL'
            elif c == 'G':          return 'NERVOUS'
            elif c == 'H':
                if rest and rest[0] in '0123456789': return 'EYE_EAR'
                return 'OTHER'
            elif c == 'I':          return 'CIRCULATORY'
            elif c == 'J':          return 'RESPIRATORY'
            elif c == 'K':          return 'DIGESTIVE'
            elif c == 'L':          return 'SKIN'
            elif c == 'M':          return 'MUSCULOSKELETAL'
            elif c == 'N':          return 'GENITOURINARY'
            elif c == 'O':          return 'PREGNANCY'
            elif c == 'P':          return 'PERINATAL'
            elif c == 'Q':          return 'CONGENITAL'
            elif c == 'R':          return 'SYMPTOMS'
            elif c in ('S', 'T'):   return 'INJURY'
            elif c == 'Z':          return 'FACTORS'
            else:                   return 'OTHER'

        df['ICD10_CHAPTER'] = df['DIAG_CODE'].apply(_icd10_chapter)

    # ---- 4. BEN_HEAD 拆分 ----
    if 'BEN_HEAD' in df.columns:
        bh = df['BEN_HEAD'].fillna('').astype(str)
        df['BH_PREFIX'] = 'OTHER'
        df.loc[bh.str.startswith('S-'), 'BH_PREFIX'] = 'SOCIAL'
        df.loc[bh.str.startswith('F-'), 'BH_PREFIX'] = 'NON_SOCIAL'
        df.loc[bh.str.startswith('NS-'), 'BH_PREFIX'] = 'NS'
        df.loc[bh.str.startswith('NF-'), 'BH_PREFIX'] = 'NF'
        df.loc[bh.str.startswith('100P'), 'BH_PREFIX'] = '100PCT'
        df['BH_CATEGORY'] = bh.str.extract(r'[-]?(YPF|GHF|JCF|ZLF|CJF|ZYF|ZFYP|SSF|CLF|CWF)$')
        df['BH_CATEGORY'] = df['BH_CATEGORY'].fillna('OTHER')

    # ---- 5. PROV_LEVEL 序数化 ----
    if 'PROV_LEVEL' in df.columns:
        order = {
            '一级': 1, '二级': 2, '三级': 3,
            '医保': 10, '非医保': 11,
            '未评级': 0, '卫生所': 1, '特需': 4,
        }
        df['PROV_LEVEL_ORDINAL'] = (
            df['PROV_LEVEL'].astype(str).str.upper().map(order).fillna(-1).astype(int)
        )

    # ---- 6. 类别特征标准化 ----
    if 'MBR_TYPE' in df.columns:
        df['MBR_TYPE'] = df['MBR_TYPE'].astype(str).str.upper().replace(
            ['NAN', 'NONE', 'NULL', ''], 'UNKNOWN'
        )
    if 'SCMA_OID_BEN_TYPE' in df.columns:
        df['BEN_TYPE'] = df['SCMA_OID_BEN_TYPE'].astype(str).str.upper()
    if 'KIND_CODE' in df.columns:
        df['KIND_CODE'] = df['KIND_CODE'].astype(str).str.upper()
    if 'POCY_PLAN_DESC' in df.columns:
        df['POCY_PLAN_DESC'] = (
            df['POCY_PLAN_DESC'].astype(str).str.upper()
            .replace(['NAN', 'NONE', 'NULL', ''], 'UNKNOWN')
        )

    # ---- 7. 数值列转换 ----
    for col in ['NO_OF_YR', 'POLICY_CNT', 'INVOICE_CNT', 'COPAY_PCT',
                'SUB_AMT', 'TOTAL_RECEIPT_AMT', 'ORG_PRES_AMT_VALUE']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # ---- 8. 派生比率 ----
    if 'TOTAL_RECEIPT_AMT' in df.columns and 'SUB_AMT' in df.columns:
        df['RECEIPT_TO_SUB_RATIO'] = np.where(
            df['SUB_AMT'].fillna(0) > 0,
            df['TOTAL_RECEIPT_AMT'].fillna(0) / df['SUB_AMT'].clip(lower=1),
            0,
        )

    # ---- 9. 被保人特征 ----
    if 'NO_OF_YR' in df.columns:
        df['IS_NEW_INSURED'] = (df['NO_OF_YR'].fillna(0) <= 1).astype(int)
        df['IS_LONGTERM_INSURED'] = (df['NO_OF_YR'].fillna(0) >= 5).astype(int)

    # ---- 10. 被保人聚合特征 ----
    if 'MBR_NO' in df.columns:
        df['MBR_CLAIM_COUNT'] = df.groupby('MBR_NO')['MBR_NO'].transform('count')
        if 'SUB_AMT' in df.columns:
            df['MBR_AVG_SUB_AMT'] = df.groupby('MBR_NO')['SUB_AMT'].transform('mean')
        if 'PROV_CODE' in df.columns:
            df['MBR_UNIQUE_HOSPITALS'] = df.groupby('MBR_NO')['PROV_CODE'].transform('nunique')

    # ---- 11. 筛选 35 特征列 ----
    all_features = CATEGORICAL + CONTINUOUS
    available = [c for c in all_features if c in df.columns]
    missing = set(all_features) - set(available)

    if missing:
        raise AppException(
            f"预处理后缺少 {len(missing)} 个必需特征列: {sorted(missing)}",
            status_code=500,
        )

    logger.info("Preprocess done: %d rows, %d features", len(df), len(available))
    return df[available]
```

- [ ] **Step 2: 验证语法**

```bash
uv run python -c "from backend.app.services.preprocess_service import preprocess_raw_excel; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/preprocess_service.py
git commit -m "feat: add preprocess service for 108→35 feature engineering"
```

---

### Task 2: 新增 Celery 数据导入任务

**Files:**
- Create: `backend/app/tasks/data_tasks.py`
- Modify: `backend/app/tasks/celery_app.py`

- [ ] **Step 1: 创建 data_tasks.py**

```python
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

        # 2. 预处理: 108列 → 35特征
        from backend.app.services.preprocess_service import preprocess_raw_excel
        feature_df = preprocess_raw_excel(df)
        feature_cols = list(feature_df.columns)
        del df

        _update_progress(task_id, step="inference")

        # 3. 逐行: 特征变换 → 推理 → 入库
        import asyncio
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(
            _process_rows(feature_df, feature_cols, task_id, total)
        )
        loop.close()

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
    """逐行处理: 特征变换 → 推理 → 持久化."""
    from backend.app.database import async_session
    from backend.app.models.insuree import Insuree
    from backend.app.models.policy import Policy
    from backend.app.models.accident_claim import AccidentClaim
    from backend.app.models.fraud_detect_result import FraudDetectResult
    from backend.app.models.model_info import ModelInfo
    from backend.app.services import model_service, feature_transform

    feature_transform._load_params()
    cat_cols = feature_transform.CAT_COLS

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
                # Build feature dict from preprocessed row
                feature_dict = {}
                for col in feature_cols:
                    val = row[col]
                    if pd.isna(val):
                        feature_dict[col] = 0.0 if col not in cat_cols else "UNKNOWN"
                    elif col in cat_cols:
                        feature_dict[col] = str(val)
                    else:
                        feature_dict[col] = float(val)

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
```

- [ ] **Step 2: 修改 celery_app.py**

将 `celery_app.py` 第 11 行的 `include` 从：

```python
include=["backend.app.tasks.batch_tasks"],
```

改为：

```python
include=["backend.app.tasks.batch_tasks", "backend.app.tasks.data_tasks"],
```

- [ ] **Step 3: 验证语法**

```bash
uv run python -c "from backend.app.tasks.data_tasks import process_data_import; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/tasks/data_tasks.py backend/app/tasks/celery_app.py
git commit -m "feat: add Celery data import task for preprocessing + inference pipeline"
```

---

### Task 3: 扩展 Admin Schema + Service

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/services/admin_service.py`

- [ ] **Step 1: 追加 schema**

在 `schemas/admin.py` 末尾追加：

```python
class DataTaskStatus(BaseModel):
    task_id: str
    filename: str
    status: str  # pending | processing | completed | failed
    total: int | None = None
    processed: int | None = None
    success: int | None = None
    failed: int | None = None
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class DataTaskListResponse(BaseModel):
    items: list[DataTaskStatus]
    total: int
    page: int
    size: int
```

- [ ] **Step 2: 追加 service 函数**

在 `services/admin_service.py` 末尾追加：

```python
from backend.app.utils.redis_utils import redis_get


async def get_data_task_status(task_id: str) -> dict:
    """从 Redis 查询数据导入任务进度."""
    data = redis_get(f"data_task:{task_id}")
    if data is None:
        raise AppException("任务不存在或已过期", status_code=404)
    data["task_id"] = task_id
    return data
```

- [ ] **Step 3: 验证语法**

```bash
uv run python -c "from backend.app.schemas.admin import DataTaskStatus, DataTaskListResponse; from backend.app.services.admin_service import get_data_task_status; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/services/admin_service.py
git commit -m "feat: add data task schemas and status query service"
```

---

### Task 4: 扩展 Admin Router

**Files:**
- Modify: `backend/app/routers/admin.py`

- [ ] **Step 1: 追加 3 个数据管理端点**

在 `routers/admin.py` 末尾追加：

```python
import uuid as _uuid
import os as _os

from fastapi import UploadFile, File

UPLOAD_DIR = _os.path.join(settings.BATCH_RESULT_DIR, "uploads")
_os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/data/upload")
async def upload_data(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
):
    """上传原始 Excel，创建数据导入任务."""
    allowed_ext = (".xlsx", ".xls")
    if not file.filename or not file.filename.lower().endswith(allowed_ext):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "仅支持 Excel 文件 (.xlsx/.xls)"},
        )

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "文件大小不能超过 100MB"},
        )
    if len(content) == 0:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "data": None, "message": "文件为空"},
        )

    task_id = _uuid.uuid4().hex
    filepath = _os.path.join(UPLOAD_DIR, f"{task_id}.xlsx")
    with open(filepath, "wb") as f:
        f.write(content)

    from backend.app.utils.redis_utils import redis_set
    from datetime import datetime as _dt

    redis_set(
        f"data_task:{task_id}",
        {
            "filename": file.filename,
            "status": "pending",
            "created_at": _dt.now().isoformat(),
        },
    )

    from backend.app.tasks.data_tasks import process_data_import
    process_data_import.delay(task_id, filepath, file.filename)

    return ok({"task_id": task_id})


@router.get("/data/tasks")
async def list_data_tasks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_admin),
):
    """历史数据导入任务列表."""
    from backend.app.utils.redis_utils import _get_redis, redis_get

    r = _get_redis()
    keys = [k.decode() for k in r.keys("data_task:*") if b":" in k]
    items = []
    for key in keys:
        data = redis_get(key)
        if data:
            data["task_id"] = key.split(":", 1)[1]
            items.append(data)

    # 按创建时间降序
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total = len(items)
    # 分页
    offset = (page - 1) * size
    paged = items[offset : offset + size]

    return ok(DataTaskListResponse(
        items=[DataTaskStatus(**it) for it in paged],
        total=total,
        page=page,
        size=size,
    ).model_dump(mode="json"))


@router.get("/data/tasks/{task_id}/status")
async def data_task_status(
    task_id: str,
    current_user: User = Depends(require_admin),
):
    """查询数据导入任务进度."""
    from backend.app.services.admin_service import get_data_task_status
    data = await get_data_task_status(task_id)
    return ok(data)
```

导入区域追加：

```python
from backend.app.config import settings
```

- [ ] **Step 2: 验证语法**

```bash
uv run python -c "from backend.app.routers.admin import router; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/admin.py
git commit -m "feat: add data upload/tasks/status endpoints to admin router"
```

---

### Task 5: 前端类型 + API 扩展

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/admin.ts`

- [ ] **Step 1: 追加类型定义**

在 `types/index.ts` 末尾追加：

```typescript
// ---- 数据管理 ----
export interface DataTaskStatus {
  task_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total: number | null;
  processed: number | null;
  success: number | null;
  failed: number | null;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface DataTaskListResponse {
  items: DataTaskStatus[];
  total: number;
  page: number;
  size: number;
}
```

- [ ] **Step 2: 追加 API 函数**

在 `api/admin.ts` 末尾追加：

```typescript
import type { DataTaskStatus, DataTaskListResponse } from '../types';

export async function uploadData(file: File): Promise<{ task_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await client.post<ApiResponse<{ task_id: string }>>('/admin/data/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data.data;
}

export async function fetchDataTaskStatus(taskId: string): Promise<DataTaskStatus> {
  const res = await client.get<ApiResponse<DataTaskStatus>>(`/admin/data/tasks/${taskId}/status`);
  return res.data.data;
}
```

- [ ] **Step 3: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/admin.ts
git commit -m "feat: add data management types and API functions"
```

---

### Task 6: DataUpload 前端组件

**Files:**
- Create: `frontend/src/components/admin/DataUpload.tsx`

- [ ] **Step 1: 创建上传组件**

```typescript
import { useState, useCallback, useRef } from 'react';
import {
  Upload, Button, Table, message, Tag, Space, Typography,
} from 'antd';
import { UploadOutlined, InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { uploadData, fetchDataTaskStatus } from '../../api/admin';
import type { DataTaskStatus } from '../../types';

const { Dragger } = Upload;
const { Text } = Typography;

const STATUS_COLOR: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
};
const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

interface TaskRecord extends DataTaskStatus {
  key: string;
}

export default function DataUpload() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback((taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await fetchDataTaskStatus(taskId);
        setTasks((prev) =>
          prev.map((t) => (t.key === taskId ? { ...status, key: taskId } : t))
        );
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval);
          if (status.status === 'completed') {
            message.success(`文件 ${status.filename} 导入完成: ${status.success} 条成功`);
          } else {
            message.error(`文件 ${status.filename} 导入失败: ${status.error_message}`);
          }
        }
      } catch {
        // status not yet available
      }
    }, 5000);
    pollRef.current = interval;
  }, []);

  const handleUpload: UploadProps['customRequest'] = useCallback(
    async (options) => {
      const { file, onSuccess, onError } = options as any;
      setUploading(true);
      try {
        const result = await uploadData(file as File);
        const newTask: TaskRecord = {
          key: result.task_id,
          task_id: result.task_id,
          filename: (file as File).name,
          status: 'pending',
          total: null,
          processed: null,
          success: null,
          failed: null,
          error_message: null,
          created_at: new Date().toISOString(),
          completed_at: null,
        };
        setTasks((prev) => [newTask, ...prev]);
        startPolling(result.task_id);
        onSuccess?.(result, file);
        message.success('文件已上传，开始处理');
      } catch (err: any) {
        onError?.(err);
        message.error('上传失败: ' + (err?.message || '未知错误'));
      } finally {
        setUploading(false);
      }
    },
    [startPolling],
  );

  const columns: ColumnsType<TaskRecord> = [
    { title: '文件名', dataIndex: 'filename', key: 'filename' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLOR[s]}>{STATUS_LABEL[s] || s}</Tag>,
    },
    {
      title: '进度', key: 'progress',
      render: (_: unknown, r: TaskRecord) => {
        if (r.total == null) return '-';
        const pct = r.total > 0 ? Math.round(((r.processed ?? 0) / r.total) * 100) : 0;
        return `${r.processed ?? 0} / ${r.total} (${pct}%)`;
      },
    },
    {
      title: '成功/失败', key: 'result',
      render: (_: unknown, r: TaskRecord) => {
        if (r.success == null && r.failed == null) return '-';
        return (
          <span>
            <Text type="success">{r.success ?? 0}</Text>
            {' / '}
            <Text type="danger">{r.failed ?? 0}</Text>
          </span>
        );
      },
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at',
      render: (v: string | null) => v ? new Date(v).toLocaleString() : '-',
    },
  ];

  return (
    <div>
      <Dragger
        accept=".xlsx,.xls"
        maxCount={1}
        customRequest={handleUpload}
        disabled={uploading}
        showUploadList={false}
        style={{ marginBottom: 24 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽上传原始 Excel 文件</p>
        <p className="ant-upload-hint">支持 .xlsx / .xls 格式，最大 100MB</p>
      </Dragger>

      <Table
        rowKey="key"
        columns={columns}
        dataSource={tasks}
        pagination={false}
        locale={{ emptyText: '暂无导入任务' }}
      />
    </div>
  );
}
```

- [ ] **Step 2: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/admin/DataUpload.tsx
git commit -m "feat: add DataUpload component with drag-upload and task list"
```

---

### Task 7: AdminPage 追加数据管理 Tab

**Files:**
- Modify: `frontend/src/pages/AdminPage.tsx`

- [ ] **Step 1: 追加数据管理 Tab**

将 `AdminPage.tsx` 修改为：

```typescript
import { Tabs } from 'antd';
import { TeamOutlined, CloudUploadOutlined } from '@ant-design/icons';
import UserManagement from '../components/admin/UserManagement';
import DataUpload from '../components/admin/DataUpload';

export default function AdminPage() {
  return (
    <Tabs
      defaultActiveKey="users"
      items={[
        {
          key: 'users',
          label: (
            <span><TeamOutlined /> 用户管理</span>
          ),
          children: <UserManagement />,
        },
        {
          key: 'data',
          label: (
            <span><CloudUploadOutlined /> 数据管理</span>
          ),
          children: <DataUpload />,
        },
      ]}
    />
  );
}
```

- [ ] **Step 2: TypeScript 检查**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AdminPage.tsx
git commit -m "feat: add data management tab to AdminPage"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 验证后端 API 导入路径正确**

```bash
uv run python -c "
from backend.app.main import app
from backend.app.tasks.data_tasks import process_data_import
from backend.app.services.preprocess_service import preprocess_raw_excel
from backend.app.schemas.admin import DataTaskStatus, DataTaskListResponse
from backend.app.routers.admin import router
print('All imports OK')
"
```

- [ ] **Step 2: 验证预处理管线（用 test.xlsx）**

```bash
cd D:/rgzn-class && uv run python -c "
import pandas as pd
from backend.app.services.preprocess_service import preprocess_raw_excel

df = pd.read_excel('data/raw/test.xlsx', dtype=str)
df.columns = df.columns.str.strip().str.upper()
df = df.drop_duplicates()
print(f'Input: {df.shape}')

result = preprocess_raw_excel(df)
print(f'Output: {result.shape}')
print(f'Columns: {list(result.columns)}')
print('First row:')
print(result.head(1).T.to_string())
"
```

- [ ] **Step 3: 前端 build 验证**

```bash
cd frontend && npx tsc --noEmit && npx vite build
```

- [ ] **Step 4: 完整流程测试（需要 Redis + Celery worker 运行）**

```bash
# 终端 1: 确保 postgres + redis 运行, 启动 backend
docker compose up -d postgres
uv run uvicorn backend.app.main:app --reload --port 8000

# 终端 2: 启动 Celery worker
uv run celery -A backend.app.tasks.celery_app worker --loglevel=info --pool=solo

# 终端 3: 测试上传
curl -X POST http://localhost:8000/api/admin/data/upload \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@data/raw/test.xlsx"

# 轮询状态
curl http://localhost:8000/api/admin/data/tasks/<task_id>/status \
  -H "Authorization: Bearer <admin_token>"

# 检查案件列表确认入库
curl http://localhost:8000/api/cases?page=1&size=5 \
  -H "Authorization: Bearer <admin_token>"
```

- [ ] **Step 5: Commit（如有修复）**

```bash
git status
# 如有修复，commit
```
