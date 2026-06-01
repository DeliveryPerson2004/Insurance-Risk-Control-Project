# 医保理赔风控系统 — 全栈 Web 应用设计文档

## Context

医疗保险理赔欺诈检测系统，ML 建模阶段已完成（XGBoost + IsotonicRegression，35 特征，AUC 0.9934）。需要构建一个生产级 Web 应用，包装模型为可用的企业级系统。

**硬约束**：Docker Compose 一键部署，开发台式机 + 演示笔记本均可运行；前端 Chrome/Firefox/Edge 兼容；单条预测 < 3 秒；批量预测 ≤ 1 万条。

**关键发现**：模型实际有 35 个特征（v4 预处理产出的 `FEATURE_COLS`），而非 CLAUDE.md 或 README 中记录的 27/30 个。7 个类别特征必须转为 pandas `'category'` dtype 才能正确推理。推理分 3 步：原始概率 → IsotonicRegression 校准 → 阈值判定（0.36）。

---

## 技术栈终版

| 层级 | 技术 | 
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| 数据库 | PostgreSQL 16 |
| 异步任务 | Celery + Redis 7 |
| 认证 | JWT (python-jose) + bcrypt (passlib) |
| 前端 | React 18 + TypeScript + Vite 5 |
| UI | Ant Design 5 (浅色主题) + @ant-design/icons |
| 图表 | @ant-design/charts (底层 AntV/G2Plot) |
| 状态管理 | Zustand (auth) + TanStack Query (server data) |
| Agent | DeepSeek V4 Flash API |
| 容器 | Docker Compose (5 个容器服务 + Vite dev server) |

---

## 项目目录结构

```
rgzn-class/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory + lifespan
│   │   ├── config.py                # pydantic-settings, 环境变量驱动
│   │   ├── database.py              # AsyncEngine + session factory
│   │   ├── deps.py                  # get_db, get_current_user, require_admin
│   │   ├── models/                  # 7 个 SQLAlchemy ORM 模型
│   │   │   ├── policy.py, insuree.py, accident_claim.py
│   │   │   ├── fraud_detect_result.py, model_info.py
│   │   │   ├── user.py, case_history.py
│   │   ├── schemas/                 # Pydantic v2 请求/响应模型
│   │   │   ├── auth.py, predict.py, batch.py
│   │   │   ├── case.py, dashboard.py, admin.py, agent.py
│   │   ├── routers/                 # 6 个路由模块（薄层，调 service）
│   │   │   ├── auth.py, predict.py, cases.py
│   │   │   ├── dashboard.py, admin.py, agent.py
│   │   ├── services/                # 业务逻辑层
│   │   │   ├── model_service.py     # 模型加载 + 3 步推理 + SHAP
│   │   │   ├── feature_transform.py # 原始数据 → 35 特征
│   │   │   ├── auth_service.py, predict_service.py
│   │   │   ├── batch_service.py, case_service.py
│   │   │   ├── dashboard_service.py, agent_service.py
│   │   │   └── preprocess_params.json # 训练时的 winsor/log 参数
│   │   ├── tasks/                   # Celery 异步任务
│   │   │   ├── celery_app.py, batch_tasks.py
│   │   ├── agent/                   # Agent 模块（扩展点）
│   │   │   ├── interface.py         # BaseAgent 抽象类
│   │   │   ├── deepseek_agent.py    # DeepSeek V4 Flash 实现
│   │   │   └── prompts/fraud_analysis.py  # Prompt 模板
│   │   └── utils/
│   │       ├── security.py          # JWT + bcrypt
│   │       ├── file_parser.py       # CSV/Excel 解析
│   │       └── exceptions.py        # 全局异常处理
│   ├── scripts/backfill_data.py     # 数据回填脚本
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/                     # Axios + 6 个 API 模块
│   │   ├── components/
│   │   │   ├── layout/              # AppLayout, SideMenu, UserAvatar
│   │   │   ├── predict/             # PredictionForm, RiskGauge, ShapExplanation
│   │   │   ├── batch/               # BatchUpload, BatchProgress
│   │   │   ├── cases/               # CaseTable, CaseDetail, AdjudicateModal
│   │   │   ├── dashboard/           # StatsCards, RiskTrendChart, HighRiskTable
│   │   │   ├── admin/               # ModelMonitor, DataUpload, UserManagement
│   │   │   └── common/              # LoadingSpinner, StatusTag, EmptyState
│   │   ├── pages/                   # 8 个页面组件
│   │   ├── hooks/                   # useAuth, usePagination
│   │   ├── store/authStore.ts       # Zustand
│   │   ├── types/index.ts           # TypeScript 类型定义
│   │   └── utils/                   # constants, format
│   ├── Dockerfile
│   └── vite.config.ts
│
├── docker/
│   ├── nginx/default.conf
│   └── postgres/init.sql
├── docker-compose.yml
└── pyproject.toml                   # 新增 FastAPI/Celery/SQLAlchemy 等依赖
```

