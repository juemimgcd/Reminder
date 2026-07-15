from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.database import get_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.chat.service import (
    _resolve_model_config,
    answer_via_memory_agent,
    build_chat_message_id,
    memory_agent_answer_to_chat_result,
)
from app.mneme.models.user import User
from app.mneme.schemas.companion import CompanionAnswerResult, CompanionQueryRequest
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

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

    model_config = await _resolve_model_config(db, user_id=current_user.id, config_id=None)
    await db.rollback()
    agent_response = await answer_via_memory_agent(
        owner_id=current_user.id,
        question=payload.question,
        answer_mode="analysis_query",
        top_k=payload.top_k,
        knowledge_base_id=knowledge_base_id,
        session_id=None,
        message_id=build_chat_message_id(),
        model_config=model_config,
    )
    result = memory_agent_answer_to_chat_result(agent_response)
    citations = [
        {
            "document_id": item.get("document_id") or item["source_id"],
            "chunk_id": item.get("chunk_id") or item["source_id"],
            "page_no": item.get("page_no"),
            "text": item.get("quote", ""),
            "reason": item.get("reason", "memory agent evidence"),
        }
        for item in result["citations"]
    ]
    data = CompanionAnswerResult(
        knowledge_base_id=knowledge_base_id,
        question=payload.question,
        direct_answer=result["answer"],
        citations=citations,
        profile_snapshot="",
        growth_snapshot="",
        next_step_hint="",
        follow_up_questions=[],
        companion_message=result["answer"],
    )
    return success_response(data=data)
