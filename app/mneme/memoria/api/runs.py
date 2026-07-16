import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.config import settings
from app.mneme.conf.database import get_database, get_write_database
from app.mneme.domains.chat.service import require_owned_chat_session
from app.mneme.memoria.events import AgentEvent
from app.mneme.memoria.persistence.automation import durable_run_to_record, get_durable_run, save_durable_run
from app.mneme.memoria.persistence.runs import agent_run_store
from app.mneme.memoria.run_models import TERMINAL_AGENT_RUN_STATUSES, AgentRunRecord, AgentRunStatus
from app.mneme.memoria.run_submission import submit_agent_run
from app.mneme.models.user import User
from app.mneme.schemas.chat_session import ChatSessionMessageRequest
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
    if record.status not in TERMINAL_AGENT_RUN_STATUSES:
        was_queued = record.started_at is None
        transitioned = await agent_run_store.transition_to_aborting(run_id)
        record = transitioned or record.model_copy(update={"status": AgentRunStatus.ABORTING})
        if was_queued:
            record.status = AgentRunStatus.ABORTED
            record.completed_at = datetime.now(timezone.utc)
            await agent_run_store.save(record)
            await agent_run_store.remove_from_session_queue(session_id=record.session_id, run_id=record.run_id)
            await agent_run_store.append_event(
                record.run_id,
                AgentEvent.lifecycle("aborted", loop_index=0, loop_reason="abort_while_queued"),
            )
            record = await agent_run_store.get(record.run_id) or record
        await save_durable_run(db, record)
    return success_response(data=record, message="agent run abort requested")


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

    async def event_stream():
        active_cursor = starting_cursor
        while True:
            events = await agent_run_store.list_events(run_id, after_id=active_cursor)
            for stored in events:
                active_cursor = stored.event_id
                event = stored.event
                data = json.dumps(event.to_stream_dict(), ensure_ascii=False)
                yield f"id: {stored.event_id}\nevent: {event.type.value}\ndata: {data}\n\n"
            record = await agent_run_store.get(run_id)
            if record is None or (record.status in TERMINAL_AGENT_RUN_STATUSES and not events):
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
