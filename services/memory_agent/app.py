from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from services.memory_agent.api.answers import router as answers_router
from services.memory_agent.api.errors import AgentAPIError, agent_api_error_handler, validation_error_handler
from services.memory_agent.api.events import router as event_router
from services.memory_agent.api.health import router as health_router
from services.memory_agent.api.memories import router as memories_router
from services.memory_agent.api.runs import router as runs_router


def create_memory_agent_app() -> FastAPI:
    app = FastAPI(title="Mneme Memory Agent", version="1.0.0")
    app.add_exception_handler(AgentAPIError, agent_api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(health_router)
    app.include_router(event_router, prefix="/internal/v1")
    app.include_router(answers_router, prefix="/v1")
    app.include_router(runs_router, prefix="/v1")
    app.include_router(memories_router, prefix="/v1")
    return app
