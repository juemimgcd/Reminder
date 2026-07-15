from typing import Any

from app.mneme.agent.orchestrator import build_growth_answer, build_profile_answer, serialize_route
from app.mneme.agent.router import route_answer_mode
from app.mneme.agent.runtime_context import AgentRunContext
from app.mneme.agent.tools.base import ToolErrorKind
from app.mneme.agent.tools.contracts import BackendToolResult
from app.mneme.crud.memory_entry import search_memory_entries_by_keywords
from app.mneme.domains.profile.insight import build_growth_for_knowledge_base, build_profile_for_knowledge_base
from app.mneme.domains.retrieval.context_service import build_query_context, extract_query_terms


async def search_knowledge_base(
    *,
    query: str,
    top_k: int,
    context: AgentRunContext,
) -> BackendToolResult:
    packet = await build_query_context(
        query=query,
        db=context.db,
        top_k=top_k,
        user_id=context.user_id,
        knowledge_base_id=context.knowledge_base_id,
    )
    sources = packet["sources"]
    if not sources:
        return _empty_evidence_error("kb_search", "No knowledge-base evidence matched the query.")
    counts = _retrieval_counts(packet)
    return BackendToolResult.success(
        tool_name="kb_search",
        evidence={
            "kind": "knowledge_base_search",
            "query": query,
            "context": packet["context_text"],
            "retrieval_counts": counts,
        },
        fallback_answer=_render_source_fallback(sources),
        sources=sources,
        confidence="medium",
        route=serialize_route(route_answer_mode("kb_qa")),
        debug=packet["debug"],
    )


async def search_memory(
    *,
    query: str,
    top_k: int,
    context: AgentRunContext,
) -> BackendToolResult:
    rows = await search_memory_entries_by_keywords(
        context.db,
        knowledge_base_id=context.knowledge_base_id,
        user_id=context.user_id,
        query_terms=extract_query_terms(query),
        limit=top_k,
    )
    if not rows:
        return _empty_evidence_error("memory_search", "No stored memory evidence matched the query.")

    records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for index, (entry, score) in enumerate(rows, start=1):
        source_id = f"M{index}"
        evidence_text = entry.evidence_text or entry.summary
        records.append(
            {
                "source_id": source_id,
                "memory_entry_id": entry.id,
                "entry_name": entry.entry_name,
                "entry_type": entry.entry_type,
                "summary": entry.summary,
                "evidence_text": evidence_text,
                "keyword_score": score,
                "importance_score": entry.importance_score,
                "confidence": entry.confidence,
                "last_seen_at": entry.last_seen_at.isoformat(),
            }
        )
        sources.append(
            {
                "source_id": source_id,
                "knowledge_base_id": entry.knowledge_base_id,
                "document_id": entry.document_id,
                "chunk_id": entry.chunk_id,
                "page_no": None,
                "text": evidence_text,
            }
        )
    return BackendToolResult.success(
        tool_name="memory_search",
        evidence={"kind": "memory_search", "query": query, "records": records},
        fallback_answer=_render_source_fallback(sources),
        sources=sources,
        confidence="medium",
        route=serialize_route(route_answer_mode("memory_query")),
        debug={"matched_memory_count": len(records)},
    )


async def get_profile(
    *,
    query: str,
    top_k: int,
    context: AgentRunContext,
) -> BackendToolResult:
    del query, top_k
    entries, profile = await build_profile_for_knowledge_base(
        context.db,
        user_id=context.user_id,
        knowledge_base_id=context.knowledge_base_id,
    )
    if not entries:
        return _empty_evidence_error("profile_get", "No memory entries are available for profile generation.")
    return BackendToolResult.success(
        tool_name="profile_get",
        evidence={"kind": "profile_snapshot", "entry_count": len(entries), "profile": profile},
        fallback_answer=build_profile_answer(profile),
        confidence="medium",
        route=serialize_route(route_answer_mode("profile_query")),
        debug={"profile_entry_count": len(entries)},
    )


async def analyze_growth(
    *,
    query: str,
    top_k: int,
    context: AgentRunContext,
) -> BackendToolResult:
    del query, top_k
    entries, profile, report = await build_growth_for_knowledge_base(
        context.db,
        user_id=context.user_id,
        knowledge_base_id=context.knowledge_base_id,
        recent_days=30,
    )
    if not entries:
        return _empty_evidence_error("growth_analysis", "No memory entries are available for growth analysis.")
    return BackendToolResult.success(
        tool_name="growth_analysis",
        evidence={
            "kind": "growth_analysis",
            "entry_count": len(entries),
            "profile": profile,
            "report": report,
        },
        fallback_answer=build_growth_answer(report),
        confidence="medium",
        route=serialize_route(route_answer_mode("analysis_query")),
        debug={"analysis_entry_count": len(entries), "analysis_window_days": 30},
    )


def _retrieval_counts(packet: dict[str, Any]) -> dict[str, int]:
    keys = (
        "raw_count",
        "dedup_count",
        "vector_count",
        "keyword_count",
        "memory_count",
        "candidate_count",
        "merged_count",
        "fusion_count",
        "rerank_count",
        "final_count",
    )
    return {key: int(packet.get(key) or 0) for key in keys}


def _render_source_fallback(sources: list[dict[str, Any]]) -> str:
    lines = ["The backend returned the following evidence:"]
    for source in sources:
        source_id = str(source.get("source_id") or "source")
        text = " ".join(str(source.get("text") or "").split())
        lines.append(f"- [{source_id}] {text[:400]}")
    return "\n".join(lines)


def _empty_evidence_error(tool_name: str, message: str) -> BackendToolResult:
    return BackendToolResult.error(
        tool_name=tool_name,
        kind=ToolErrorKind.UNAVAILABLE,
        message=message,
    )