---

## 数据库设计（7 张表）

核心设计原则：UUID 主键用于内部（user_id, model_id），varchar 业务键用于外部（policy_id, insuree_id）。`fraud_detect_result` 用 JSONB 存储 35 个特征值和 SHAP 值，保证预测可复现。

- **policy_info**: policy_id(PK), insuree_id(FK), insurance_type, insurance_amount, premium, insure_date, effect_date
- **insuree_info**: insuree_id(PK), age, gender, occupation, marital_status, claim_times
- **accident_claim_info**: id(PK), policy_id(FK), accident_date, accident_type, has_witness, claim_amount, claim_date, is_paid, paid_amount, is_fraud
- **fraud_detect_result**: id(PK), policy_id(FK), accident_claim_id(FK, UNIQUE), model_id(FK), fraud_prob, raw_prob, risk_level, threshold_used, feature_values(JSONB), shap_values(JSONB), detect_time, manual_result
- **model_info**: model_id(UUID PK), model_name, model_algorithm, model_version, model_auc, model_f1, model_precision, model_recall, pr_auc, threshold, feature_count, cv_f1_mean, cv_f1_std, param_config(JSONB), train_time, is_active, model_file_path
- **user_info**: user_id(UUID PK), username(UNIQUE), password_hash, display_name, user_role(reviewer/admin), phone, email(UNIQUE), is_active, last_login
- **case_history**: id(PK), policy_id(FK), detect_result_id(FK), user_id(FK), operate_time, manual_result, remark

关键索引：`fraud_detect_result(detect_time)`, `fraud_detect_result(risk_level)`, `case_history(policy_id)`。

**字段语义约定**：

- `accident_claim_info.is_fraud`：**仅用于训练数据回填时的真实标签**。通过回填脚本从 train/eval/test.csv 的 FRAUD 列写入。对系统运行中产生的新案件（单条预测或批量预测），该字段始终为 NULL——因为真实世界没有即时标签，需要人工核实后才能确认。
- `fraud_detect_result.manual_result`：AI 预测后审核员的**初始标注**（pass/reject/investigate），存储在检测结果中，与预测记录绑定。
- `case_history.manual_result`：审核员的**最终判定结论**，记录在案件历史中。每次人工操作都会写入一条 case_history 记录，追溯完整的审核链路。
- 判定结论以 `case_history` 为权威来源，`fraud_detect_result.manual_result` 仅作为最新一次标注的快照，方便列表页展示。

---

## API 端点设计

所有响应统一格式：`{ "code": 0, "data": ..., "message": "ok" }`

### 认证 `/api/auth`
- `POST /register` — 注册（首个用户自动成为 admin）
- `POST /login` — 登录，返回 access_token + refresh_token + user 信息
- `POST /refresh` — 刷新 token
- `GET /me` — 当前用户信息

### 预测 `/api/predict`
- `GET /field-options` — 返回 7 个类别特征的合法取值列表 + 连续特征的范围
- `POST /single` — 单条预测（输入 35 特征 → 返回 fraud_prob + risk_level + SHAP top 10）
- `POST /batch` — 上传 CSV/Excel → 返回 task_id
- `GET /batch` — 当前用户的历史批量任务列表（`?page=1&size=20`，支持按状态筛选）
- `GET /batch/{task_id}/status` — 查询批量任务进度
- `GET /batch/{task_id}/download` — 下载结果 CSV

### 案件管理 `/api/cases`
- `GET /` — 分页列表（支持 risk_level / manual_result / 日期范围 / 关键词筛选）
- `GET /{id}` — 案件详情（关联保单 + 被保险人 + 事故 + 检测结果 + 审核历史）
- `PUT /{id}/adjudicate` — 人工判定（pass/reject/investigate + 备注）
- `GET /stats/summary` — 聚合统计

### 仪表盘 `/api/dashboard`
- `GET /trend?days=30` — 每日检测量 + 欺诈率趋势
- `GET /high-risk?limit=5` — 高风险案件 Top N

