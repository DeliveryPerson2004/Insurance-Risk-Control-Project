# Phase 1 — 基础设施 设计文档

> 基于 `docs/design/fullstack-design.md` 全栈设计文档，落地 Phase 1 基础设施。

## 目标

`docker compose up` → 登录流程（注册/登录/刷新 token）前后端贯通。

## 决策汇总

| 决策点 | 选择 |
|--------|------|
| 依赖管理 | 统一 `pyproject.toml`，uv `[dependency-groups]` 分组（`ml` / `web`） |
| ORM 模型 | 一次性建完 7 张表，Alembic 初始迁移作为基线 |
| 前端初始化 | `npm create vite@latest` + 手动添加 Ant Design / Zustand / TanStack Query / React Router |
| 执行顺序 | 1.1 依赖 → 1.2 后端+DB → 1.3 认证 → 1.4 前端骨架 → 1.5 Docker 全栈验证 |

---

## Step 1: 项目初始化 (1.1)

### pyproject.toml 依赖分组

- **`ml` 组**（保留现有）：pandas, numpy, xgboost, scikit-learn, optuna, shap, matplotlib, seaborn, joblib, openpyxl, imbalanced-learn
- **`web` 组**（新增）：fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, celery[redis], redis, passlib[bcrypt], python-jose[cryptography], pydantic-settings, python-multipart, aiofiles, httpx

### 产出
- 更新后的 `pyproject.toml`
- `uv.lock` 重新生成
- `uv sync` 全部依赖就绪

---

## Step 2: 后端骨架 + 数据库 (1.2)

### 文件清单

```
backend/
├── app/
│   ├── main.py          # FastAPI app factory + lifespan + CORS
│   ├── config.py        # pydantic-settings (DB_URL, JWT_SECRET, MODEL_PATH, CORS_ORIGINS...)
│   ├── database.py      # AsyncEngine + async session factory (SQLAlchemy 2.0)
│   └── models/
│       ├── __init__.py  # Base, 导入全部模型供 Alembic 发现
│       ├── user.py
│       ├── policy.py
│       ├── insuree.py
│       ├── accident_claim.py
│       ├── fraud_detect_result.py
│       ├── model_info.py
│       └── case_history.py
├── alembic/
│   ├── env.py           # 配置异步引擎 + Base.metadata
│   └── versions/        # 初始迁移脚本
├── alembic.ini
├── Dockerfile
└── .env.example         # 开发环境变量模板
```

### 7 个 ORM 模型关键约束

| 表 | 主键 | 外键 | 特殊字段 |
|---|------|------|----------|
| `user_info` | `user_id` (UUID) | — | `username` UNIQUE, `email` UNIQUE |
| `policy_info` | `policy_id` (varchar) | `insuree_id` → `insuree_info` | — |
| `insuree_info` | `insuree_id` (varchar) | — | — |
| `accident_claim_info` | `id` (int, PK) | `policy_id` → `policy_info` | `is_fraud` 仅用于回填训练标签，新案件为 NULL |
| `fraud_detect_result` | `id` (int, PK) | `policy_id`, `accident_claim_id` (UNIQUE), `model_id` | `feature_values` JSONB, `shap_values` JSONB, `agent_report` JSONB |
| `model_info` | `model_id` (UUID) | — | `param_config` JSONB |
| `case_history` | `id` (int, PK) | `policy_id`, `detect_result_id`, `user_id` | — |

所有表带 `created_at` (UTC) 和 `updated_at` (UTC) 时间戳。

### 关键设计决策
- **`fraud_detect_result` 外键**：`accident_claim_id` UNIQUE 确保每条事故记录最多一条检测结果，避免重复预测覆盖
- **`accident_claim_info.is_fraud`**：仅回填脚本写入真实标签，运行时新案件始终为 NULL
- **Alembic 自动迁移**：backend 容器启动时执行 `alembic upgrade head`

### Docker Compose 初版（3 个服务）

```yaml
services:
  postgres:   # postgres:16-alpine
  redis:      # redis:7-alpine
  backend:    # python:3.12-slim, uvicorn --reload
```

backend 通过环境变量获取 `DATABASE_URL=postgresql+asyncpg://...` 和 `REDIS_URL=redis://...`。

