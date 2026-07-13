import uuid
from collections import defaultdict
from datetime import datetime, timezone

from langchain_core.documents import Document as LCDocument
from langchain_core.output_parsers import PydanticOutputParser
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.llm_client import get_llm
from app.mneme.conf.database import open_read_session, open_write_session
from app.mneme.conf.logging import log_event
from app.mneme.crud.chunk import list_chunks_by_document_id
from app.mneme.crud.document import list_documents
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.crud.memory_entry import (
    list_memory_entries_by_document_id,
    list_memory_entries_by_knowledge_base_id,
)
from app.mneme.crud.user import get_user_by_id
from app.mneme.domains.graph.projection import sync_document_memory_projection
from app.mneme.domains.memory.identity import prepare_memory_entry_payload
from app.mneme.domains.memory.projection import rebuild_memory_governance_projection
from app.mneme.models.document import Document
from app.mneme.models.memory_entry import MemoryEntry
from app.mneme.schemas.memory_entry import MemoryEntryExtractionResult
from app.mneme.utils.entry_prompt import get_entry_extraction_prompt


def group_entries_by_type(entries: list[dict]) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)

    for item in entries:
        grouped[item["entry_type"]].append(item["entry_name"])

    return dict(grouped)


def build_timeline(entries: list[dict]) -> list[dict]:
    sorted_entries = sorted(entries, key=lambda x: x["created_at"])

    return [
        {
            "entry_id": item["id"],
            "entry_name": item["entry_name"],
            "entry_type": item["entry_type"],
            "summary": item["summary"],
            "created_at": item["created_at"],
        }
        for item in sorted_entries
    ]


def build_theme_groups(entries: list[dict]) -> list[dict]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for item in entries:
        grouped[item["entry_name"]].append(item["summary"])

    result: list[dict] = []

    for theme_name, related_entries in grouped.items():
        result.append(
            {
                "theme_name": theme_name,
                "entries": related_entries,
                "count": len(related_entries),
            }
        )

    return sorted(result, key=lambda x: x["count"], reverse=True)


def build_memory_library(entries: list[dict]) -> dict:
    return {
        "timeline": build_timeline(entries),
        "by_type": group_entries_by_type(entries),
        "by_theme": build_theme_groups(entries),
    }


def serialize_memory_entries(entries: list[dict | object]) -> list[dict]:
    result: list[dict] = []

    for item in entries:
        result.append(
            {
                "id": item.get("id") if isinstance(item, dict) else getattr(item, "id", None),
                "entry_name": item.get("entry_name") if isinstance(item, dict) else getattr(item, "entry_name", None),
                "entry_type": item.get("entry_type") if isinstance(item, dict) else getattr(item, "entry_type", None),
                "summary": item.get("summary") if isinstance(item, dict) else getattr(item, "summary", None),
                "created_at": item.get("created_at") if isinstance(item, dict) else getattr(item, "created_at", None),
            }
        )

    return result


def build_chunk_documents_from_rows(
        *,
        document: Document,
        chunk_rows: list,
) -> list[LCDocument]:
    docs: list[LCDocument] = []

    for chunk in chunk_rows:
        docs.append(
            LCDocument(
                page_content=chunk.content,
                metadata={
                    "user_id": document.user_id,
                    "knowledge_base_id": document.knowledge_base_id,
                    "knowledge_base_pk": document.knowledge_base_pk,
                    "document_id": document.id,
                    "document_pk": document.pk,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "source": document.file_path,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no,
                    "start_offset": chunk.start_offset,
                },
            )
        )

    return docs


