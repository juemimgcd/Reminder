from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.database import get_db

router = APIRouter()


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/readiness")
async def readiness(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return {"status": "ready"}
