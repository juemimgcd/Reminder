from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from conf.database import get_database
from conf.logging import app_logger
from crud.knowledge_base import get_knowledge_base_by_id
from models.user import User
from schemas.companion import CompanionAnswerResult, CompanionQueryRequest
from services.companion_service import build_companion_response
from services.insight_service import build_growth_for_knowledge_base
from services.query_service import generate_rag_answer
from utils.auth import get_current_user
from utils.exceptions import BusinessException
from utils.response import success_response


router = APIRouter(prefix="/companion", tags=["companion"])


@router.post("/knowledge-bases/{knowledge_base_id}/reply")
async def get_companion_reply(
    knowledge_base_id: str,
    payload: CompanionQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    app_logger.bind(module="companion_router").info(
        f"companion request knowledge_base_id={knowledge_base_id} "
        f"current_user_id={current_user.id} top_k={payload.top_k}"
    )

    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于当前用户", code=4007)

    result = await generate_rag_answer(
        question=payload.question,
        db=db,
        top_k=payload.top_k,
        knowledge_base_id=knowledge_base_id,
        user_id=current_user.id,
    )

    entries, profile, report = await build_growth_for_knowledge_base(
        db,
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        recent_days=30,
    )

    companion = await build_companion_response(
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
        question=payload.question,
        rag_result=result,
        profile=profile,
        growth_report=report,
    )

    data = CompanionAnswerResult(**companion)
    app_logger.bind(module="companion_router").info(
        f"companion success knowledge_base_id={knowledge_base_id} current_user_id={current_user.id} "
        f"entry_count={len(entries)} source_count={len(result['sources'])}"
    )
    return success_response(data=data)
