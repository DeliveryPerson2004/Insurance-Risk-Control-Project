FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（分层缓存）
COPY pyproject.toml uv.lock ./
RUN pip install uv --no-cache-dir \
    && uv sync --group web --group ml

# 应用代码
COPY backend/ ./backend/
COPY modeling/ ./modeling/

# 启动脚本
COPY <<'ENTRYPOINT_SCRIPT' /usr/local/bin/entrypoint.sh
#!/bin/bash
set -e
echo "Running Alembic migrations..."
cd /app/backend && uv run alembic upgrade head
echo "Starting application..."
cd /app && exec uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
ENTRYPOINT_SCRIPT

RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000
CMD ["entrypoint.sh"]
