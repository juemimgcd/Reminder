from typing import Any

from schemas.chat import ContextItem, QueryRouteDecision


def preview_text(text: str, *, max_chars: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def serialize_context_item(item: ContextItem, *, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "recall_type": item.recall_type,
        "document_id": item.document_id,
        "chunk_id": item.chunk_id,
        "memory_entry_id": item.memory_entry_id,
        "entry_name": item.entry_name,
        "page_no": item.page_no,
        "section_title": item.section_title,
        "section_path": item.section_path,
        "matched_terms": item.matched_terms,
        "score": item.score,
        "vector_score": item.vector_score,
        "keyword_score": item.keyword_score,
        "memory_score": item.memory_score,
        "fusion_score": item.fusion_score,
        "rerank_score": item.rerank_score,
        "exact_match_count": item.exact_match_count,
        "recall_ranks": item.recall_ranks,
        "rerank_reasons": item.rerank_reasons,
        "text_preview": preview_text(item.text),
    }


def serialize_context_items(items: list[ContextItem], *, limit: int = 10) -> list[dict[str, Any]]:
    return [
        serialize_context_item(item, rank=index)
        for index, item in enumerate(items[:limit], start=1)
    ]


def build_non_retrieval_debug(
    *,
    route: QueryRouteDecision,
    reason: str,
) -> dict[str, Any]:
    return {
        "route": route.model_dump(),
        "query_terms": [],
        "lexical_backend": None,
        "counts": {
            "vector_count": 0,
            "lexical_count": 0,
            "memory_count": 0,
            "candidate_count": 0,
            "fusion_count": 0,
            "rerank_count": 0,
            "final_count": 0,
        },
        "vector_candidates": [],
        "lexical_candidates": [],
        "memory_candidates": [],
        "fused_candidates": [],
        "final_context": [],
        "answer_debug": {
            "path": route.target_pipeline,
            "reason": reason,
            "source_count": 0,
            "citation_count": 0,
        },
    }


def build_retrieval_debug_packet(
    *,
    query_terms: list[str],
    lexical_backend: str,
    counts: dict[str, int],
    vector_items: list[ContextItem],
    lexical_items: list[ContextItem],
    memory_items: list[ContextItem],
    fused_items: list[ContextItem],
    final_items: list[ContextItem],
) -> dict[str, Any]:
    return {
        "route": None,
        "query_terms": query_terms,
        "lexical_backend": lexical_backend,
        "counts": counts,
        "vector_candidates": serialize_context_items(vector_items),
        "lexical_candidates": serialize_context_items(lexical_items),
        "memory_candidates": serialize_context_items(memory_items),
        "fused_candidates": serialize_context_items(fused_items),
        "final_context": serialize_context_items(final_items),
        "answer_debug": None,
    }


def build_answer_debug(
    *,
    answer: str,
    sources: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    confidence: str,
    uncertainty: str | None,
    citation_validation: dict[str, Any] | None = None,
    invalid_citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cited_source_ids = [
        citation["source_id"]
        for citation in citations
        if citation.get("source_id")
    ]
    available_source_ids = [
        source["source_id"]
        for source in sources
        if source.get("source_id")
    ]
    return {
        "answer_length": len(answer),
        "source_count": len(sources),
        "citation_count": len(citations),
        "available_source_ids": available_source_ids,
        "cited_source_ids": cited_source_ids,
        "confidence": confidence,
        "uncertainty": uncertainty,
        "citation_validation": citation_validation,
        "invalid_citations": invalid_citations or [],
    }
