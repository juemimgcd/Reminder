from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.adapters import build_mneme_agent
from app.mneme.agent.contracts import AgentRequest
from app.mneme.conf.config import settings
from app.mneme.conf.database import get_write_database
from app.mneme.conf.logging import app_logger
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.chat.service import ask_in_chat_session, message_to_data
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

    knowledge_base = await get_knowledge_base_by_id(db, payload.knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="知识库不存在", code=4042, status_code=404)

    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="知识库不属于当前用户", code=4007)

    if payload.session_id:
        _session, messages = await ask_in_chat_session(
            db,
            current_user=current_user,
            session_id=payload.session_id,
            question=payload.question,
            top_k=payload.top_k,
            answer_mode=payload.answer_mode,
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

    agent_response = await build_mneme_agent(db).run(
        AgentRequest(
            question=payload.question,
            knowledge_base_id=payload.knowledge_base_id,
            user_id=current_user.id,
            top_k=payload.top_k,
            answer_mode=payload.answer_mode,
        )
    )
    result = agent_response.to_legacy_result()
    app_logger.bind(module="chat_router").info(
        f"chat query success user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"source_count={len(result['sources'])} citation_count={len(result['citations'])} "
        f"confidence={result['confidence']} query_type={result.get('route', {}).get('query_type')}"
    )

    data = ChatQueryData(**result)
    return success_response(data=data)
