from copy import deepcopy
from typing import Any

from langchain_core.documents import Document as LCDocument

from clients.vector_store_client import get_vector_store


MetadataFilter = dict[str, int | str]


def build_document_key(doc: LCDocument) -> tuple:
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


def dedupe_preserve_order(items: list) -> list:
    seen: set = set()
    result: list = []

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
    if user_id:
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
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
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
):
    vector_store = get_vector_store()
    search_kwargs = build_similarity_search_kwargs(
        query,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    return vector_store.similarity_search_with_score(**search_kwargs)


def build_source_item(doc: LCDocument) -> dict:
    ensure_source_metadata(doc)
    source_chunk_ids = doc.metadata["source_chunk_ids"]
    source_page_nos = doc.metadata["source_page_nos"]
    if len(source_chunk_ids) <= 1:
        chunk_ref = source_chunk_ids[0] if source_chunk_ids else doc.metadata.get("chunk_id")
    else:
        chunk_ref = f"{source_chunk_ids[0]}..{source_chunk_ids[-1]}"

    return {
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
    seen_keys: set[tuple] = set()
    seen_text_keys: set[tuple] = set()

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
        sections.append(
            "\n".join(
                [
                    f"[片段 {index}]",
                    f"knowledge_base_id={doc.metadata.get('knowledge_base_id')}",
                    f"document_id={doc.metadata.get('document_id')}",
                    f"chunk_id={doc.metadata.get('chunk_id')}",
                    f"page_no={doc.metadata.get('page_no')}",
                    f"text={doc.page_content}",
                ]
            )
        )
    return "\n\n".join(sections)



async def build_query_context(
        query: str,
        *,
        top_k: int = 4,
        user_id: int | None = None,
        knowledge_base_id: str | None = None,
        context_budget: int = 4000,
) -> dict:
    raw_items = await retrieve_documents_with_scores(
        query=query,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )

    deduped_items = deduplicate_retrieved_documents(raw_items)
    merged_items = merge_adjacent_scored_documents(deduped_items)
    final_items = trim_scored_documents_by_budget(
        merged_items,
        max_chars=context_budget,
    )

    final_docs = [doc for doc, _ in final_items]

    return {
        "context_text": format_context_docs(final_docs),
        "sources": [build_source_item(doc) for doc in final_docs],
        "raw_count": len(raw_items),
        "dedup_count": len(deduped_items),
        "merged_count": len(merged_items),
        "final_count": len(final_items),
    }












