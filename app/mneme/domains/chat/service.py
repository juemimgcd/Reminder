import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.contracts import AnswerMode
from app.mneme.agent.events import AgentEvent
from app.mneme.agent.router import route_answer_mode
from app.mneme.clients.memory_agent_client import MemoryAgentClient, MemoryAgentRejected, MemoryAgentUnavailable
from app.mneme.conf.config import settings
from app.mneme.crud.ai_model_config import get_ai_model_config, get_default_ai_model_config
from app.mneme.crud.chat_message import (
    create_chat_message,
    delete_chat_messages,
    list_chat_messages,
    list_chat_messages_by_agent_run_id,
)
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
from app.mneme.domains.settings.ai_models import decrypt_api_key
from app.mneme.domains.tasks.outbox import (
    enqueue_conversation_completed,
    enqueue_conversation_deleted,
    enqueue_user_memory_requested,
)
from app.mneme.infra.agent_runs import agent_run_store
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
    metadata = message.answer_metadata_json or {}
    return ChatMessageData(
        id=message.id,
        session_id=message.session_id,
        user_id=message.user_id,
        knowledge_base_id=message.knowledge_base_id,
        role=message.role,
        content=message.content,
        agent_run_id=message.agent_run_id,
        sequence_no=message.sequence_no,
        sources=sources,
        citations=citations,
        tool_calls=message.tool_calls_json or [],
        route=route,
        model_config_id=message.model_config_id,
        confidence=metadata.get("confidence"),
        uncertainty=metadata.get("uncertainty"),
        insufficient_evidence=bool(metadata.get("insufficient_evidence", False)),
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
        source_id = item.get("source_id") if isinstance(item.get("source_id"), str) else None
        evidence_id = item.get("evidence_id") if isinstance(item.get("evidence_id"), str) else None
        quote = item.get("quote") if isinstance(item.get("quote"), str) else ""
        document_id = metadata.get("document_id") if isinstance(metadata.get("document_id"), str) else None
        chunk_id = source_id if source_type == "document" else None
        source_time = metadata.get("source_time") or metadata.get("valid_from") or metadata.get("created_at")
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
                "source_time": source_time,
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
                "source_time": source_time,
            }
        )
    return {
        "answer": response.answer,
        "sources": sources,
        "citations": citations,
        "confidence": confidence,
        "uncertainty": response.uncertainty,
        "insufficient_evidence": response.insufficient_evidence,
        "confidence_numeric": response.confidence,
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
    regenerate_message_id: str | None = None,
    agent_run_id: str | None = None,
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

    existing_user_message: ChatMessage | None = None
    if agent_run_id:
        existing = await list_chat_messages_by_agent_run_id(
            db,
            agent_run_id=agent_run_id,
            user_id=current_user.id,
        )
        if any(message.role == "assistant" for message in existing):
            return session, existing
        existing_user_message = next((message for message in existing if message.role == "user"), None)

    selected_mode: AnswerMode = answer_mode or session.answer_mode
    if selected_mode != "general_chat" and session.knowledge_base_id is None:
        raise BusinessException(message="knowledge base is required for this answer mode", code=4053)

    model_config = await _resolve_model_config(db, user_id=current_user.id, config_id=model_config_id)
    next_sequence = (session.message_count or 0) + 1

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
    elif regenerate_message_id is not None:
        original = await db.scalar(
            select(ChatMessage).where(
                ChatMessage.id == regenerate_message_id,
                ChatMessage.session_id == session.id,
                ChatMessage.user_id == current_user.id,
                ChatMessage.role == "user",
            )
        )
        if original is None or original.knowledge_base_id != session.knowledge_base_id:
            raise BusinessException(message="regenerate message not found", code=4057, status_code=404)
        original_answer = await db.scalar(
            select(ChatMessage.id).where(
                ChatMessage.id == build_chat_answer_message_id(original.id),
                ChatMessage.session_id == session.id,
                ChatMessage.user_id == current_user.id,
                ChatMessage.role == "assistant",
            )
        )
        if original_answer is None:
            raise BusinessException(message="message has no answer to regenerate", code=4058, status_code=409)
        question = original.content
        user_message = await create_chat_message(
            db,
            message_id=build_chat_message_id(),
            session_id=session.id,
            user_id=current_user.id,
            knowledge_base_id=session.knowledge_base_id,
            knowledge_base_pk=session.knowledge_base_pk,
            role="user",
            content=question,
            agent_run_id=agent_run_id,
            sequence_no=next_sequence,
        )
        session.message_count = (session.message_count or 0) + 1
        session.last_message_at = datetime.now(timezone.utc)
    else:
        if existing_user_message is not None:
            user_message = existing_user_message
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
                agent_run_id=agent_run_id,
                sequence_no=next_sequence,
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
        agent_run_id=agent_run_id or agent_response.run_id,
        sequence_no=(user_message.sequence_no or next_sequence) + 1,
        answer_metadata_json={
            "confidence": result["confidence_numeric"],
            "uncertainty": result["uncertainty"],
            "insufficient_evidence": result["insufficient_evidence"],
        },
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


async def stream_in_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    question: str,
    top_k: int,
    answer_mode: AnswerMode | None = None,
    abort_signal: asyncio.Event | None = None,
    agent_run_id: str | None = None,
    session_turn_claimed: bool = False,
) -> AsyncIterator[AgentEvent]:
    if abort_signal is not None and abort_signal.is_set():
        yield AgentEvent.lifecycle("aborted", reason="abort_before_start")
        return
    yield AgentEvent.lifecycle("start")
    async with _chat_session_turn(
        session_id,
        abort_signal=abort_signal,
        already_claimed=session_turn_claimed,
    ):
        _session, messages = await ask_in_chat_session(
            db,
            current_user=current_user,
            session_id=session_id,
            question=question,
            top_k=top_k,
            answer_mode=answer_mode,
            agent_run_id=agent_run_id,
        )
    if abort_signal is not None and abort_signal.is_set():
        yield AgentEvent.lifecycle("aborted", reason="abort_after_answer")
        return
    yield AgentEvent.assistant_delta(messages[-1].content)
    yield AgentEvent.lifecycle("end")


