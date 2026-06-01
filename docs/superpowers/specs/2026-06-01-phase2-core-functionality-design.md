# Phase 2: 核心功能 — 设计文档

## 元信息

- **日期**: 2026-06-01
- **范围**: 模型服务 + 单条预测（API + 前端）+ 仪表盘（API + 前端）
- **前提**: Phase 1 基础设施已完成（认证、数据库、Docker 拓扑）
- **实现路径**: 方案 B（功能优先、端到端），4 步推进

---

## 步骤 2.1: 模型服务 + 特征变换

### `model_service.py`

模块级单例，首次 import 时加载 .pkl，全局复用：

```python
MODEL_PATH = os.environ.get("MODEL_PATH", "modeling/xgb_fraud_model.pkl")
model_bundle = joblib.load(MODEL_PATH)
# dict keys: base_model, calibrator, threshold, feature_cols, cat_cols
```

**推理接口**：

```python
def predict(X: pd.DataFrame) -> dict:
    """
    X: (1, 35) DataFrame, 列序与 feature_cols 一致
    返回: {fraud_prob, raw_prob, risk_level, shap_values}
    """
```

- `raw_prob` = `model_bundle['base_model'].predict_proba(X)[:, 1][0]`
- `fraud_prob` = `model_bundle['calibrator'].predict([raw_prob])[0]`
- `risk_level`: `high (≥0.7) / medium (0.36–0.7) / low (<0.36)`
- `shap_values`: `shap.TreeExplainer(base_model).shap_values(X)` → 返回 Top 10 正影响特征列表 `[{feature, value, shap_value}]`，按 `abs(shap_value)` 降序
- 错误处理：模型文件不存在 → `AppException("模型未部署", 503)`

### `feature_transform.py`

对单条输入执行与训练时相同的变换管线：

```
原始 35 个特征值
  → 类别特征（7 个）: astype('category')
  → 连续特征填充（23 个）: preprocess_params.fill_values 中的中位数
  → 缺失标记生成: 检查 5 个字段 → 0/1 标记
  → Winsor 截尾: 10 个特征，使用 preprocess_params.winsor_bounds
  → log1p 变换: 9 个偏态特征，使用 preprocess_params.log_params
  → StandardScaler: 23 个连续特征，使用 preprocess_params.scaler_params
  → 返回 (1, 35) pandas DataFrame
```

**成员聚合特征**（MBR_CLAIM_COUNT, MBR_AVG_SUB_AMT, MBR_UNIQUE_HOSPITALS）：
- 根据 `insuree_id` 从 `insuree_info` + `accident_claim_info` + `fraud_detect_result` 表动态计算
- 新 insuree（无历史记录）：3 个值均为 0
- 批量预测时按批次内 insuree 分组统一计算

**依赖**: `preprocess_params.json`（已提取完毕，35 特征参数完整）

---

## 步骤 2.2: 单条预测 API

### `GET /api/predict/field-options`

返回每个特征的展示 meta，供前端 PredictionForm 动态渲染。需认证。

**响应结构**：

```json
{
  "code": 0,
  "data": {
    "fields": [
      {"name": "ICD10_CHAPTER", "label": "ICD-10 诊断大类", "type": "select",
       "group": "诊断信息", "required": true,
       "options": ["INFECTIOUS", "NEOPLASM", "BLOOD", "ENDOCRINE", ...]},
      {"name": "SUB_AMT", "label": "理赔申请金额", "type": "number",
       "group": "金额信息", "required": true, "min": 0, "step": 0.01},
      ...
    ],
    "groups": ["诊断信息", "金额信息", "保单信息", "时间特征", "被保险人画像", "医院信息"]
  }
}
```

- 不包括 3 个成员聚合特征（后端自动计算）
- 类别特征选项: 从训练数据 `data/train_eval_test/train.csv` 中提取实际唯一值
- 字段配置集中定义在 `schemas/predict.py` 的 `FIELD_META` 字典中
- 实现: 首次请求时构建并缓存（模块级变量），后续请求直接返回缓存

