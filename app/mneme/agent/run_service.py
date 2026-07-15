import asyncio
import time
import uuid
from datetime import datetime, timezone

from app.mneme.agent.events import AgentEvent, AgentEventType
from app.mneme.agent.run_models import TERMINAL_AGENT_RUN_STATUSES, AgentRunRecord, AgentRunStatus
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_write_session
from app.mneme.crud.user import get_user_by_id
from app.mneme.domains.chat.service import stream_in_chat_session
from app.mneme.infra.agent_runs import agent_run_store


async def execute_agent_run(run_id: str) -> None:
    record = await agent_run_store.get(run_id)
    if record is None or record.status in TERMINAL_AGENT_RUN_STATUSES:
        return

    lease_token = f"lease_{uuid.uuid4().hex}"
    claimed = await _wait_for_session_turn(record, lease_token)
    if not claimed:
        return

    if await agent_run_store.is_abort_requested(run_id):
        await _mark_aborted(record, loop_reason="abort_before_start")
        await agent_run_store.release_session_turn(
            session_id=record.session_id,
            run_id=record.run_id,
            lease_token=lease_token,
        )
        return

    record.status = AgentRunStatus.RUNNING
    record.started_at = datetime.now(timezone.utc)
    await agent_run_store.save(record)
    abort_signal = asyncio.Event()
    lease_lost = asyncio.Event()
    owner_task = asyncio.current_task()
    if owner_task is None:
        raise RuntimeError("agent run has no owning asyncio task")
    abort_monitor = asyncio.create_task(_monitor_abort(run_id, abort_signal))
    lease_monitor = asyncio.create_task(
        _monitor_session_lease(
            record.session_id,
            lease_token,
            abort_signal,
            lease_lost,
            owner_task,
        )
    )
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
                agent_run_id=record.run_id,
                session_turn_claimed=True,
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
    except asyncio.CancelledError:
        if not lease_lost.is_set():
            raise
        final_status = AgentRunStatus.FAILED
        record.error = "agent run lost its session lease"
        await agent_run_store.append_event(
            run_id,
            AgentEvent.error_event(
                "Agent run lost its session lease.",
                error_type="SessionLeaseLost",
                loop_index=0,
                loop_reason="session_lease_lost",
            ),
        )
        await agent_run_store.append_event(
            run_id,
            AgentEvent.lifecycle(
                "error",
                reason="session_lease_lost",
                loop_index=0,
                loop_reason="session_lease_lost",
            ),
        )
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
        lease_monitor.cancel()
        await asyncio.gather(abort_monitor, lease_monitor, return_exceptions=True)
        await agent_run_store.release_session_turn(
            session_id=record.session_id,
            run_id=record.run_id,
            lease_token=lease_token,
        )
        latest = await agent_run_store.get(run_id)
        if latest:
            latest.status = final_status or AgentRunStatus.FAILED
            latest.error = record.error
            latest.completed_at = datetime.now(timezone.utc)
            await agent_run_store.save(latest)


async def _wait_for_session_turn(record: AgentRunRecord, lease_token: str) -> bool:
    wait_started = time.monotonic()
    while True:
        if await agent_run_store.is_abort_requested(record.run_id):
            latest = await agent_run_store.get(record.run_id)
            if latest and latest.started_at is not None:
                return False
            record = latest or record
            await _mark_aborted(record, loop_reason="abort_while_queued")
            await agent_run_store.remove_from_session_queue(
                session_id=record.session_id,
                run_id=record.run_id,
            )
            return False
        claimed = await agent_run_store.claim_session_turn(
            session_id=record.session_id,
            run_id=record.run_id,
            lease_token=lease_token,
        )
        if claimed:
            record.queue_wait_ms = int((time.monotonic() - wait_started) * 1000)
            return True
        latest = await agent_run_store.get(record.run_id)
        if latest is None or latest.status in TERMINAL_AGENT_RUN_STATUSES:
            await agent_run_store.remove_from_session_queue(
                session_id=record.session_id,
                run_id=record.run_id,
            )
            return False
        await asyncio.sleep(settings.AGENT_RUN_POLL_INTERVAL_SECONDS)


async def _mark_aborted(record: AgentRunRecord, *, loop_reason: str) -> None:
    record.status = AgentRunStatus.ABORTED
    record.completed_at = datetime.now(timezone.utc)
    await agent_run_store.save(record)
    await agent_run_store.append_event(
        record.run_id,
        AgentEvent.lifecycle("aborted", loop_index=0, loop_reason=loop_reason),
    )


async def _monitor_abort(run_id: str, abort_signal: asyncio.Event) -> None:
    while not abort_signal.is_set():
        if await agent_run_store.is_abort_requested(run_id):
            abort_signal.set()
            return
        await asyncio.sleep(settings.AGENT_RUN_POLL_INTERVAL_SECONDS)


async def _monitor_session_lease(
    session_id: str,
    lease_token: str,
    abort_signal: asyncio.Event,
    lease_lost: asyncio.Event,
    owner_task: asyncio.Task,
) -> None:
    while not abort_signal.is_set():
        await asyncio.sleep(settings.AGENT_SESSION_LEASE_RENEW_SECONDS)
        try:
            renewed = await agent_run_store.renew_session_lease(
                session_id=session_id,
                lease_token=lease_token,
            )
        except Exception:
            renewed = False
        if not renewed:
            lease_lost.set()
            abort_signal.set()
            owner_task.cancel()
            return
