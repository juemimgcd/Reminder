from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clients.neo4j_client import close_neo4j_driver
from conf.config import settings
from conf.database import engine
from clients.embedding_client import get_embeddings
from routers import auth, chat, documents, health, memory, users, advice, companion, profile, analysis, tasks, graph
from utils.exceptions import BusinessException, business_exception_handler
from utils.response import success_response
from conf.logging import setup_logger, app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    app_logger.bind(module="system").info("application start")
    if settings.EMBEDDING_PRELOAD_ON_STARTUP:
        get_embeddings()
    try:
        yield
    finally:
        app_logger.bind(module="system").info("application stop")
        logger_complete = app_logger.complete()
        if logger_complete:
            await logger_complete
        await close_neo4j_driver()
        await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX or None,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

app.add_exception_handler(BusinessException, business_exception_handler)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(advice.router)
app.include_router(analysis.router)
app.include_router(profile.router)
app.include_router(companion.router)
app.include_router(tasks.router)
app.include_router(graph.router)


@app.get("/")
async def root():
    return success_response(
        data={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
        message="welcome to agentic rag assistant",
    )


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
