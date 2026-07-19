from app.mneme.clients.reranker_client import rerank_pairs
from app.mneme.conf.config import settings
from app.mneme.schemas.chat import ContextItem

RRF_K = 60
RECALL_WEIGHTS = {
    "vector": 1.0,
    "keyword": 0.75,
    "memory": 0.9,
}
SCORE_FIELDS = {
    "vector": "vector_score",
    "keyword": "keyword_score",
    "memory": "memory_score",
}


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def merge_recall_types(left: str, right: str) -> str:
    return "+".join(dedupe_preserve_order(left.split("+") + right.split("+")))


def build_candidate_key(item: ContextItem) -> tuple[str, str]:
    if item.chunk_id:
        return (item.document_id, item.chunk_id)
    if item.memory_entry_id:
        return ("memory", item.memory_entry_id)
    return (item.document_id, item.text[:120])


def fill_missing_context_fields(base: ContextItem, other: ContextItem) -> None:
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
    base.source_page_nos = list(dict.fromkeys(base.source_page_nos + other.source_page_nos))
    base.matched_terms = dedupe_preserve_order(base.matched_terms + other.matched_terms)
    base.merged_chunk_count = max(base.merged_chunk_count, other.merged_chunk_count)
    base.recall_type = merge_recall_types(base.recall_type, other.recall_type)


def attach_source_score(item: ContextItem, recall_type: str, score: float, rank: int) -> None:
    score_field = SCORE_FIELDS.get(recall_type)
    if score_field:
        setattr(item, score_field, score)
    item.recall_ranks[recall_type] = rank


def fuse_context_items_by_rrf(
    *,
    recall_groups: dict[str, list[ContextItem]],
    rrf_k: int = RRF_K,
) -> list[ContextItem]:
    candidates: dict[tuple[str, str], ContextItem] = {}

    for recall_type, items in recall_groups.items():
        weight = RECALL_WEIGHTS.get(recall_type, 1.0)
        ranked_items = sorted(items, key=lambda item: item.score, reverse=True)
        for rank, item in enumerate(ranked_items, start=1):
            key = build_candidate_key(item)
            contribution = weight / (rrf_k + rank)
            existing = candidates.get(key)
            if not existing:
                candidate = item.model_copy(deep=True)
                candidate.fusion_score = 0.0
                candidate.recall_ranks = {}
                candidate.rerank_reasons = []
                attach_source_score(candidate, recall_type, item.score, rank)
                candidates[key] = candidate
            else:
                candidate = existing
                fill_missing_context_fields(candidate, item)
                attach_source_score(candidate, recall_type, item.score, rank)

            candidate.fusion_score = float(candidate.fusion_score or 0.0) + contribution
            candidate.score = candidate.fusion_score

    return sorted(
        candidates.values(),
        key=lambda item: (
            item.fusion_score or 0.0,
            len(item.recall_type.split("+")),
            item.score,
        ),
        reverse=True,
    )


def count_term_matches(text: str, query_terms: list[str]) -> int:
    normalized = text.lower()
    return sum(1 for term in query_terms if term.lower() in normalized)


def rerank_context_items(
    items: list[ContextItem],
    *,
    query_terms: list[str],
) -> list[ContextItem]:
    reranked: list[ContextItem] = []
    for item in items:
        candidate = item.model_copy(deep=True)
        base_score = float(candidate.fusion_score or candidate.score)
        text_match_count = count_term_matches(candidate.text, query_terms)
        section_text = " ".join(
            value
            for value in [
                candidate.section_title,
                candidate.section_path,
                candidate.section_summary,
                candidate.entry_name,
            ]
            if value
        )
        section_match_count = count_term_matches(section_text, query_terms)
        source_count = len(candidate.recall_type.split("+"))

        matched_term_count = len(candidate.matched_terms)
        exact_match_count = max(text_match_count + section_match_count, matched_term_count)
        bonus = 0.0
        reasons: list[str] = []
        if exact_match_count:
            bonus += min(exact_match_count, 3) * 0.003
            reasons.append("exact_text_match")
        if section_match_count:
            bonus += min(section_match_count, 2) * 0.004
            reasons.append("section_match")
        if source_count > 1:
            bonus += min(source_count - 1, 2) * 0.003
            reasons.append("multi_source")

        candidate.exact_match_count = exact_match_count
        candidate.rerank_score = base_score + bonus
        candidate.score = candidate.rerank_score
        candidate.rerank_reasons = reasons
        reranked.append(candidate)

    return sorted(
        reranked,
        key=lambda item: (
            item.rerank_score or 0.0,
            item.fusion_score or 0.0,
            len(item.recall_type.split("+")),
        ),
        reverse=True,
    )


def build_reranker_text(item: ContextItem) -> str:
    sections = [
        item.section_title or "",
        item.section_path or "",
        item.section_summary or "",
        item.entry_name or "",
        item.text or "",
    ]
    return "\n".join(part for part in sections if part).strip()


async def apply_model_rerank(
    items: list[ContextItem],
    *,
    query: str,
) -> list[ContextItem]:
    if not settings.RERANKER_ENABLED or not items:
        return items

    rerank_candidate_k = max(1, settings.RETRIEVAL_RERANK_CANDIDATE_K)
    head = [item.model_copy(deep=True) for item in items[:rerank_candidate_k]]
    tail = [item.model_copy(deep=True) for item in items[rerank_candidate_k:]]
    pairs = [(query, build_reranker_text(item)) for item in head]
    scores = await rerank_pairs(pairs=pairs)
    if not scores:
        return items

    for item, score in zip(head, scores, strict=False):
        item.rerank_score = score
        item.score = score
        item.rerank_reasons = dedupe_preserve_order(item.rerank_reasons + ["bge_reranker"])

    head = sorted(
        head,
        key=lambda item: (
            item.rerank_score or 0.0,
            item.fusion_score or 0.0,
            len(item.recall_type.split("+")),
        ),
        reverse=True,
    )
    return head + tail


async def fuse_and_rerank_context_items(
    *,
    query: str,
    vector_items: list[ContextItem],
    lexical_items: list[ContextItem],
    memory_items: list[ContextItem],
    query_terms: list[str],
) -> list[ContextItem]:
    fused_items = fuse_context_items_by_rrf(
        recall_groups={
            "vector": vector_items,
            "keyword": lexical_items,
            "memory": memory_items,
        }
    )
    heuristically_reranked = rerank_context_items(fused_items, query_terms=query_terms)
    return await apply_model_rerank(heuristically_reranked, query=query)
