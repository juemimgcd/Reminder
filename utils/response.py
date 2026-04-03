from typing import Any

from schemas.common import ApiResponse


def success_response(data: Any = None, message: str = "ok") -> ApiResponse:
    # 这里统一返回 ApiResponse，好处是后面所有成功接口都长得一样。
    return ApiResponse(code=0, message=message, data=data)