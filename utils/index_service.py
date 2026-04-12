from sqlalchemy.ext.asyncio import AsyncSession

from crud.chunk import create_chunks
from crud.document import update_document_status
from models.document import Document
from utils.file_loader import load_langchain_documents
from utils.text_splitter import split_documents
from utils.vector_store import add_documents_to_vector_store


async def index_document(db: AsyncSession, document: Document) -> dict:

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

    await add_documents_to_vector_store(chunk_docs=chunk_docs)
    await update_document_status(db, document_id=document.id, status="indexed")

    return {
        "document_id": document.id,
        "knowledge_base_id": document.knowledge_base_id,
        "chunk_count": len(chunk_docs),
        "status": "indexed",
    }





















































