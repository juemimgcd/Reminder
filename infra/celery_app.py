from celery import Celery
from conf.config import settings


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
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=False,
        imports=("tasks.index_tasks",),
    )
    return app





celery_app = build_celery_app()
