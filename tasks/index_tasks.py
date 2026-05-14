import asyncio

from conf.database import open_read_session, open_write_session
from conf.logging import app_logger
from crud.document import get_document_by_id, update_document_status
from crud.task_record import get_task_record_by_id
from infra.celery_app import celery_app
from models.document import Document
from pipelines.document_index_pipeline import run_document_index_pipeline
from services.task_state_service import transition_task_status
from utils.exceptions import BusinessException


async def load_document_snapshot(*, document_id: str) -> Document | None:
    async with open_read_session() as db:
        return await get_document_by_id(db, document_id=document_id)


async def load_task_status(*, task_id: str) -> str | None:
    async with open_read_session() as db:
        task_record = await get_task_record_by_id(db, task_id=task_id)
        return task_record.status if task_record else None


async def transition_task_status_in_new_session(
    *,
    task_id: str,
    to_status: str,
    error_message: str | None = None,
) -> None:
    async with open_write_session() as db:
        await transition_task_status(
            db,
            task_id=task_id,
            to_status=to_status,
            error_message=error_message,
        )


async def update_document_status_in_new_session(
    *,
    document_id: str,
    status: str,
) -> None:
    async with open_write_session() as db:
        await update_document_status(
            db,
            document_id=document_id,
            status=status,
        )


@celery_app.task(name="tasks.index_document_task")
def index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    app_logger.bind(module="index_task").info(
        f"worker task start task_id={task_id} document_id={document_id}"
    )
    asyncio.run(
        run_index_document_task_async(
            task_id=task_id,
            document_id=document_id,
        )
    )


async def run_index_document_task_async(
    *,
    task_id: str,
    document_id: str,
) -> None:
    try:
        async def report_stage(stage: str) -> None:
            app_logger.bind(module="index_task").info(
                f"worker task stage task_id={task_id} document_id={document_id} stage={stage}"
            )
            await transition_task_status_in_new_session(
                task_id=task_id,
                to_status=stage,
            )

        doc = await load_document_snapshot(document_id=document_id)
        if not doc:
            raise BusinessException(message="document not found", code=404)

        task_status = await load_task_status(task_id=task_id)
        if task_status == "canceled":
            app_logger.bind(module="index_task").info(
                f"worker task skipped because canceled task_id={task_id} document_id={document_id}"
            )
            await update_document_status_in_new_session(
                document_id=document_id,
                status="uploaded",
            )
            return

        result = await run_document_index_pipeline(
            document=doc,
            on_stage_change=report_stage,
        )

        app_logger.bind(module="index_task").info(
            f"index task completed task_id={task_id} document_id={document_id} "
            f"chunk_count={result.chunk_count} "
            f"deleted_memory_entry_count={result.deleted_memory_entry_count} "
            f"memory_entry_count={result.memory_entry_count} "
            f"vector_batch_count={result.vector_batch_count} "
            f"vector_batch_size={result.vector_batch_size}"
        )
        await transition_task_status_in_new_session(
            task_id=task_id,
            to_status="completed",
        )
    except Exception as exc:
        app_logger.bind(module="index_task").exception(
            f"index task failed task_id={task_id} document_id={document_id} "
            f"error_type={type(exc).__name__} error={exc}"
        )
        await transition_task_status_in_new_session(
            task_id=task_id,
            to_status="failed",
            error_message=str(exc),
        )
        await update_document_status_in_new_session(
            document_id=document_id,
            status="failed",
        )
        raise
