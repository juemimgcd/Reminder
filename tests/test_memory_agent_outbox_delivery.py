import asyncio
from types import SimpleNamespace

import pytest

from app.mneme.clients.memory_agent_client import MemoryAgentRetryable
from app.mneme.domains.tasks import outbox


def _event(status="pending", attempt_count=0, max_attempts=3):
    return SimpleNamespace(
        id="event-1", event_type="user.memory_requested", target_backend="memory_agent_http",
        status=status, attempt_count=attempt_count, max_attempts=max_attempts,
    )


def test_outbox_success_and_duplicate_receipt_are_idempotent(monkeypatch):
    event = _event()
    calls = []
    monkeypatch.setattr(outbox, "load_outbox_event_snapshot", lambda event_id: asyncio.sleep(0, result=event))
    monkeypatch.setattr(outbox, "mark_outbox_running", lambda event: asyncio.sleep(0, result=calls.append("running")))
    monkeypatch.setattr(outbox, "apply_outbox_event", lambda event: asyncio.sleep(0, result={"duplicate": True}))
    monkeypatch.setattr(
        outbox,
        "mark_outbox_succeeded",
        lambda event_id: asyncio.sleep(0, result=calls.append("succeeded")),
    )

    result = asyncio.run(outbox.process_outbox_event_by_id(event_id="event-1"))
    assert result["status"] == outbox.OUTBOX_SUCCEEDED
    assert calls == ["running", "succeeded"]

    event.status = outbox.OUTBOX_SUCCEEDED
    skipped = asyncio.run(outbox.process_outbox_event_by_id(event_id="event-1"))
    assert skipped["skipped"] is True


@pytest.mark.parametrize(
    "exc,attempt,status",
    [
        (MemoryAgentRetryable("retry"), 1, "failed"),
        (MemoryAgentRetryable("retry"), 3, "dead_letter"),
        (RuntimeError("bad request"), 1, "dead_letter"),
    ],
)
def test_outbox_retryable_and_permanent_failures_have_distinct_lifecycle(monkeypatch, exc, attempt, status):
    event = _event(attempt_count=attempt - 1, max_attempts=3)
    captured = {}
    monkeypatch.setattr(outbox, "load_outbox_event_snapshot", lambda event_id: asyncio.sleep(0, result=event))
    monkeypatch.setattr(outbox, "mark_outbox_running", lambda event: asyncio.sleep(0))
    monkeypatch.setattr(outbox, "apply_outbox_event", lambda event: asyncio.sleep(0, result=_raise(exc)))
    async def mark_failed(*, event, exc):
        next_attempt = event.attempt_count + 1
        captured["status"] = (
            "failed"
            if isinstance(exc, MemoryAgentRetryable) and next_attempt < event.max_attempts
            else "dead_letter"
        )
    monkeypatch.setattr(outbox, "mark_outbox_failed", mark_failed)

    with pytest.raises(Exception):
        asyncio.run(outbox.process_outbox_event_by_id(event_id="event-1"))
    assert captured["status"] == status


def _raise(exc):
    raise exc