async def extract_entries_from_chunk(doc: LCDocument) -> list[dict]:
    log_event(
        "memory_service",
        "debug",
        "memory.extract_chunk.start",
        document_id=doc.metadata.get("document_id"),
        chunk_id=doc.metadata.get("chunk_id"),
    )
    parser = PydanticOutputParser(pydantic_object=MemoryEntryExtractionResult)
    instructions = parser.get_format_instructions()

    prompt = get_entry_extraction_prompt(format_instructions=instructions)
    llm = get_llm()

    chain = prompt | llm | parser
    result = await chain.ainvoke(
        {
            "document_id": doc.metadata.get("document_id"),
            "chunk_id": doc.metadata.get("chunk_id"),
            "page_no": doc.metadata.get("page_no"),
            "chunk_text": doc.page_content,
        }
    )

    entries: list[dict] = []

    for item in result.entries:
        entries.append(
            {
                "id": f"entry_{uuid.uuid4().hex[:12]}",
                "user_id": doc.metadata.get("user_id"),
                "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
                "knowledge_base_pk": doc.metadata.get("knowledge_base_pk"),
                "document_id": doc.metadata.get("document_id"),
                "document_pk": doc.metadata.get("document_pk"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "entry_name": item.entry_name,
                "entry_type": item.entry_type,
                "summary": item.summary,
                "evidence_text": item.evidence_text,
                "importance_score": item.importance_score,
            }
        )

    log_event(
        "memory_service",
        "debug",
        "memory.extract_chunk.completed",
        document_id=doc.metadata.get("document_id"),
        chunk_id=doc.metadata.get("chunk_id"),
        entry_count=len(entries),
    )
    return entries


async def extract_entries_from_chunks(chunk_docs: list[LCDocument]) -> list[dict]:
    log_event(
        "memory_service",
        "info",
        "memory.extract_batch.start",
        chunk_count=len(chunk_docs),
    )
    entries: list[dict] = []
    for chunk in chunk_docs:
        chunk_entries = await extract_entries_from_chunk(chunk)
        entries.extend(chunk_entries)

    log_event(
        "memory_service",
        "info",
        "memory.extract_batch.completed",
        chunk_count=len(chunk_docs),
        total_entry_count=len(entries),
    )
    return entries


async def rebuild_memory_entries_for_document(
        *,
        document: Document,
) -> dict[str, int]:
    async with open_read_session() as db:
        chunk_rows = await list_chunks_by_document_id(
            db,
            document_id=document.id,
        )

    if not chunk_rows:
        deleted_entry_count, _ = await replace_memory_entries_for_document(
            document=document,
            entries=[],
        )
        log_event(
            "memory_service",
            "info",
            "memory.rebuild_document.skipped",
            document_id=document.id,
            deleted_entry_count=deleted_entry_count,
            reason="no_chunks",
        )
        return {
            "chunk_count": 0,
            "deleted_entry_count": deleted_entry_count,
            "entry_count": 0,
        }

    chunk_docs = build_chunk_documents_from_rows(
        document=document,
        chunk_rows=chunk_rows,
    )
    entries = await extract_entries_from_chunks(chunk_docs)
    deleted_entry_count, persisted_entries = await replace_memory_entries_for_document(
        document=document,
        entries=entries,
    )

    log_event(
        "memory_service",
        "info",
        "memory.rebuild_document.completed",
        document_id=document.id,
        chunk_count=len(chunk_docs),
        deleted_entry_count=deleted_entry_count,
        entry_count=len(persisted_entries),
    )
    return {
        "chunk_count": len(chunk_docs),
        "deleted_entry_count": deleted_entry_count,
        "entry_count": len(persisted_entries),
    }


async def rebuild_memory_entries_for_knowledge_base(
        *,
        knowledge_base_pk: int,
        knowledge_base_id: str,
) -> dict[str, int | str]:
    async with open_read_session() as db:
        documents = await list_documents(
            db,
            knowledge_base_pk=knowledge_base_pk,
        )

    processed_document_count = 0
    total_chunk_count = 0
    total_deleted_entry_count = 0
    total_entry_count = 0

    for document in documents:
        result = await rebuild_memory_entries_for_document(
            document=document,
        )
        if result["chunk_count"] > 0:
            processed_document_count += 1
        total_chunk_count += result["chunk_count"]
        total_deleted_entry_count += result["deleted_entry_count"]
        total_entry_count += result["entry_count"]

    log_event(
        "memory_service",
        "info",
        "memory.rebuild_knowledge_base.completed",
        knowledge_base_id=knowledge_base_id,
        document_count=len(documents),
        processed_document_count=processed_document_count,
        chunk_count=total_chunk_count,
        deleted_entry_count=total_deleted_entry_count,
        entry_count=total_entry_count,
    )
    return {
        "knowledge_base_id": knowledge_base_id,
        "document_count": len(documents),
        "processed_document_count": processed_document_count,
        "chunk_count": total_chunk_count,
        "deleted_entry_count": total_deleted_entry_count,
        "entry_count": total_entry_count,
    }


async def reconcile_memory_entries_for_document(
    db: AsyncSession,
    *,
    document: Document,
    entries: list[dict],
) -> tuple[int, list[MemoryEntry]]:
    existing_entries = await list_memory_entries_by_document_id(
        db,
        document_id=document.id,
        include_inactive=True,
    )
    now = datetime.now(timezone.utc)
    incoming_by_fingerprint = {
        payload["source_fingerprint"]: payload
        for item in entries
        for payload in [prepare_memory_entry_payload(item, stable_id=True)]
    }
    existing_by_fingerprint = {
        item.source_fingerprint: item
        for item in existing_entries
    }

    persisted_entries: list[MemoryEntry] = []
    for fingerprint, payload in incoming_by_fingerprint.items():
        existing = existing_by_fingerprint.get(fingerprint)
        if existing:
            existing.status = "active"
            existing.valid_to = None
            existing.last_seen_at = now
            existing.confidence = payload["confidence"]
            existing.importance_score = payload["importance_score"]
            persisted_entries.append(existing)
            continue

        memory_entry = MemoryEntry(
            **payload,
            first_seen_at=now,
            last_seen_at=now,
            valid_from=now,
            valid_to=None,
        )
        db.add(memory_entry)
        persisted_entries.append(memory_entry)

    retired_entry_count = 0
    incoming_fingerprints = set(incoming_by_fingerprint)
    for existing in existing_entries:
        if existing.status == "active" and existing.source_fingerprint not in incoming_fingerprints:
            existing.status = "superseded"
            existing.valid_to = now
            retired_entry_count += 1

    await db.flush()

    active_knowledge_base_entries = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=document.knowledge_base_id,
    )
    await rebuild_memory_governance_projection(
        db,
        user_id=document.user_id,
        knowledge_base_id=document.knowledge_base_id,
        knowledge_base_pk=document.knowledge_base_pk,
        entries=active_knowledge_base_entries,
    )
    return retired_entry_count, persisted_entries


async def replace_memory_entries_for_document(
        *,
        document: Document,
        entries: list[dict],
) -> tuple[int, list]:
    async with open_write_session() as db:
        retired_entry_count, persisted_entries = await reconcile_memory_entries_for_document(
            db,
            document=document,
            entries=entries,
        )

        knowledge_base = await get_knowledge_base_by_id(
            db,
            knowledge_base_id=document.knowledge_base_id,
        )
        user = await get_user_by_id(
            db,
            user_id=document.user_id,
        )
        if knowledge_base and user:
            await sync_document_memory_projection(
                db,
                user=user,
                knowledge_base=knowledge_base,
                document=document,
                memory_entries=persisted_entries,
            )

        return retired_entry_count, persisted_entries
