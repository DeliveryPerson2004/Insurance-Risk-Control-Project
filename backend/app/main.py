"""FastAPI app factory + lifespan + CORS."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭生命周期管理."""
    yield


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
