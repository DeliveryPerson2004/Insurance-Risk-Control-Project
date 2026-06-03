# 医保风控系统 — 医疗保险理赔欺诈检测

基于 XGBoost + SHAP 的机器学习欺诈检测系统，提供完整的 Web 管理界面，支持单条/批量预测、案件审核工作流、AI 辅助分析和数据管理。

## 项目概览

系统对医疗保险理赔案件进行自动化欺诈风险评估。核心流程：

```
原始理赔数据 (108列) → 特征工程 (35特征) → XGBoost 推理 → IsotonicRegression 校准 → 风险分级 → 人工审核
```

模型训练阶段已完成（ROC-AUC 0.9934，F1 0.8835），Web 应用已完整构建（Phase 1-4 全部完成）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| 数据库 | PostgreSQL 16 |
| 异步任务 | Celery + Redis 7 |
| 认证 | JWT (python-jose) + bcrypt |
| 前端 | React 18 + TypeScript + Vite 5 |
| UI 组件 | Ant Design 5 + @ant-design/icons |
| 图表 | @antv/g2 |
| 状态管理 | Zustand (auth) + TanStack Query (server data) |
| AI Agent | DeepSeek V4 Flash API |
| ML 模型 | XGBoost + SHAP + IsotonicRegression, 35 特征 |
| 容器 | Docker Compose (5 服务) |

## 快速开始

### 前置要求

| 工具 | 最低版本 |
|------|----------|
| Docker + Docker Compose | Docker 24+, Compose v2 |
| Python | 3.12+ |
| uv | 0.4+ |
| Node.js | 18+ |

### 首次启动（5 分钟）

```bash
# 1. 克隆项目
git clone git@github.com:DeliveryPerson2004/Insurance-Risk-Control-Project.git
cd Insurance-Risk-Control-Project

# 2. 安装依赖
uv sync --group ml --group web
cd frontend && npm install && cd ..

# 3. 放入必需文件（.gitignore 中，需手动准备）
#   - 模型文件: modeling/xgb_fraud_model.pkl
#   - 原始数据: data/raw/data-14-01.xlsx, data/raw/data-18-01.xlsx

# 4. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，修改 JWT_SECRET

# 5. 启动全部服务
docker compose up -d --build

# 6. 注册管理员 + 填充演示数据
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","display_name":"管理员"}'

docker compose exec backend uv run python backend/scripts/seed_demo.py

# 7. 浏览器访问 http://localhost → 登录 → 仪表盘
```

### 日常开发（前后端分离）

```bash
# 终端 1: 基础服务
docker compose up -d postgres redis

# 终端 2: 后端（热重载，端口 8000）
uv run uvicorn backend.app.main:app --reload --port 8000

# 终端 3: Celery worker（批量预测 + 数据导入）
uv run celery -A backend.app.tasks.celery_app worker --loglevel=info --pool=solo --without-mingle --without-gossip --without-heartbeat

# 终端 4: 前端（热重载，端口 5173）
cd frontend && npm run dev
```

详细启动说明（含环境变量、常见问题）见 [`docs/STARTUP.md`](docs/STARTUP.md)。

## 功能模块

### 认证系统
- JWT 双 token（access 30min + refresh 7d）
- RBAC 角色控制（admin / reviewer）
- 前端 Axios interceptor 自动刷新 token
- 路由守卫：ProtectedRoute / GuestRoute / AdminRoute

### 仪表盘
- 4 核心指标实时统计（待审核 / 高风险 / 今日已处理 / 累计检测量）
- 30 天检测量 & 欺诈率双轴趋势图
- 高风险案件 Top 5 列表
- 60 秒自动轮询刷新

### 单条预测
- 27 字段动态表单（6 组，2 列网格布局）
- 类别字段 Select 下拉（选项从训练数据提取）
- 返回欺诈概率 + 风险等级 + SHAP Top 10 解释
- 结果区展示 RiskGauge 仪表盘 + 特征贡献列表

### 批量预测
- CSV / Excel 上传，Celery 异步处理
- 实时进度轮询 + 结果下载
- 历史任务列表（支持状态筛选）
- 单文件 ≤ 10,000 条

### 案件管理
- 分页列表，多条件筛选（风险等级 / 判定结果 / 日期范围 / 关键词）
- 案件详情：保单信息 + 被保险人 + 事故理赔 + AI 预测结果 + SHAP 解释
- 人工判定工作流（通过 / 拒绝 / 调查中 + 备注）
- 审核历史时间线

### AI 分析报告
- DeepSeek V4 Flash 生成结构化分析报告
- JSONB 缓存（同一案件只生成一次）
- API 不可用时自动降级
- admin 可手动刷新报告

