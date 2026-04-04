from fastapi import FastAPI
from conf.config import settings
from routers import documents, health, memory
from utils.exceptions import BusinessException, business_exception_handler
from utils.response import success_response
from contextlib import asynccontextmanager
from conf.database import engine


@asynccontextmanager
async def lifespan(app:FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION
)


app.add_exception_handler(BusinessException, business_exception_handler)


app.include_router(health.router)
app.include_router(documents.router)
app.include_router(memory.router)


@app.get("/")
async def root():
    return success_response(
        data={
            "project":settings.PROJECT_NAME,
            "version":settings.VERSION
        },
        message="welcome to agentic rag assistant",
    )


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
