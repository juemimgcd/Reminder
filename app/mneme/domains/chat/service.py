import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.adapters import build_mneme_agent
from app.mneme.agent.context_manager import (
    HistoryBudgetResult,
    apply_history_budget,
    merge_history_summaries,
)
from app.mneme.agent.contracts import AgentRequest, AgentResponse, AnswerMode
from app.mneme.agent.events import AgentEvent
from app.mneme.agent.history import build_agent_history
from app.mneme.agent.prompt_builder import build_agent_system_prompt
from app.mneme.conf.config import settings
from app.mneme.crud.ai_model_config import get_default_ai_model_config
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
from app.mneme.domains.settings.ai_models import ai_model_config_runtime_kwargs
from app.mneme.infra.agent_runs import agent_run_store
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
    await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
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
        agent_run_id=message.agent_run_id,
        sequence_no=message.sequence_no,
        sources=sources,
        citations=citations,
        tool_calls=message.tool_calls_json or [],
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

    async with _chat_session_turn(session.id):
        await db.refresh(session)
        if session.archived_at is not None:
            raise BusinessException(message="chat session is archived", code=4049, status_code=400)
        model_config, agent_request = await build_chat_agent_request(
            db,
            current_user=current_user,
            session=session,
            question=question,
            top_k=top_k,
            answer_mode=answer_mode,
        )
        agent_response = await build_mneme_agent(db).run(agent_request)
        messages = await persist_chat_exchange(
            db,
            current_user=current_user,
            session=session,
            question=question,
            response=agent_response,
            model_config=model_config,
        )
        await db.commit()
        return session, messages


async def build_chat_agent_request(
    db: AsyncSession,
    *,
    current_user: User,
    session: ChatSession,
    question: str,
    top_k: int,
    answer_mode: AnswerMode,
) -> tuple[Any, AgentRequest]:
    model_config = await get_default_ai_model_config(db, user_id=current_user.id)
    llm_config = ai_model_config_runtime_kwargs(model_config) if model_config else None
    persisted_messages = await list_chat_messages(db, session_id=session.id, user_id=current_user.id)
    persisted_messages = _messages_after_summary_watermark(
        persisted_messages,
        session.context_summary_through_message_id,
    )
    history = build_agent_history(persisted_messages)
    system_prompt = build_agent_system_prompt(answer_mode=answer_mode)
    context_window = int((llm_config or {}).get("context_window") or 64_000)
    history_budget = apply_history_budget(
        history,
        context_window_tokens=context_window,
        output_reserve_tokens=settings.AGENT_OUTPUT_RESERVE_TOKENS,
        system_chars=len(system_prompt) + len(session.context_summary or ""),
        current_question_chars=len(question),
        max_turns=settings.AGENT_HISTORY_MAX_TURNS,
        summary_max_chars=settings.AGENT_SUMMARY_MAX_CHARS,
        chars_per_token=settings.AGENT_CHARS_PER_TOKEN,
        tool_result_soft_chars=settings.AGENT_TOOL_RESULT_SOFT_CHARS,
    )
    history_summary = merge_history_summaries(
        session.context_summary or "",
        history_budget.summary,
        settings.AGENT_SUMMARY_MAX_CHARS,
    )
    if history_budget.summary_through_message_id:
        session.context_summary = history_summary
        session.context_summary_through_message_id = history_budget.summary_through_message_id
        await db.flush()
    return model_config, AgentRequest(
        question=question,
        knowledge_base_id=session.knowledge_base_id,
        user_id=current_user.id,
        session_id=session.id,
        top_k=top_k,
        answer_mode=answer_mode,
        llm_config=llm_config,
        history=history_budget.messages,
        history_summary=history_summary,
        history_compaction=(
            _history_compaction_metadata(history_budget)
            if history_budget.was_compacted
            else None
        ),
        history_prepared=True,
    )


def _messages_after_summary_watermark(
    messages: list[ChatMessage],
    watermark_message_id: str | None,
) -> list[ChatMessage]:
    if not watermark_message_id:
        return messages
    for index, message in enumerate(messages):
        if message.id == watermark_message_id:
            return messages[index + 1 :]
    return messages


def _history_compaction_metadata(history_budget: HistoryBudgetResult) -> dict[str, Any]:
    return {
        "reason": history_budget.reason,
        "original_count": history_budget.original_count,
        "kept_count": history_budget.kept_count,
        "original_chars": history_budget.original_chars,
        "kept_chars": history_budget.kept_chars,
        "estimated_tokens_before": history_budget.estimated_tokens_before,
        "estimated_tokens_after": history_budget.estimated_tokens_after,
        "tool_payloads_trimmed": history_budget.tool_payloads_trimmed,
        "summary_through_message_id": history_budget.summary_through_message_id,
    }


async def persist_chat_exchange(
    db: AsyncSession,
    *,
    current_user: User,
    session: ChatSession,
    question: str,
    response: AgentResponse,
    model_config: Any,
    agent_run_id: str | None = None,
) -> list[ChatMessage]:
    if agent_run_id:
        existing = await list_chat_messages_by_agent_run_id(
            db,
            agent_run_id=agent_run_id,
            user_id=current_user.id,
        )
        if existing:
            return existing
    result = response.to_legacy_result()
    now = datetime.now(timezone.utc)
    next_sequence = (session.message_count or 0) + 1
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
    assistant_message = await create_chat_message(
        db,
        message_id=build_chat_message_id(),
        session_id=session.id,
        user_id=current_user.id,
        knowledge_base_id=session.knowledge_base_id,
        knowledge_base_pk=session.knowledge_base_pk,
        role="assistant",
        content=result["answer"],
        agent_run_id=agent_run_id,
        sequence_no=next_sequence + 1,
        sources_json=result.get("sources") or [],
        citations_json=result.get("citations") or [],
        tool_calls_json=response.tool_calls,
        route_json=result.get("route"),
        model_config_id=model_config.id if model_config else None,
    )
    if not session.title:
        session.title = question[:80]
    session.message_count = (session.message_count or 0) + 2
    session.last_message_at = now
    await db.flush()
    await db.refresh(session)
    return [user_message, assistant_message]


async def stream_in_chat_session(
    db: AsyncSession,
    *,
    current_user: User,
    session_id: str,
    question: str,
    top_k: int,
    answer_mode: AnswerMode = "kb_qa",
    abort_signal: asyncio.Event | None = None,
    agent_run_id: str | None = None,
    session_turn_claimed: bool = False,
) -> AsyncIterator[AgentEvent]:
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if session.archived_at is not None:
        raise BusinessException(message="chat session is archived", code=4049, status_code=400)

    async with _chat_session_turn(
        session.id,
        abort_signal=abort_signal,
        already_claimed=session_turn_claimed,
    ):
        await db.refresh(session)
        if session.archived_at is not None:
            raise BusinessException(message="chat session is archived", code=4049, status_code=400)
        model_config, agent_request = await build_chat_agent_request(
            db,
            current_user=current_user,
            session=session,
            question=question,
            top_k=top_k,
            answer_mode=answer_mode,
        )
        agent = build_mneme_agent(db)
        persisted = False
        async for event in agent.stream(agent_request, abort_signal=abort_signal):
            response_payload = event.metadata.get("response")
            if response_payload and not persisted:
                response = AgentResponse.model_validate(response_payload)
                await persist_chat_exchange(
                    db,
                    current_user=current_user,
                    session=session,
                    question=question,
                    response=response,
                    model_config=model_config,
                    agent_run_id=agent_run_id,
                )
                await db.commit()
                persisted = True
            yield event


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
