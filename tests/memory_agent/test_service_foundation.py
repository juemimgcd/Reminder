from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient

from services.memory_agent.app import create_memory_agent_app
from services.memory_agent.celery_app import celery_app
from services.memory_agent.config import MemoryAgentSettings

ROOT = Path(__file__).resolve().parents[2]


def test_memory_agent_settings_use_independent_persistence_and_queue_defaults():
    agent = MemoryAgentSettings(_env_file=None, SERVICE_JWT_SECRET="test-secret")

    assert agent.DATABASE_URL.endswith("/memory_agent")
    assert agent.CELERY_BROKER_URL.endswith("/2")
    assert agent.CELERY_RESULT_BACKEND.endswith("/3")
    assert agent.CELERY_QUEUE == "memory_agent"


def test_celery_routes_agent_tasks_to_the_agent_queue():
    routes = celery_app.conf.task_routes

    assert routes["memory_agent.process_event"] == {"queue": "memory_agent"}
    assert routes["memory_agent.dispatch_pending_events"] == {"queue": "memory_agent"}
    assert celery_app.conf.task_default_queue == "memory_agent"


def test_memory_agent_has_one_migration_head():
    config = Config(str(ROOT / "services" / "memory_agent" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert len(script.get_heads()) == 1


def test_liveness_does_not_require_external_dependencies():
    with TestClient(create_memory_agent_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
