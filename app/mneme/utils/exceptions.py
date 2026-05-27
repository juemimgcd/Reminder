from fastapi import Request
from fastapi.responses import JSONResponse

from app.mneme.conf.logging import app_logger


class BusinessException(Exception):
    def __init__(self, message: str, code: int = 4000, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code


async def business_exception_handler(request: Request, exc: BusinessException):
    app_logger.bind(module="exception_handler").warning(
        f"business exception path={request.url.path} method={request.method} "
        f"status_code={exc.status_code} code={exc.code} message={exc.message}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
        },
    )
