from typing import Any

from app.mneme.schemas.common import ApiResponse


def success_response(data: Any = None, message: str = "ok") -> ApiResponse:
    # 杩欓噷缁熶竴杩斿洖 ApiResponse锛屽ソ澶勬槸鍚庨潰鎵€鏈夋垚鍔熸帴鍙ｉ兘闀垮緱涓€鏍枫€?
    return ApiResponse(code=0, message=message, data=data)