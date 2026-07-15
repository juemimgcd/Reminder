from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

from fastapi.testclient import TestClient

from services.memory_agent.api import events as events_api
from services.memory_agent.app import create_memory_agent_app
from services.memory_agent.database import get_db
from services.memory_agent.models.inbox_event import InboxEvent
from services.memory_agent.security.service_tokens import create_service_token


class FakeSession:
    async def commit(self):
        return None


def test_concurrent_duplicate_receipts_create_and_schedule_once(monkeypatch):
    app = create_memory_agent_app()
    store = {}
    store_lock = Lock()
    scheduled = []

    async def fake_db():
        yield FakeSession()

    async def accept_once(_db, envelope):
        with store_lock:
            created = envelope.event_id not in store
            row = store.setdefault(envelope.event_id, SimpleNamespace(event_id=envelope.event_id))
        return row, created

    async def schedule(event_id):
        with store_lock:
            scheduled.append(event_id)

    monkeypatch.setattr(events_api, "accept_event", accept_once)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[events_api.get_event_scheduler] = lambda: schedule
    headers = {"Authorization": f"Bearer {create_service_token('test-secret-at-least-32-bytes-long')}"}
    payload = {
        "event_id": "same-event",
        "event_type": "conversation.completed",
        "schema_version": "1",
        "occurred_at": "2026-07-15T00:00:00Z",
        "owner_id": 1,
        "knowledge_base_id": None,
        "payload": {"session_id": "session-1"},
    }

    def post_event():
        with TestClient(app) as client:
            return client.post("/internal/v1/events", json=payload, headers=headers)

    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda _index: post_event(), range(8)))

    assert len(store) == 1
    assert scheduled == ["same-event"]
    assert [response.status_code for response in responses].count(202) == 1
    assert [response.status_code for response in responses].count(200) == 7
    assert sum(not response.json()["duplicate"] for response in responses) == 1


def test_inbox_repository_uses_database_conflict_handling():
    from inspect import getsource

    from services.memory_agent.repositories.inbox import accept_event

    repository_source = getsource(accept_event)
    assert InboxEvent.__table__.c.event_id.unique is True
    assert ".on_conflict_do_nothing(" in repository_source
    assert "InboxEvent.event_id" in repository_source


def test_inbox_migration_declares_event_id_unique_constraint():
    migration = Path(__file__).parents[2] / "services" / "memory_agent" / "alembic" / "versions" / (
        "20260714_01_create_memory_agent_core.py"
    )

    source = migration.read_text(encoding="utf-8")

    assert 'sa.UniqueConstraint("event_id")' in source