### 管理面板（admin only）
- **用户管理**：列表搜索 + 角色编辑 + 启用/停用，禁止自编辑
- **数据管理**：上传原始 Excel (108列) → Celery 预处理管线 → 35 特征 → 推理 → 入库
- 路由守卫：前端 AdminRoute + 后端 require_admin 双重校验

## 项目结构

```
Insurance-Risk-Control-Project/
├── backend/                           # FastAPI 后端
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory + CORS + lifespan
│   │   ├── config.py                  # pydantic-settings，环境变量驱动
│   │   ├── database.py                # AsyncEngine + session factory
│   │   ├── deps.py                    # get_current_user, require_admin
│   │   ├── models/                    # 7 个 SQLAlchemy ORM 模型
│   │   ├── schemas/                   # Pydantic v2 请求/响应
│   │   ├── routers/                   # 6 个路由模块（薄层，调 service）
│   │   ├── services/                  # 业务逻辑层（model/feature/predict/batch/case/dashboard/agent/admin）
│   │   ├── tasks/                     # Celery 异步任务（batch_tasks + data_tasks）
│   │   ├── agent/                     # BaseAgent 抽象 + DeepSeek 实现 + Prompt 模板
│   │   └── utils/                     # security, file_parser, exceptions, redis_utils
│   ├── scripts/                       # seed_demo, backfill_data, extract_preprocess_params
│   ├── alembic/                       # 数据库迁移（3 个迁移）
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                          # React 18 + TypeScript 前端
│   └── src/
│       ├── api/                       # Axios + 7 个 API 模块
│       ├── components/
│       │   ├── layout/                # AppLayout（浅色侧边栏 + Header）
│       │   ├── predict/               # PredictionForm, RiskGauge, ShapExplanation
│       │   ├── batch/                 # BatchUpload, BatchProgress
│       │   ├── cases/                 # CaseTable, CaseDetail, AdjudicateModal
│       │   ├── dashboard/             # StatsCards, RiskTrendChart, HighRiskTable
│       │   ├── admin/                 # UserManagement, DataUpload
│       │   └── common/                # ErrorBoundary, Skeleton, EmptyState
│       ├── pages/                     # 8 个页面组件
│       ├── store/authStore.ts         # Zustand 认证状态
│       ├── hooks/                     # useAuth
│       └── types/                     # TypeScript 类型定义
│
├── data/                              # 特征工程（不再修改）
│   ├── raw/                           # 原始 Excel（不入库）
│   ├── preprocessing.py               # 特征工程脚本 v4
│   └── train_eval_test/               # train/eval/test.csv (76,911条)
│
├── modeling/                          # 模型（不再修改）
│   ├── modeling.py                    # XGBoost 建模脚本
│   ├── xgb_fraud_model.pkl            # 训练好的模型（不入库）
│   └── plots/                         # 评估图表 + SHAP
│
├── docker/                            # nginx 反向代理配置
├── docker-compose.yml                 # 5 服务拓扑
├── pyproject.toml                     # uv 依赖管理（ml + web groups）
│
└── docs/                              # 项目文档
    ├── STARTUP.md                     # 完整启动方案
    ├── design/fullstack-design.md     # 全栈设计文档
    ├── reference/architecture.md      # 架构参考
    └── superpowers/                   # Phase 1-4 设计 spec + 实施计划
```

## API 端点总览

