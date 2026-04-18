from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.knowledge_base import get_knowledge_base_by_id
from crud.memory_entry import list_memory_entries_by_user_id
from models.user import User
from schemas.growth_report import GrowthReportResult
from utils.auth import get_current_user
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile
from utils.response import success_response

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/knowledge-bases/{knowledge_base_id}/growth")
async def get_growth_report(
        knowledge_base_id: str,
        recent_days: int = 30,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="analysis_router").info(
        f"growth report request knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} recent_days={recent_days}"
    )

    kb = await get_knowledge_base_by_id(db, knowledge_base_id=knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="knowledge_base not found")

    if not kb.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you have no right")

    entries = await list_memory_entries_by_user_id(db, user_id=current_user.id)
    e_list = [u.__dict__ for u in entries]
    js_memory = build_memory_library(e_list)

    result = await build_personal_profile(
        user_id=current_user.id,
        knowledge_base_id=kb.id,
        memory_library=js_memory

    )

    report = await build_growth_report(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        memory_library=js_memory,
        profile=result,
        recent_days=recent_days
    )
    data = GrowthReportResult(**report)
    app_logger.bind(module="analysis_router").info(
        f"growth report success knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} entry_count={len(entries)} recent_days={recent_days}"
    )
    return success_response(data=data)



