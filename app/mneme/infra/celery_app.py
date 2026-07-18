from celery import Celery

from app.mneme.conf.config import settings


def build_celery_app() -> Celery:
    app = Celery(
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND
    )
    app.conf.update(
        task_default_queue=settings.CELERY_INDEX_QUEUE,
        task_routes={
            "tasks.index_document_task": {"queue": settings.CELERY_INDEX_QUEUE},
            "tasks.process_outbox_event_task": {"queue": settings.CELERY_OUTBOX_QUEUE},
            "tasks.dispatch_pending_outbox_events_task": {"queue": settings.CELERY_OUTBOX_QUEUE},
            "tasks.execute_agent_run_task": {"queue": settings.CELERY_AGENT_QUEUE},
            "tasks.recover_agent_runs_task": {"queue": settings.CELERY_AUTOMATION_QUEUE},
            "tasks.dispatch_due_heartbeat_jobs_task": {"queue": settings.CELERY_AUTOMATION_QUEUE},
            "tasks.execute_maintenance_task": {"queue": settings.CELERY_MAINTENANCE_QUEUE},
            "tasks.recover_maintenance_tasks": {"queue": settings.CELERY_AUTOMATION_QUEUE},
            "tasks.process_channel_delivery_task": {"queue": settings.CELERY_CHANNEL_QUEUE},
            "tasks.dispatch_channel_deliveries_task": {"queue": settings.CELERY_CHANNEL_QUEUE},
            "tasks.process_channel_inbound_task": {"queue": settings.CELERY_CHANNEL_QUEUE},
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=False,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
        imports=(
            "app.mneme.tasks.index_tasks",
            "app.mneme.tasks.outbox_tasks",
            "app.mneme.memoria.tasks.runs",
            "app.mneme.memoria.tasks.heartbeats",
            "app.mneme.tasks.maintenance_tasks",
            "app.mneme.channels.tasks",
        ),
        beat_schedule={
            "recover-agent-runs": {
                "task": "tasks.recover_agent_runs_task",
                "schedule": 60.0,
            },
            "dispatch-due-heartbeats": {
                "task": "tasks.dispatch_due_heartbeat_jobs_task",
                "schedule": float(settings.HEARTBEAT_DISPATCH_INTERVAL_SECONDS),
            },
            "dispatch-outbox": {
                "task": "tasks.dispatch_pending_outbox_events_task",
                "schedule": 15.0,
            },
            "recover-maintenance-tasks": {
                "task": "tasks.recover_maintenance_tasks",
                "schedule": 60.0,
            },
            "dispatch-channel-deliveries": {
                "task": "tasks.dispatch_channel_deliveries_task",
                "schedule": 10.0,
            },
        },
    )
    return app





celery_app = build_celery_app()
