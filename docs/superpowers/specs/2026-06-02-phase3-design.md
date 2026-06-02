# Phase 3 设计规格 — 批量预测 + 案件管理 + Agent 集成 + 数据回填

> 基于 `docs/design/fullstack-design.md` Phase 3 章节，经 brainstorming 确认后的最终规格。

## 实现顺序

串行：3.1 数据回填 → 3.2 批量预测 → 3.3 案件管理 → 3.4 Agent 集成

依赖链：3.1 提供案件数据 → 3.3 以案件为单位管理 → 3.4 以案件为单位做 AI 分析。3.2 与 3.3/3.4 无依赖，但按串行顺序执行。

---

## 3.1 数据回填

**文件**: `backend/scripts/backfill_data.py`

### 输入

- `data/train_eval_test/train.csv`、`eval.csv`、`test.csv`（合并 76,911 行）
- 仅使用前 1,000 行做开发验证，全量回填留到全部开发完成后执行

### 映射规则

CSV 每行 → 1 insuree + 1 policy + 1 claim + 1 fraud_detect_result（1:1:1:1）

> **已知局限**: 简化后每个 insuree 只有 1 个 policy 和 1 个 claim，成员聚合特征（MBR_CLAIM_COUNT 恒为 1，MBR_AVG_SUB_AMT = SUB_AMT）缺乏多样性，可能影响演示数据的真实感。全量回填时可考虑按设计文档原文实现多保单分组。

| 实体 | ID 生成 | 关键字段 |
|------|--------|---------|
| `insuree_info` | `uuid.uuid4().hex` | age, gender（从 CSV 特征提取） |
| `policy_info` | `uuid.uuid4().hex` | FK→insuree，`is_synthetic=False`（默认值） |
| `accident_claim_info` | auto | FK→policy，`is_fraud`=CSV FRAUD 列，`is_synthetic=False`（默认值） |
| `fraud_detect_result` | auto | FK→policy + claim + model，完整特征值和预测结果 |

### 模型推理

CSV 中数据**已经是标准化后的 35 特征**（z-score 值），无需走 7 步特征变换管线：

```
读取 35 列 → 7 类别特征 astype('category') → model['base_model'].predict_proba()
→ model['calibrator'].predict(raw_prob) → 阈值判定 risk_level
```

### 数据生成规则

| 项目 | 规则 |
|------|------|
| 时间戳 | 过去 180 天均匀随机分布 |
| 审核记录 | 随机 20% 案件预生成 case_history（pass 60% / reject 20% / investigate 20%） |
| model_info | 硬编码插入一条记录（AUC 0.9934, threshold 0.36, 35 特征） |
| is_synthetic | policy_info 和 accident_claim_info 使用默认值 False（回填数据应作为"真实"演示数据参与 dashboard 统计和成员聚合计算）；fraud_detect_result 无此字段不受影响 |

### 执行方式

```bash
docker compose exec backend uv run python backend/scripts/backfill_data.py
```

---

## 3.2 批量预测

### 后端

**新增文件**:
- `backend/app/services/batch_service.py` — 业务逻辑层
- `backend/app/routers/batch.py` — 路由（挂载到 predict router 前缀 `/api/predict` 下）
- `backend/app/schemas/batch.py` — 请求/响应模型
- 完善 `backend/app/tasks/batch_tasks.py` — Celery 异步任务

**API 端点**:

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/predict/batch` | 上传 CSV/Excel，返回 task_id |
| `GET` | `/api/predict/batch` | 当前用户历史批量任务列表（`?page&size`，按状态筛选） |
| `GET` | `/api/predict/batch/{task_id}/status` | 查询进度（total/processed/success/failed） |
| `GET` | `/api/predict/batch/{task_id}/download` | 下载结果 CSV |

**进度响应格式**: `{ "task_id": "...", "status": "processing", "total": 1000, "processed": 450, "success": 440, "failed": 10 }`

**输入格式**: 原始业务数据（与单条预测表单字段一致），不是预处理后的 35 特征。

**处理流程**:
```
上传文件 → 解析（CSV/Excel）→ Celery 异步任务
  → 逐行: feature_transform 7 步管线 → predict_proba → 校准 → 阈值判定
  → 写入 fraud_detect_result + policy + claim + insuree
  → 生成结果文件（原始列 + fraud_prob + risk_level + shap_top10）
  → 任务完成，通知可下载
