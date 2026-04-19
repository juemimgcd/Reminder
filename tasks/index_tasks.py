import asyncio
from conf.database import AsyncSessionLocal
from conf.logging import app_logger
from crud.document import update_document_status
from crud.task_record import get_task_record_by_id
from infra.celery_app import celery_app
from crud.document import get_document_by_id
from pipelines.document_index_pipeline import run_document_index_pipeline
from services.task_state_service import transition_task_status
from utils.exceptions import BusinessException


@celery_app.task(name="tasks.index_document_task")
# Celery 同步任务入口，负责把任务转进异步 runner。
def index_document_task(
        *,
        task_id: str,
        document_id: str,
) -> None:
    # 你要做的事：
    # 1. 用 asyncio.run(...) 调 async runner
    # 2. 把 task_id / document_id 传进去
    app_logger.bind(module="index_task").info(
        f"worker task start task_id={task_id} document_id={document_id}"
    )
    asyncio.run(
        run_index_document_task_async(
            task_id=task_id,
            document_id=document_id,
        )
    )


# 在 worker 里执行文档索引任务，并驱动 task/document 状态推进。
async def run_index_document_task_async(
        *,
        task_id: str,
        document_id: str,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            async def report_stage(stage: str) -> None:
                app_logger.bind(module="index_task").info(
                    f"worker task stage task_id={task_id} document_id={document_id} stage={stage}"
                )
                await transition_task_status(db,task_id=task_id,to_status=stage,)

            doc = await get_document_by_id(db, document_id=document_id)
            if not doc:
                raise BusinessException(message="document not found", code=404)

            task_record = await get_task_record_by_id(db, task_id=task_id)
            if task_record and task_record.status == "canceled":
                app_logger.bind(module="index_task").info(
                    f"worker task skipped because canceled task_id={task_id} document_id={document_id}"
                )
                await update_document_status(db, document_id=document_id, status="uploaded")
                await db.commit()
                return

            result = await run_document_index_pipeline(
                db,
                document=doc,
                on_stage_change=report_stage,
            )

            app_logger.bind(module="index_task").info(
                f"index task completed task_id={task_id} document_id={document_id} "
                f"chunk_count={result.chunk_count} vector_batch_count={result.vector_batch_count} "
                f"vector_batch_size={result.vector_batch_size}"
            )
            await transition_task_status(db,task_id=task_id,to_status="completed",)
            await db.commit()
        except Exception as exc:
            app_logger.bind(module="index_task").exception(
                f"index task failed task_id={task_id} document_id={document_id} "
                f"error_type={type(exc).__name__} error={exc}"
            )
            await transition_task_status(
                db,
                task_id=task_id,
                to_status="failed",
                error_message=str(exc),
            )
            await update_document_status(db,document_id=document_id,status="failed",)
            await db.commit()
            raise
