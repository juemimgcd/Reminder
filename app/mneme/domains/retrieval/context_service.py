import asyncio
import re
from copy import deepcopy
from typing import Any

from fastapi import HTTPException
from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.vector_store_client import similarity_search_with_score_resilient
from app.mneme.conf.config import settings
from app.mneme.conf.database import open_read_session
from app.mneme.conf.logging import log_event
from app.mneme.crud.chunk import search_chunks_by_keywords
from app.mneme.crud.memory_entry import search_memory_entries_by_keywords
from app.mneme.models import Chunk, MemoryEntry
from app.mneme.schemas.chat import ContextItem
from app.mneme.domains.retrieval.debug import build_retrieval_debug_packet
from app.mneme.domains.retrieval.fusion import fuse_and_rerank_context_items


MetadataFilter = dict[str, int | str]


def build_document_key(doc: LCDocument) -> tuple[Any, ...]:
    chunk_id = doc.metadata.get("chunk_id")
    if chunk_id:
        return ("chunk_id", str(chunk_id))

    return (
        "fallback",
        doc.metadata.get("document_id"),
        doc.metadata.get("page_no"),
        doc.metadata.get("chunk_index"),
        doc.page_content,
    )


def dedupe_preserve_order(items: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)

    return result


def ensure_source_metadata(doc: LCDocument) -> LCDocument:
    source_chunk_ids = doc.metadata.get("source_chunk_ids")
    if not isinstance(source_chunk_ids, list) or not source_chunk_ids:
        chunk_id = doc.metadata.get("chunk_id")
        doc.metadata["source_chunk_ids"] = [str(chunk_id)] if chunk_id else []

    source_page_nos = doc.metadata.get("source_page_nos")
    if not isinstance(source_page_nos, list):
        page_no = doc.metadata.get("page_no")
        doc.metadata["source_page_nos"] = [page_no] if isinstance(page_no, int) else []

    doc.metadata["merged_chunk_count"] = int(doc.metadata.get("merged_chunk_count", 1))
    return doc


def can_merge_documents(
    prev_doc: LCDocument,
    current_doc: LCDocument,
    *,
    max_merged_length: int,
) -> bool:
    prev_index = prev_doc.metadata.get("chunk_index")
    current_index = current_doc.metadata.get("chunk_index")
    same_document = prev_doc.metadata.get("document_id") == current_doc.metadata.get("document_id")
    consecutive = (
        isinstance(prev_index, int)
        and isinstance(current_index, int)
        and current_index == prev_index + 1
    )
    if not (same_document and consecutive):
        return False

    prev_section = prev_doc.metadata.get("section_id")
    current_section = current_doc.metadata.get("section_id")
    if prev_section != current_section:
        return False

    prev_page = prev_doc.metadata.get("page_no")
    current_page = current_doc.metadata.get("page_no")
    page_close = not (
        isinstance(prev_page, int)
        and isinstance(current_page, int)
        and abs(current_page - prev_page) > 1
    )
    if not page_close:
        return False

    return len(prev_doc.page_content) + len(current_doc.page_content) <= max_merged_length


def merge_two_documents(
    prev_doc: LCDocument,
    prev_score: float,
    current_doc: LCDocument,
    current_score: float,
) -> tuple[LCDocument, float]:
    prev_doc.page_content = f"{prev_doc.page_content}\n{current_doc.page_content}"
    source_page_nos = dedupe_preserve_order(
        prev_doc.metadata["source_page_nos"] + current_doc.metadata["source_page_nos"]
    )

    prev_doc.metadata["source_chunk_ids"] = dedupe_preserve_order(
        prev_doc.metadata["source_chunk_ids"] + current_doc.metadata["source_chunk_ids"]
    )
    prev_doc.metadata["source_page_nos"] = source_page_nos
    prev_doc.metadata["merged_chunk_count"] += current_doc.metadata["merged_chunk_count"]
    prev_doc.metadata["chunk_index"] = current_doc.metadata.get("chunk_index")
    prev_doc.metadata["page_no"] = source_page_nos[0] if len(source_page_nos) == 1 else None

    return prev_doc, min(prev_score, current_score)


def build_metadata_filter(
    *,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
) -> MetadataFilter:
    metadata_filter: MetadataFilter = {}
    if user_id is not None:
        metadata_filter["user_id"] = user_id
    if knowledge_base_id:
        metadata_filter["knowledge_base_id"] = knowledge_base_id
    return metadata_filter


def build_milvus_expr(metadata_filter: MetadataFilter) -> str | None:
    if not metadata_filter:
        return None

    expr_parts: list[str] = []
    for key, value in metadata_filter.items():
        if isinstance(value, str):
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            expr_parts.append(f'{key} == "{escaped_value}"')
        else:
            expr_parts.append(f"{key} == {value}")
    return " and ".join(expr_parts)


