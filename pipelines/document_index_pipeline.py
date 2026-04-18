from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from crud.chunk import create_chunks
from crud.document import update_document_status
from models.document import Document
from clients.document_loader_client import load_langchain_documents
from clients.text_splitter_client import split_documents
from clients.vector_store_client import add_documents_to_vector_store_in_batches


# 执行文档索引主流水线：加载文档、切分 chunk、落库并写入向量库。
async def run_document_index_pipeline(
        db: AsyncSession,
        document: Document,
        on_stage_change=None
) -> dict:
    # on_stage_change 用来把 parsing / chunking / embedding / vector_upserting
    # 这类阶段信号往 task 层回传；它本身不是业务动作。
    doc = await update_document_status(db,document_id=document.id,status="indexing")

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

    chunk_docs = await split_documents(
        document_id=document.id,
        documents=docs,
    )

    await create_chunks(
        db,
        document_id=doc.id,
        document_pk=doc.pk,
        chunk_docs=chunk_docs,
    )

    vector_result = await add_documents_to_vector_store_in_batches(chunk_docs=chunk_docs,batch_size=settings.INDEX_VECTOR_BATCH_SIZE)
    await update_document_status(db, document_id=document.id, status="indexed")

    return {
        "document_id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "chunk_count": len(chunk_docs),
        "vector_batch_count": vector_result["batch_count"],
        "vector_batch_size": vector_result["batch_size"],
        "indexed_vector_count": vector_result["total_count"],
        "status": "indexed",
    }
















































