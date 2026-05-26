from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.conf.logging import app_logger
from app.mneme.crud.document import get_document_by_id
from app.mneme.crud.knowledge_base import get_knowledge_base_by_id
from app.mneme.crud.user import get_user_by_id
from app.mneme.crud.memory_entry import create_memory_entries
from app.mneme.schemas.memory_entry import MemoryExtractPipelineResult, MemoryEntryPayload
from app.mneme.services.graph_projection_service import sync_document_memory_projection
from app.mneme.services.memory_service import extract_entries_from_chunks


async def run_memory_extract_pipeline(
        db: AsyncSession,
        *,
        chunk_docs: list[LCDocument],
        knowledge_base_id: str,
        document_id: str | None = None,
) -> MemoryExtractPipelineResult:
    # 浣犺鍋氱殑浜嬶細
    # 1. 鍏堜粠 chunk docs 鎶?entries
    # 2. 鍋氱涓€鐗堝幓閲?/ 褰掑苟
    # 3. 璋?create_memory_entries(...) 鍏ュ簱
    # 4. 杩斿洖缁撴瀯鍖栫粺璁＄粨鏋?
    app_logger.bind(module="memory_pipeline").info(
        f"memory extract pipeline start knowledge_base_id={knowledge_base_id} "
        f"document_id={document_id} chunk_count={len(chunk_docs)}"
    )
    raw_entries = await extract_entries_from_chunks(chunk_docs)
    deduped_entries = deduplicate_memory_entries(raw_entries)

    payloads = [
        MemoryEntryPayload(**item).model_dump()
        for item in deduped_entries
    ]
    persisted_entries = await create_memory_entries(
        db,
        entries=payloads,
    )
    if document_id:
        document = await get_document_by_id(
            db,
            document_id=document_id,
        )
        knowledge_base = await get_knowledge_base_by_id(
            db,
            knowledge_base_id=knowledge_base_id,
        )
        user = await get_user_by_id(
            db,
            user_id=payloads[0]["user_id"],
        ) if payloads else None
        if document and knowledge_base and user:
            await sync_document_memory_projection(
                db,
                user=user,
                knowledge_base=knowledge_base,
                document=document,
                memory_entries=persisted_entries,
            )
    app_logger.bind(module="memory_pipeline").info(
        f"memory extract pipeline completed knowledge_base_id={knowledge_base_id} "
        f"document_id={document_id} raw_entry_count={len(raw_entries)} "
        f"dedup_entry_count={len(deduped_entries)} persisted_entry_count={len(payloads)}"
    )

    return MemoryExtractPipelineResult(
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        raw_entry_count=len(raw_entries),
        dedup_entry_count=len(deduped_entries),
        persisted_entry_count=len(payloads),
    )


def deduplicate_memory_entries(entries: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result: list[dict] = []

    for item in entries:
        key = (
            item.get("knowledge_base_id"),
            item.get("document_id"),
            item.get("chunk_id"),
            item.get("entry_name"),
            item.get("entry_type"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result
