import asyncio
from conf.database import AsyncSessionLocal
from crud.document import update_document_status
from crud.task_record import update_task_record_status
from infra.celery_app import celery_app
from crud.document import get_document_by_id
from pipelines.document_index_pipeline import run_document_index_pipeline
from utils.exceptions import BusinessException



@celery_app.task(name="tasks.index_document_task")
def index_document_task(
        *,
        task_id: str,
        document_id: str,
) -> None:
    # 你要做的事：
    # 1. 用 asyncio.run(...) 调 async runner
    # 2. 把 task_id / document_id 传进去
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
    # 你要做的事：
    # 1. 创建 AsyncSession
    # 2. 把 task_record.status 改成 running
    # 3. 把 document.status 改成 indexing
    # 4. 查询 document
    # 5. 调 run_document_index_pipeline(...)
    # 6. 成功时标记 completed
    # 7. 失败时标记 failed 和 error_message
    async with AsyncSessionLocal() as db:
        try:
            await update_task_record_status(
                db,
                task_id=task_id,
                status="running"
            )
            await update_document_status(
                db,
                document_id=document_id,
                status="indexing"
            )

            doc = await get_document_by_id(
                db,
                document_id=document_id
            )

            if not doc:
                raise BusinessException(message="document not found",code=404)

            await run_document_index_pipeline(
                db,
                document=doc
            )

            await update_document_status(
                db,
                document_id=doc.id,
                status="completed"
            )
            await db.commit()

        except Exception as exc:
            await update_task_record_status(
                db,
                task_id=task_id,
                status="failed",
                error_message=str(exc),
            )
            await update_document_status(
                db,
                document_id=document_id,
                status="failed",
            )
            await db.commit()
            raise

















