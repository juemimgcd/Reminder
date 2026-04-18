from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from crud.chunk import create_chunks
from crud.document import update_document_status
from models.document import Document
from utils.file_loader import load_langchain_documents
from utils.text_splitter import split_documents
from clients.vector_store_client import add_documents_to_vector_store, add_documents_to_vector_store_in_batches


async def run_document_index_pipeline(
        db: AsyncSession,
        document: Document,
        on_stage_change=None
) -> dict:

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
















































