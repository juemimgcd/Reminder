from typing import Any

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.clients.llm_client import get_llm
from app.mneme.conf.config import settings
from app.mneme.conf.logging import app_logger, log_event
from app.mneme.infra.circuit_breaker import before_call, record_failure, record_success
from app.mneme.infra.retry import retry_async
from app.mneme.schemas.chat import EvidenceAnswerDraft, EvidenceCitationDraft, QueryRouteDecision
from app.mneme.domains.retrieval.citation_validation import apply_citation_confidence_policy, validate_citation_drafts
from app.mneme.domains.retrieval.context_service import build_query_context
from app.mneme.domains.retrieval.debug import build_answer_debug, build_non_retrieval_debug
from app.mneme.domains.retrieval.query_router import route_query
from app.mneme.domains.profile.insight import build_growth_for_knowledge_base, build_profile_for_knowledge_base
from app.mneme.utils.prompt_builder import get_evidence_rag_prompt, get_general_chat_prompt


def is_retryable_external_error(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def serialize_route(route: QueryRouteDecision) -> dict[str, Any]:
    return route.model_dump()


def build_action_request_answer(route: QueryRouteDecision) -> dict[str, Any]:
    return {
        "answer": (
            "This request needs to be completed through the corresponding system page or API. "
            "I did not execute upload, delete, rebuild, or similar actions in chat. "
            "Please use the product controls for the action and review the result there."
        ),
        "sources": [],
        "citations": [],
        "confidence": "medium",
        "uncertainty": "This response did not execute a system action.",
        "route": serialize_route(route),
        "debug": build_non_retrieval_debug(
            route=route,
            reason="action request bypassed retrieval",
        ),
    }


def build_profile_answer(profile: dict[str, Any]) -> str:
    themes = [
        item.get("theme_name")
        for item in profile.get("main_themes", [])
        if item.get("theme_name")
    ]
    abilities = [
        item.get("ability_name")
        for item in profile.get("ability_tags", [])
        if item.get("ability_name")
    ]
    lines = [
        profile.get("profile_summary") or "No stable profile summary is available yet.",
    ]
    if themes:
        lines.append("Themes: " + ", ".join(themes))
    if abilities:
        lines.append("Abilities: " + ", ".join(abilities))
    if profile.get("expression_style"):
        lines.append("Expression style: " + profile["expression_style"])
    if profile.get("growth_focus"):
        lines.append("Growth focus: " + ", ".join(profile["growth_focus"]))
    return "\n".join(lines)


def build_growth_answer(report: dict[str, Any]) -> str:
    lines = [
        report.get("stage_summary") or "No stable stage analysis is available yet.",
    ]
    if report.get("recent_focus"):
        lines.append("Recent focus: " + ", ".join(report["recent_focus"]))
    if report.get("highlights"):
        lines.append("Highlights: " + ", ".join(report["highlights"]))
    if report.get("blockers"):
        lines.append("Blockers: " + ", ".join(report["blockers"]))
    if report.get("next_actions"):
        lines.append("Next actions: " + ", ".join(report["next_actions"]))
    return "\n".join(lines)


async def invoke_llm_answer(
    *,
    prompt: Any,
    question: str,
    context_text: str | None = None,
    knowledge_base_id: str | None = None,
    user_id: int | None = None,
) -> str:
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    async def do_invoke() -> str:
        before_call(
            name="llm",
            recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
        )
        try:
            log_event(
                "query_service",
                "debug",
                "llm.invoke.start",
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
            )
            answer_text = await chain.ainvoke(
                {
                    "context": context_text or "",
                    "question": question,
                }
            )
            record_success(name="llm")
            log_event(
                "query_service",
                "info",
                "llm.invoke.completed",
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                answer_length=len(answer_text),
            )
            return answer_text
        except Exception as exc:
            record_failure(
                name="llm",
                failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
            )
            app_logger.bind(module="query_service").exception(
                f"llm invoke failed knowledge_base_id={knowledge_base_id} user_id={user_id} "
                f"error_type={type(exc).__name__} error={exc}"
            )
            raise

    return await retry_async(
        do_invoke,
        is_retryable=is_retryable_external_error,
        max_attempts=settings.EXTERNAL_RETRY_MAX_ATTEMPTS,
        base_delay_seconds=settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS,
        max_delay_seconds=settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )


async def generate_rag_answer(
    question: str,
    *,
    db: AsyncSession | None = None,
    knowledge_base_id: str,
    user_id: int | None = None,
    top_k: int = 4,
) -> dict[str, Any]:
    route = route_query(question)
    log_event(
        "query_service",
        "info",
        "rag.answer.start",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        top_k=top_k,
        question_length=len(question),
        query_type=route.query_type,
        requires_retrieval=route.requires_retrieval,
        target_pipeline=route.target_pipeline,
    )

    if route.query_type == "general_chat":
        log_event(
            "query_service",
            "info",
            "router.general_chat_bypass",
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            reason=route.reason,
        )
        answer = await invoke_llm_answer(
            prompt=get_general_chat_prompt(),
            question=question,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
        )
        return {
            "answer": answer,
            "sources": [],
            "citations": [],
            "confidence": "medium",
            "uncertainty": "This response did not use knowledge-base evidence.",
            "route": serialize_route(route),
            "debug": build_non_retrieval_debug(
                route=route,
                reason="general chat bypassed retrieval",
            ),
        }

    if route.query_type == "action_request":
        log_event(
            "query_service",
            "info",
            "router.action_request_bypass",
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            reason=route.reason,
        )
        return build_action_request_answer(route)

    if db is None:
        raise ValueError("db is required for retrieval-augmented answers")

    if route.query_type == "profile_query":
        entries, profile = await build_profile_for_knowledge_base(
            db,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )
        log_event(
            "query_service",
            "info",
            "router.profile.completed",
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            entry_count=len(entries),
        )
        return {
            "answer": build_profile_answer(profile),
            "sources": [],
            "citations": [],
            "confidence": "medium" if entries else "low",
            "uncertainty": None if entries else "No memory entries are available for profile generation.",
            "route": serialize_route(route),
            "debug": build_non_retrieval_debug(
                route=route,
                reason="profile query routed to profile pipeline",
            ),
        }

    if route.query_type == "analysis_query":
        entries, _, report = await build_growth_for_knowledge_base(
            db,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            recent_days=30,
        )
        log_event(
            "query_service",
            "info",
            "router.analysis.completed",
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            entry_count=len(entries),
        )
        return {
            "answer": build_growth_answer(report),
            "sources": [],
            "citations": [],
            "confidence": "medium" if entries else "low",
            "uncertainty": None if entries else "No memory entries are available for growth analysis.",
            "route": serialize_route(route),
            "debug": build_non_retrieval_debug(
                route=route,
                reason="analysis query routed to growth analysis pipeline",
            ),
        }

    context_packet = await build_query_context(
        query=question,
        db=db,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    log_event(
        "query_service",
        "info",
        "rag.context.ready",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        raw_count=context_packet["raw_count"],
        dedup_count=context_packet["dedup_count"],
        lexical_backend=context_packet["lexical_backend"],
        candidate_count=context_packet["candidate_count"],
        merged_count=context_packet["merged_count"],
        fusion_count=context_packet["fusion_count"],
        rerank_count=context_packet["rerank_count"],
        final_count=context_packet["final_count"],
    )

    if not context_packet["sources"]:
        debug_packet = context_packet["debug"]
        debug_packet["route"] = serialize_route(route)
        debug_packet["answer_debug"] = build_answer_debug(
            answer="I could not retrieve enough relevant evidence from the current knowledge base. Please confirm the document has been indexed.",
            sources=[],
            citations=[],
            confidence="low",
            uncertainty="No retrieval evidence is currently available.",
        )
        log_event(
            "query_service",
            "warning",
            "rag.answer.empty_sources",
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
        )
        return {
            "answer": "I could not retrieve enough relevant evidence from the current knowledge base. Please confirm the document has been indexed.",
            "sources": [],
            "citations": [],
            "confidence": "low",
            "uncertainty": "No retrieval evidence is currently available.",
            "route": serialize_route(route),
            "debug": debug_packet,
        }

    evidence_result = await invoke_evidence_answer(
        question=question,
        context_text=context_packet["context_text"],
        sources=context_packet["sources"],
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
    )
    log_event(
        "query_service",
        "info",
        "rag.answer.completed",
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        source_count=len(context_packet["sources"]),
        citation_count=len(evidence_result["citations"]),
        answer_length=len(evidence_result["answer"]),
    )
    debug_packet = context_packet["debug"]
    debug_packet["route"] = serialize_route(route)
    debug_packet["answer_debug"] = build_answer_debug(
        answer=evidence_result["answer"],
        sources=context_packet["sources"],
        citations=evidence_result["citations"],
        confidence=evidence_result["confidence"],
        uncertainty=evidence_result["uncertainty"],
        citation_validation=evidence_result["citation_validation"],
        invalid_citations=evidence_result["invalid_citations"],
    )

    return {
        "answer": evidence_result["answer"],
        "sources": context_packet["sources"],
        "citations": evidence_result["citations"],
        "confidence": evidence_result["confidence"],
        "uncertainty": evidence_result["uncertainty"],
        "route": serialize_route(route),
        "debug": debug_packet,
    }


def resolve_citations(citation_drafts: list[EvidenceCitationDraft], sources: list[dict[str, Any]]) -> dict[str, Any]:
    return validate_citation_drafts(citation_drafts, sources)


async def invoke_evidence_answer(
    *,
    question: str,
    context_text: str,
    sources: list[dict[str, Any]],
    knowledge_base_id: str | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    parser = PydanticOutputParser(pydantic_object=EvidenceAnswerDraft)
    prompt = get_evidence_rag_prompt(parser.get_format_instructions())
    llm = get_llm()
    chain = prompt | llm | parser

    async def do_invoke() -> EvidenceAnswerDraft:
        before_call(
            name="llm",
            recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
        )
        try:
            result = await chain.ainvoke(
                {
                    "context": context_text,
                    "question": question,
                }
            )
            record_success(name="llm")
            return result
        except Exception as exc:
            record_failure(
                name="llm",
                failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                recovery_timeout_seconds=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
            )
            app_logger.bind(module="query_service").exception(
                f"evidence llm invoke failed knowledge_base_id={knowledge_base_id} user_id={user_id} "
                f"error_type={type(exc).__name__} error={exc}"
            )
            raise

    result = await retry_async(
        do_invoke,
        is_retryable=is_retryable_external_error,
        max_attempts=settings.EXTERNAL_RETRY_MAX_ATTEMPTS,
        base_delay_seconds=settings.EXTERNAL_RETRY_BASE_DELAY_SECONDS,
        max_delay_seconds=settings.EXTERNAL_RETRY_MAX_DELAY_SECONDS,
    )
    citation_validation = resolve_citations(result.citations, sources)
    confidence, uncertainty = apply_citation_confidence_policy(
        confidence=result.confidence,
        uncertainty=result.uncertainty,
        citation_validation=citation_validation,
    )
    return {
        "answer": result.answer,
        "citations": citation_validation["valid_citations"],
        "confidence": confidence,
        "uncertainty": uncertainty,
        "citation_validation": citation_validation["summary"],
        "invalid_citations": citation_validation["invalid_citations"],
    }
