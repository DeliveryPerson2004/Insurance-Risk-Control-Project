# Phase 1 基础设施 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docker compose up` → 登录流程（注册/登录/刷新 token）前后端贯通。

**Architecture:** FastAPI 后端（async SQLAlchemy + PostgreSQL）+ React 前端（Vite + TypeScript + Ant Design）。统一 `pyproject.toml` 通过 uv `[dependency-groups]` 管理 ml/web 两组依赖。Alembic 管理数据库迁移，Docker Compose 6 个服务（postgres, redis, backend, celery-worker, nginx, frontend dev）。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Redis 7, Alembic, Celery, passlib[bcrypt], python-jose, React 18, TypeScript, Vite 5, Ant Design 5, Zustand, TanStack Query, Axios, Docker Compose

---

## File Structure Map

```
rgzn-class/
├── pyproject.toml                    # [MODIFY] 添加 web 依赖分组
├── docker-compose.yml                # [CREATE] 全栈编排
├── docker/
│   ├── nginx/default.conf            # [CREATE] nginx 反向代理
│   └── postgres/init.sql             # [CREATE] 初始数据库
│
├── backend/
│   ├── .env.example                  # [CREATE]
│   ├── Dockerfile                    # [CREATE] python:3.12-slim
│   ├── alembic.ini                   # [CREATE] alembic 配置
│   ├── alembic/
│   │   ├── env.py                    # [CREATE] async engine + Base.metadata
│   │   ├── script.py.mako            # [CREATE] 迁移模板
│   │   └── versions/                 # [CREATE] 初始迁移
│   └── app/
│       ├── __init__.py
│       ├── main.py                   # [CREATE] FastAPI app factory + lifespan
│       ├── config.py                 # [CREATE] pydantic-settings
│       ├── database.py               # [CREATE] AsyncEngine + session factory
│       ├── deps.py                   # [CREATE] get_current_user, require_admin
│       ├── models/
│       │   ├── __init__.py           # [CREATE] Base + import all
│       │   ├── user.py               # [CREATE] user_info
│       │   ├── policy.py             # [CREATE] policy_info
│       │   ├── insuree.py            # [CREATE] insuree_info
│       │   ├── accident_claim.py     # [CREATE] accident_claim_info
│       │   ├── fraud_detect_result.py # [CREATE] fraud_detect_result
│       │   ├── model_info.py         # [CREATE] model_info
│       │   └── case_history.py       # [CREATE] case_history
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── auth.py               # [CREATE] Register/Login/Token schemas
│       ├── services/
│       │   ├── __init__.py
│       │   └── auth_service.py       # [CREATE] register/login/refresh/me
│       ├── routers/
│       │   ├── __init__.py
│       │   └── auth.py               # [CREATE] /api/auth/*
│       └── utils/
│           ├── __init__.py
│           ├── security.py           # [CREATE] JWT + bcrypt
│           └── exceptions.py         # [CREATE] 全局异常处理
│
└── frontend/                         # [CREATE] Vite + React + TS
    ├── vite.config.ts                # [CREATE] proxy /api → :8000
    └── src/
        ├── main.tsx                  # [MODIFY] ReactDOM + QueryClient
        ├── App.tsx                   # [CREATE] Router + ConfigProvider
        ├── types/index.ts            # [CREATE] TS 类型
        ├── utils/constants.ts        # [CREATE] API_BASE_URL
        ├── api/
        │   ├── client.ts             # [CREATE] Axios + JWT interceptor
        │   └── auth.ts               # [CREATE] auth API 函数
        ├── store/authStore.ts        # [CREATE] Zustand auth state
        ├── hooks/useAuth.ts          # [CREATE] auth hook
        ├── components/layout/AppLayout.tsx  # [CREATE] Layout 骨架
        └── pages/
            ├── LoginPage.tsx         # [CREATE] 登录表单
            └── DashboardPage.tsx     # [CREATE] 仪表盘空壳
```

---

### Task 1: 更新 pyproject.toml，添加 web 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 在 pyproject.toml 中添加 web 依赖分组**

`pyproject.toml` 当前内容见 `Read` 结果。在文件末尾追加 `[dependency-groups]` 配置。注意：uv 使用 `[dependency-groups]`（不是 `[project.optional-dependencies]`）。

```toml
[dependency-groups]
ml = [
    "pandas>=2.0",
    "numpy>=1.24",
    "xgboost>=2.0",
    "scikit-learn>=1.3",
    "optuna>=3.0",
    "shap>=0.44",
    "matplotlib>=3.7",
    "seaborn>=0.12",
    "joblib>=1.3",
    "openpyxl>=3.1",
    "imbalanced-learn>=0.11",
]
web = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "celery[redis]>=5.4.0",
    "redis>=5.0.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pydantic-settings>=2.3.0",
    "python-multipart>=0.0.9",
    "aiofiles>=24.0",
    "httpx>=0.27.0",
]
```

将原 `[project].dependencies` 精简为空列表（依赖已移到 groups）：