所有响应统一格式：`{"code": 0, "data": ..., "message": "ok"}`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `GET` | `/api/health` | 健康检查 | 公开 |
| `POST` | `/api/auth/register` | 注册（首个用户 → admin） | 公开 |
| `POST` | `/api/auth/login` | 登录，返回 access + refresh token | 公开 |
| `POST` | `/api/auth/refresh` | 刷新 access token | refresh_token |
| `GET` | `/api/auth/me` | 当前用户信息 | access_token |
| `GET` | `/api/predict/field-options` | 27 字段配置（类别选项 + 连续范围） | access_token |
| `POST` | `/api/predict/single` | 单条预测，返回概率 + 风险 + SHAP | access_token |
| `POST` | `/api/predict/batch` | 上传 CSV/Excel 批量预测 | access_token |
| `GET` | `/api/predict/batch` | 历史批量任务列表 | access_token |
| `GET` | `/api/predict/batch/{id}/status` | 批量任务进度 | access_token |
| `GET` | `/api/predict/batch/{id}/download` | 下载批量结果 CSV | access_token |
| `GET` | `/api/dashboard/stats` | 4 核心指标 | access_token |
| `GET` | `/api/dashboard/trend?days=30` | 每日检测量 + 欺诈率趋势 | access_token |
| `GET` | `/api/dashboard/high-risk?limit=5` | 高风险案件 Top N | access_token |
| `GET` | `/api/cases` | 案件分页列表（多条件筛选） | access_token |
| `GET` | `/api/cases/stats/summary` | 案件聚合统计 | access_token |
| `GET` | `/api/cases/{id}` | 案件详情（含关联数据） | access_token |
| `PUT` | `/api/cases/{id}/adjudicate` | 人工判定（pass/reject/investigate） | access_token |
| `GET` | `/api/agent/health` | Agent 服务可用性 | access_token |
| `POST` | `/api/agent/analyze` | 生成 AI 分析报告 | access_token |
| `GET` | `/api/admin/users` | 用户分页列表（支持搜索） | admin |
| `PUT` | `/api/admin/users/{id}` | 修改角色 + 停用/启用 | admin |
| `POST` | `/api/admin/data/upload` | 上传原始 Excel (108列) 导入 | admin |
| `GET` | `/api/admin/data/tasks` | 历史导入任务列表 | admin |
| `GET` | `/api/admin/data/tasks/{id}/status` | 导入任务进度 | admin |

## 数据库

7 张表，PostgreSQL 16，Alembic 管理迁移：

| 表 | 说明 | 关键字段 |
|----|------|---------|
| `user_info` | 系统用户 | UUID PK, username UNIQUE, user_role (admin/reviewer) |
| `policy_info` | 保单信息 | varchar PK, FK→insuree_info |
| `insuree_info` | 被保险人信息 | varchar PK, age, gender, occupation |
| `accident_claim_info` | 事故与索赔 | int PK, FK→policy_info, is_fraud (训练标签) |
| `fraud_detect_result` | 欺诈检测结果 | int PK, FK×3, fraud_prob, risk_level, feature_values (JSONB), shap_values (JSONB), agent_report (JSONB) |
| `model_info` | 模型元数据 | UUID PK, AUC, F1, 阈值, 参数配置 (JSONB) |
| `case_history` | 审核历史 | int PK, FK×3, manual_result, remark, operate_time |

## 模型推理

```python
import joblib

m = joblib.load('modeling/xgb_fraud_model.pkl')

# 模型文件包含 5 个字段
raw_prob  = m['base_model'].predict_proba(X)[:, 1]      # XGBoost 原始概率
cal_prob  = m['calibrator'].predict(raw_prob)            # IsotonicRegression 校准
pred      = (cal_prob >= m['threshold']).astype(int)     # 阈值 = 0.36
# m['feature_cols'] — 35 特征列名
# m['cat_cols']      — 7 类别特征列名
```

推理前类别特征必须 `astype('category')`（XGBoost 2.0+ 原生类别支持），否则结果不正确。

## 模型性能 (v4)

| 指标 | 值 |
|------|-----|
| ROC-AUC | 0.9934 |
| PR-AUC | 0.9487 |
| F1 Score | 0.8835 |
| Precision (Fraud) | 0.87 |
| Recall (Fraud) | 0.89 |
| 5-fold CV F1 | 0.9259 ± 0.0037 |
| 最优阈值 | 0.36 |

## 设计文档

| 文档 | 说明 |
|------|------|
| [`docs/design/fullstack-design.md`](docs/design/fullstack-design.md) | 全栈设计文档（数据库、API、架构决策） |
| [`docs/reference/architecture.md`](docs/reference/architecture.md) | 系统架构参考 |
| [`docs/STARTUP.md`](docs/STARTUP.md) | 完整启动方案 + 常见问题 |
| [`data/train_eval_test/README.md`](data/train_eval_test/README.md) | 特征说明 + 版本演进 (v1→v4) |

## 常用命令

```bash
# TypeScript 类型检查
cd frontend && npx tsc --noEmit

# 后端健康检查
curl http://localhost:8000/api/health

# 通过 nginx 访问
curl http://localhost/api/health

# 数据库迁移
docker compose exec backend uv run alembic upgrade head

# 清空数据库重来
docker compose down -v && docker compose up -d --build
```

## 关键约束

- `data/raw/*` 不在 Git 中（`.gitignore`）
- 类别特征推理前必须 `astype('category')`
- 前端不使用 emoji，统一使用 `@ant-design/icons`
- 仪表盘组件 60s 自动轮询

## Team

GitHub: [DeliveryPerson2004/Insurance-Risk-Control-Project](https://github.com/DeliveryPerson2004/Insurance-Risk-Control-Project)