### `POST /api/predict/single`

需认证。请求体（32 个可见字段 + `insuree_id`）：

```json
{
  "insuree_id": "INS001",
  "ICD10_CHAPTER": "INJURY",
  "BH_PREFIX": "SOCIAL",
  "BH_CATEGORY": "OTHER",
  "MBR_TYPE": "EMPLOYEE",
  "BEN_TYPE": "OUTPATIENT",
  "KIND_CODE": "A01",
  "POCY_PLAN_DESC": "STANDARD",
  "SUB_AMT": 500.00,
  "TOTAL_RECEIPT_AMT": 650.00,
  ...
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "id": 42,
    "fraud_prob": 0.78,
    "raw_prob": 0.72,
    "risk_level": "high",
    "threshold_used": 0.36,
    "feature_values": { "SUB_AMT": 500.00, ... },
    "shap_top10": [
      {"feature": "MBR_CLAIM_COUNT", "value": 12.0, "shap_value": 1.25, "direction": "+"},
      ...
    ],
    "detect_time": "2026-06-01T12:00:00Z"
  }
}
```

- `feature_values`: 实际参与推理的 35 个值（含后端计算的缺失标记 + 成员聚合）
- `shap_top10`: 按 `abs(shap_value)` 降序，`direction` = `+` 表示推高欺诈概率

### `predict_service.py` 编排流程

```
1. 校验 insured_id 存在性（不存在 → 400）
2. 查询 insuree 历史记录，计算成员聚合特征
3. 合并用户输入 + 成员聚合 → 35 特征 dict
4. feature_transform.transform_single() → (1, 35) DataFrame
5. model_service.predict() → fraud_prob + raw_prob + shap_values
6. 评级: 根据 threshold 映射 risk_level
7. 写入 fraud_detect_result 表:
   - feature_values (JSONB) → 35 特征值
   - shap_values (JSONB) → Top 10 shap 数据
   - model_id → 当前活跃模型
8. 返回 PredictSingleResponse
```

### 文件清单

```
backend/app/
├── schemas/predict.py                 # 新增
├── services/model_service.py          # 新增
├── services/feature_transform.py      # 新增
├── services/predict_service.py        # 新增
└── routers/predict.py                 # 新增
```

---

## 步骤 2.3: 单条预测前端

### 整体布局: PredictionPage

上下结构：表单区（上）→ 结果展示区（下，提交后渲染）

### PredictionForm 组件

- **位置**: `frontend/src/components/predict/PredictionForm.tsx`
- **职责**: 32 字段表单 + 模式切换 + 提交
- **实现**:
  - 首次加载调用 `GET /api/predict/field-options` 获取字段 meta
  - 默认模式: **Ant Design Collapse**（6 个分组面板），每组可展开/折叠
  - 顶部切换按钮: 折叠面板 ↔ **Ant Design Steps 向导**（4 步: 诊断+金额 → 保单+时间 → 被保人画像+医院 → 确认提交）
  - 类别特征: Select 组件，选项从 field-options 获取
  - 连续特征: InputNumber 组件
  - 提交: `POST /api/predict/single`
  - 成功: 调用父组件 `onResult` callback

### RiskGauge 组件

- **位置**: `frontend/src/components/predict/RiskGauge.tsx`
- **职责**: 半圆弧仪表盘，展示 fraud_prob + risk_level
- **实现**: 纯 CSS/SVG，无外部图表依赖
  - 半圆弧色标: 红(0.7-1.0) → 橙(0.36-0.7) → 绿(0-0.36)
  - 指针位置由 fraud_prob 驱动
  - 中心大字显示概率值 + 风险等级文字
  - Props: `{ fraudProb: number; riskLevel: 'high' | 'medium' | 'low'; threshold: number }`

### ShapExplanation 组件

