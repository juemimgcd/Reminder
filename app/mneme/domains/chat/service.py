import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.adapters import build_mneme_agent
from app.mneme.agent.contracts import AgentRequest, AnswerMode
from app.mneme.conf.config import settings
from app.mneme.crud.ai_model_config import get_default_ai_model_config
from app.mneme.crud.chat_message import create_chat_message, delete_chat_messages, list_chat_messages
from app.mneme.crud.chat_session import (
    create_chat_session as insert_chat_session,
)
from app.mneme.crud.chat_session import (
    delete_chat_session as delete_chat_session_row,
)
from app.mneme.crud.chat_session import (
    get_chat_session_by_id,
)
from app.mneme.crud.chat_session import (
    list_chat_sessions as list_chat_session_rows,
)
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.domains.settings.ai_models import ai_model_config_runtime_kwargs
from app.mneme.domains.tasks.outbox import (
    enqueue_conversation_completed,
    enqueue_conversation_deleted,
    enqueue_user_memory_requested,
)
from app.mneme.models.chat_message import ChatMessage
from app.mneme.models.chat_session import ChatSession
from app.mneme.models.knowledge_base import KnowledgeBase
from app.mneme.models.user import User
from app.mneme.schemas.chat import ChatCitationItem, ChatSourceItem, QueryRouteDecision
from app.mneme.schemas.chat_session import ChatMessageData
from app.mneme.utils.exceptions import BusinessException


def build_chat_session_id() -> str:
    return f"chat_{uuid.uuid4().hex[:16]}"


def build_chat_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:16]}"


async def require_owned_knowledge_base(
    db: AsyncSession,
    *,
    current_user: User,
    knowledge_base_id: str,
) -> KnowledgeBase:
    knowledge_base = await get_knowledge_base_by_id(db, knowledge_base_id)
    if not knowledge_base:
        raise BusinessException(message="knowledge base not found", code=4042, status_code=404)
    if knowledge_base.user_id != current_user.id:
        raise BusinessException(message="knowledge base does not belong to current user", code=4007, status_code=403)
    return knowledge_base


async def require_owned_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
) -> ChatSession:
    session = await get_chat_session_by_id(db, session_id=session_id, user_id=current_user.id)
    if not session:
        raise BusinessException(message="chat session not found", code=4048, status_code=404)
    return session


async def create_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    knowledge_base_id: str,
    title: str | None,
) -> ChatSession:
    knowledge_base = await require_owned_knowledge_base(
        db,
        current_user=current_user,
        knowledge_base_id=knowledge_base_id,
    )
    return await insert_chat_session(
        db,
        session_id=build_chat_session_id(),
        user_id=current_user.id,
        knowledge_base_id=knowledge_base.id,
        knowledge_base_pk=knowledge_base.pk,
        title=title,
    )


async def list_chat_sessions(
    db: AsyncSession,
    *,
    current_user: User,
    knowledge_base_id: str | None,
) -> list[ChatSession]:
    if knowledge_base_id:
        await require_owned_knowledge_base(db, current_user=current_user, knowledge_base_id=knowledge_base_id)
    return await list_chat_session_rows(
        db,
        user_id=current_user.id,
        knowledge_base_id=knowledge_base_id,
    )


async def get_chat_session_detail(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
) -> tuple[ChatSession, list[ChatMessage]]:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    messages = await list_chat_messages(db, session_id=session.id, user_id=current_user.id)
    return session, messages


async def update_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    title: str | None = None,
    archived: bool | None = None,
) -> ChatSession:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if title is not None:
        session.title = title
    if archived is not None:
        session.archived_at = datetime.now(timezone.utc) if archived else None
    await db.flush()
    await db.refresh(session)
    return session


async def delete_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
) -> int:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    messages = await list_chat_messages(db, session_id=session.id, user_id=current_user.id)
    if settings.MEMORY_AGENT_ENABLED:
        await enqueue_conversation_deleted(
            db,
            owner_id=current_user.id,
            knowledge_base_id=session.knowledge_base_id,
            session_id=session.id,
            message_ids=[message.id for message in messages],
            source_version=datetime.now(timezone.utc),
        )
    await delete_chat_messages(db, session_id=session_id, user_id=current_user.id)
    return await delete_chat_session_row(db, session_id=session_id, user_id=current_user.id)


