import asyncio
from datetime import datetime, timezone

from app.mneme.agent.events import AgentEvent, AgentEventType
from app.mneme.agent.run_models import TERMINAL_AGENT_RUN_STATUSES, AgentRunStatus
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.crud.user import get_user_by_id
from app.mneme.domains.chat.service import stream_in_chat_session
from app.mneme.infra.agent_runs import agent_run_store


async def execute_agent_run(run_id: str) -> None:
    record = await agent_run_store.get(run_id)
    if record is None or record.status in TERMINAL_AGENT_RUN_STATUSES:
        return
    if await agent_run_store.is_abort_requested(run_id):
        record.status = AgentRunStatus.ABORTED
        record.completed_at = datetime.now(timezone.utc)
        await agent_run_store.save(record)
        await agent_run_store.append_event(
            run_id,
            AgentEvent.lifecycle("aborted", loop_index=0, loop_reason="abort_before_start"),
        )
        return

    record.status = AgentRunStatus.RUNNING
    record.started_at = datetime.now(timezone.utc)
    await agent_run_store.save(record)
    abort_signal = asyncio.Event()
    abort_monitor = asyncio.create_task(_monitor_abort(run_id, abort_signal))
    final_status: AgentRunStatus | None = None
    try:
        async with open_write_session() as db:
            current_user = await get_user_by_id(db, user_id=record.user_id)
            if current_user is None:
                raise RuntimeError("agent run user no longer exists")
            async for event in stream_in_chat_session(
                db,
                current_user=current_user,
                session_id=record.session_id,
                question=record.question,
                top_k=record.top_k,
                answer_mode=record.answer_mode,
                abort_signal=abort_signal,
            ):
                await agent_run_store.append_event(run_id, event)
                if event.type == AgentEventType.LIFECYCLE:
                    final_status = {
                        "end": AgentRunStatus.COMPLETED,
                        "error": AgentRunStatus.FAILED,
                        "aborted": AgentRunStatus.ABORTED,
                    }.get(event.phase, final_status)
        if final_status is None:
            final_status = AgentRunStatus.FAILED
            record.error = "agent run ended without a terminal event"
    except Exception as exc:
        final_status = AgentRunStatus.FAILED
        record.error = str(exc)
        await agent_run_store.append_event(
            run_id,
            AgentEvent.error_event(
                "Agent run failed.",
                error_type=type(exc).__name__,
                loop_index=0,
                loop_reason="background_execution_error",
            ),
        )
        await agent_run_store.append_event(
            run_id,
            AgentEvent.lifecycle(
                "error",
                reason="background_execution_error",
                loop_index=0,
                loop_reason="background_execution_error",
            ),
        )
    finally:
        abort_monitor.cancel()
        await asyncio.gather(abort_monitor, return_exceptions=True)
        latest = await agent_run_store.get(run_id)
        if latest:
            latest.status = final_status or AgentRunStatus.FAILED
            latest.error = record.error
            latest.completed_at = datetime.now(timezone.utc)
            await agent_run_store.save(latest)


async def _monitor_abort(run_id: str, abort_signal: asyncio.Event) -> None:
    while not abort_signal.is_set():
        if await agent_run_store.is_abort_requested(run_id):
            abort_signal.set()
            return
        await asyncio.sleep(settings.AGENT_RUN_POLL_INTERVAL_SECONDS)