def build_similarity_search_kwargs(
    query: str,
    *,
    top_k: int = 4,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
) -> dict[str, Any]:
    metadata_filter = build_metadata_filter(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    expr = build_milvus_expr(metadata_filter)
    search_kwargs: dict[str, Any] = {
        "query": query,
        "k": top_k,
    }
    if expr:
        search_kwargs["expr"] = expr
    return search_kwargs


async def retrieve_documents_with_scores(
    query: str,
    top_k: int = 4,
    *,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
) -> list[tuple[LCDocument, float]]:
    search_kwargs = build_similarity_search_kwargs(
        query,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    log_event(
        "context_service",
        "debug",
        "context.retrieve.start",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        top_k=top_k,
        has_expr="expr" in search_kwargs,
    )
    return await similarity_search_with_score_resilient(**search_kwargs)


def build_source_item(doc: LCDocument, *, source_id: str) -> dict[str, Any]:
    ensure_source_metadata(doc)
    source_chunk_ids = doc.metadata["source_chunk_ids"]
    source_page_nos = doc.metadata["source_page_nos"]
    if len(source_chunk_ids) <= 1:
        chunk_ref = source_chunk_ids[0] if source_chunk_ids else doc.metadata.get("chunk_id")
    else:
        chunk_ref = f"{source_chunk_ids[0]}..{source_chunk_ids[-1]}"

    return {
        "source_id": source_id,
        "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
        "document_id": doc.metadata.get("document_id"),
        "chunk_id": chunk_ref,
        "page_no": source_page_nos[0] if len(source_page_nos) == 1 else None,
        "text": doc.page_content,
        "source_chunk_ids": source_chunk_ids,
        "source_page_nos": source_page_nos,
        "merged_chunk_count": doc.metadata.get("merged_chunk_count", 1),
    }


def deduplicate_retrieved_documents(
    items: list[tuple[LCDocument, float]],
) -> list[tuple[LCDocument, float]]:
    deduped: list[tuple[LCDocument, float]] = []
    seen_keys: set[tuple[Any, ...]] = set()
    seen_text_keys: set[tuple[Any, ...]] = set()

    for doc, score in items:
        key = build_document_key(doc)
        if key in seen_keys:
            continue

        text_key = (
            doc.metadata.get("document_id"),
            doc.metadata.get("page_no"),
            doc.page_content,
        )
        if text_key in seen_text_keys:
            continue

        seen_keys.add(key)
        seen_text_keys.add(text_key)
        deduped.append((doc, score))

    return deduped


def merge_adjacent_scored_documents(
    items: list[tuple[LCDocument, float]],
    *,
    max_merged_length: int = 1200,
) -> list[tuple[LCDocument, float]]:
    merged: list[tuple[LCDocument, float]] = []

    for doc, score in items:
        current_doc = ensure_source_metadata(deepcopy(doc))

        if not merged:
            merged.append((current_doc, score))
            continue

        prev_doc, prev_score = merged[-1]
        if can_merge_documents(
            prev_doc,
            current_doc,
            max_merged_length=max_merged_length,
        ):
            merged[-1] = merge_two_documents(
                prev_doc,
                prev_score,
                current_doc,
                score,
            )
            continue

        merged.append((current_doc, score))

    return merged


def trim_scored_documents_by_budget(
    items: list[tuple[LCDocument, float]],
    *,
    max_chars: int,
) -> list[tuple[LCDocument, float]]:
    if max_chars <= 0:
        return []

    kept: list[tuple[LCDocument, float]] = []
    total_chars = 0

    for doc, score in items:
        current_length = len(doc.page_content)
        if kept and total_chars + current_length > max_chars:
            break
        if not kept and current_length > max_chars:
            kept.append((doc, score))
            break

        kept.append((doc, score))
        total_chars += current_length

    return kept


def format_context_docs(docs: list[LCDocument]) -> str:
    sections: list[str] = []
    for index, doc in enumerate(docs, start=1):
        source_id = f"S{index}"
        ensure_source_metadata(doc)
        sections.append(
            "\n".join(
                [
                    f"[Source {source_id}]",
                    f"source_id={source_id}",
                    f"knowledge_base_id={doc.metadata.get('knowledge_base_id')}",
                    f"document_id={doc.metadata.get('document_id')}",
                    f"chunk_id={doc.metadata.get('chunk_id')}",
                    f"source_chunk_ids={doc.metadata.get('source_chunk_ids')}",
                    f"page_no={doc.metadata.get('page_no')}",
                    f"section_title={doc.metadata.get('section_title')}",
                    f"section_path={doc.metadata.get('section_path')}",
                    f"section_summary={doc.metadata.get('section_summary')}",
                    f"text={doc.page_content}",
                ]
            )
        )
    return "\n\n".join(sections)


async def build_query_context(
    query: str,
    *,
    db: AsyncSession,
    top_k: int = 4,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
    context_budget: int | None = None,
) -> dict[str, Any]:
    if not knowledge_base_id:
        raise HTTPException(status_code=400, detail="Knowledge base id not provided")

    context_budget = context_budget or settings.RETRIEVAL_CONTEXT_BUDGET_CHARS
    vector_recall_k = max(top_k, settings.RETRIEVAL_VECTOR_RECALL_K)
    keyword_recall_k = max(top_k, settings.RETRIEVAL_KEYWORD_RECALL_K)
    memory_recall_k = max(top_k, settings.RETRIEVAL_MEMORY_RECALL_K)

    vector_task = asyncio.create_task(
        retrieve_documents_with_scores(
            query=query,
            top_k=vector_recall_k,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    query_terms = extract_query_terms(query)

    async with open_read_session() as keyword_db, open_read_session() as memory_db:
        keyword_task = asyncio.create_task(
            search_chunks_by_keywords(
                keyword_db,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                query_terms=query_terms,
                limit=keyword_recall_k,
            )
        )
        memory_task = asyncio.create_task(
            search_memory_entries_by_keywords(
                memory_db,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                query_terms=query_terms,
                limit=memory_recall_k,
            )
        )
        raw_vector_items, chunk_rows, memory_rows = await asyncio.gather(vector_task, keyword_task, memory_task)

    deduped_vector_items = deduplicate_retrieved_documents(raw_vector_items)
    merged_vector_docs = merge_adjacent_scored_documents(deduped_vector_items)
    vector_items = [
        build_context_item_from_vector(doc, score)
        for doc, score in merged_vector_docs
    ]

    keyword_items = [
        build_context_item_from_chunk(
            chunk,
            score=score,
            knowledge_base_id=knowledge_base_id,
            matched_terms=[
                term
                for term in query_terms
                if term.lower() in " ".join(
                    [
                        chunk.content or "",
                        chunk.section_title or "",
                        chunk.section_path or "",
                        chunk.section_summary or "",
                    ]
                ).lower()
            ],
        )
        for chunk, score in chunk_rows
    ]
    lexical_backend = "postgres_keyword_ranked"

    memory_items = [
        build_context_item_from_memory(
            row,
            score=score,
            matched_terms=[
                term
                for term in query_terms
                if term.lower() in (row.entry_name or "").lower()
                or term.lower() in (row.summary or "").lower()
                or term.lower() in (row.evidence_text or "").lower()
            ],
        )
        for row, score in memory_rows
    ]

    reranked_items = await fuse_and_rerank_context_items(
        query=query,
        vector_items=vector_items,
        lexical_items=keyword_items,
        memory_items=memory_items,
        query_terms=query_terms,
    )

    final_items: list[ContextItem] = []
    total_chars = 0
    for item in reranked_items:
        item_len = len(item.text)
        if len(final_items) >= top_k:
            break
        if final_items and total_chars + item_len > context_budget:
            break
        final_items.append(item)
        total_chars += item_len

    final_docs: list[LCDocument] = []
    for item in final_items:
        final_docs.append(
            LCDocument(
                page_content=item.text,
                metadata={
                    "knowledge_base_id": item.knowledge_base_id,
                    "document_id": item.document_id,
                    "chunk_id": item.chunk_id,
                    "page_no": item.page_no,
                    "source_chunk_ids": item.source_chunk_ids or [item.chunk_id],
                    "source_page_nos": item.source_page_nos,
                    "merged_chunk_count": item.merged_chunk_count,
                    "section_id": item.section_id,
                    "section_title": item.section_title,
                    "section_level": item.section_level,
                    "section_path": item.section_path,
                    "section_summary": item.section_summary,
                    "section_chunk_index": item.section_chunk_index,
                    "recall_type": item.recall_type,
                    "fusion_score": item.fusion_score,
                    "rerank_score": item.rerank_score,
                    "exact_match_count": item.exact_match_count,
                    "recall_ranks": item.recall_ranks,
                    "rerank_reasons": item.rerank_reasons,
                },
            )
        )

    counts = {
        "raw_count": len(raw_vector_items),
        "dedup_count": len(deduped_vector_items),
        "merged_count": len(merged_vector_docs),
        "vector_count": len(vector_items),
        "lexical_count": len(keyword_items),
        "memory_count": len(memory_items),
        "candidate_count": len(vector_items) + len(keyword_items) + len(memory_items),
        "fusion_count": len(reranked_items),
        "rerank_count": len(reranked_items),
        "final_count": len(final_items),
    }

    return {
        "context_text": format_context_docs(final_docs),
        "sources": [
            build_source_item(doc, source_id=f"S{index}")
            for index, doc in enumerate(final_docs, start=1)
        ],
        "raw_count": counts["raw_count"],
        "dedup_count": counts["dedup_count"],
        "vector_count": counts["vector_count"],
        "keyword_count": counts["lexical_count"],
        "lexical_backend": lexical_backend,
        "memory_count": counts["memory_count"],
        "candidate_count": counts["candidate_count"],
        "merged_count": counts["merged_count"],
        "fusion_count": counts["fusion_count"],
        "rerank_count": counts["rerank_count"],
        "final_count": counts["final_count"],
        "debug": build_retrieval_debug_packet(
            query_terms=query_terms,
            lexical_backend=lexical_backend,
            counts=counts,
            vector_items=vector_items,
            lexical_items=keyword_items,
            memory_items=memory_items,
            fused_items=reranked_items,
            final_items=final_items,
        ),
    }


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