```toml
dependencies = []
```

- [ ] **Step 2: 运行 uv lock 和 uv sync**

```bash
uv lock
uv sync --group ml --group web
```

Expected: 无报错，所有依赖解析成功。`uv sync` 输出显示安装的包列表。

- [ ] **Step 3: 验证关键包可导入**

```bash
uv run python -c "import fastapi; import sqlalchemy; import asyncpg; import passlib; import jose; print('All ok')"
```

Expected: `All ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add web dependencies (FastAPI, SQLAlchemy, Celery, etc.) via uv dependency-groups"
```

---

### Task 2: Backend 配置 + 数据库引擎

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/.env.example`

- [ ] **Step 1: 创建 backend/app/__init__.py**

```bash
mkdir -p backend/app
touch backend/app/__init__.py
```

- [ ] **Step 2: 创建 backend/app/config.py**

```python
"""应用配置 — pydantic-settings, 环境变量驱动."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "Fraud Detection API"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fraud_detect"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # 模型
    MODEL_PATH: str = "modeling/xgb_fraud_model.pkl"


settings = Settings()
```

- [ ] **Step 3: 创建 backend/app/database.py**

```python
"""Async SQLAlchemy engine + session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI 依赖：获取数据库会话."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 4: 创建 backend/.env.example**

```ini
APP_NAME=Fraud Detection API
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fraud_detect
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:5173"]
MODEL_PATH=modeling/xgb_fraud_model.pkl
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/__init__.py backend/app/config.py backend/app/database.py backend/.env.example
git commit -m "feat: add backend config (pydantic-settings) and async database engine"
```

---

### Task 3: 7 个 SQLAlchemy ORM 模型

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/policy.py`
- Create: `backend/app/models/insuree.py`
- Create: `backend/app/models/accident_claim.py`
- Create: `backend/app/models/fraud_detect_result.py`
- Create: `backend/app/models/model_info.py`
- Create: `backend/app/models/case_history.py`

- [ ] **Step 1: 创建 backend/app/models/__init__.py**

```python
"""ORM 模型 — 导入全部模型供 Alembic 发现."""

from backend.app.database import Base

# 按依赖顺序导入（有外键的模型后导入），确保 Alembic autogenerate 能解析关系
from backend.app.models.user import User
from backend.app.models.model_info import ModelInfo
from backend.app.models.insuree import Insuree
from backend.app.models.policy import Policy
from backend.app.models.accident_claim import AccidentClaim
from backend.app.models.fraud_detect_result import FraudDetectResult
from backend.app.models.case_history import CaseHistory

__all__ = [
    "Base",
    "User",
    "ModelInfo",
    "Insuree",
    "Policy",
    "AccidentClaim",
    "FraudDetectResult",
    "CaseHistory",
]
```

- [ ] **Step 2: 创建 backend/app/models/user.py**

```python
"""user_info — 系统用户."""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class User(Base):
    __tablename__ = "user_info"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="reviewer", index=True
    )
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(128), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 3: 创建 backend/app/models/insuree.py**

```python
"""insuree_info — 被保险人."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Insuree(Base):
    __tablename__ = "insuree_info"

    insuree_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(16))
    occupation: Mapped[str | None] = mapped_column(String(128))
    marital_status: Mapped[str | None] = mapped_column(String(32))
    claim_times: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: 创建 backend/app/models/policy.py**

```python
"""policy_info — 保单."""

from datetime import datetime

from sqlalchemy import String, Float, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Policy(Base):
    __tablename__ = "policy_info"

    policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    insuree_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("insuree_info.insuree_id"), nullable=False, index=True
    )
    insurance_type: Mapped[str | None] = mapped_column(String(64))
    insurance_amount: Mapped[float | None] = mapped_column(Float)
    premium: Mapped[float | None] = mapped_column(Float)
    insure_date: Mapped[datetime | None] = mapped_column(Date)
    effect_date: Mapped[datetime | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    insuree: Mapped["Insuree"] = relationship("Insuree", lazy="selectin")
```

- [ ] **Step 5: 创建 backend/app/models/accident_claim.py**

```python
"""accident_claim_info — 事故理赔."""

from datetime import datetime

from sqlalchemy import (
    String, Float, Integer, Boolean, Date, DateTime, ForeignKey, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class AccidentClaim(Base):
    __tablename__ = "accident_claim_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_info.policy_id"), nullable=False, index=True
    )
    accident_date: Mapped[datetime | None] = mapped_column(Date)
    accident_type: Mapped[str | None] = mapped_column(String(64))
    has_witness: Mapped[bool | None] = mapped_column(Boolean)
    claim_amount: Mapped[float | None] = mapped_column(Float)
    claim_date: Mapped[datetime | None] = mapped_column(Date)
    is_paid: Mapped[bool | None] = mapped_column(Boolean)
    paid_amount: Mapped[float | None] = mapped_column(Float)
    # 仅回填脚本写入真实标签，运行时新案件为 NULL
    is_fraud: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped["Policy"] = relationship("Policy", lazy="selectin")
