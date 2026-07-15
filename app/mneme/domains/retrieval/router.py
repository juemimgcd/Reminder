from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.conf.database import get_write_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.chat.service import (
    _resolve_model_config,
    answer_via_memory_agent,
    ask_in_chat_session,
    build_chat_message_id,
    memory_agent_answer_to_chat_result,
    message_to_data,
)
from app.mneme.infra.rate_limit import enforce_fixed_window_rate_limit
from app.mneme.models.user import User
from app.mneme.schemas.chat import ChatQueryData, ChatQueryRequest
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/kb/chat", tags=["chat"])


@router.post("/query")
async def query_chat(
    payload: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    app_logger.bind(module="chat_router").info(
        f"chat query request user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"top_k={payload.top_k} question_length={len(payload.question)}"
    )

    enforce_fixed_window_rate_limit(
        bucket="chat_query",
        key=f"user:{current_user.id}:kb:{payload.knowledge_base_id}",
        limit=settings.CHAT_QUERY_RATE_LIMIT_MAX,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    if payload.answer_mode != "general_chat" and payload.knowledge_base_id is None:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)
    knowledge_base = (
        await get_knowledge_base_by_id(db, payload.knowledge_base_id)
        if payload.knowledge_base_id is not None
        else None
    )
    if payload.knowledge_base_id is not None and not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base is not None and knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于当前用户", code=4007)

    if payload.session_id:
        _session, messages = await ask_in_chat_session(
            db,
            current_user=current_user,
            session_id=payload.session_id,
            question=payload.question,
            top_k=payload.top_k,
            answer_mode=payload.answer_mode,
            model_config_id=payload.model_config_id,
            expected_knowledge_base_id=payload.knowledge_base_id,
        )
        assistant_message = message_to_data(messages[-1])
        data = ChatQueryData(
            answer=assistant_message.content,
            sources=assistant_message.sources,
            citations=assistant_message.citations,
            confidence=assistant_message.route.confidence if assistant_message.route else "medium",
            uncertainty=None,
            route=assistant_message.route,
            debug=None,
        )
        return success_response(data=data)

    model_config = await _resolve_model_config(
        db, user_id=current_user.id, config_id=payload.model_config_id
    )
    await db.rollback()
    agent_response = await answer_via_memory_agent(
        owner_id=current_user.id,
        question=payload.question,
        answer_mode=payload.answer_mode,
        top_k=payload.top_k,
        knowledge_base_id=payload.knowledge_base_id,
        session_id=None,
        message_id=build_chat_message_id(),
        model_config=model_config,
    )
    result = memory_agent_answer_to_chat_result(agent_response)
    app_logger.bind(module="chat_router").info(
        f"chat query success user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"source_count={len(result['sources'])} citation_count={len(result['citations'])} "
        f"confidence={result['confidence']} query_type={result.get('route', {}).get('query_type')}"
    )

    data = ChatQueryData(**result)
    return success_response(data=data)
