from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.knowledge_base import get_knowledge_base_by_id
from crud.memory_entry import list_memory_entries_by_user_id
from crud.user import get_user_by_id
from models.user import User
from schemas.advice import GrowthAdviceRequest, GrowthAdviceResult
from services.advice_service import build_growth_advice
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile
from utils.response import success_response


router = APIRouter(prefix="/advice", tags=["advice"])


@router.post("/knowledge-bases/{knowledge_base_id}")
async def get_growth_advice(
        knowledge_base_id: str,
        payload: GrowthAdviceRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="advice_router").info(
        f"growth advice request knowledge_base_id={knowledge_base_id} "
        f"payload_user_id={payload.user_id} current_user_id={current_user.id}"
    )

    user = await get_user_by_id(db, payload.user_id)
    if not user:
        raise BusinessException(message="用户不存在", code=4041, status_code=404)

    knowledge_base = await get_knowledge_base_by_id(db, payload.knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != payload.user_id:
        raise BusinessException(message="知识库不属于该用户", code=4007)



    entries = await list_memory_entries_by_user_id(
        db,
        user_id=current_user.id
    )
    e_list = [u.__dict__ for u in entries]
    js_memory = build_memory_library(e_list)

    profile = await build_personal_profile(
        user_id=current_user.id,
        memory_library=js_memory,
        knowledge_base_id=knowledge_base_id
    )

    report = await build_growth_report(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        profile=profile,
        memory_library=js_memory
    )

    advice = await build_growth_advice(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        profile=profile,
        growth_report=report,
        focus_goal=payload["focus_goal"]

    )

    data = GrowthAdviceResult(**advice)
    app_logger.bind(module="advice_router").info(
        f"growth advice success knowledge_base_id={knowledge_base_id} current_user_id={current_user.id} "
        f"entry_count={len(entries)}"
    )
    return success_response(data=data)