def message_to_data(message: ChatMessage) -> ChatMessageData:
    route = QueryRouteDecision(**message.route_json) if message.route_json else None
    sources = [ChatSourceItem(**item) for item in (message.sources_json or [])]
    citations = [ChatCitationItem(**item) for item in (message.citations_json or [])]
    return ChatMessageData(
        id=message.id,
        session_id=message.session_id,
        user_id=message.user_id,
        knowledge_base_id=message.knowledge_base_id,
        role=message.role,
        content=message.content,
        sources=sources,
        citations=citations,
        route=route,
        model_config_id=message.model_config_id,
        created_at=message.created_at,
    )


async def ask_in_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    question: str,
    top_k: int,
    answer_mode: AnswerMode = "kb_qa",
    expected_knowledge_base_id: str | None = None,
) -> tuple[ChatSession, list[ChatMessage]]:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if expected_knowledge_base_id and session.knowledge_base_id != expected_knowledge_base_id:
        raise BusinessException(
            message="chat session does not belong to this knowledge base",
            code=4050,
            status_code=400,
        )
    if session.archived_at is not None:
        raise BusinessException(message="chat session is archived", code=4049, status_code=400)

    model_config = await get_default_ai_model_config(db, user_id=current_user.id)
    llm_config = ai_model_config_runtime_kwargs(model_config) if model_config else None
    agent_response = await build_mneme_agent(db).run(
        AgentRequest(
            question=question,
            knowledge_base_id=session.knowledge_base_id,
            user_id=current_user.id,
            top_k=top_k,
            answer_mode=answer_mode,
            llm_config=llm_config,
        )
    )
    result = agent_response.to_legacy_result()
    now = datetime.now(timezone.utc)
    user_message = await create_chat_message(
        db,
        message_id=build_chat_message_id(),
        session_id=session.id,
        user_id=current_user.id,
        knowledge_base_id=session.knowledge_base_id,
        knowledge_base_pk=session.knowledge_base_pk,
        role="user",
        content=question,
    )
    assistant_message = await create_chat_message(
        db,
        message_id=build_chat_message_id(),
        session_id=session.id,
        user_id=current_user.id,
        knowledge_base_id=session.knowledge_base_id,
        knowledge_base_pk=session.knowledge_base_pk,
        role="assistant",
        content=result["answer"],
        sources_json=result.get("sources") or [],
        citations_json=result.get("citations") or [],
        route_json=result.get("route"),
        model_config_id=model_config.id if model_config else None,
    )
    if not session.title:
        session.title = question[:80]
    session.message_count = (session.message_count or 0) + 2
    session.last_message_at = now
    await db.flush()
    if settings.MEMORY_AGENT_ENABLED:
        await enqueue_conversation_completed(
            db,
            owner_id=current_user.id,
            knowledge_base_id=session.knowledge_base_id,
            session_id=session.id,
            user_message_id=user_message.id,
            user_content=user_message.content,
            user_created_at=user_message.created_at,
            assistant_message_id=assistant_message.id,
            assistant_content=assistant_message.content,
            assistant_created_at=assistant_message.created_at,
        )
    await db.refresh(session)
    return session, [user_message, assistant_message]


async def remember_chat_message(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    message_id: str,
) -> tuple[ChatMessage, bool]:
    if not settings.MEMORY_AGENT_ENABLED:
        raise BusinessException(
            message="memory agent is disabled",
            code=5034,
            status_code=503,
        )
    session = await require_owned_chat_session(
        db,
        current_user=current_user,
        session_id=session_id,
    )
    message = await db.scalar(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.session_id == session.id,
            ChatMessage.user_id == current_user.id,
            ChatMessage.knowledge_base_id == session.knowledge_base_id,
        )
    )
    if message is None:
        raise BusinessException(message="chat message not found", code=4051, status_code=404)
    if message.role != "user":
        raise BusinessException(
            message="only user messages can be remembered",
            code=4052,
            status_code=400,
        )
    event = await enqueue_user_memory_requested(
        db,
        owner_id=current_user.id,
        knowledge_base_id=session.knowledge_base_id,
        session_id=session.id,
        message_id=message.id,
        excerpt=message.content,
        message_created_at=message.created_at,
    )
    return message, event is not None
