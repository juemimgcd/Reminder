from typing import Any

from app.mneme.schemas.common import ApiResponse


def success_response(data: Any = None, message: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, message=message, data=data)
