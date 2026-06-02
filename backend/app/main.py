"""FastAPI app factory + lifespan + CORS."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

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

    # 注册 auth 路由
    from backend.app.routers.auth import router as auth_router
    app.include_router(auth_router)

    # 注册 predict 路由
    from backend.app.routers.predict import router as predict_router
    app.include_router(predict_router)

    # 注册 dashboard 路由
    from backend.app.routers.dashboard import router as dashboard_router
    app.include_router(dashboard_router)

    # 注册 batch 路由（Phase 3.2）
    from backend.app.routers.batch import router as batch_router
    app.include_router(batch_router)

    @app.get("/api/health")
    async def health():
        return {"code": 0, "data": {"status": "ok"}, "message": "ok"}

    return app


app = create_app()