```

- [ ] **Step 6: 创建 backend/app/models/model_info.py**

```python
"""model_info — 模型元数据."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ModelInfo(Base):
    __tablename__ = "model_info"

    model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_algorithm: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(32))
    model_auc: Mapped[float | None] = mapped_column(Float)
    model_f1: Mapped[float | None] = mapped_column(Float)
    model_precision: Mapped[float | None] = mapped_column(Float)
    model_recall: Mapped[float | None] = mapped_column(Float)
    pr_auc: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[float | None] = mapped_column(Float)
    feature_count: Mapped[int | None] = mapped_column(Integer)
    cv_f1_mean: Mapped[float | None] = mapped_column(Float)
    cv_f1_std: Mapped[float | None] = mapped_column(Float)
    param_config: Mapped[dict | None] = mapped_column(JSONB)
    train_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    model_file_path: Mapped[str | None] = mapped_column(String(256))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 7: 创建 backend/app/models/fraud_detect_result.py**

```python
"""fraud_detect_result — AI 预测结果."""

from datetime import datetime

from sqlalchemy import (
    String, Float, Integer, DateTime, ForeignKey, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class FraudDetectResult(Base):
    __tablename__ = "fraud_detect_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_info.policy_id"), nullable=False, index=True
    )
    accident_claim_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accident_claim_info.id"),
        unique=True,
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("model_info.model_id"), nullable=False
    )
    fraud_prob: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    raw_prob: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    threshold_used: Mapped[float | None] = mapped_column(Float)
    feature_values: Mapped[dict | None] = mapped_column(JSONB)
    shap_values: Mapped[dict | None] = mapped_column(JSONB)
    agent_report: Mapped[dict | None] = mapped_column(JSONB)
    detect_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), index=True
    )
    manual_result: Mapped[str | None] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped["Policy"] = relationship("Policy", lazy="selectin")
    accident_claim: Mapped["AccidentClaim"] = relationship(
        "AccidentClaim", lazy="selectin"
    )
    model: Mapped["ModelInfo"] = relationship("ModelInfo", lazy="selectin")
```

- [ ] **Step 8: 创建 backend/app/models/case_history.py**

```python
"""case_history — 人工审核历史."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class CaseHistory(Base):
    __tablename__ = "case_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("policy_info.policy_id"), nullable=False, index=True
    )
    detect_result_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fraud_detect_result.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_info.user_id"), nullable=False
    )
    operate_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    manual_result: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    policy: Mapped["Policy"] = relationship("Policy", lazy="selectin")
    detect_result: Mapped["FraudDetectResult"] = relationship(
        "FraudDetectResult", lazy="selectin"
    )
    reviewer: Mapped["User"] = relationship("User", lazy="selectin")
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add 7 SQLAlchemy ORM models (user, policy, insuree, accident_claim, fraud_detect_result, model_info, case_history)"
```

---

### Task 4: FastAPI app factory + health check

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建 backend/app/main.py**

```python
"""FastAPI app factory + lifespan + CORS."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭生命周期管理."""
    # 启动时：数据库迁移由 Alembic 在容器启动脚本中处理
    # 此处不做重操作，只做轻量初始化
    yield
    # 关闭时：（暂无清理逻辑）


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS（开发模式允许 Vite dev server）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"code": 0, "data": {"status": "ok"}, "message": "ok"}

    return app


