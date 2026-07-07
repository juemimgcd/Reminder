from datetime import datetime
import re
from typing import Any

from app.mneme.schemas.graph_rag import (
    GraphRagContextItem,
    GraphRagDecisionData,
    GraphRagEvalComparisonData,
    GraphRagExpansionItem,
    GraphRagSeedItem,
)
from app.mneme.services.eval_service import dedupe_preserve_order, evaluate_retrieval, extract_terms
from app.mneme.domains.graph.service import _build_related_document_edges


GRAPH_QUERY_MARKERS = (
    "relation",
    "related",
    "relationship",
    "conflict",
    "contradict",
    "timeline",
    "evolution",
    "dependency",
    "impact",
    "\u5173\u7cfb",
    "\u5173\u8054",
    "\u51b2\u7a81",
    "\u53d8\u5316",
    "\u6f14\u5316",
    "\u65f6\u95f4\u7ebf",
    "\u5f71\u54cd",
    "\u4f9d\u8d56",
    "\u5171\u540c",
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _document_id_from_node(node_id: str) -> str:
    return node_id.removeprefix("document:")


def _document_name(document: Any | None) -> str | None:
    if document is None:
        return None
    return getattr(document, "file_name", None)


def _entry_text(entry: Any) -> str:
    return _normalize_text(
        " ".join(
            [
                str(getattr(entry, "entry_name", "") or ""),
                str(getattr(entry, "entry_type", "") or ""),
                str(getattr(entry, "summary", "") or ""),
                str(getattr(entry, "evidence_text", "") or ""),
            ]
        )
    )


def _memory_signature(entry: Any) -> tuple[str, str]:
    return (
        _normalize_text(getattr(entry, "entry_name", None)),
        _normalize_text(getattr(entry, "entry_type", None)),
    )


def _shared_memory_signature(item: dict[str, Any]) -> tuple[str, str]:
    return (
        _normalize_text(item.get("entry_name")),
        _normalize_text(item.get("entry_type")),
    )


def extract_graph_query_terms(query: str) -> list[str]:
    terms = extract_terms(query)
    extra_terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,}", query.lower())
    return dedupe_preserve_order([*terms, *extra_terms])


def find_seed_memory_entries(
    *,
    entries: list[Any],
    query_terms: list[str],
    limit: int,
) -> list[GraphRagSeedItem]:
    seeds: list[GraphRagSeedItem] = []
    for entry in entries:
        text = _entry_text(entry)
        matched_terms = [term for term in query_terms if term.lower() in text]
        if not matched_terms:
            continue
        importance_score = float(getattr(entry, "importance_score", 0.0) or 0.0)
        score = round(
            min(len(matched_terms) / max(len(query_terms), 1), 1.0) * 0.7
            + min(importance_score, 1.0) * 0.3,
            4,
        )
        seeds.append(
            GraphRagSeedItem(
                entry_id=getattr(entry, "id"),
                entry_name=getattr(entry, "entry_name"),
                entry_type=getattr(entry, "entry_type"),
                summary=getattr(entry, "summary"),
                document_id=getattr(entry, "document_id"),
                chunk_id=getattr(entry, "chunk_id"),
                matched_terms=matched_terms,
                score=score,
                importance_score=importance_score,
                created_at=getattr(entry, "created_at"),
            )
        )

    seeds.sort(
        key=lambda item: (
            -item.score,
            -item.importance_score,
            item.entry_name,
            item.entry_id,
        )
    )
    return seeds[:limit]


def collect_expansion_evidence(
    *,
    entries: list[Any],
    source_document_id: str,
    target_document_id: str,
    shared_memories: list[dict[str, Any]],
) -> list[str]:
    shared_signatures = {_shared_memory_signature(item) for item in shared_memories}
    evidence_ids = [
        getattr(entry, "id")
        for entry in entries
        if getattr(entry, "document_id", None) in {source_document_id, target_document_id}
        and _memory_signature(entry) in shared_signatures
    ]
    return dedupe_preserve_order(evidence_ids)


