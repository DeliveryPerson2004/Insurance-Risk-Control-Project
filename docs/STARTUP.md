# 完整启动方案

> 从零开始启动医保风控系统的完整步骤。最后更新：2026-06-02。

## 前置要求

| 工具 | 最低版本 | 用途 |
|------|----------|------|
| Docker + Docker Compose | Docker 24+, Compose v2 | 运行 PostgreSQL、Redis、Nginx |
| Python | 3.12+ | 后端开发 |
| uv | 0.4+ | Python 依赖管理 |
| Node.js | 18+ | 前端开发 |

## 首次启动

### 1. 克隆 + 安装依赖

```bash
git clone <repo-url> rgzn-class
cd rgzn-class

# Python 依赖（ml = 特征工程/建模依赖，web = 后端依赖）
uv sync --group ml --group web

# 前端依赖
cd frontend && npm install && cd ..
```

### 2. 放入必需文件

原始数据文件在 `.gitignore` 中，需手动准备：

```bash
# 原始数据文件（放入 data/raw/）
cp /path/to/data-14-01.xlsx data/raw/
cp /path/to/data-18-01.xlsx data/raw/
```

> 模型文件（`modeling/xgb_fraud_model.pkl`）已在 Git 仓库中，无需手动准备。

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，确认数据库连接和 JWT 密钥
```

关键环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 连接串 |
| `JWT_SECRET` | （需修改） | JWT 签名密钥，生产环境务必修改 |
| `MODEL_PATH` | `modeling/xgb_fraud_model.pkl` | 模型文件路径 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 允许的跨域来源 |

### 4. 启动 Docker 服务

```bash
# 启动 PostgreSQL + Redis + Nginx + backend + celery-worker
docker compose up -d --build

# 确认 5 个容器都在运行
docker compose ps
```

Alembic 迁移会在 backend 容器 entrypoint 中自动执行。

### 5. 填充演示数据

```bash
# 注册一个管理员用户
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","display_name":"管理员"}'

# 填入 100 条演示预测记录（供仪表盘展示）
docker compose exec backend uv run python backend/scripts/seed_demo.py
```

### 6. 验证

```bash
# 健康检查
curl http://localhost/api/health

# 登录获取 token
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 仪表盘统计
curl http://localhost/api/dashboard/stats \
  -H "Authorization: Bearer <token>"

# 浏览器访问 http://localhost → 登录 → 仪表盘
```

---

## 日常开发启动

### 纯 Docker（全栈）

```bash
docker compose up -d --build
# 访问 http://localhost
```

### 前后端分离开发（推荐）

```bash
# 终端 1: Docker 基础服务
docker compose up -d postgres redis
# 或只用 postgres（若不需要 Celery）
# docker compose up -d postgres

# 终端 2: 后端热重载
uv run uvicorn backend.app.main:app --reload --port 8000

# 终端 3: Celery worker（批量预测 + 数据导入任务处理）
uv run celery -A backend.app.tasks.celery_app worker --loglevel=info --pool=solo --without-mingle --without-gossip --without-heartbeat

# 终端 4: 前端热重载
cd frontend && npm run dev
# 访问 http://localhost:5173（Vite proxy → 后端 8000）
```

### 仅验证后端 API

```bash
uv run uvicorn backend.app.main:app --reload --port 8000

# 另一个终端
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['tokens']['access_token'])")

# 测试各端点
curl http://localhost:8000/api/health
curl http://localhost:8000/api/predict/field-options -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/dashboard/stats -H "Authorization: Bearer $TOKEN"
```

---

## 前端路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录/注册 | 公开 |
| `/` | 仪表盘 | reviewer, admin |
| `/predict/single` | 单条预测 | reviewer, admin |
| `/predict/batch` | 批量预测（占位） | reviewer, admin |
| `/cases` | 案件管理（占位） | reviewer, admin |
| `/admin` | 管理面板（占位） | admin only |

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
```

---

## 常见问题

### "模型未部署" (503)

模型文件不存在。确认 `modeling/xgb_fraud_model.pkl` 存在，或设置 `MODEL_PATH` 环境变量。

### "没有活跃的模型" (503)

`model_info` 表中没有 `is_active=True` 的记录。运行 seed_demo 不会自动创建 model_info 记录——需要通过回填脚本（Phase 3）或手动插入。

### 前端 TypeScript 编译报错

```bash
cd frontend
npm install          # 确认依赖完整
npx tsc --noEmit     # 查看具体错误
```

### Docker 容器启动失败

```bash
docker compose logs backend     # 查看后端日志
docker compose logs postgres    # 查看数据库日志
docker compose down -v          # 清空数据重来
```

### CORS 错误（前端 localhost:5173 调用后端）

确认 `backend/.env` 中 `CORS_ORIGINS=["http://localhost:5173"]`。

### Windows 下 uv sync 失败

确保安装了 Visual C++ 构建工具（shap 依赖编译）。
