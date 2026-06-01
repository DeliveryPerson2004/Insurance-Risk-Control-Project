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