def build_graph_expansions(
    *,
    documents: list[Any],
    entries: list[Any],
    seed_document_ids: set[str],
    max_expansions: int,
) -> list[GraphRagExpansionItem]:
    if not seed_document_ids or max_expansions <= 0:
        return []

    related_edges = _build_related_document_edges(
        documents=documents,
        memory_entries=entries,
        min_shared_memory_count=1,
        min_relationship_score=0.0,
        max_related_edges=None,
    )
    expansions: list[GraphRagExpansionItem] = []
    for edge in related_edges:
        source_document_id = _document_id_from_node(edge["source"])
        target_document_id = _document_id_from_node(edge["target"])
        if source_document_id not in seed_document_ids and target_document_id not in seed_document_ids:
            continue

        metadata = edge.get("metadata") or {}
        shared_memories = metadata.get("shared_memories") or []
        expansions.append(
            GraphRagExpansionItem(
                edge_id=edge["id"],
                source_document_id=source_document_id,
                target_document_id=target_document_id,
                source_document_name=metadata.get("source_document_name"),
                target_document_name=metadata.get("target_document_name"),
                relationship_score=float(metadata.get("relationship_score") or 0.0),
                shared_memory_count=int(metadata.get("shared_memory_count") or 0),
                shared_memories=shared_memories,
                evidence_entry_ids=collect_expansion_evidence(
                    entries=entries,
                    source_document_id=source_document_id,
                    target_document_id=target_document_id,
                    shared_memories=shared_memories,
                ),
                relationship_rank=metadata.get("relationship_rank"),
            )
        )

    expansions.sort(
        key=lambda item: (
            -item.relationship_score,
            -item.shared_memory_count,
            item.source_document_id,
            item.target_document_id,
        )
    )
    return expansions[:max_expansions]


def build_graph_contexts(
    *,
    documents: list[Any],
    entries: list[Any],
    seeds: list[GraphRagSeedItem],
    expansions: list[GraphRagExpansionItem],
) -> list[GraphRagContextItem]:
    documents_by_id = {getattr(document, "id"): document for document in documents}
    entries_by_id = {getattr(entry, "id"): entry for entry in entries}
    seed_document_ids = {seed.document_id for seed in seeds}
    contexts: list[GraphRagContextItem] = []

    for seed in seeds:
        entry = entries_by_id.get(seed.entry_id)
        contexts.append(
            GraphRagContextItem(
                context_id=f"memory_entry:{seed.entry_id}",
                context_type="seed",
                document_id=seed.document_id,
                document_name=_document_name(documents_by_id.get(seed.document_id)),
                chunk_id=seed.chunk_id,
                memory_entry_ids=[seed.entry_id],
                score=seed.score,
                reason=f"matched query terms: {', '.join(seed.matched_terms)}",
                text=" ".join(
                    [
                        str(seed.summary or ""),
                        str(getattr(entry, "evidence_text", "") if entry else ""),
                    ]
                ).strip(),
            )
        )

    seen_expansion_documents: set[str] = set()
    for expansion in expansions:
        related_document_ids = [
            document_id
            for document_id in (expansion.source_document_id, expansion.target_document_id)
            if document_id not in seed_document_ids
        ]
        if not related_document_ids:
            related_document_ids = [expansion.target_document_id]

        for document_id in related_document_ids:
            if document_id in seen_expansion_documents:
                continue
            seen_expansion_documents.add(document_id)
            evidence_entries = [
                entries_by_id[entry_id]
                for entry_id in expansion.evidence_entry_ids
                if entry_id in entries_by_id and getattr(entries_by_id[entry_id], "document_id", None) == document_id
            ]
            if not evidence_entries:
                evidence_entries = [
                    entries_by_id[entry_id]
                    for entry_id in expansion.evidence_entry_ids
                    if entry_id in entries_by_id
                ]
            chunk_id = getattr(evidence_entries[0], "chunk_id", None) if evidence_entries else None
            text_parts = [
                f"{entry.entry_name}: {entry.summary}"
                for entry in evidence_entries[:3]
            ]
            if not text_parts:
                text_parts = [
                    f"{item.get('entry_name')}: shared memory"
                    for item in expansion.shared_memories[:3]
                ]
            contexts.append(
                GraphRagContextItem(
                    context_id=f"graph_edge:{expansion.edge_id}:{document_id}",
                    context_type="expansion",
                    document_id=document_id,
                    document_name=_document_name(documents_by_id.get(document_id)),
                    chunk_id=chunk_id,
                    memory_entry_ids=[getattr(entry, "id") for entry in evidence_entries],
                    score=expansion.relationship_score,
                    reason="document connected by shared governed memory",
                    text="\n".join(text_parts),
                )
            )

    contexts.sort(
        key=lambda item: (
            item.context_type != "seed",
            -item.score,
            item.document_id,
        )
    )
    return contexts