- **位置**: `frontend/src/components/predict/ShapExplanation.tsx`
- **职责**: SHAP Top 10 特征列表
- **实现**: 简洁列表 + 颜色编码
  - 正 SHAP（推高欺诈）: 红色文字 + 上箭头
  - 负 SHAP（降低欺诈）: 绿色文字 + 下箭头
  - 每行: 特征名 · 特征值 · SHAP 贡献值
  - Props: `{ items: ShapItem[] }`

### 结果展示区

- 表单下方，横向三栏:
  - 左: RiskGauge（固定宽度 240px）
  - 中: ShapExplanation（flex: 1）
  - 右: 快捷审核按钮（pass / reject / investigate）+ 备注框
- 审核按钮点击: 调用 `PUT /api/cases/{id}/adjudicate`（Phase 3 端点，Phase 2 可预留）

### 文件清单

```
frontend/src/
├── api/predict.ts                           # 新增（getFieldOptions, postSinglePredict）
├── components/predict/
│   ├── PredictionForm.tsx                   # 新增
│   ├── RiskGauge.tsx                        # 新增
│   └── ShapExplanation.tsx                  # 新增
└── pages/PredictionPage.tsx                 # 新增
```

### 路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/predict/single` | PredictionPage | reviewer, admin |

侧边栏菜单新增 `单条预测` 项。

---

## 步骤 2.4: 仪表盘 API + 前端 + Seed 数据

### 仪表盘后端

新增 `backend/app/services/dashboard_service.py` + `backend/app/routers/dashboard.py`。

#### `GET /api/dashboard/stats`

返回 4 个核心指标（基于 `fraud_detect_result` 和 `case_history` 当天数据）：

```json
{
  "code": 0,
  "data": {
    "today_pending": 156,       // 今日产生且未审的检测结果数
    "today_high_risk": 23,      // 今日高风险（risk_level='high'）
    "today_processed": 89,      // 今日已审核数（case_history 当天记录数）
    "total_detected": 76911     // 累计检测量
  }
}
```

#### `GET /api/dashboard/trend?days=30`

每日检测量 + 欺诈率时间序列（`days` 默认 30，支持 7/30/90）：

```json
{
  "code": 0,
  "data": {
    "trend": [
      {"date": "2026-05-03", "total": 42, "fraud_rate": 0.12},
      {"date": "2026-05-04", "total": 38, "fraud_rate": 0.09},
      ...
    ]
  }
}
```

- SQL: `fraud_detect_result` 按 `detect_time::date` GROUP BY
- fraud_rate = 当天 `risk_level='high'` 数 / 当天检测总数

#### `GET /api/dashboard/high-risk?limit=5`

高风险案件 Top N，按 fraud_prob DESC：

```json
{
  "code": 0,
  "data": {
    "items": [
      {"id": 42, "policy_id": "POL-xxx", "fraud_prob": 0.96, "risk_level": "high",
       "claim_amount": 8500.0, "detect_time": "..."},
      ...
    ]
  }
}
```

- SQL: `fraud_detect_result` JOIN `accident_claim_info`，WHERE `risk_level='high'`，ORDER BY `fraud_prob DESC`，LIMIT

### 仪表盘前端

替换当前 `DashboardPage.tsx` 的占位卡片。

#### StatsCards 组件

- **位置**: `frontend/src/components/dashboard/StatsCards.tsx`
- **实现**: Ant Design `Card` + `Statistic`，4 列 Row > Col
- 数据源: `GET /api/dashboard/stats`
- 每 60s 自动轮询刷新

#### RiskTrendChart 组件

- **位置**: `frontend/src/components/dashboard/RiskTrendChart.tsx`
- **实现**: `@ant-design/charts` 的 `DualAxes`（双轴图）
  - 左轴（柱状）: 每日检测量
  - 右轴（折线）: 欺诈率 %
  - 顶部按钮组: 7天 / 30天 / 90天
  - 无 emoji 图标

#### HighRiskTable 组件

