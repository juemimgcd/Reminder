from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = Field(default=0, description="0 表示成功，非 0 表示失败")
    message: str = Field(default="ok", description="给前端或调用方看的提示信息")
    data: Any | None = Field(default=None, description="真正的业务数据")


