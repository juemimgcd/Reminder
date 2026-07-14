from fastapi import APIRouter, FastAPI

health_router = APIRouter()
event_router = APIRouter()


def create_memory_agent_app() -> FastAPI:
    app = FastAPI(title="Mneme Memory Agent", version="1.0.0")
    app.include_router(health_router)
    app.include_router(event_router, prefix="/internal/v1")
    return app
