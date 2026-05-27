from fastapi import APIRouter

from app.mneme.conf.config import settings
from app.mneme.utils.response import success_response


router = APIRouter(tags=["root"])


@router.get("/")
async def root():
    return success_response(
        data={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
        message="welcome to agentic rag assistant",
    )


@router.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