### backend Dockerfile（初版）

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --group web --group ml
COPY backend/ ./backend/
COPY modeling/ ./modeling/
CMD ["uv", "run", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 产出
- `docker compose up` → Backend 健康检查 `GET /api/health` 通过
- Alembic 自动建表，7 张表全部存在
- `docker compose down` 后数据不丢失（volume 挂载）
- `backend/Dockerfile` 初版就绪（Step 5 仅做完善：复制静态文件、启动脚本调整等）

---

## Step 3: 认证系统 (1.3)

### 文件清单

```
backend/app/
├── utils/
│   ├── __init__.py
│   ├── security.py      # create_access_token, create_refresh_token, verify_password, hash_password
│   └── exceptions.py    # 全局异常 handler（AppException, 统一格式返回）
├── schemas/
│   ├── __init__.py
│   └── auth.py          # RegisterRequest, LoginRequest, TokenResponse, UserResponse
├── services/
│   ├── __init__.py
│   └── auth_service.py  # register, login, refresh_token, get_current_user
├── routers/
│   ├── __init__.py
│   └── auth.py          # POST /register, POST /login, POST /refresh, GET /me
└── deps.py              # get_current_user (Depends), require_admin (Depends)
                          # 注意: Phase 2/3 其他路由模块也会用到这里的依赖，
                          # 后续膨胀时考虑按领域拆分（如 deps/auth.py, deps/pagination.py）
```

### API 端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `POST` | `/api/auth/register` | 注册，首个用户自动 admin | 公开 |
| `POST` | `/api/auth/login` | 登录，返回 access + refresh token | 公开 |
| `POST` | `/api/auth/refresh` | 刷新 access token | refresh token |
| `GET` | `/api/auth/me` | 当前用户信息 | access token |

### 统一响应格式

```json
{ "code": 0, "data": {...}, "message": "ok" }
```

错误时 `code` 非 0，`data` 为 null。

### JWT 设计
- access_token: 30 分钟过期，payload 含 `sub` (user_id), `role`, `type: "access"`
- refresh_token: 7 天过期，payload 含 `sub` (user_id), `type: "refresh"`
- 密码: bcrypt (passlib), 12 rounds
- `get_current_user`: 从 `Authorization: Bearer <token>` 解析 → 查 DB → 返回 User ORM 对象
- `require_admin`: 调用 `get_current_user` → 检查 `role == "admin"` → 否则 403

### 产出
- `curl POST /api/auth/register` → 返回 token
- `curl POST /api/auth/login` → 返回 token
- `curl GET /api/auth/me -H "Authorization: Bearer <token>"` → 返回用户信息
- admin role 守卫生效

---

## Step 4: 前端基础 (1.4)

### 项目初始化

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install antd @ant-design/icons @ant-design/charts
npm install react-router-dom zustand @tanstack/react-query axios
```

### 文件结构

```
frontend/
├── vite.config.ts            # Vite 配置（含 proxy: /api → localhost:8000）
├── src/
│   ├── api/
│   │   ├── client.ts         # Axios 实例 + interceptor (JWT 附加 + 401 refresh)
│   │   └── auth.ts           # login, register, refresh, getMe
│   ├── store/
│   │   └── authStore.ts      # Zustand: user, accessToken, login/logout actions
│   ├── types/
│   │   └── index.ts          # User, LoginRequest, RegisterRequest, ApiResponse<T>
│   ├── components/
│   │   └── layout/
│   │       └── AppLayout.tsx # Ant Design Layout: Sider + Header + Content + 用户菜单
│   ├── pages/
│   │   ├── LoginPage.tsx     # Ant Design Form: username + password → 登录
│   │   └── DashboardPage.tsx # 空壳: 欢迎文字 + 占位统计卡片
│   ├── hooks/
│   │   └── useAuth.ts        # 封装 authStore + TanStack Query
│   ├── utils/
│   │   └── constants.ts      # API_BASE_URL
│   ├── App.tsx               # ConfigProvider (浅色主题) + BrowserRouter + Routes
│   └── main.tsx              # ReactDOM.createRoot
```

### 路由设计

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | LoginPage | 公开 |
| `/` | DashboardPage | 需登录 |
| `*` | 暂 404 占位 | 公开 |

### 关键交互

1. **登录流程**: LoginPage Form submit → `POST /api/auth/login` → 存入 Zustand + localStorage → 跳转 `/`
2. **JWT 管理**: Axios interceptor 自动附加 `Authorization: Bearer <token>`，收到 401 时尝试 `POST /api/auth/refresh`，成功则重试请求，失败则清除 auth 状态跳转 `/login`
3. **路由守卫**: 未登录访问 `/` → 重定向 `/login`；已登录访问 `/login` → 重定向 `/`
4. **AppLayout**: Sider 留空（后续添加菜单），Header 右侧显示用户名 + 退出按钮

### 产出
- `npm run dev` → `localhost:5173` 显示登录页
- 注册 → 登录 → 跳转仪表盘空壳 → 退出 → 回到登录页
- 前后端通过 Vite proxy 联调（`/api` → `localhost:8000`）

---

## Step 5: Docker 全栈验证 (1.5)

### 新增

```
docker/
├── nginx/
│   └── default.conf      # 反向代理 /api → backend:8000，其余 serve 前端静态文件
```

### docker-compose.yml 最终拓扑（5 个服务）

```
nginx:80 ──→ frontend (静态文件)
          ──→ backend:8000 (/api/* 反向代理)

backend:8000 ──→ postgres:5432
             ──→ redis:6379

celery-worker ──→ postgres:5432
               ──→ redis:6379
               ──→ model (只读挂载)
```

- 开发时前端使用 Vite dev server + proxy，不走 nginx
- `docker-compose.yml` 作为生产/完整验证方案
- celery-worker 服务暂不定义任务（Celery app 骨架先建好，留到 Phase 3 填充）

### backend Dockerfile 完善

Step 2 已创建初版 Dockerfile。Step 5 仅做微调：若需要将前端静态文件打包进 nginx 而非 backend，Dockerfile 不变；若后续决定 backend 自 serve 静态文件，则追加 `COPY frontend/dist/ ./frontend/dist/`。

### 验证清单

1. `docker compose up` → 所有服务健康启动，Alembic 自动建表
2. `curl localhost/api/health` → `{"code": 0, "data": {"status": "ok"}}`
3. `curl POST localhost/api/auth/register` → 创建用户
4. `curl POST localhost/api/auth/login` → 返回 token
5. 浏览器 `localhost` → 登录页 → 登录 → 仪表盘

---

## 验收标准

- [ ] `uv sync` 后在 venv 中可运行 `uvicorn backend.app.main:app`
- [ ] `docker compose up` 5 个服务全部 healthy
- [ ] 7 张数据库表在 PostgreSQL 中存在（`\dt` 确认）
- [ ] `POST /api/auth/register` 首个用户成为 admin
- [ ] `POST /api/auth/login` 返回合法 JWT
- [ ] `GET /api/auth/me` 返回用户信息
- [ ] 浏览器访问 → 登录页 → 登录 → 仪表盘
- [ ] 未登录访问 `/` → 重定向到 `/login`（前端路由守卫）
- [ ] admin 路由对 reviewer 返回 403
