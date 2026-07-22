from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.mneme.conf.config import settings
from app.mneme.utils.response import success_response

router = APIRouter(tags=["root"])
FRONTEND_INDEX = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "mneme_frontend_v0.2.1"
    / "dist"
    / "index.html"
)


@router.get("/")
async def root():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)

    return success_response(
        data={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
        message="welcome to Mneme",
    )


@router.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
