from celery import Celery

from services.memory_agent.config import settings

celery_app = Celery(
    "memory_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["services.memory_agent.tasks.events"],
)
celery_app.conf.update(
    task_default_queue=settings.CELERY_QUEUE,
    task_routes={
        "memory_agent.process_event": {"queue": settings.CELERY_QUEUE},
        "memory_agent.dispatch_pending_events": {"queue": settings.CELERY_QUEUE},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "dispatch-pending-memory-agent-events": {
            "task": "memory_agent.dispatch_pending_events",
            "schedule": 30.0,
            "kwargs": {"batch_limit": 100},
        }
    },
)
