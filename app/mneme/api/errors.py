from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from app.mneme.conf.logging import app_logger
from app.mneme.utils.exceptions import BusinessException, business_exception_handler


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    app_logger.bind(
        module="exception_handler",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    ).opt(exception=exc).error("unhandled application exception")
    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": request_id},
        content={
            "code": 5000,
            "message": "服务暂时不可用，请稍后重试",
            "data": None,
            "request_id": request_id,
        },
    )


__all__ = ["BusinessException", "business_exception_handler", "unhandled_exception_handler"]