app = create_app()
```

- [ ] **Step 2: 验证 dev server 可启动**

```bash
uv run uvicorn backend.app.main:app --port 8000 &
sleep 2
curl http://localhost:8000/api/health
```

Expected: `{"code":0,"data":{"status":"ok"},"message":"ok"}`

- [ ] **Step 3: 关掉 dev server 并 commit**

```bash
kill %1 2>/dev/null || true
git add backend/app/main.py
git commit -m "feat: add FastAPI app factory with health check and CORS"
```

---

### Task 5: Alembic 配置 + 初始迁移

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (由 alembic revision 生成)

- [ ] **Step 1: 创建目录并初始化 Alembic**

```bash
cd backend
uv run alembic init alembic
cd ..
```

这会在 `backend/` 下生成 `alembic.ini` 和 `alembic/` 目录（含 `env.py`, `script.py.mako`, `versions/`）。

- [ ] **Step 2: 修改 backend/alembic.ini — 替换 sqlalchemy.url**

打开 `backend/alembic.ini`，找到 `sqlalchemy.url = ...`，替换为开发环境默认值：

```ini
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/fraud_detect
```

（容器运行时此值会被环境变量 `DATABASE_URL` 覆盖——见 env.py 修改。）

- [ ] **Step 3: 重写 backend/alembic/env.py — 异步引擎 + Base.metadata**

```python
"""Alembic 异步迁移环境."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import settings
from backend.app.database import Base

# 导入所有模型，确保 Base.metadata 包含全部表
import backend.app.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """离线模式：生成 SQL 但不连接数据库."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """在线模式：连接数据库并执行迁移."""
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: 生成初始迁移**

需要一个运行中的 PostgreSQL 来跑 autogenerate。先启动 postgres 容器：

```bash
docker run -d --name fraud-pg \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fraud_detect \
  -p 5432:5432 postgres:16-alpine
sleep 3
```

生成迁移：

```bash
cd backend
uv run alembic revision --autogenerate -m "initial: 7 tables"
cd ..
```

Expected: `Generating ... done`，`backend/alembic/versions/` 下出现 `*_initial_7_tables.py`。

清理：

```bash
docker stop fraud-pg && docker rm fraud-pg
```

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic async migration setup with initial 7-table migration"
```

---

### Task 6: Docker Compose 初版 + backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（分层缓存）
COPY pyproject.toml uv.lock ./
RUN pip install uv --no-cache-dir \
    && uv sync --group web --group ml --no-dev

# 应用代码
COPY backend/ ./backend/
COPY modeling/ ./modeling/

# 启动脚本
COPY <<'ENTRYPOINT_SCRIPT' /usr/local/bin/entrypoint.sh
#!/bin/bash
set -e
cd /app/backend
echo "Running Alembic migrations..."
uv run alembic upgrade head
echo "Starting application..."
exec uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
ENTRYPOINT_SCRIPT

RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000
CMD ["entrypoint.sh"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fraud_detect
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/fraud_detect
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: dev-secret-change-in-production
      JWT_ALGORITHM: HS256
      CORS_ORIGINS: '["http://localhost:5173"]'
      MODEL_PATH: /app/modeling/xgb_fraud_model.pkl
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 3: 验证 docker compose up**

```bash
docker compose up -d --build
sleep 10
curl http://localhost:8000/api/health
```

Expected: `{"code":0,"data":{"status":"ok"},"message":"ok"}`

- [ ] **Step 4: 验证数据库表存在**

```bash
docker compose exec postgres psql -U postgres -d fraud_detect -c "\dt"
```

Expected: 7 张表列出（user_info, policy_info, insuree_info, accident_claim_info, fraud_detect_result, model_info, case_history, alembic_version）。

- [ ] **Step 5: 停止容器，commit**

```bash
docker compose down
git add backend/Dockerfile docker-compose.yml
git commit -m "feat: add Docker Compose (postgres+redis+backend) and backend Dockerfile"
```

---

### Task 7: JWT + bcrypt 安全工具

**Files:**
- Create: `backend/app/utils/__init__.py`
- Create: `backend/app/utils/security.py`
- Create: `backend/app/utils/exceptions.py`

- [ ] **Step 1: 创建 backend/app/utils/__init__.py**

```bash
mkdir -p backend/app/utils
touch backend/app/utils/__init__.py
```

- [ ] **Step 2: 创建 backend/app/utils/security.py**

```python
"""JWT 编解码 + bcrypt 密码哈希."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT，验证签名和过期。抛出 JWTError 如果无效."""
    return jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
```

- [ ] **Step 3: 创建 backend/app/utils/exceptions.py**

```python
"""全局异常处理."""

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    """业务异常。code 为业务错误码，status_code 为 HTTP 状态码."""

    def __init__(
        self,
        message: str,
        code: int = 1,
        status_code: int = 400,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code


async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "data": None, "message": exc.message},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "data": None, "message": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = "; ".join(
        f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in errors[:3]
    )
    return JSONResponse(
        status_code=422,
        content={"code": 422, "data": None, "message": msg},
    )


async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "data": None,
            "message": f"Internal server error [request_id={request_id}]",
        },
    )
```

- [ ] **Step 4: 更新 backend/app/main.py — 注册异常 handlers**

在 `create_app()` 函数中，return app 之前添加：

```python
    # 全局异常处理
    from backend.app.utils.exceptions import (
        AppException,
        app_exception_handler,
        general_exception_handler,
        http_exception_handler,
        validation_exception_handler,
    )
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
```

同时更新 main.py 顶部 import 区域，新增 `from fastapi.exceptions import RequestValidationError` 和 `from starlette.exceptions import HTTPException as StarletteHTTPException`。

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/ backend/app/main.py
git commit -m "feat: add JWT/bcrypt security utils and global exception handlers"
```

---

### Task 8: Auth schemas + service + router + deps

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/deps.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 backend/app/schemas/__init__.py**

```bash
mkdir -p backend/app/schemas
touch backend/app/schemas/__init__.py
```

- [ ] **Step 2: 创建 backend/app/schemas/auth.py**

```python
"""认证相关 Pydantic v2 schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=64)
    email: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    user_role: str
    email: str | None
    phone: str | None
    is_active: bool
    last_login: datetime | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
```

- [ ] **Step 3: 创建 backend/app/services/__init__.py**

```bash
mkdir -p backend/app/services
touch backend/app/services/__init__.py
```

