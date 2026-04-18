from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from crud.chunk import create_chunks
from crud.document import update_document_status
from models.document import Document
from clients.document_loader_client import load_langchain_documents
from clients.text_splitter_client import split_documents
from clients.vector_store_client import add_documents_to_vector_store_in_batches
from collections.abc import Awaitable, Callable

from schemas.document import DocumentIndexPipelineResult


async def emit_stage(
        stage: str,
        *,
        on_stage_change: Callable[[str], Awaitable[None]] | None,
) -> None:
    if on_stage_change:
        await on_stage_change(stage)


# 执行文档索引主流水线：加载文档、切分 chunk、落库并写入向量库。
async def run_document_index_pipeline(
        db: AsyncSession,
        *,
        document: Document,
        on_stage_change: Callable[[str], Awaitable[None]] | None = None,
) -> DocumentIndexPipelineResult:
    # 你要做的事：
    # 1. 在开始时写 document.status = indexing
    # 2. 在 parsing / chunking / embedding / vector_upserting 前发阶段信号
    # 3. 保持 load -> split -> create_chunks -> vector upsert 主链
    # 4. 在成功时写 document.status = indexed
    # 5. 返回结构化结果
    doc = await update_document_status(
        db,
        document_id=document.id,
        status="indexing"
    )
    await emit_stage("parsing", on_stage_change=on_stage_change)
    docs = await load_langchain_documents(
        file_path=doc.file_path,
        file_type=doc.file_type,
        user_id=doc.user_id,
        knowledge_base_id=doc.knowledge_base_id,
        knowledge_base_pk=doc.knowledge_base_pk,
        file_name=doc.file_name,
        document_id=doc.id,
        document_pk=doc.pk,
    )

    await emit_stage("chunking", on_stage_change=on_stage_change)

    chunk_docs = await split_documents(document_id=doc.id, documents=docs, )

    await create_chunks(
        db,
        document_id=doc.id,
        document_pk=doc.pk,
        chunk_docs=chunk_docs,
    )

    await emit_stage("embedding", on_stage_change=on_stage_change)
    await emit_stage("vector_upserting", on_stage_change=on_stage_change)

    vector_result = await add_documents_to_vector_store_in_batches(
        chunk_docs=chunk_docs,
        batch_size=settings.INDEX_VECTOR_BATCH_SIZE,
    )

    await update_document_status(db, document_id=doc.id, status="indexed", )

    return DocumentIndexPipelineResult(
        document_id=doc.id,
        knowledge_base_id=doc.knowledge_base_id,
        chunk_count=len(chunk_docs),
        vector_batch_count=vector_result["batch_count"],
        vector_batch_size=vector_result["batch_size"],
        indexed_vector_count=vector_result["total_count"],
        status="indexed",
    )
