from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.knowledge_base import get_knowledge_base_by_id
from models.user import User
from schemas.profile import PersonalProfileResult
from services.insight_service import build_profile_for_knowledge_base
from utils.auth import get_current_user
from utils.response import success_response


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/knowledge-bases/{knowledge_base_id}")
async def get_personal_profile(
        knowledge_base_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="profile_router").info(
        f"profile request knowledge_base_id={knowledge_base_id} current_user_id={current_user.id}"
    )

    kb = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge_base not found")

    if kb.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you have no right")

    entries, result = await build_profile_for_knowledge_base(
        db,
        user_id=current_user.id,
        knowledge_base_id=kb.id,
    )
    data = PersonalProfileResult(**result)
    app_logger.bind(module="profile_router").info(
        f"profile success knowledge_base_id={knowledge_base_id} current_user_id={current_user.id} "
        f"entry_count={len(entries)}"
    )

    return success_response(data=data)