- [ ] **Step 4: 创建 backend/app/services/auth_service.py**

```python
"""认证业务逻辑."""

from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
    LoginResponse,
)
from backend.app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.utils.exceptions import AppException


async def register(db: AsyncSession, req: RegisterRequest) -> LoginResponse:
    """注册新用户。首个用户自动成为 admin."""
    # 检查用户名唯一
    existing = await db.execute(
        select(User).where(User.username == req.username)
    )
    if existing.scalar_one_or_none() is not None:
        raise AppException("用户名已存在", code=1001, status_code=409)

    # 检查是否为第一个用户
    count_result = await db.execute(select(User))
    is_first = count_result.first() is None

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.display_name or req.username,
        user_role="admin" if is_first else "reviewer",
        email=req.email,
        phone=req.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = _make_tokens(user)
    return LoginResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def login(db: AsyncSession, username: str, password: str) -> LoginResponse:
    """登录."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise AppException("用户名或密码错误", code=1002, status_code=401)

    if not user.is_active:
        raise AppException("账户已被停用", code=1003, status_code=403)

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    tokens = _make_tokens(user)
    return LoginResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """用 refresh token 换取新的 access token."""
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise AppException("无效的 refresh token", code=1004, status_code=401)

    if payload.get("type") != "refresh":
        raise AppException("token 类型错误", code=1005, status_code=401)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AppException("用户不存在或已停用", code=1006, status_code=401)

    return TokenResponse(
        access_token=create_access_token(user.user_id, user.user_role),
        refresh_token=create_refresh_token(user.user_id),
    )


async def get_me(db: AsyncSession, user_id: str) -> UserResponse:
    """获取当前用户信息."""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppException("用户不存在", code=1007, status_code=404)
    return UserResponse.model_validate(user)


def _make_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.user_id, user.user_role),
        refresh_token=create_refresh_token(user.user_id),
    )
```

- [ ] **Step 5: 创建 backend/app/deps.py**

```python
"""FastAPI 依赖注入 — 认证 + 权限."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.utils.security import decode_token
from backend.app.utils.exceptions import AppException

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 JWT 解析当前用户，返回 ORM 对象."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise AppException("token 无效或已过期", code=401, status_code=401)

    if payload.get("type") != "access":
        raise AppException("token 类型错误，请使用 access token", code=401, status_code=401)

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise AppException("用户不存在或已停用", code=401, status_code=401)

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """仅允许 admin 角色."""
    if current_user.user_role != "admin":
        raise AppException("需要管理员权限", code=403, status_code=403)
    return current_user
```

- [ ] **Step 6: 创建 backend/app/routers/__init__.py + auth.py**

```bash
mkdir -p backend/app/routers
touch backend/app/routers/__init__.py
```

```python
"""认证路由 — POST /api/auth/*."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
)
from backend.app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.register(db, req)


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, req.username, req.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Refresh token 从 Authorization header 提取，这里用 access token 通过验证后，
    要求显式传入 refresh_token。实际由前端 interceptor 处理：401 → 用 refresh_token 调此接口。
    
    简化处理：refresh token 通过请求体传入。
    """
    # 注意：这里需要另一种方式接收 refresh_token。
    # 改为从 JSON body 取 refresh_token 参数。
    pass
```

等等，`POST /refresh` 需要接收 refresh_token。让我修正设计：refresh_token 通过 JSON body 传入。

```python
"""认证路由 — POST /api/auth/*."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
)
from backend.app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=LoginResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.register(db, req)


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, req.username, req.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh_access_token(db, req.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
```

- [ ] **Step 7: 更新 backend/app/main.py — 注册 auth router**

在 `create_app()` 函数中，health check endpoint 之前添加：

```python
    from backend.app.routers.auth import router as auth_router
    app.include_router(auth_router)
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/ backend/app/services/ backend/app/routers/ backend/app/deps.py backend/app/main.py
git commit -m "feat: add auth system (register/login/refresh/me) with JWT + bcrypt + RBAC deps"
```

---

### Task 9: 验证认证流程

- [ ] **Step 1: 启动 Docker 环境**

```bash
docker compose up -d --build
sleep 10
```

- [ ] **Step 2: 测试注册（首个用户应为 admin）**

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","display_name":"管理员"}' | python -m json.tool
```

Expected: 返回 `access_token`, `refresh_token`, `user` 对象且 `user_role` 为 `"admin"`。

- [ ] **Step 3: 测试登录**

```bash
# 保存 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['tokens']['access_token'])")

# 测试 /me
curl -s http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: 返回用户信息。

- [ ] **Step 4: 测试第二个用户注册为 reviewer**

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"reviewer1","password":"pass123","display_name":"审核员"}' | python -c "import sys,json; d=json.load(sys.stdin); print('Role:', d['user']['user_role'])"
```

Expected: `Role: reviewer`

- [ ] **Step 5: 测试 refresh token**

```bash
# 先从登录获取 refresh_token
REFRESH=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['tokens']['refresh_token'])")

