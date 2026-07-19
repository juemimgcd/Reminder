import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.conf.database import get_database, get_write_database
from app.mneme.domains.chat.service import require_owned_chat_session
from app.mneme.memoria.events import AgentEvent, AgentRunEventType
from app.mneme.memoria.persistence.automation import durable_run_to_record, get_durable_run, save_durable_run
from app.mneme.memoria.persistence.runs import agent_run_store
from app.mneme.memoria.persistence.runtime_events import parse_event_sequence
from app.mneme.memoria.run_models import TERMINAL_AGENT_RUN_STATUSES, AgentRunRecord, AgentRunStatus
from app.mneme.memoria.run_submission import submit_agent_run
from app.mneme.models.user import User
from app.mneme.schemas.chat_session import AgentRunControlRequest, ChatSessionMessageRequest
from app.mneme.utils.auth import get_current_user
from app.mneme.utils.exceptions import BusinessException
from app.mneme.utils.response import success_response

router = APIRouter(tags=["chat"])


@router.post("/kb/chat/sessions/{session_id}/runs")
async def create_agent_run_api(
    session_id: str,
    payload: ChatSessionMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    session = await require_owned_chat_session(db, current_user=current_user, session_id=session_id)
    if session.archived_at is not None:
        raise BusinessException(message="chat session is archived", code=4049, status_code=400)
    record = AgentRunRecord.create(
        run_id=f"run_{uuid.uuid4().hex}",
        session_id=session_id,
        user_id=current_user.id,
        client_request_id=payload.client_request_id or f"request_{uuid.uuid4().hex}",
        question=payload.question,
        top_k=payload.top_k,
        answer_mode=payload.answer_mode or session.answer_mode,
        execution_mode=payload.execution_mode or (
            "multi" if session.multi_agent_enabled else "single"
        ),
        max_attempts=settings.AGENT_RUN_MAX_ATTEMPTS,
    )
    record, created = await submit_agent_run(db, record)
    return success_response(
        data=record,
        message="agent run queued" if created else "existing agent run returned",
    )


@router.get("/kb/chat/runs/{run_id}")
async def get_agent_run_api(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    record = await _require_owned_run(run_id, current_user.id, db=db)
    return success_response(data=record)


@router.post("/kb/chat/runs/{run_id}/abort")
async def abort_agent_run_api(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    record = await _require_owned_run(run_id, current_user.id, db=db)
    record = await _request_run_abort(record, db=db)
    return success_response(data=record, message="agent run abort requested")


@router.post("/kb/chat/runs/{run_id}/control")
async def control_agent_run_api(
    run_id: str,
    payload: AgentRunControlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_write_database),
):
    target = await _require_owned_run(run_id, current_user.id, db=db)
    if payload.mode == "interrupt":
        target = await _request_run_abort(target, db=db)
        await agent_run_store.append_event(
            target.run_id,
            AgentEvent.rag_progress(
                AgentRunEventType.RUN_CONTROL_ACCEPTED,
                phase="control",
                run_id=target.run_id,
                control_mode=payload.mode,
                behavior="interrupt",
            ),
        )
        return success_response(
            data={
                "mode": payload.mode,
                "behavior": "interrupt",
                "target_run": target,
                "scheduled_run": None,
            },
            message="agent run interrupt requested",
        )

    session = await require_owned_chat_session(
        db,
        current_user=current_user,
        session_id=target.session_id,
    )
    if session.archived_at is not None:
        raise BusinessException(message="chat session is archived", code=4049, status_code=400)

    behavior = "queue_after_current"
    if payload.mode == "steer":
        target = await _request_run_abort(target, db=db)
        behavior = "restart_with_updated_direction"

    scheduled = _build_controlled_run(
        target,
        payload,
        default_execution_mode=("multi" if session.multi_agent_enabled else "single"),
        user_id=current_user.id,
    )
    scheduled, created = await submit_agent_run(db, scheduled)
    await agent_run_store.append_event(
        target.run_id,
        AgentEvent.rag_progress(
            AgentRunEventType.RUN_CONTROL_ACCEPTED,
            phase="control",
            run_id=target.run_id,
            control_mode=payload.mode,
            behavior=behavior,
            scheduled_run_id=scheduled.run_id,
            scheduled_trace_id=scheduled.trace_id,
        ),
    )
    return success_response(
        data={
            "mode": payload.mode,
            "behavior": behavior,
            "target_run": target,
            "scheduled_run": scheduled,
        },
        message=(
            "agent run control scheduled"
            if created
            else "existing controlled run returned"
        ),
    )


@router.get("/kb/chat/runs/{run_id}/stream")
async def stream_agent_run_api(
    run_id: str,
    cursor: str | None = Query(default=None),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    await _require_owned_run(run_id, current_user.id, db=db)
    starting_cursor = last_event_id or cursor
    try:
        parse_event_sequence(starting_cursor)
    except ValueError as exc:
        raise BusinessException(
            message=str(exc),
            code=4053,
            status_code=400,
        ) from exc

    async def event_stream():
        active_cursor = starting_cursor
        while True:
            events = await agent_run_store.list_events(run_id, after_id=active_cursor)
            for stored in events:
                active_cursor = stored.event_id
                event = stored.event
                data = json.dumps(event.to_stream_dict(), ensure_ascii=False)
                yield f"id: {stored.event_id}\nevent: {event.name.value}\ndata: {data}\n\n"
            record = await agent_run_store.get(run_id)
            if record is None:
                durable = await get_durable_run(db, run_id=run_id)
                record = durable_run_to_record(durable) if durable else None
            if record is None or (
                record.status in TERMINAL_AGENT_RUN_STATUSES and not events
            ):
                break
            await asyncio.sleep(settings.AGENT_RUN_POLL_INTERVAL_SECONDS)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _require_owned_run(run_id: str, user_id: int, *, db: AsyncSession) -> AgentRunRecord:
    record = await agent_run_store.get(run_id)
    if record is None:
        durable = await get_durable_run(db, run_id=run_id)
        if durable is None:
            raise BusinessException(message="agent run not found", code=4051, status_code=404)
        record = durable_run_to_record(durable)
    if record.user_id != user_id:
        raise BusinessException(message="agent run does not belong to current user", code=4052, status_code=403)
    return record


async def _request_run_abort(
    record: AgentRunRecord,
    *,
    db: AsyncSession,
) -> AgentRunRecord:
    if record.status in TERMINAL_AGENT_RUN_STATUSES:
        return record
    was_queued = record.started_at is None
    transitioned = await agent_run_store.transition_to_aborting(record.run_id)
    record = transitioned or record.model_copy(update={"status": AgentRunStatus.ABORTING})
    if was_queued:
        record.status = AgentRunStatus.ABORTED
        record.completed_at = datetime.now(timezone.utc)
        await agent_run_store.save(record)
        await agent_run_store.remove_from_session_queue(
            session_id=record.session_id,
            run_id=record.run_id,
        )
        await agent_run_store.append_event(
            record.run_id,
            AgentEvent.rag_progress(
                AgentRunEventType.RUN_CANCELLED,
                phase="cancelled",
                run_id=record.run_id,
                loop_index=0,
                loop_reason="abort_while_queued",
            ),
        )
        record = await agent_run_store.get(record.run_id) or record
    await save_durable_run(db, record)
    return record


def _build_controlled_run(
    target: AgentRunRecord,
    payload: AgentRunControlRequest,
    *,
    default_execution_mode: Literal["single", "multi"],
    user_id: int,
) -> AgentRunRecord:
    question = payload.question
    if question is None:
        raise ValueError("controlled run requires a question")
    return AgentRunRecord.create(
        run_id=f"run_{uuid.uuid4().hex}",
        session_id=target.session_id,
        user_id=user_id,
        client_request_id=payload.client_request_id or f"request_{uuid.uuid4().hex}",
        question=question,
        top_k=payload.top_k or target.top_k,
        answer_mode=payload.answer_mode or target.answer_mode,
        execution_mode=payload.execution_mode or target.execution_mode or default_execution_mode,
        trigger_type=payload.mode,
        trigger_id=target.run_id,
        max_attempts=settings.AGENT_RUN_MAX_ATTEMPTS,
    )
