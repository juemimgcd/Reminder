import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.adapters import build_mneme_agent
from app.mneme.agent.contracts import AgentRequest, AnswerMode
from app.mneme.agent.router import route_answer_mode
from app.mneme.clients.memory_agent_client import MemoryAgentClient, MemoryAgentRejected, MemoryAgentUnavailable
from app.mneme.conf.config import settings
from app.mneme.crud.ai_model_config import get_ai_model_config, get_default_ai_model_config
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
from app.mneme.domains.settings.ai_models import ai_model_config_runtime_kwargs, decrypt_api_key
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
from app.mneme.schemas.memory_agent import (
    MemoryAgentAnswerRequest,
    MemoryAgentAnswerResponse,
    ModelInvocationConfig,
)
from app.mneme.utils.exceptions import BusinessException


def build_chat_session_id() -> str:
    return f"chat_{uuid.uuid4().hex[:16]}"


def build_chat_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:16]}"


def build_chat_answer_message_id(user_message_id: str) -> str:
    return f"answer_{user_message_id}"


_EXPECTED_SCOPE_UNSET = object()


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
    knowledge_base_id: str | None,
    title: str | None,
    answer_mode: AnswerMode = "kb_qa",
) -> ChatSession:
    if answer_mode != "general_chat" and knowledge_base_id is None:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)
    if knowledge_base_id is None and not settings.MEMORY_AGENT_ENABLED:
        raise BusinessException(message="general chat requires memory agent", code=5034, status_code=503)
    knowledge_base = (
        await require_owned_knowledge_base(db, current_user=current_user, knowledge_base_id=knowledge_base_id)
        if knowledge_base_id is not None
        else None
    )
    return await insert_chat_session(
        db,
        session_id=build_chat_session_id(),
        user_id=current_user.id,
        knowledge_base_id=knowledge_base.id if knowledge_base else None,
        knowledge_base_pk=knowledge_base.pk if knowledge_base else None,
        title=title,
        answer_mode=answer_mode,
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
    answer_mode: AnswerMode | None = None,
) -> ChatSession:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if title is not None:
        session.title = title
    if archived is not None:
        session.archived_at = datetime.now(timezone.utc) if archived else None
    if answer_mode is not None:
        if answer_mode != "general_chat" and session.knowledge_base_id is None:
            raise BusinessException(message="knowledge base is required for this answer mode", code=4053)
        session.answer_mode = answer_mode
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
    if settings.MEMORY_AGENT_ENABLED:
        message_ids = list(
            await db.scalars(
                select(ChatMessage.id)
                .where(
                    ChatMessage.session_id == session.id,
                    ChatMessage.user_id == current_user.id,
                )
                .order_by(ChatMessage.id)
            )
        )
        await enqueue_conversation_deleted(
            db,
            owner_id=current_user.id,
            knowledge_base_id=session.knowledge_base_id,
            session_id=session.id,
            message_ids=message_ids,
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
        agent_run_id=message.agent_run_id,
        created_at=message.created_at,
    )


async def _resolve_model_config(db: AsyncSession, *, user_id: int, config_id: str | None):
    if config_id is not None:
        config = await get_ai_model_config(db, config_id=config_id, user_id=user_id)
        if config is None or not config.enabled:
            raise BusinessException(message="AI model config not found", code=4061, status_code=404)
        return config
    return await get_default_ai_model_config(db, user_id=user_id)


def _model_invocation_config(model_config) -> ModelInvocationConfig | None:
    if model_config is None:
        return None
    return ModelInvocationConfig(
        provider=model_config.provider,
        base_url=model_config.base_url,
        model_name=model_config.model_name,
        api_key=decrypt_api_key(model_config.api_key_ciphertext),
        temperature=model_config.temperature,
    )


async def answer_via_memory_agent(
    *,
    owner_id: int,
    question: str,
    answer_mode: AnswerMode,
    top_k: int,
    knowledge_base_id: str | None,
    session_id: str | None,
    message_id: str,
    model_config=None,
) -> MemoryAgentAnswerResponse:
    if answer_mode != "general_chat" and knowledge_base_id is None:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)
    request = MemoryAgentAnswerRequest(
        request_id=f"answer_{message_id}",
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        session_id=session_id,
        message_id=message_id,
        question=question,
        answer_mode=answer_mode,
        top_k=top_k,
        model=_model_invocation_config(model_config),
    )
    async with MemoryAgentClient() as client:
        return await client.create_answer(request)


def memory_agent_answer_to_chat_result(response: MemoryAgentAnswerResponse) -> dict:
    confidence = "high" if response.confidence >= 0.75 else "medium" if response.confidence >= 0.4 else "low"
    route = route_answer_mode(response.mode).model_dump()
    route["confidence"] = confidence
    route["reason"] = "user-selected answer mode"
    citations = []
    sources = []
    for item in response.citations:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        source_type = item.get("source_type") if isinstance(item.get("source_type"), str) else None
        source_id = item.get("source_id") if isinstance(item.get("source_id"), str) else ""
        evidence_id = item.get("evidence_id") if isinstance(item.get("evidence_id"), str) else None
        quote = item.get("quote") if isinstance(item.get("quote"), str) else ""
        document_id = metadata.get("document_id") if isinstance(metadata.get("document_id"), str) else None
        chunk_id = source_id if source_type == "document" else None
        citations.append(
            {
                "source_id": source_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "page_no": metadata.get("page_no"),
                "quote": quote,
                "reason": "memory agent evidence",
                "source_type": source_type,
                "evidence_id": evidence_id,
                "validation_status": "valid",
            }
        )
        sources.append(
            {
                "source_id": source_id,
                "knowledge_base_id": None,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "page_no": metadata.get("page_no"),
                "text": quote,
                "source_type": source_type,
                "evidence_id": evidence_id,
            }
        )
    return {
        "answer": response.answer,
        "sources": sources,
        "citations": citations,
        "confidence": confidence,
        "uncertainty": response.uncertainty,
        "route": route,
        "debug": None,
    }