curl -s -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}" | python -m json.tool
```

Expected: 返回新的 `access_token` 和 `refresh_token`。

- [ ] **Step 6: 测试错误场景**

```bash
# 错误的密码
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong"}' | python -m json.tool

# 无效 token
curl -s http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer invalidtoken" | python -m json.tool

# 重复注册
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -m json.tool
```

Expected: 分别返回 401 / 401 / 409，统一格式 `{"code": ..., "message": "...", "data": null}`。

- [ ] **Step 7: 停止 Docker 环境，commit（如有代码修改）**

```bash
docker compose down
```

---

### Task 10: 前端项目初始化 + 依赖安装

**Files:**
- Create: `frontend/` (Vite 脚手架生成)
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: 用 Vite 创建 React + TypeScript 项目**

```bash
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: 安装依赖**

```bash
cd frontend
npm install
npm install antd @ant-design/icons react-router-dom zustand @tanstack/react-query axios
```

- [ ] **Step 3: 配置 Vite proxy 和端口**

修改 `frontend/vite.config.ts`：

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: 验证开发服务器启动**

```bash
cd frontend
npm run dev &
sleep 3
curl -s http://localhost:5173 | head -20
```

Expected: 返回 HTML（Vite 默认模板）。然后 `kill %1`。

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: init frontend with Vite + React + TypeScript + Ant Design + routing dependencies"
```

---

### Task 11: 前端核心文件 — types, constants, API client, auth store

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/utils/constants.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/store/authStore.ts`
- Create: `frontend/src/hooks/useAuth.ts`

- [ ] **Step 1: 创建 frontend/src/types/index.ts**

```typescript
// ---- API 通用 ----
export interface ApiResponse<T> {
  code: number;
  data: T;
  message: string;
}

// ---- 用户 ----
export interface User {
  user_id: string;
  username: string;
  display_name: string;
  user_role: 'admin' | 'reviewer';
  email: string | null;
  phone: string | null;
  is_active: boolean;
  last_login: string | null;
  created_at: string | null;
}

// ---- 认证 ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  display_name?: string;
  email?: string;
  phone?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse {
  user: User;
  tokens: TokenResponse;
}

export interface RefreshRequest {
  refresh_token: string;
}
```

- [ ] **Step 2: 创建 frontend/src/utils/constants.ts**

```typescript
export const API_BASE_URL = '/api';
```

- [ ] **Step 3: 创建 frontend/src/api/client.ts**

```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL } from '../utils/constants';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器：附加 JWT
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 时尝试 refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
}

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          },
          reject,
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      localStorage.clear();
      window.location.href = '/login';
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const newAccess = data.data.access_token;
      const newRefresh = data.data.refresh_token;
      localStorage.setItem('access_token', newAccess);
      localStorage.setItem('refresh_token', newRefresh);
      processQueue(null, newAccess);
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      return client(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.clear();
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default client;
```

- [ ] **Step 4: 创建 frontend/src/api/auth.ts**

```typescript
import client from './client';
import type { ApiResponse, LoginRequest, LoginResponse, RegisterRequest, RefreshRequest, TokenResponse, User } from '../types';

export async function login(req: LoginRequest): Promise<LoginResponse> {
  const { data } = await client.post<ApiResponse<LoginResponse>>('/auth/login', req);
  return data.data;
}

export async function register(req: RegisterRequest): Promise<LoginResponse> {
  const { data } = await client.post<ApiResponse<LoginResponse>>('/auth/register', req);
  return data.data;
}

export async function refresh(req: RefreshRequest): Promise<TokenResponse> {
  const { data } = await client.post<ApiResponse<TokenResponse>>('/auth/refresh', req);
  return data.data;
}

export async function getMe(): Promise<User> {
  const { data } = await client.get<ApiResponse<User>>('/auth/me');
  return data.data;
}
```

- [ ] **Step 5: 创建 frontend/src/store/authStore.ts**

```typescript
import { create } from 'zustand';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),

  setAuth: (user, accessToken, refreshToken) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    set({ user, isAuthenticated: true });
  },

  clearAuth: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
  },
}));
```

- [ ] **Step 6: 创建 frontend/src/hooks/useAuth.ts**

```typescript
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import * as authApi from '../api/auth';
import type { LoginRequest, RegisterRequest } from '../types';

export function useAuth() {
  const { user, isAuthenticated, setAuth, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const login = useCallback(
    async (req: LoginRequest) => {
      const res = await authApi.login(req);
      setAuth(res.user, res.tokens.access_token, res.tokens.refresh_token);
      navigate('/');
    },
    [setAuth, navigate],
  );

  const register = useCallback(
    async (req: RegisterRequest) => {
      const res = await authApi.register(req);
      setAuth(res.user, res.tokens.access_token, res.tokens.refresh_token);
      navigate('/');
    },
    [setAuth, navigate],
  );

  const logout = useCallback(() => {
    clearAuth();
    navigate('/login');
  }, [clearAuth, navigate]);

  const fetchMe = useCallback(async () => {
    try {
      const u = await authApi.getMe();
      // 只更新 user，不改变 token
      useAuthStore.setState({ user: u });
    } catch {
      clearAuth();
      navigate('/login');
    }
  }, [clearAuth, navigate]);

  return { user, isAuthenticated, login, register, logout, fetchMe };
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/ frontend/src/utils/ frontend/src/api/ frontend/src/store/ frontend/src/hooks/
git commit -m "feat: add frontend API client, auth store, and auth hook"
```

