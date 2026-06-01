# 项目架构参考

> 从 CLAUDE.md 移出的详细参考信息，按需读取。

## 项目结构

```
rgzn-class/
├── data/                                # 特征工程（不再修改）
│   ├── raw/                             # 原始 Excel（不入库，需手动放入）
│   ├── preprocessing.py                 # 特征工程脚本 v4
│   └── train_eval_test/                 # 训练/验证/测试集 (76,911 条)
│
├── modeling/                            # 模型（不再修改）
│   ├── modeling.py                      # XGBoost 建模脚本
│   ├── xgb_fraud_model.pkl              # 训练好的模型（不入库）
│   └── plots/                           # 评估图表 + SHAP
│
├── backend/
│   ├── Dockerfile                       # python:3.12-slim, uv, entrypoint 自动迁移
│   ├── alembic.ini + alembic/           # 异步迁移
│   │   └── versions/                    # 3 个迁移: 初始 7 表 + user_role enum + is_synthetic
│   ├── scripts/
│   │   ├── extract_preprocess_params.py # 从训练脚本提取 winsor/log 参数
│   │   └── seed_demo.py                 # 100 条演示预测记录
│   └── app/
│       ├── main.py                      # FastAPI app factory + CORS + lifespan
│       ├── config.py                    # pydantic-settings, 环境变量驱动
│       ├── database.py                  # AsyncEngine + session + get_db (auto commit/rollback)
│       ├── deps.py                      # get_current_user, require_admin
│       ├── models/                      # 7 个 ORM 模型
│       │   ├── user.py                  # UserRole(str, Enum) + SQLAlchemyEnum
│       │   ├── policy.py                # + is_synthetic 标记
│       │   ├── insuree.py, accident_claim.py  # accident_claim 含 is_synthetic 标记
│       │   ├── fraud_detect_result.py   # JSONB: feature_values, shap_values, agent_report
│       │   ├── model_info.py, case_history.py
│       ├── schemas/
│       │   ├── auth.py                  # RegisterRequest, LoginRequest, TokenResponse
│       │   ├── predict.py               # FieldOption, PredictSingleRequest/Response, ShapItem
│       │   └── dashboard.py             # DashboardStats, TrendItem, HighRiskItem
│       ├── services/
│       │   ├── auth_service.py          # register/login/refresh/me
│       │   ├── model_service.py         # 模块级单例: 加载 .pkl, 3 步推理 + SHAP Top 10
│       │   ├── feature_transform.py     # 7 步管线: 缺失标记→填充→Winsor→log1p→Scaler
│       │   ├── predict_service.py       # 单条预测编排 + field-options 构建
│       │   ├── dashboard_service.py     # stats/trend/high-risk 聚合查询
│       │   └── preprocess_params.json   # 训练参数（含 cat_options 烘焙值）
│       ├── routers/
│       │   ├── auth.py                  # /api/auth/*
│       │   ├── predict.py               # /api/predict/*
│       │   └── dashboard.py             # /api/dashboard/*
│       ├── tasks/                       # Celery app 骨架（Phase 3 填充）
│       │   ├── celery_app.py, batch_tasks.py
│       └── utils/
│           ├── security.py              # JWT + bcrypt（直接调 bcrypt，不用 passlib）
│           └── exceptions.py            # 全局异常处理 + AppException
│
├── frontend/
│   ├── vite.config.ts                   # proxy /api → localhost:8000
│   └── src/
│       ├── main.tsx, App.tsx            # ConfigProvider + BrowserRouter + 路由守卫（5 路由）
│       ├── types/index.ts               # ApiResponse<T>, User, auth/predict/dashboard types
│       ├── api/
│       │   ├── client.ts                # Axios + JWT interceptor + 自动 refresh
│       │   ├── auth.ts, predict.ts, dashboard.ts
│       ├── store/authStore.ts           # Zustand（localStorage 持久化 token）
│       ├── hooks/useAuth.ts             # login/logout/register/fetchMe
│       ├── components/
│       │   ├── layout/AppLayout.tsx     # 侧边栏 + Header + 内容区
│       │   ├── predict/
│       │   │   ├── PredictionForm.tsx    # 27 字段/6 组 Collapse + Steps 向导
│       │   │   ├── RiskGauge.tsx         # SVG 半圆仪表盘
│       │   │   └── ShapExplanation.tsx   # SHAP Top 10 列表
│       │   └── dashboard/
│       │       ├── StatsCards.tsx        # 4 列统计卡片（60s 轮询）
│       │       ├── RiskTrendChart.tsx    # @ant-design/charts DualAxes
│       │       └── HighRiskTable.tsx     # 高风险 Top 5 表格（60s 轮询）
│       └── pages/
│           ├── LoginPage.tsx            # 登录/注册 Tab 页
│           ├── DashboardPage.tsx        # 仪表盘
│           └── PredictionPage.tsx       # 单条预测
│
├── docker/
│   ├── nginx/default.conf               # 反向代理 /api → backend:8000
│   └── postgres/init.sql
├── docker-compose.yml                   # 5 服务: postgres, redis, backend, celery-worker, nginx
└── pyproject.toml                       # uv dependency-groups: ml + web
```

