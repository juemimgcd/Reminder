import argparse
import asyncio
import sys
from pathlib import Path

from langchain_core.documents import Document as LCDocument
from sqlalchemy import Select, select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(stdout_reconfigure):
    stdout_reconfigure(errors="replace")

from app.mneme.conf.database import AsyncSessionLocal
from app.mneme.models.chunk import Chunk
from app.mneme.models.document import Document
from app.mneme.clients.vector_store_client import (
    add_documents_to_vector_store,
    delete_documents_from_vector_store,
    drop_vector_collection,
)


BATCH_SIZE = 64


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild Milvus vectors from chunk rows")
    parser.add_argument("--knowledge-base-id", help="Only rebuild one knowledge base")
    parser.add_argument("--user-id", type=int, help="Only rebuild one user's documents")
    parser.add_argument("--document-id", help="Only rebuild one document")
    parser.add_argument(
        "--drop-collection",
        action="store_true",
        help="Drop the whole target collection before rebuilding",
    )
    parser.add_argument(
        "--delete-existing",
        action="store_true",
        help="Delete matching vector ids before inserting rebuilt vectors",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only without mutating Milvus",
    )
    return parser


async def load_rows(
    *,
    knowledge_base_id: str | None,
    user_id: int | None,
    document_id: str | None,
) -> list[tuple[Document, Chunk]]:
    async with AsyncSessionLocal() as session:
        sql: Select[tuple[Document, Chunk]] = (
            select(Document, Chunk)
            .join(Chunk, Chunk.document_id == Document.id)
            .order_by(Document.id.asc(), Chunk.chunk_index.asc())
        )

        if knowledge_base_id:
            sql = sql.where(Document.knowledge_base_id == knowledge_base_id)
        if user_id:
            sql = sql.where(Document.user_id == user_id)
        if document_id:
            sql = sql.where(Document.id == document_id)

        result = await session.execute(sql)
        rows: list[tuple[Document, Chunk]] = [
            (document, chunk)
            for document, chunk in result.tuples().all()
        ]
        return rows



def build_chunk_document(document: Document, chunk: Chunk) -> LCDocument:
    return LCDocument(
        page_content=chunk.content,
        metadata={
            "user_id": document.user_id,
            "knowledge_base_id": document.knowledge_base_id,
            "document_id": document.id,
            "file_name": document.file_name,
            "file_type": document.file_type,
            "source": document.file_path,
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "page_no": chunk.page_no,
            "start_offset": chunk.start_offset,
        },
    )


async def rebuild_vectors(args: argparse.Namespace) -> None:
    rows = await load_rows(
        knowledge_base_id=args.knowledge_base_id,
        user_id=args.user_id,
        document_id=args.document_id,
    )

    chunk_docs = [build_chunk_document(document, chunk) for document, chunk in rows]
    vector_ids = [str(doc.metadata["chunk_id"]) for doc in chunk_docs]

    document_ids = {document.id for document, _ in rows}
    knowledge_base_ids = {document.knowledge_base_id for document, _ in rows}

    print(f"matched_documents={len(document_ids)}")
    print(f"matched_chunks={len(chunk_docs)}")
    print(f"matched_knowledge_bases={len(knowledge_base_ids)}")
    print(f"drop_collection={args.drop_collection}")
    print(f"delete_existing={args.delete_existing}")
    print(f"dry_run={args.dry_run}")

    if args.dry_run:
        return

    if args.drop_collection:
        await drop_vector_collection()
    elif args.delete_existing and vector_ids:
        await delete_documents_from_vector_store(ids=vector_ids)

    inserted = 0
    for offset in range(0, len(chunk_docs), BATCH_SIZE):
        batch = chunk_docs[offset: offset + BATCH_SIZE]
        await add_documents_to_vector_store(batch)
        inserted += len(batch)
        print(f"inserted={inserted}")

    print("rebuild_completed=true")


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    await rebuild_vectors(args)


if __name__ == "__main__":
    asyncio.run(main())