```

**Celery 任务**:
- Broker: Redis
- 超时: soft 600s, hard 900s（单文件最多 10,000 条）
- 进度更新存 Redis，status 端点查询
- 结果文件存本地临时目录

### 前端

**新增文件**:
- `frontend/src/pages/BatchPredictPage.tsx`
- `frontend/src/components/batch/BatchUpload.tsx`
- `frontend/src/components/batch/BatchProgress.tsx`
- `frontend/src/api/batch.ts`

**页面流程**:
1. 拖拽/点击上传 CSV 或 Excel 文件
2. 上传成功 → 显示进度条（轮询 3s）
3. 完成后显示"下载结果"按钮 + 统计摘要（成功/失败数量）
4. 底部历史任务列表（可筛选状态：等待中/进行中/已完成/失败）

---

## 3.3 案件管理

### 后端

**新增文件**:
- `backend/app/services/case_service.py`
- `backend/app/routers/cases.py`
- `backend/app/schemas/case.py`

**API 端点**:

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/cases` | 分页列表（`?page&size&risk_level&manual_result&date_from&date_to&keyword`） |
| `GET` | `/api/cases/{id}` | 案件详情（关联 policy + insuree + claim + result + case_history 列表） |
| `PUT` | `/api/cases/{id}/adjudicate` | 人工判定（`{ "manual_result": "pass"\|"reject"\|"investigate", "remark": "..." }`），写入 case_history |
| `GET` | `/api/cases/stats/summary` | 聚合统计（各风险等级数量、各判定结果数量） |

**列表排序**: 按 detect_time 倒序，高风险优先。

**数据来源**: `fraud_detect_result` 表（回填数据中 is_synthetic 标记在 policy/claim 上，result 本身不设此标记，可直接作为案件管理数据源）。

### 前端

**新增文件**:
- `frontend/src/pages/CaseListPage.tsx`
- `frontend/src/pages/CaseDetailPage.tsx`
- `frontend/src/components/cases/CaseTable.tsx`
- `frontend/src/components/cases/CaseDetail.tsx`
- `frontend/src/components/cases/AdjudicateModal.tsx`
- `frontend/src/api/cases.ts`

**列表页**:
- Ant Design Table + 分页
- 筛选栏：风险等级下拉、判定状态下拉、日期范围选择器、关键词搜索
- 列：案件 ID、保单号、理赔金额、欺诈概率、风险等级、检测时间、审核状态
- 点击行进入详情页

**详情页**:
- 保单信息卡片 + 被保险人信息卡片 + 事故理赔卡片
- AI 预测结果卡片（fraud_prob、risk_level、阈值）
- SHAP 解释展示（从 shap_values JSONB 读取）
- 审核历史时间线（case_history 列表）
- "AI 分析"按钮（→ 3.4 Agent）
- "人工判定"按钮 → AdjudicateModal

**AdjudicateModal**:
- Radio: pass / reject / investigate
- TextArea: 备注
- 提交 → PUT /api/cases/{id}/adjudicate → 刷新详情

---

## 3.4 Agent 集成

### 后端

**新增文件**:
- `backend/app/agent/__init__.py`
- `backend/app/agent/interface.py` — `BaseAgent` 抽象类
- `backend/app/agent/deepseek_agent.py` — DeepSeek V4 Flash 实现
- `backend/app/agent/prompts/fraud_analysis.py` — Prompt 模板
- `backend/app/services/agent_service.py`
- `backend/app/routers/agent.py`
- `backend/app/schemas/agent.py`

**API 端点**:

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/agent/health` | Agent 服务健康检查（`{ "available": true/false }`），前端据此决定是否显示"AI 分析"按钮 |
| `POST` | `/api/agent/analyze` | 对指定 case（fraud_detect_result.id）生成 AI 报告 |

**请求/响应**:
- Request: `{ "case_id": 123 }`
- Response（正常）: `{ "report": "# AI 分析报告\n...", "model_used": "deepseek-v4-flash", "cached": false }`
- Response（缓存命中）: `{ "report": "...", "cached": true }`
- Response（降级）: `{ "report": null, "error": "Agent service unavailable", "fallback": true }`

**架构**:
```
BaseAgent (ABC)
  ├── generate_report(case: CaseContext) → AgentReport
  └── health_check() → bool

DeepSeekAgent(BaseAgent)
  ├── 调用 DeepSeek V4 Flash Chat Completions API
  ├── base_url: https://api.deepseek.com
  └── model: deepseek-chat
```

**缓存策略**:
- 缓存 key: case_id（fraud_detect_result.id）
- 存储: `fraud_detect_result.agent_report` JSONB 字段（已建）
- 结构: `{ "report_text": "...", "model_used": "...", "tokens_used": 0, "generated_at": "..." }`
- 逻辑: 查询 → 非 NULL 则直接返回；NULL 则调 API → 写入缓存 → 返回
- 刷新: `POST /api/agent/analyze` 支持 `force_refresh=true` 参数（admin only）

**配置**:
- `DEEPSEEK_API_KEY` — 环境变量，不硬编码
- `DEEPSEEK_BASE_URL` — 默认 `https://api.deepseek.com`，可配置
- 超时: 30s
- 重试: 不重试（不可用时直接 fallback）

