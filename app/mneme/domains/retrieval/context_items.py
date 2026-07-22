import re
from typing import Any

from langchain_core.documents import Document as LCDocument

from app.mneme.models import Chunk, MemoryEntry
from app.mneme.schemas.chat import ContextItem


def dedupe_preserve_order(items: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)

    return result


def extract_query_terms(query: str) -> list[str]:
    normalized = query.strip()
    if not normalized:
        return []

    raw_terms = re.findall(r"[A-Za-z0-9_-]+|[\u4e00-\u9fff]{2,}", normalized)
    noise_words = {"what", "how", "this", "that", "please", "about"}
    result: list[str] = []
    for term in raw_terms:
        item = term.strip()
        if len(item) <= 1:
            continue
        if item in noise_words:
            continue
        if item not in result:
            result.append(item)
    return result


def build_context_item_from_vector(doc: LCDocument, score: float) -> ContextItem:
    source_chunk_ids = doc.metadata.get("source_chunk_ids") or [doc.metadata.get("chunk_id")]
    source_page_nos = doc.metadata.get("source_page_nos") or (
        [doc.metadata.get("page_no")] if doc.metadata.get("page_no") is not None else []
    )
    return ContextItem(
        recall_type="vector",
        score=float(score),
        knowledge_base_id=doc.metadata.get("knowledge_base_id"),
        document_id=doc.metadata.get("document_id"),
        chunk_id=doc.metadata.get("chunk_id"),
        page_no=doc.metadata.get("page_no"),
        text=doc.page_content,
        source_chunk_ids=[str(item) for item in source_chunk_ids if item],
        source_page_nos=[item for item in source_page_nos if isinstance(item, int)],
        merged_chunk_count=int(doc.metadata.get("merged_chunk_count", 1)),
        section_id=doc.metadata.get("section_id"),
        section_title=doc.metadata.get("section_title"),
        section_level=doc.metadata.get("section_level"),
        section_path=doc.metadata.get("section_path"),
        section_summary=doc.metadata.get("section_summary"),
        section_chunk_index=doc.metadata.get("section_chunk_index"),
    )


def build_context_item_from_chunk(
    chunk: Chunk,
    *,
    score: float,
    knowledge_base_id: str,
    matched_terms: list[str],
) -> ContextItem:
    return ContextItem(
        recall_type="keyword",
        score=float(score),
        knowledge_base_id=knowledge_base_id,
        document_id=chunk.document_id,
        chunk_id=chunk.id,
        page_no=chunk.page_no,
        text=chunk.content,
        source_chunk_ids=[chunk.id],
        source_page_nos=[chunk.page_no] if chunk.page_no is not None else [],
        merged_chunk_count=1,
        matched_terms=matched_terms,
        section_id=chunk.section_id,
        section_title=chunk.section_title,
        section_level=chunk.section_level,
        section_path=chunk.section_path,
        section_summary=chunk.section_summary,
        section_chunk_index=chunk.section_chunk_index,
    )


def build_context_item_from_memory(
    memory_entry: MemoryEntry,
    *,
    score: float,
    matched_terms: list[str],
) -> ContextItem:
    importance_bonus = max(0.0, min(float(memory_entry.importance_score or 0.0), 1.0)) * 0.15
    return ContextItem(
        recall_type="memory",
        score=float(score) + importance_bonus,
        knowledge_base_id=memory_entry.knowledge_base_id,
        document_id=memory_entry.document_id,
        chunk_id=memory_entry.chunk_id,
        text=memory_entry.evidence_text or memory_entry.summary or "",
        source_chunk_ids=[memory_entry.chunk_id],
        source_page_nos=[],
        merged_chunk_count=1,
        memory_entry_id=memory_entry.id,
        entry_name=memory_entry.entry_name,
        matched_terms=matched_terms,
    )


def _merge_recall_types(left: str, right: str) -> str:
    types = dedupe_preserve_order(left.split("+") + right.split("+"))
    return "+".join(types)


def _fill_missing_context_fields(base: ContextItem, other: ContextItem) -> None:
    if not base.knowledge_base_id:
        base.knowledge_base_id = other.knowledge_base_id
    if base.page_no is None:
        base.page_no = other.page_no
    if not base.text:
        base.text = other.text
    if not base.memory_entry_id:
        base.memory_entry_id = other.memory_entry_id
    if not base.entry_name:
        base.entry_name = other.entry_name
    if not base.section_id:
        base.section_id = other.section_id
    if not base.section_title:
        base.section_title = other.section_title
    if base.section_level is None:
        base.section_level = other.section_level
    if not base.section_path:
        base.section_path = other.section_path
    if not base.section_summary:
        base.section_summary = other.section_summary
    if base.section_chunk_index is None:
        base.section_chunk_index = other.section_chunk_index

    base.source_chunk_ids = dedupe_preserve_order(base.source_chunk_ids + other.source_chunk_ids)
    base.source_page_nos = dedupe_preserve_order(base.source_page_nos + other.source_page_nos)
    base.matched_terms = dedupe_preserve_order(base.matched_terms + other.matched_terms)
    base.merged_chunk_count = max(base.merged_chunk_count, other.merged_chunk_count)
    base.recall_type = _merge_recall_types(base.recall_type, other.recall_type)


def merge_context_items(items: list[ContextItem]) -> list[ContextItem]:
    merged: dict[tuple[str, str], ContextItem] = {}

    for item in items:
        key = (item.document_id, item.chunk_id)
        existing = merged.get(key)
        if not existing:
            merged[key] = item.model_copy(deep=True)
            continue

        if item.score > existing.score:
            base = item.model_copy(deep=True)
            other = existing
        else:
            base = existing.model_copy(deep=True)
            other = item

        _fill_missing_context_fields(base, other)
        merged[key] = base

    return list(merged.values())


__all__ = [
    "build_context_item_from_chunk",
    "build_context_item_from_memory",
    "build_context_item_from_vector",
    "dedupe_preserve_order",
    "extract_query_terms",
    "merge_context_items",
]