---

### Task 12: 前端页面组件 + App shell

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/components/layout/AppLayout.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 创建 frontend/src/pages/LoginPage.tsx**

```tsx
import { useState } from 'react';
import { Button, Card, Form, Input, message, Tabs } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuth } from '../hooks/useAuth';
import type { LoginRequest, RegisterRequest } from '../types';

export default function LoginPage() {
  const { login, register } = useAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('login');

  const handleLogin = async (values: LoginRequest) => {
    setLoading(true);
    try {
      await login(values);
      message.success('登录成功');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || '登录失败';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: RegisterRequest) => {
    setLoading(true);
    try {
      await register(values);
      message.success('注册成功');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || '注册失败';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card style={{ width: 400 }}>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>
          医保风控系统
        </h2>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form onFinish={handleLogin} size="large">
                  <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading} block>
                      登录
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form onFinish={handleRegister} size="large">
                  <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item name="display_name">
                    <Input placeholder="显示名称（可选）" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading} block>
                      注册
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: 创建 frontend/src/pages/DashboardPage.tsx**

```tsx
import { Card, Col, Row, Statistic } from 'antd';
import { SafetyOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useAuth } from '../hooks/useAuth';

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div>
      <h2>欢迎，{user?.display_name || user?.username}</h2>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="今日待审核"
              value={0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="今日风险案件"
              value={0}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="今日已处理"
              value={0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
```

- [ ] **Step 3: 创建 frontend/src/components/layout/AppLayout.tsx**

```tsx
import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Layout, Menu, Button, theme } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  FileTextOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { token: themeToken } = theme.useToken();

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/predict/single', icon: <SearchOutlined />, label: '单条预测' },
    { key: '/predict/batch', icon: <FileTextOutlined />, label: '批量预测' },
    { key: '/cases', icon: <FileTextOutlined />, label: '案件管理' },
    ...(user?.user_role === 'admin'
      ? [{ key: '/admin', icon: <SettingOutlined />, label: '管理面板' }]
      : []),
  ];

  const selectedKey = '/' + location.pathname.split('/')[1];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div
          style={{
            height: 32,
            margin: 16,
            color: '#fff',
            fontWeight: 'bold',
            textAlign: 'center',
            lineHeight: '32px',
            overflow: 'hidden',
          }}
        >
          {collapsed ? '风控' : '医保风控系统'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: themeToken.colorBgContainer,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <div>
            <span style={{ marginRight: 12 }}>{user?.display_name}</span>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={logout}
            >
              退出
            </Button>
          </div>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 4: 修改 frontend/src/App.tsx**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from './store/authStore';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AppLayout from './components/layout/AppLayout';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#1677ff',
          },
        }}
      >
        <AntApp>
          <BrowserRouter>
            <Routes>
              <Route
                path="/login"
                element={
                  <GuestRoute>
                    <LoginPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="predict/single" element={<div>单条预测（Phase 2）</div>} />
                <Route path="predict/batch" element={<div>批量预测（Phase 3）</div>} />
                <Route path="cases" element={<div>案件管理（Phase 3）</div>} />
                <Route path="admin" element={<div>管理面板（Phase 4）</div>} />
              </Route>
              <Route path="*" element={<div style={{ padding: 48, textAlign: 'center' }}>404</div>} />
            </Routes>
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 5: 修改 frontend/src/main.tsx**（Vite 生成的默认文件，需删除默认样式并确保 load）

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';  // Vite 默认生成，保留 reset 样式

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add login page, dashboard shell, app layout with routing guards"
```

---

### Task 13: 前后端联调验证

- [ ] **Step 1: 启动后端（Docker）**

```bash
docker compose up -d --build
sleep 10
```

- [ ] **Step 2: 注册测试用户**

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123","display_name":"演示用户"}'
```

- [ ] **Step 3: 验证前端登录流程**

```bash
cd frontend
npm run dev &
sleep 3
echo "打开浏览器 http://localhost:5173/login 测试登录"
```

手动验证步骤：
1. 浏览器打开 `http://localhost:5173`
2. 应该被重定向到 `/login`
3. 切换到「注册」标签，注册新用户
4. 注册成功 → 跳转仪表盘，显示"欢迎，XXX"
5. 点击「退出」→ 回到登录页
6. 重新登录 → 进入仪表盘
7. 未登录直接访问 `/` → 重定向到 `/login`

- [ ] **Step 4: 清理**

```bash
kill %1 2>/dev/null || true
docker compose down
```

---

### Task 14: Docker Compose 完整拓扑 + nginx

**Files:**
- Create: `docker/nginx/default.conf`
- Modify: `docker-compose.yml`
- Create: `docker/postgres/init.sql`

- [ ] **Step 1: 创建 docker/nginx/default.conf**

```bash
mkdir -p docker/nginx
```

```nginx
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

- [ ] **Step 2: 创建 docker/postgres/init.sql**

```bash
mkdir -p docker/postgres
```

```sql
-- 确保数据库已创建（docker compose 通过 POSTGRES_DB 环境变量自动创建）
-- 此文件可用于后续初始化种子数据
```

- [ ] **Step 3: 更新 docker-compose.yml — 添加 nginx + celery-worker 服务**

在 `docker-compose.yml` 末尾，`volumes:` 之前添加：

```yaml
  celery-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    command: uv run celery -A backend.app.tasks.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/fraud_detect
      REDIS_URL: redis://redis:6379/0
      MODEL_PATH: /app/modeling/xgb_fraud_model.pkl
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./modeling:/app/modeling:ro

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      # 生产模式：映射前端构建产物
      # - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
```

确保 `version` 是 `"3.9"`，`services` 块包含 5 个服务：`postgres`, `redis`, `backend`, `celery-worker`, `nginx`。`volumes` 块保留 `pgdata:`。

backend 服务新增 `volumes`:

```yaml
    volumes:
      - ./modeling:/app/modeling:ro
```

这样 backend 和 celery-worker 都能访问模型文件。

- [ ] **Step 4: Commit**

```bash
git add docker/ docker-compose.yml
git commit -m "feat: complete Docker Compose topology with nginx + celery-worker"
```

---

### Task 15: Celery app 骨架 + tasks 目录

**Files:**
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/tasks/celery_app.py`

- [ ] **Step 1: 创建 Celery app 骨架**

```bash
mkdir -p backend/app/tasks
touch backend/app/tasks/__init__.py
```

```python
"""Celery app — 异步任务队列."""

from celery import Celery

from backend.app.config import settings

celery_app = Celery(
    "fraud_detect",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.app.tasks.batch_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
)
```

```python
"""批量预测异步任务 —— Phase 3 填充具体逻辑."""

from backend.app.tasks.celery_app import celery_app


# Phase 3 在此添加:
# @celery_app.task(bind=True)
# def process_batch_predict(self, task_id: str, file_path: str):
#     ...
```

先创建 `backend/app/tasks/batch_tasks.py`（占位）：

```python
"""批量预测异步任务 — Phase 3 实现."""

from backend.app.tasks.celery_app import celery_app

# Phase 3 填充任务实现
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/tasks/
git commit -m "feat: add Celery app skeleton for async batch prediction (Phase 3)"
```

---

### Task 16: 最终端到端验证

- [ ] **Step 1: 清理旧容器/volume**

```bash
docker compose down -v
```

- [ ] **Step 2: 全栈启动**

```bash
docker compose up -d --build
sleep 15
```

- [ ] **Step 3: 验证所有服务健康**

```bash
docker compose ps
```

Expected: 5 个服务全部 `Up`（healthy）或 `Up` running。

- [ ] **Step 4: 验证 API 可达（通过 nginx 反向代理）**

```bash
curl -s http://localhost/api/health
```

Expected: `{"code":0,"data":{"status":"ok"},"message":"ok"}`

- [ ] **Step 5: 验证认证流程（通过 nginx）**

```bash
# 注册
curl -s -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","display_name":"管理员"}'

# 登录
curl -s -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Expected: 两种方式都返回正确的 JSON 响应。

- [ ] **Step 6: 验证数据库表**

```bash
docker compose exec postgres psql -U postgres -d fraud_detect -c "\dt"
```

Expected: 8 张表（含 alembic_version）。

- [ ] **Step 7: 停止所有服务**

```bash
docker compose down
```

---

## 验收标准 Checklist

- [ ] Task 1: `uv sync --group ml --group web` 成功，所有包可导入
- [ ] Task 4: `GET /api/health` 返回 `{"code":0,...}`
- [ ] Task 6: Docker Compose 启动（postgres + redis + backend），7 张表在 PostgreSQL 中存在
- [ ] Task 8-9: `POST /api/auth/register` 首个用户为 admin
- [ ] Task 8-9: `POST /api/auth/login` 返回合法 JWT
- [ ] Task 8-9: `GET /api/auth/me` 返回用户信息
- [ ] Task 12-13: 浏览器访问 → 登录页 → 登录 → 仪表盘
- [ ] Task 12-13: 未登录访问 `/` → 重定向到 `/login`（前端路由守卫）
- [ ] Task 8: admin 路由对 reviewer 返回 403
- [ ] Task 16: `docker compose up` 5 个服务全部 healthy
- [ ] Task 16: `curl localhost/api/health`（通过 nginx）正常响应
