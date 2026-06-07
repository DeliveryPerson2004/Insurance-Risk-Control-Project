# 完整启动方案

> 从零开始启动医保风控系统的完整步骤。最后更新：2026-06-03（Phase 4 完成）。

---

## 前置要求

| 工具 | 最低版本 | 用途 |
|------|----------|------|
| Docker + Docker Compose | Docker 24+, Compose v2 | 运行 PostgreSQL、Redis、Nginx |
| Python | 3.12+ | 后端开发 |
| uv | 0.4+ | Python 依赖管理 |
| Node.js | 18+ | 前端开发 |

---

## 首次启动

### 1. 安装依赖

```bash
# 克隆项目
git clone <repo-url> rgzn-class
cd rgzn-class

# Python 依赖（ml = 特征工程/建模依赖，web = 后端依赖）
uv sync --group ml --group web

# 前端依赖
cd frontend && npm install && cd ..
```

### 2. 确认必需文件

以下文件需确认存在（已在仓库中或需手动放入）：

```bash
# 原始数据文件（data/raw/，teacher 提供的 108 列 Excel）
ls data/raw/data-14-01.xlsx   # 18.7MB，2014 年数据
ls data/raw/data-18-01.xlsx   # 18.2MB，2018 年数据
ls data/raw/test.xlsx          # 1.0MB，演示测试用
ls data/raw/保险理赔数据-字段说明-学生.xlsx

# 模型文件
ls modeling/xgb_fraud_model.pkl  # 2.6MB，XGBoost + IsotonicRegression

# 预处理参数文件
ls backend/app/services/preprocess_params.json  # winsor/log/scaler 参数
```

> 如果只需要后端和前端的开发调试（不需要模型推理），可以跳过模型文件。调用预测 API 时会返回 503。

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

关键环境变量（`backend/.env`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/rgzn_class` | PostgreSQL 连接串 |
| `JWT_SECRET` | （需修改） | JWT 签名密钥，生产环境务必修改 |
| `MODEL_PATH` | `modeling/xgb_fraud_model.pkl` | 模型文件路径 |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + 结果后端 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 允许的跨域来源 |
| `BATCH_RESULT_DIR` | `/tmp/batch_results` | 批量结果存储（Windows 开发建议设为 Windows 路径如 `D:/tmp/batch_results`） |
| `DEEPSEEK_API_KEY` | （可选） | AI 分析 Agent 的 API 密钥 |

---

## 日常开发启动（推荐方式 — 4 个终端）

### 终端 1: Docker 基础服务

```bash
# 启动 PostgreSQL + Redis
docker compose up -d postgres redis

# 确认两个容器运行正常
docker compose ps
# 应看到:
#   rgzn-class-postgres-1   Up (healthy)   0.0.0.0:5432->5432/tcp
#   rgzn-class-redis-1      Up (healthy)   0.0.0.0:6379->6379/tcp
```

### 终端 2: FastAPI 后端

```bash
uv run uvicorn backend.app.main:app --reload --port 8000
```

验证：
```bash
curl http://localhost:8000/api/health
# → {"code":0,"data":{"status":"ok"},"message":"ok"}
```

### 终端 3: Celery Worker

```bash
uv run celery -A backend.app.tasks.celery_app worker \
  --loglevel=info \
  --pool=solo \
  --without-mingle \
  --without-gossip \
  --without-heartbeat
```

参数说明：
- `--pool=solo`：单进程 worker（Windows 兼容，prefork 在 Windows 上不可用）
- `--without-mingle --without-gossip --without-heartbeat`：跳过集群同步（单 worker 场景不需要，避免 2-3 分钟启动延迟）

验证（应看到两个已注册任务）：
```
[tasks]
  . backend.app.tasks.batch_tasks.process_batch
  . backend.app.tasks.data_tasks.process_data_import
```

### 终端 4: 前端 Vite

```bash
cd frontend && npm run dev
```

访问 `http://localhost:5173`（Vite 代理 `/api` → `localhost:8000`）

---

## 首次使用流程

### 1. 注册管理员

访问 `http://localhost:5173/login`，点击"注册"，填写：

```
用户名:   admin
密码:     admin123
显示名:   管理员
```

> 系统规则：**首个注册用户自动成为 admin**，后续注册用户均为 reviewer。

