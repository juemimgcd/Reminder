import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.mneme.memoria.server.api.answers import router as answers_router
from app.mneme.memoria.server.api.errors import AgentAPIError, agent_api_error_handler, validation_error_handler
from app.mneme.memoria.server.api.events import router as event_router
from app.mneme.memoria.server.api.health import router as health_router
from app.mneme.memoria.server.api.memories import router as memories_router
from app.mneme.memoria.server.api.runs import router as runs_router
from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.observability.context import safe_log
from app.mneme.memoria.server.services.embeddings import preload_embedding_model
from app.mneme.observability.http import HttpMetrics, configure_http_observability

logger = logging.getLogger(__name__)
memory_agent_http_metrics = HttpMetrics()


def _emit_http_event(event: str, **fields: str | int) -> None:
    level = logging.ERROR if event == "request_failed" else logging.INFO
    safe_log(logger, level, event, **fields)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.EMBEDDING_PRELOAD_ON_STARTUP:
        await preload_embedding_model()
    yield


def create_memory_agent_app() -> FastAPI:
    app = FastAPI(title="Mneme Memoria", version="1.0.0", lifespan=lifespan)
    configure_http_observability(app, metrics=memory_agent_http_metrics, emit=_emit_http_event)
    app.add_exception_handler(AgentAPIError, agent_api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(health_router)
    app.include_router(event_router, prefix="/internal/v1")
    app.include_router(answers_router, prefix="/v1")
    app.include_router(runs_router, prefix="/v1")
    app.include_router(memories_router, prefix="/v1")
    return app
