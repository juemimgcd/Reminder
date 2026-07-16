from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import yaml

from app.mneme.bootstrap.app_factory import create_app
from app.mneme.infra.celery_app import celery_app
from app.mneme.memoria.actions import WRITE_ACTION_CATALOG, ToolRiskLevel
from app.mneme.memoria.automation.service import heartbeat_is_active
from app.mneme.memoria.run_models import AgentRunRecord

ROOT = Path(__file__).resolve().parents[1]


def test_agent_run_records_preserve_durable_trigger_identity():
    record = AgentRunRecord.create(
        run_id="run_1",
        session_id="chat_1",
        user_id=7,
        client_request_id="heartbeat:job_1:2026-07-15T09:00:00Z",
        question="Review recent memories",
        top_k=4,
        answer_mode="general_chat",
        trigger_type="heartbeat",
        trigger_id="job_1",
        max_attempts=5,
    )

    assert record.trigger_type == "heartbeat"
    assert record.trigger_id == "job_1"
    assert record.max_attempts == 5


def test_heartbeat_active_hours_support_day_and_overnight_windows():
    day_job = SimpleNamespace(active_timezone="Asia/Shanghai", active_start="09:00", active_end="22:00")
    overnight_job = SimpleNamespace(active_timezone="Asia/Shanghai", active_start="22:00", active_end="07:00")
    one_pm_shanghai = datetime(2026, 7, 15, 5, 0, tzinfo=timezone.utc)
    eleven_pm_shanghai = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc)

    assert heartbeat_is_active(day_job, now=one_pm_shanghai)
    assert not heartbeat_is_active(day_job, now=eleven_pm_shanghai)
    assert heartbeat_is_active(overnight_job, now=eleven_pm_shanghai)


def test_write_actions_are_propose_only_and_risk_classified():
    assert WRITE_ACTION_CATALOG["memory_review.propose"].risk_level == ToolRiskLevel.LOW_WRITE
    assert WRITE_ACTION_CATALOG["document_reindex.propose"].risk_level == ToolRiskLevel.HIGH_WRITE
    assert all(not definition.apply_enabled for definition in WRITE_ACTION_CATALOG.values())


def test_agent_automation_routes_are_registered():
    paths = {route.path for route in create_app().routes}

    assert "/agent/heartbeats" in paths
    assert "/agent/heartbeats/{job_id}/run" in paths
    assert "/agent/notifications" in paths
    assert "/agent/approvals/{approval_id}/decision" in paths


def test_celery_has_durable_agent_and_heartbeat_schedules():
    routes = celery_app.conf.task_routes
    schedules = celery_app.conf.beat_schedule

    assert routes["tasks.execute_agent_run_task"]["queue"] == "agent_run"
    assert routes["tasks.recover_agent_runs_task"]["queue"] == "agent_automation"
    assert routes["tasks.dispatch_due_heartbeat_jobs_task"]["queue"] == "agent_automation"
    assert routes["tasks.execute_maintenance_task"]["queue"] == "maintenance"
    assert set(schedules) >= {
        "recover-agent-runs",
        "dispatch-due-heartbeats",
        "dispatch-outbox",
        "recover-maintenance-tasks",
    }


def test_http_layer_uses_durable_queues_instead_of_fastapi_background_tasks():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "app" / "mneme").rglob("*.py")
    )

    assert "BackgroundTasks" not in combined
    assert "background_tasks.add_task" not in combined
    assert "enqueue_graph_projection_upsert" in combined
    assert "submit_maintenance_task" in combined


def test_compose_runs_worker_and_scheduler_as_separate_processes():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    assert compose["services"]["worker"]["command"] == ["sh", "/app/docker/start-worker.sh"]
    assert compose["services"]["beat"]["command"] == ["sh", "/app/docker/start-beat.sh"]
    worker_script = (ROOT / "docker/start-worker.sh").read_text(encoding="utf-8")
    assert "CELERY_AGENT_QUEUE" in worker_script
    assert "CELERY_AUTOMATION_QUEUE" in worker_script
    assert "CELERY_OUTBOX_QUEUE" in worker_script
    assert "CELERY_MAINTENANCE_QUEUE" in worker_script