### 管理（admin only）`/api/admin`
- `GET /models` — 模型列表 + 指标
- `GET /models/{id}/metrics` — 详细指标
- `GET /models/plots/{type}` — 返回评估图 PNG（roc_curve/pr_curve/confusion_matrix/feature_importance/threshold_tuning）
- `POST /data/upload` — 上传原始 Excel → 触发预处理 Celery 任务
- `GET /data/status/{task_id}` — 查询导入进度
- `GET /users` — 用户列表
- `PUT /users/{id}` — 修改角色/状态
- `DELETE /users/{id}` — 软删除（停用）

### Agent `/api/agent`
- `POST /analyze` — 对指定案件生成 AI 风险分析报告（输入 case_id，返回 Markdown 报告）

---

## 前端路由设计

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录页 | 公开 |
| `/` | 审核员仪表盘 | reviewer, admin |
| `/predict/single` | 单条预测 | reviewer, admin |
| `/predict/batch` | 批量预测 | reviewer, admin |
| `/cases` | 案件列表 | reviewer, admin |
| `/cases/:id` | 案件详情 | reviewer, admin |
| `/admin` | 管理面板（Tab: 模型监控/数据管理/用户管理） | admin only |
| `*` | 404 | 公开 |

---

## Agent 模块设计

**接口抽象**（`app/agent/interface.py`）：
```
BaseAgent (ABC)
  ├── generate_report(case: CaseContext) → AgentReport
  └── health_check() → bool
```

**DeepSeek 实现**：调用 DeepSeek V4 Flash Chat Completions API。System prompt 定义角色为"资深医保欺诈调查员"，User prompt 包含案件关键信息（欺诈概率、风险等级、Top 10 SHAP 特征及影响方向、理赔金额、诊断大类等）。输出 300-500 字 Markdown 结构化报告（Summary / Risk Factors / Recommendation / Key Evidence）。

**缓存策略**：
- 缓存 key：`case_id`（即 `fraud_detect_result.id`）
- 缓存位置：`fraud_detect_result` 表新增 `agent_report` JSONB 字段，存储 `{ "report_text": "...", "model_used": "...", "tokens_used": 0, "generated_at": "..." }`
- 生成前先检查该字段是否为 NULL，不为 NULL 则直接返回缓存
- 缓存永不过期（案件特征和预测结果不可变），如需刷新由管理员手动触发重新生成

**容错与降级**：
- Agent API 不可用时（超时 30s / 返回 5xx / 网络错误），返回 `{ "report": null, "error": "Agent service unavailable", "fallback": true }`
- 前端收到 fallback 标记后展示"AI 分析暂时不可用，请稍后重试"，不阻塞页面其他功能
- Agent 调用失败不写入缓存，允许后续重试
- 在 `DeepSeekAgent.health_check()` 返回 False 时，前端可在案件详情页隐藏"AI 分析"按钮

**Token 消耗估算**（DeepSeek V4 Flash 参考价格）：
- System prompt: ~200 tokens
- User prompt（含 10 个 SHAP 特征）: ~500 tokens
- 输出（300-500 字中文报告）: ~600 tokens
- 单次调用总计: ~1,300 tokens，约 ¥0.002-0.005
- 全量 76,911 案件分析: ~100M tokens，约 ¥150-200（仅在批量预生成时需要）

**扩展点**：
- 实现 `BaseAgent` 即可切换 LLM（GPT-4、Claude 等）
- `CaseContext` dataclass 可扩展字段（历史对比、同类案件统计等）
- 未来可加 `generate_report_stream()` 实现流式输出

---

## 数据回填策略

目标：将 76,911 条训练/验证/测试数据回灌到数据库，构造真实可用的演示数据。

1. 加载 `data/train_eval_test/{train,eval,test}.csv`，合并为 76,911 行
2. 为每行生成唯一 `policy_id` 和 `insuree_id`；按特征分组模拟多保单成员（70% 单次理赔，20% 2 次，10% 3+ 次）
3. 生成合成时间戳（过去 180 天随机分布，欺诈案件在最近几周密度稍高，模拟欺诈团伙场景，使趋势图有看点）
4. 用模型对每行做推理，写入 `fraud_detect_result`
5. 随机抽取 20% 案件生成预存的审核记录（60% 通过，20% 拒绝，20% 待调查）
6. 插入当前模型元数据到 `model_info`

脚本位置：`backend/scripts/backfill_data.py`，通过 `docker compose exec backend uv run python backend/scripts/backfill_data.py` 执行。

---

## Docker Compose 拓扑

