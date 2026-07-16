import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.mneme.memoria.server.api.answers import router as answers_router
from app.mneme.memoria.server.api.errors import AgentAPIError, agent_api_error_handler, validation_error_handler
from app.mneme.memoria.server.api.events import router as event_router
from app.mneme.memoria.server.api.health import router as health_router
from app.mneme.memoria.server.api.memories import router as memories_router
from app.mneme.memoria.server.api.runs import router as runs_router
from app.mneme.memoria.server.observability.context import observation_context, safe_identifier, safe_log

logger = logging.getLogger(__name__)


def create_memory_agent_app() -> FastAPI:
    app = FastAPI(title="Mneme Memoria", version="1.0.0")

    @app.middleware("http")
    async def correlate_request(request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = safe_identifier(supplied) or uuid4().hex
        started = perf_counter()
        with observation_context(request_id=request_id):
            try:
                response = await call_next(request)
            except Exception:
                safe_log(logger, logging.ERROR, "request_failed", method=request.method)
                raise
            response.headers["X-Request-ID"] = request_id
            safe_log(
                logger,
                logging.INFO,
                "request_completed",
                method=request.method,
                http_status=response.status_code,
                duration_ms=max(0, round((perf_counter() - started) * 1000)),
            )
            return response
    app.add_exception_handler(AgentAPIError, agent_api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(health_router)
    app.include_router(event_router, prefix="/internal/v1")
    app.include_router(answers_router, prefix="/v1")
    app.include_router(runs_router, prefix="/v1")
    app.include_router(memories_router, prefix="/v1")
    return app
