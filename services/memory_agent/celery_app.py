from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger, worker_process_init

from services.memory_agent.config import settings
from services.memory_agent.logging import configure_logger, configure_logging

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
        "memory_agent.fail_stale_answer_runs": {"queue": settings.CELERY_QUEUE},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "dispatch-pending-memory-agent-events": {
            "task": "memory_agent.dispatch_pending_events",
            "schedule": 30.0,
            "kwargs": {"batch_limit": 100},
        },
        "fail-stale-memory-agent-answer-runs": {
            "task": "memory_agent.fail_stale_answer_runs",
            "schedule": 60.0,
        },
    },
)


@after_setup_logger.connect
@after_setup_task_logger.connect
def configure_celery_logger(logger, **_kwargs) -> None:
    configure_logger(logger)


@worker_process_init.connect
def configure_worker_process_logging(**_kwargs) -> None:
    configure_logging()