- **位置**: `frontend/src/components/dashboard/HighRiskTable.tsx`
- **实现**: Ant Design `Table`（compact），显示 policy_id、fraud_prob、claim_amount
- 欺诈概率列用 `Progress` 组件或颜色编码
- "查看全部" 链接跳转 `/cases`（Phase 3）

### Seed 数据脚本

**位置**: `backend/scripts/seed_demo.py`

- 用于 Phase 2 开发/演示阶段
- 插入约 100 条 `fraud_detect_result` 记录（随机 fraud_prob 分布，过去 30 天随机 detect_time）
- 附带几条 `case_history` 审核记录
- 完整数据回填（76,911 条）仍留在 Phase 3

### 文件清单

```
backend/app/
├── services/dashboard_service.py           # 新增
├── routers/dashboard.py                    # 新增
├── schemas/dashboard.py                    # 新增
└── scripts/seed_demo.py                    # 新增

frontend/src/
├── api/dashboard.ts                        # 新增
├── components/dashboard/
│   ├── StatsCards.tsx                      # 新增
│   ├── RiskTrendChart.tsx                  # 新增
│   └── HighRiskTable.tsx                   # 新增
└── pages/DashboardPage.tsx                 # 修改（替换占位卡片）
```

---

## 设计决策摘要

1. **表单混合模式**: 默认 Collapse 分组折叠面板，可一键切换到 Steps 向导
2. **成员聚合特征**: 后端动态计算，表单不展示，新 insuree 填 0
3. **RiskGauge 纯 CSS/SVG**: 不引入额外图表库（@ant-design/charts 仅用于趋势图）
4. **SHAP 展示**: Top 10 列表 + 颜色编码，不额外调用 SHAP waterfall（数据已存入 JSONB 可审计）
5. **仪表盘数据策略**: Phase 2 seed 脚本（~100 条）+ Phase 3 完整回填（76,911 条）
6. **无 emoji 图标**: 所有 UI 组件不使用 emoji 作为装饰图标，统一用 @ant-design/icons
7. **schemas 统一风格**: 所有响应遵循 `{code, data, message}` 格式，Pydantic v2 模型

---

## Phase 2 整体文件变更清单

```
新增 (14 个文件):
  backend/app/schemas/predict.py
  backend/app/schemas/dashboard.py
  backend/app/services/model_service.py
  backend/app/services/feature_transform.py
  backend/app/services/predict_service.py
  backend/app/services/dashboard_service.py
  backend/app/routers/predict.py
  backend/app/routers/dashboard.py
  backend/scripts/seed_demo.py
  frontend/src/api/predict.ts
  frontend/src/api/dashboard.ts
  frontend/src/components/predict/PredictionForm.tsx
  frontend/src/components/predict/RiskGauge.tsx
  frontend/src/components/predict/ShapExplanation.tsx
  frontend/src/components/dashboard/StatsCards.tsx
  frontend/src/components/dashboard/RiskTrendChart.tsx
  frontend/src/components/dashboard/HighRiskTable.tsx
  frontend/src/pages/PredictionPage.tsx

修改 (4 个文件):
  backend/app/main.py                    (+ predict/dashboard 路由注册)
  frontend/src/pages/DashboardPage.tsx    (替换占位卡片)
  frontend/src/App.tsx                   (+ 新增路由)
  frontend/src/components/layout/AppLayout.tsx  (+ 侧边栏菜单项)

依赖新增:
  后端: shap (pip install shap)
  前端: @ant-design/charts (npm install)
```

---

## 验证方式

1. `curl http://localhost:8000/api/predict/field-options` → 返回 32 个字段 meta + 6 个分组
2. `curl -X POST http://localhost:8000/api/predict/single` → 返回 fraud_prob + risk_level + shap_top10
3. 浏览器访问 `/predict/single` → 表单填写 → 提交 → 结果区展示 RiskGauge + SHAP
4. 浏览器访问 `/` → 仪表盘显示真实统计（seed 数据填充后）
5. Model 推理正确性验证: 用训练集中已知样本的 35 特征输入 API，对比预测结果是否与建模阶段一致
