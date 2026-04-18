from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession

from crud.memory_entry import create_memory_entries
from schemas.memory_entry import MemoryExtractPipelineResult, MemoryEntryPayload
from services.memory_service import extract_entries_from_chunks


async def run_memory_extract_pipeline(
        db: AsyncSession,
        *,
        chunk_docs: list[LCDocument],
        knowledge_base_id: str,
        document_id: str | None = None,
) -> MemoryExtractPipelineResult:
    # 你要做的事：
    # 1. 先从 chunk docs 抽 entries
    # 2. 做第一版去重 / 归并
    # 3. 调 create_memory_entries(...) 入库
    # 4. 返回结构化统计结果
    raw_entries = await extract_entries_from_chunks(chunk_docs)
    deduped_entries = deduplicate_memory_entries(raw_entries)

    payloads = [
        MemoryEntryPayload(**item).model_dump()
        for item in deduped_entries
    ]
    await create_memory_entries(
        db,
        entries=payloads,
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