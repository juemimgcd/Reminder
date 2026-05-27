from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.mneme.clients.embedding_client import get_embeddings
from app.mneme.clients.neo4j_client import close_neo4j_driver
from app.mneme.conf.config import settings
from app.mneme.conf.database import engine
from app.mneme.conf.logging import app_logger, setup_logger


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