```
nginx (80) ──→ frontend (静态文件)
            ──→ backend:8000 (/api/* 反向代理)

backend:8000 ──→ postgres:5432
             ──→ redis:6379 (Celery broker + result backend)

celery-worker ──→ postgres:5432
               ──→ redis:6379
               ──→ xgb_fraud_model.pkl (只读挂载)
```

5 个容器服务：nginx + backend + celery-worker + postgres + redis。开发时前端使用 Vite dev server（`localhost:5173`），生产部署时前端 `npm run build` 产出静态文件由 nginx 直接 serve，无需独立前端容器。

`modeling/xgb_fraud_model.pkl` 只读挂载到 backend 和 celery-worker 容器。挂载路径统一为 `/app/modeling/xgb_fraud_model.pkl`，通过环境变量 `MODEL_PATH` 配置。

---

## 关键设计决策

1. **单条预测表单直接收集 35 特征**（而非原始业务数据）：避免在关键路径上重跑完整预处理流水线（尤其成员级聚合特征单条无法计算）。表单为类别特征提供 Select 下拉（选项从 `GET /field-options` 获取），连续特征提供 InputNumber。5 个缺失标记由后端自动计算。

2. **预处理流水线仅用于批量数据导入**：管理员通过 `/api/admin/data/upload` 上传原始 Excel 时，Celery 任务运行完整 `preprocessing.py` 逻辑，填充业务表。

3. **JSONB 存储特征和 SHAP 值**：保证每次预测可复现审计，SHAP 无需重复计算。

4. **RBAC 在路由层通过 FastAPI Dependency 强制**：`get_current_user` 解析 JWT，`require_admin` 检查角色。Service 层角色无关。

5. **单条预测中 3 个成员聚合特征的计算策略**：`MBR_CLAIM_COUNT`、`MBR_AVG_SUB_AMT`、`MBR_UNIQUE_HOSPITALS` 属于跨记录聚合特征，无法从单条表单输入直接获取。处理方案：
   - 前端表单**不展示**这 3 个字段（用户不可见，避免困惑）
   - 后端 `feature_transform.py` 在收到预测请求后，查询 `insuree_info` + `accident_claim_info` + `fraud_detect_result` 表，动态计算该 insuree 的历史统计
   - 若该 insuree 无历史记录（新用户），`MBR_CLAIM_COUNT=0`，`MBR_AVG_SUB_AMT=0`，`MBR_UNIQUE_HOSPITALS=0`（与训练数据中缺失值的填充策略一致）
   - 批量预测时，按批次内 insuree 分组后统一计算，逻辑与回填脚本一致

6. **CORS 配置**：
   - 开发模式：后端允许 `localhost:5173`（Vite dev server）跨域请求
   - 生产模式：同源部署（nginx serve 前端 + 反向代理 `/api`），无需 CORS
   - 通过环境变量 `CORS_ORIGINS` 控制，开发时设为 `["http://localhost:5173"]`，生产时为空

7. **日志策略**：
   - 后端：Python `logging` 模块，JSON 格式输出到 stdout（Docker 自动收集）
   - 每条请求自动注入 `request_id`（UUID），贯穿日志和错误响应
   - 关键节点打点：推理耗时、SHAP 计算耗时、Agent API 调用耗时
   - 前端：Console 级别日志，生产构建时关闭

8. **测试策略**：
   - 后端：`pytest` + `httpx`，至少覆盖认证流程、单条预测输入校验和输出格式、模型推理正确性（对比已知样本的预测结果）
   - 前端：暂不做自动化测试（v1 范围外），依赖 TypeScript 类型检查 + 手动验收
   - 数据库迁移：Alembic 的 `--autogenerate` + 手动审查生成的迁移脚本

---

## 开发阶段

### Phase 1: 基础设施（后端骨架 + 数据库 + 认证 + 前端骨架 + Docker）

**1.1 项目初始化**
- 更新 `pyproject.toml` 添加 Web 依赖，`uv lock`
- 创建 FastAPI 项目骨架（`app/main.py`, `config.py`, `database.py`）
- 初始化 React + Vite + TypeScript + Ant Design 项目

**1.2 数据库**
- 编写 7 个 SQLAlchemy 模型
- 配置 Alembic，生成初始迁移
- Docker Compose 启动 PostgreSQL + Redis

**1.3 认证系统**
- `utils/security.py`：JWT 编解码 + bcrypt 密码哈希
- `routers/auth.py` + `services/auth_service.py`：注册、登录、刷新、获取当前用户
- `deps.py`：`get_current_user`、`require_admin` 依赖注入

