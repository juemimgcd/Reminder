from fastapi import FastAPI

from services.memory_agent.api.events import router as event_router
from services.memory_agent.api.health import router as health_router


def create_memory_agent_app() -> FastAPI:
    app = FastAPI(title="Mneme Memory Agent", version="1.0.0")
    app.include_router(health_router)
    app.include_router(event_router, prefix="/internal/v1")
    return app