**Prompt**:
- System: "你是一位资深的医疗保险欺诈调查员..."
- User: 案件关键信息（fraud_prob, risk_level, Top 10 SHAP 特征及影响方向, claim_amount, ICD10_CHAPTER 等）
- Output: 300-500 字 Markdown（Summary / Risk Factors / Recommendation / Key Evidence）

### 前端

**新增文件**:
- `frontend/src/api/agent.ts` — Agent API 调用模块

**修改文件**:
- `frontend/src/pages/CaseDetailPage.tsx` — 添加"AI 分析"区域

**交互**:
- 案件详情页显示"AI 分析"区域
- 首次点击"生成分析报告" → loading → 展示 Markdown 报告
- 缓存命中 → 直接展示，显示"已缓存"标记 + 生成时间
- API 不可用 → "AI 分析暂时不可用，请稍后重试"
- admin 可见"重新生成"按钮

---

## 3.5 全量回填

> **延期执行**: 全部开发（含 Phase 4）完成后，确认数据表结构稳定，再修改 `backfill_data.py` 运行全量 76,911 条。当前阶段仅回填 1,000 条用于开发验证。

---

## 新增文件清单

### 后端（15 文件）

| 文件 | 所属任务 |
|------|---------|
| `backend/scripts/backfill_data.py` | 3.1 |
| `backend/app/services/batch_service.py` | 3.2 |
| `backend/app/routers/batch.py` | 3.2 |
| `backend/app/tasks/batch_tasks.py` | 3.2（已有骨架，完善） |
| `backend/app/schemas/batch.py` | 3.2 |
| `backend/app/services/case_service.py` | 3.3 |
| `backend/app/routers/cases.py` | 3.3 |
| `backend/app/schemas/case.py` | 3.3 |
| `backend/app/agent/__init__.py` | 3.4 |
| `backend/app/agent/interface.py` | 3.4 |
| `backend/app/agent/deepseek_agent.py` | 3.4 |
| `backend/app/agent/prompts/fraud_analysis.py` | 3.4 |
| `backend/app/services/agent_service.py` | 3.4 |
| `backend/app/routers/agent.py` | 3.4 |
| `backend/app/schemas/agent.py` | 3.4 |

### 前端（11 文件）

| 文件 | 所属任务 |
|------|---------|
| `frontend/src/pages/BatchPredictPage.tsx` | 3.2 |
| `frontend/src/components/batch/BatchUpload.tsx` | 3.2 |
| `frontend/src/components/batch/BatchProgress.tsx` | 3.2 |
| `frontend/src/api/batch.ts` | 3.2 |
| `frontend/src/pages/CaseListPage.tsx` | 3.3 |
| `frontend/src/pages/CaseDetailPage.tsx` | 3.3 |
| `frontend/src/components/cases/CaseTable.tsx` | 3.3 |
| `frontend/src/components/cases/CaseDetail.tsx` | 3.3 |
| `frontend/src/components/cases/AdjudicateModal.tsx` | 3.3 |
| `frontend/src/api/cases.ts` | 3.3 |
| `frontend/src/api/agent.ts` | 3.4 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `backend/app/main.py` | 注册 batch/cases/agent router |
| `backend/app/config.py` | 添加 DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL |
| `docker-compose.yml` | celery-worker 添加 DEEPSEEK_API_KEY 环境变量 |
| `frontend/src/App.tsx` | 添加 batch/cases/detail 路由 |
| `frontend/src/types/index.ts` | 添加 batch/case/agent 类型 |

---

## 决策汇总

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | 实现顺序 | 串行 A: 3.1 → 3.2 → 3.3 → 3.4 |
| 2 | 回填数据量 | 先 1,000 条，全量延期到 Phase 4 后 |
| 3 | 回填 ID 生成 | UUID (uuid4) |
| 4 | 回填模拟聚类 | 不做，CSV 行 1:1:1:1 简单映射 |
| 5 | 特征变换 | 回填跳过（CSV 已标准化）; 批量预测走完整 7 步 |
| 6 | model_info | 硬编码指标写入 |
| 7 | 批量输入格式 | CSV + Excel 都支持，原始业务数据 |
| 8 | Agent 缓存刷新 | admin 可手动触发重新生成 |
| 9 | Agent API key | 环境变量 DEEPSEEK_API_KEY，不硬编码 |