**1.4 前端基础**
- 登录页（Ant Design Form + 调用 `/api/auth/login`）
- AppLayout（Sider + Header + Content）+ 路由框架
- Zustand auth store + Axios interceptor（JWT 附加 + 自动刷新）

**1.5 Docker 验证**
- 编写 backend Dockerfile + nginx 配置
- `docker compose up` → 后端健康检查通过 → 登录流程可用

### Phase 2: 核心功能（模型推理 + 单条预测 + 仪表盘）

**2.1 模型服务**
- `model_service.py`：加载 .pkl，实现 3 步推理 + SHAP 解释
- `feature_transform.py`：成员聚合特征动态计算 + 缺失标记自动生成
- `preprocess_params.json`：Winsor/log 参数提取脚本

**2.2 单条预测 API**
- `GET /api/predict/field-options`：从训练数据提取合法类别值和特征范围
- `POST /api/predict/single`：35 特征 → 概率 + 风险等级 + SHAP Top 10
- `PredictService` 编排：校验 → 变换 → 推理 → 持久化 → 返回

**2.3 单条预测前端**
- PredictionForm（35 字段分 6 组，Select/InputNumber，3 个成员聚合特征隐藏）
- RiskGauge + ShapExplanation 组件
- 完整流程：填写 → 提交 → 结果展示 → 人工标注

**2.4 仪表盘**
- `DashboardService`：聚合查询（今日待审、欺诈率、风险分布、30 天趋势、Top 5 高风险）
- 前端 DashboardPage：StatsCards + RiskTrendChart + HighRiskTable

### Phase 3: 高级功能（批量预测 + 案件管理 + Agent + 数据回填）

**3.1 批量预测**
- Celery 配置 + `batch_tasks.py`：异步读取文件 → 逐行预测 → 生成结果 CSV
- `POST /api/predict/batch` + 状态查询 + 下载端点 + 历史任务列表
- 前端 BatchPredictPage：拖拽上传 + 进度轮询 + 下载按钮

**3.2 案件管理**
- `CaseService`：列表分页/筛选/搜索 + 详情关联查询 + 人工判定
- 前端 CaseListPage + CaseDetailPage + AdjudicateModal

**3.3 Agent 集成**
- `BaseAgent` 抽象 + `DeepSeekAgent` 实现 + Prompt 模板
- `POST /api/agent/analyze`：生成 → 缓存 → 返回 Markdown 报告
- 前端：案件详情页"AI 分析"按钮，展示报告，处理不可用降级

**3.4 数据回填**
- `backend/scripts/backfill_data.py`：76,911 条数据入 PostgreSQL
- 合成身份 + 时间线 + 预存审核记录 + 模型元数据

**3.5 全栈集成**
- `docker-compose.yml` 完整拓扑（+ celery-worker 服务）
- 端到端验证：`docker compose up` → 所有功能可用

### Phase 4: 管理面板 + 打磨

**4.1 模型监控**
- `GET /api/admin/models` + 指标端点 + 评估图 PNG 端点
- 前端 ModelMonitor：指标卡片 + 图表展示

**4.2 数据管理**
- `POST /api/admin/data/upload`：Celery 任务运行 preprocessing.py 管线
- 前端 DataUpload：上传 + 处理状态追踪

**4.3 用户管理**
- `GET/PUT/DELETE /api/admin/users`：列表、修改角色、停用
- 前端 UserManagement：用户表格 + 角色编辑

**4.4 打磨**
- 全局异常处理 + 友好错误提示
- 加载态（Skeleton）+ 空态（EmptyState）+ 错误边界
- 路由守卫（admin only 重定向）
- 浏览器兼容验证（Chrome/Firefox/Edge）
- Ant Design ConfigProvider 浅色主题定制

---

## 验证方式

1. `docker compose up` → 所有服务健康启动，Alembic 自动建表
2. `docker compose exec backend uv run python backend/scripts/backfill_data.py` → 76,911 条数据入库
3. 浏览器访问 `localhost` → 登录页 → 注册 → 登录 → 仪表盘显示统计卡片和趋势图
4. 单条预测：填写表单 → 提交 → < 3 秒返回概率 + 风险等级 + SHAP 疑点
5. 批量预测：上传测试 CSV → 显示进度 → 完成 → 下载结果
6. 案件详情：点击高风险案件 → 查看完整信息 + 审核历史 → 点击"AI 分析" → Agent 生成报告
7. 管理员面板：模型指标展示 + 用户管理 + 数据上传
8. 笔记本上 `git clone` → `docker compose up` → 同样的体验