## 数据库设计（7 张表）

| 表 | 主键 | 关键字段 | 说明 |
|---|------|----------|------|
| `user_info` | UUID | username UNIQUE, email UNIQUE, user_role(UserRole enum) | 系统用户 |
| `policy_info` | varchar | FK→insuree_info, is_synthetic | 保单（含合成标记） |
| `insuree_info` | varchar | age, gender, occupation | 被保险人 |
| `accident_claim_info` | int auto | FK→policy_info, claim_amount, is_fraud, is_synthetic | 理赔记录 |
| `fraud_detect_result` | int auto | FK×3, fraud_prob, risk_level, feature_values(JSONB), shap_values(JSONB) | AI 预测结果 |
| `model_info` | UUID | param_config(JSONB), metrics, is_active | 模型元数据 |
| `case_history` | int auto | FK×3, manual_result, remark, operate_time | 审核历史 |

**字段语义**：
- `accident_claim_info.is_fraud`: 仅训练数据回填时的真实标签，运行时新案件为 NULL
- `fraud_detect_result.manual_result`: AI 预测后审核员的初始标注（pass/reject/investigate）
- `case_history.manual_result`: 审核员最终判定，以 case_history 为权威来源
- `is_synthetic`: 单条预测和 seed 创建的骨架记录标记为 True，dashboard 查询过滤

## 模型推理

模型文件 `modeling/xgb_fraud_model.pkl` 包含 5 个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `base_model` | XGBClassifier | 原始 XGBoost 模型（用于 SHAP 分析） |
| `calibrator` | IsotonicRegression | 概率校准器（y_min=0, y_max=1） |
| `threshold` | float | 最优阈值 0.36（验证集 F1 最大） |
| `feature_cols` | list[str] | 35 个特征列名（含顺序） |
| `cat_cols` | list[str] | 7 个类别特征列名 |

推理流程：

```python
import joblib, numpy as np
m = joblib.load('modeling/xgb_fraud_model.pkl')
raw_prob = m['base_model'].predict_proba(X)[:, 1]       # 原始概率
calibrated_prob = m['calibrator'].predict(raw_prob)      # 校准
pred = (calibrated_prob >= m['threshold']).astype(int)   # 阈值判定
```

特征构成（35 个 = 7 类别 + 23 连续 + 5 缺失标记）：