@asynccontextmanager
async def _chat_session_turn(
    session_id: str,
    *,
    abort_signal: asyncio.Event | None = None,
    already_claimed: bool = False,
) -> AsyncIterator[None]:
    if already_claimed:
        yield
        return

    ticket_id = f"direct_{uuid.uuid4().hex}"
    lease_token = f"lease_{uuid.uuid4().hex}"
    await agent_run_store.enqueue_session_turn(session_id=session_id, ticket_id=ticket_id)
    claimed = False
    try:
        while not claimed:
            if abort_signal and abort_signal.is_set():
                raise asyncio.CancelledError
            claimed = await agent_run_store.claim_session_turn(
                session_id=session_id,
                run_id=ticket_id,
                lease_token=lease_token,
            )
            if not claimed:
                await asyncio.sleep(settings.AGENT_RUN_POLL_INTERVAL_SECONDS)
    except BaseException:
        if not claimed:
            await agent_run_store.remove_from_session_queue(
                session_id=session_id,
                run_id=ticket_id,
            )
        raise

    owner_task = asyncio.current_task()
    if owner_task is None:
        raise RuntimeError("chat request has no owning asyncio task")
    lease_monitor = asyncio.create_task(
        _renew_chat_session_lease(
            session_id,
            lease_token,
            abort_signal,
            owner_task,
        )
    )
    try:
        yield
    finally:
        lease_monitor.cancel()
        await asyncio.gather(lease_monitor, return_exceptions=True)
        await agent_run_store.release_session_turn(
            session_id=session_id,
            run_id=ticket_id,
            lease_token=lease_token,
        )


async def _renew_chat_session_lease(
    session_id: str,
    lease_token: str,
    abort_signal: asyncio.Event | None,
    owner_task: asyncio.Task,
) -> None:
    while True:
        await asyncio.sleep(settings.AGENT_SESSION_LEASE_RENEW_SECONDS)
        try:
            renewed = await agent_run_store.renew_session_lease(
                session_id=session_id,
                lease_token=lease_token,
            )
        except Exception:
            renewed = False
        if not renewed:
            if abort_signal:
                abort_signal.set()
            owner_task.cancel()
            return
async def remember_chat_message(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    message_id: str,
) -> tuple[ChatMessage, bool]:
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