async def ask_in_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    question: str,
    top_k: int,
    answer_mode: AnswerMode | None = None,
    expected_knowledge_base_id: str | None | object = _EXPECTED_SCOPE_UNSET,
    model_config_id: str | None = None,
    retry_message_id: str | None = None,
) -> tuple[ChatSession, list[ChatMessage]]:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if (
        expected_knowledge_base_id is not _EXPECTED_SCOPE_UNSET
        and session.knowledge_base_id != expected_knowledge_base_id
    ):
        raise BusinessException(
            message="chat session does not belong to this knowledge base",
            code=4050,
            status_code=400,
        )
    if session.archived_at is not None:
        raise BusinessException(message="chat session is archived", code=4049, status_code=400)

    selected_mode: AnswerMode = answer_mode or session.answer_mode
    if selected_mode != "general_chat" and session.knowledge_base_id is None:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)

    if not settings.MEMORY_AGENT_ENABLED:
        model_config = await _resolve_model_config(db, user_id=current_user.id, config_id=model_config_id)
        llm_config = ai_model_config_runtime_kwargs(model_config) if model_config else None
        agent_response = await build_mneme_agent(db).run(
            AgentRequest(
                question=question,
                knowledge_base_id=session.knowledge_base_id,
                user_id=current_user.id,
                top_k=top_k,
                answer_mode=selected_mode,
                llm_config=llm_config,
            )
        )
        result = agent_response.to_legacy_result()
        if answer_mode is not None:
            session.answer_mode = answer_mode
        return await _persist_legacy_answer(
            db,
            session=session,
            current_user=current_user,
            question=question,
            result=result,
            model_config=model_config,
        )

    model_config = await _resolve_model_config(db, user_id=current_user.id, config_id=model_config_id)

    if retry_message_id is not None:
        user_message = await db.scalar(
            select(ChatMessage).where(
                ChatMessage.id == retry_message_id,
                ChatMessage.session_id == session.id,
                ChatMessage.user_id == current_user.id,
                ChatMessage.role == "user",
            )
        )
        if user_message is None or user_message.knowledge_base_id != session.knowledge_base_id:
            raise BusinessException(message="retry message not found", code=4054, status_code=404)
        if user_message.content != question:
            raise BusinessException(message="retry question does not match saved message", code=4055)
        existing_answer = await db.scalar(
            select(ChatMessage.id).where(
                ChatMessage.id == build_chat_answer_message_id(user_message.id),
                ChatMessage.session_id == session.id,
                ChatMessage.user_id == current_user.id,
                ChatMessage.role == "assistant",
                ChatMessage.agent_run_id.is_not(None),
            )
        )
        if existing_answer is not None:
            raise BusinessException(message="message already has an agent answer", code=4056, status_code=409)
    else:
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
        if not session.title:
            session.title = question[:80]
        session.message_count = (session.message_count or 0) + 1
        session.last_message_at = datetime.now(timezone.utc)
    if answer_mode is not None:
        session.answer_mode = answer_mode
    await db.commit()

    try:
        agent_response = await answer_via_memory_agent(
            owner_id=current_user.id,
            question=question,
            answer_mode=selected_mode,
            top_k=top_k,
            knowledge_base_id=session.knowledge_base_id,
            session_id=session.id,
            message_id=user_message.id,
            model_config=model_config,
        )
    except MemoryAgentRejected as exc:
        raise BusinessException(
            message="memory agent rejected the saved message",
            code=exc.code,
            status_code=exc.status_code,
            data={"message_id": user_message.id, "retryable": False},
        ) from exc
    except MemoryAgentUnavailable as exc:
        raise BusinessException(
            message="memory agent answer failed; retry the saved message",
            code=5035,
            status_code=503,
            data={"message_id": user_message.id, "retryable": True, "agent_code": exc.agent_code},
        ) from exc

    result = memory_agent_answer_to_chat_result(agent_response)
    assistant_message = await create_chat_message(
        db,
        message_id=build_chat_answer_message_id(user_message.id),
        session_id=session.id,
        user_id=current_user.id,
        knowledge_base_id=session.knowledge_base_id,
        knowledge_base_pk=session.knowledge_base_pk,
        role="assistant",
        content=result["answer"],
        sources_json=result["sources"],
        citations_json=result["citations"],
        route_json=result["route"],
        model_config_id=model_config.id if model_config else None,
        agent_run_id=agent_response.run_id,
    )
    session.message_count = (session.message_count or 0) + 1
    session.last_message_at = datetime.now(timezone.utc)
    await db.flush()
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


async def _persist_legacy_answer(
    db: AsyncSession,
    *,
    session: ChatSession,
    current_user: User,
    question: str,
    result: dict,
    model_config,
) -> tuple[ChatSession, list[ChatMessage]]:
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
