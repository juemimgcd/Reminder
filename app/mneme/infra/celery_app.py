from celery import Celery
from app.mneme.conf.config import settings


def build_celery_app() -> Celery:
    # 你要做的事：
    # 1. 读取 broker / backend
    # 2. 创建 Celery app
    # 3. 配置默认队列
    # 4. 自动发现 tasks
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
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=False,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
        imports=("tasks.index_tasks", "tasks.outbox_tasks"),
    )
    return app





celery_app = build_celery_app()