- **7 类别**: ICD10_CHAPTER, BH_PREFIX, BH_CATEGORY, MBR_TYPE, BEN_TYPE, KIND_CODE, POCY_PLAN_DESC
- **23 连续**: SUB_AMT, TOTAL_RECEIPT_AMT, ORG_PRES_AMT_VALUE, COPAY_PCT, NO_OF_YR, POLICY_CNT, INVOICE_CNT, DAYS_INCUR_TO_PAY, DAYS_RCV_TO_CLOSE, DAYS_HOSPITALIZATION, DAYS_RCV_TO_PAY, IS_INPATIENT, INCUR_MONTH, INCUR_DAYOFWEEK, INCUR_QUARTER, INCUR_IS_WEEKEND, PROV_LEVEL_ORDINAL, RECEIPT_TO_SUB_RATIO, IS_NEW_INSURED, IS_LONGTERM_INSURED, MBR_CLAIM_COUNT, MBR_AVG_SUB_AMT, MBR_UNIQUE_HOSPITALS
- **5 缺失标记**: TOTAL_RECEIPT_AMT_MISSING, DAYS_INCUR_TO_PAY_MISSING, DAYS_RCV_TO_CLOSE_MISSING, DAYS_RCV_TO_PAY_MISSING, KIND_CODE_MISSING

类别特征必须转为 pandas `'category'` dtype（XGBoost 2.0+ 原生支持）才能正确推理。

### 风险等级划分

| 等级 | 阈值 | 说明 |
|------|------|------|
| high | ≥ 0.7 | 高欺诈风险，需优先审核（业务决策阈值） |
| medium | 0.36 – 0.7 | 中等风险 |
| low | < 0.36 | 低风险（低于训练最优阈值） |

## 特征变换管线

`feature_transform.py` 的 7 步管线（与训练时 `preprocessing.py` 一致）：

```
原始 35 特征值
  (0) 生成 *_MISSING 缺失标记（BEFORE 填充）
  (1) 类别 NaN → 'UNKNOWN' → category dtype
  (2) 连续 NaN → 中位数填充
  (3) Winsor 截尾（10 特征，skip_winsor 12 特征跳过）
  (4) log1p 变换（9 偏态特征）
  (5) StandardScaler（23 连续特征）
  (6) 按 FEATURE_COLS 顺序返回 (1, 35) DataFrame
```

转换参数来自 `preprocess_params.json`，包含 `cat_options` 烘焙值（Docker 无需 `data/` 目录）。

### 成员聚合特征

3 个成员级别聚合特征（MBR_CLAIM_COUNT, MBR_AVG_SUB_AMT, MBR_UNIQUE_HOSPITALS）从数据库动态计算：
- 查询 `accident_claim_info` JOIN `policy_info` WHERE insuree_id
- 新 insuree（无历史记录）→ 全 0
- 过滤 `is_synthetic=True` 记录
- MBR_UNIQUE_HOSPITALS：训练用 PROV_CODE，DB 缺此字段，用 distinct policy_id 代理

## 认证架构

- JWT access_token（30min）+ refresh_token（7d）
- `get_current_user`：FastAPI Depends，从 Bearer token 解析用户
- `require_admin`：Depends(get_current_user) → 检查 UserRole.admin
- `UserRole(str, enum.Enum)` 继承自 `str`，JWT 序列化/depends 角色比较均正常，无需 `.value` 转换
- 前端：Zustand authStore + Axios interceptor（自动附加 token + 401 自动 refresh）
- 路由守卫：ProtectedRoute（需登录）、GuestRoute（已登录跳首页）

## 关键设计决策

- `model_service.py` 和 `feature_transform.py` 使用模块级单例 + `threading.Lock` 双检锁
- `preprocess_params.json` 含 `cat_options`（类别特征可选值），Docker 无需挂载 `data/`
- 单条预测合成 policy/claim 记录标记 `is_synthetic=True`，dashboard 查询过滤 `is_synthetic=False`
- 前端无 emoji，统一 `@ant-design/icons`；仪表盘 60s 自动轮询
- RiskGauge 纯 SVG/CSS，趋势图用 `@ant-design/charts` `DualAxes`
