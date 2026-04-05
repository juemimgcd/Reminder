from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from crud.knowledge_base import get_knowledge_base_by_id
from crud.memory_entry import list_memory_entries_by_knowledge_base_id, list_memory_entries_by_user_id
from crud.user import get_user_by_id
from models.user import User
from schemas.companion import CompanionAnswerResult, CompanionQueryRequest
from utils.auth import get_current_user
from utils.companion_builder import build_companion_response
from utils.exceptions import BusinessException
from utils.growth_analyzer import build_growth_report
from utils.memory_organizer import build_memory_library
from utils.profile_builder import build_personal_profile
from utils.rag_service import generate_rag_answer
from utils.response import success_response


router = APIRouter(prefix="/companion", tags=["companion"])


@router.post("/knowledge-bases/{knowledge_base_id}/reply")
async def get_companion_reply(
        knowledge_base_id: str,
        payload: CompanionQueryRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_database),
):

    user = await get_user_by_id(db, payload.user_id)
    if not user:
        raise BusinessException(message="用户不存在", code=4041, status_code=404)

    knowledge_base = await get_knowledge_base_by_id(db, payload.knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != payload.user_id:
        raise BusinessException(message="知识库不属于该用户", code=4007)

    result = await generate_rag_answer(
        question=payload["question"],
        top_k=payload["top_k"],
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id

    )

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
        memory_library=js_memory,
        profile=profile,
        knowledge_base_id=knowledge_base_id
    )

    companion = await build_companion_response(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        question=payload["question"],
        rag_result=result,
        profile=profile,
        growth_report=report
    )

    data = CompanionAnswerResult(**companion)
    return success_response(data=data)





































