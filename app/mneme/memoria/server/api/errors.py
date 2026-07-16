from fastapi import Request
from fastapi.responses import JSONResponse


class AgentAPIError(Exception):
    def __init__(self, *, status_code: int, code: str) -> None:
        self.status_code = status_code
        self.code = code


async def agent_api_error_handler(_request: Request, exc: AgentAPIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code})


async def validation_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    # Pydantic's default response echoes invalid inputs, which may contain private text or keys.
    return JSONResponse(status_code=422, content={"code": "AGENT_VALIDATION_ERROR"})