或通过 API：

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","display_name":"管理员"}'
```

### 2. 填充演示数据（可选）

```bash
# 填入 100 条演示预测记录（供仪表盘展示）
uv run python backend/scripts/seed_demo.py
```

### 3. 创建 model_info 记录（预测量需要）

种子数据脚本会自动插入一条 `model_info` 记录（AUC 0.9934, threshold 0.36, 35 特征）。如果没有该记录，预测会返回 503 "No active model"。

### 4. 体验各功能

| 页面 | 路由 | 做什么 |
|------|------|--------|
| 仪表盘 | `/` | 查看统计卡片、趋势图、高风险列表 |
| 单条预测 | `/predict/single` | 填写表单 → 提交 → 查看欺诈概率和 SHAP 解释 |
| 批量预测 | `/predict/batch` | 上传 CSV/Excel → 实时进度 → 下载结果 |
| 案件管理 | `/cases` | 筛选案件 → 点击进入详情 → AI 分析 → 人工判定 |
| 管理面板 | `/admin` （仅 admin） | 用户管理（角色编辑/停用启用）+ 数据管理（上传原始 Excel → 预处理 → 推理入库） |

### 5. 测试数据导入

管理面板 → 数据管理 → 上传 `data/raw/test.xlsx`（1001 条原始数据）

处理流程：
```
上传 Excel (1001行 × 108列)
  ↓ 后台 Celery 任务
11步预处理（金额清洗→日期衍生→ICD-10映射→BEN_HEAD拆分→...→聚合特征）
  → 30 特征 (raw)
  ↓
7步特征变换（缺失标记→Winsor→log→scaler）→ 35 特征 (scaled)
  ↓
3步推理（XGBoost→Isotonic校准→阈值判定）
  ↓
入库（Insuree + Policy + AccidentClaim + FraudDetectResult）
```

处理完成后进入 `/cases` 可看到 1001 条预测结果。

---

## Docker 全栈启动（一体化部署）

```bash
# 启动全部 5 服务
docker compose up -d --build

# 确认 5 个容器都在运行
docker compose ps
# 应看到: postgres, redis, backend, celery-worker, nginx

# 访问 http://localhost（Nginx → 后端 8000）
```

Alembic 迁移会在 backend 容器 entrypoint 中自动执行。

---

## 创建审核员账号

在登录页点击"注册"，输入任意新用户名密码即可自动成为 reviewer。审核员登录后看不到左侧菜单的"管理面板"。

也可以通过已有 admin 账号在管理面板中修改其他用户角色。

---

## 数据库管理

```bash
# 手动执行迁移
docker compose exec backend uv run alembic upgrade head

# 生成新迁移（修改 ORM 模型后）
docker compose exec backend uv run alembic revision --autogenerate -m "描述"

# 清空所有数据重来
docker compose down -v
docker compose up -d --build
docker compose exec backend uv run python backend/scripts/seed_demo.py

# 进入 PostgreSQL
docker compose exec postgres psql -U postgres -d rgzn_class

# 开发模式下连接本地 PostgreSQL
psql -U postgres -d rgzn_class
```

---

## 常见问题

### "模型未部署" (503)

模型文件不存在。确认 `modeling/xgb_fraud_model.pkl` 存在，或设置 `MODEL_PATH` 环境变量。

### "没有活跃的模型" (503)

`model_info` 表中没有 `is_active=True` 的记录。运行 `seed_demo.py` 会自动创建。

### 批量预测/数据导入任务一直"等待中"

Celery worker 未启动或已崩溃。在终端 3 重新启动 worker。

### 批量预测/数据导入全部失败（0 success / all failed）

检查 worker 日志中的错误信息。常见原因：
- asyncpg 连接池冲突 → 重启 worker（`--pool=solo` 已配置）
- 特征列序不匹配 → 已修复，确保代码是最新版

### 上传文件超时/422 错误

刷新前端页面（Vite HMR 可能未生效），确保 `client.post` 时 `Content-Type` 为 `undefined`。

### 前端 TypeScript 编译报错

```bash
cd frontend
npm install          # 确认依赖完整
npx tsc --noEmit     # 查看具体错误
```

### CORS 错误（前端 localhost:5173 调用后端）

确认 `backend/.env` 中 `CORS_ORIGINS=["http://localhost:5173"]`。

### Windows 下 uv sync 失败

确保安装了 Visual C++ 构建工具（shap 依赖需要编译）。

### Docker 容器启动失败

```bash
docker compose logs backend     # 查看后端日志
docker compose logs postgres    # 查看数据库日志
docker compose down -v          # 清空数据重来
```