def should_use_graph_expansion(
    *,
    query: str,
    seeds: list[GraphRagSeedItem],
    expansions: list[GraphRagExpansionItem],
) -> tuple[bool, str]:
    normalized_query = _normalize_text(query)
    has_graph_marker = any(marker in normalized_query for marker in GRAPH_QUERY_MARKERS)
    if not seeds:
        return False, "No seed memory matched the query."
    if not expansions:
        return False, "Seed memories were found, but no related document edges were available."
    if has_graph_marker:
        return True, "The query asks for relationship, conflict, timeline, or dependency evidence."
    if len({seed.document_id for seed in seeds}) > 1:
        return True, "The query matched multiple seed documents, so graph expansion can help compare context."
    return True, "Related document evidence is available for the matched seed memory."


def build_graph_rag_decision(
    *,
    knowledge_base_id: str,
    query: str,
    documents: list[Any],
    entries: list[Any],
    top_k: int = 6,
    max_expansions: int = 8,
) -> GraphRagDecisionData:
    query_terms = extract_graph_query_terms(query)
    seeds = find_seed_memory_entries(
        entries=entries,
        query_terms=query_terms,
        limit=top_k,
    )
    seed_document_ids = {seed.document_id for seed in seeds}
    expansions = build_graph_expansions(
        documents=documents,
        entries=entries,
        seed_document_ids=seed_document_ids,
        max_expansions=max_expansions,
    )
    contexts = build_graph_contexts(
        documents=documents,
        entries=entries,
        seeds=seeds,
        expansions=expansions,
    )[:top_k]
    graph_useful, reason = should_use_graph_expansion(
        query=query,
        seeds=seeds,
        expansions=expansions,
    )

    return GraphRagDecisionData(
        knowledge_base_id=knowledge_base_id,
        query=query,
        query_terms=query_terms,
        graph_useful=graph_useful,
        reason=reason,
        seed_count=len(seeds),
        expansion_count=len(expansions),
        context_count=len(contexts),
        generated_at=datetime.now(),
        seeds=seeds,
        expansions=expansions,
        contexts=contexts,
    )


def _debug_from_chunk_ids(chunk_ids: list[str]) -> dict[str, Any]:
    return {
        "final_context": [
            {"chunk_id": chunk_id}
            for chunk_id in dedupe_preserve_order(chunk_ids)
        ]
    }


def compare_graph_retrieval(
    *,
    decision: GraphRagDecisionData,
    expected_source_chunk_ids: list[str],
    k: int,
) -> GraphRagEvalComparisonData:
    baseline_chunk_ids = [
        context.chunk_id
        for context in decision.contexts
        if context.context_type == "seed" and context.chunk_id
    ]
    graph_chunk_ids = [
        context.chunk_id
        for context in decision.contexts
        if context.chunk_id
    ]
    baseline = evaluate_retrieval(
        expected_source_chunk_ids=expected_source_chunk_ids,
        debug=_debug_from_chunk_ids(baseline_chunk_ids),
        k=k,
    )
    graph = evaluate_retrieval(
        expected_source_chunk_ids=expected_source_chunk_ids,
        debug=_debug_from_chunk_ids(graph_chunk_ids),
        k=k,
    )
    return GraphRagEvalComparisonData(
        query=decision.query,
        expected_source_chunk_ids=expected_source_chunk_ids,
        baseline_chunk_ids=dedupe_preserve_order(baseline_chunk_ids),
        graph_chunk_ids=dedupe_preserve_order(graph_chunk_ids),
        baseline=baseline,
        graph=graph,
        delta={
            "recall_at_k": round(graph.recall_at_k - baseline.recall_at_k, 4),
            "mrr": round(graph.mrr - baseline.mrr, 4),
            "ndcg": round(graph.ndcg - baseline.ndcg, 4),
        },
    )
