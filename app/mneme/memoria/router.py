"""Map a user-selected answer mode to an Agent pipeline."""

from app.mneme.memoria.contracts import AnswerMode, RetrievalScope
from app.mneme.schemas.chat import QueryRouteDecision

ANSWER_MODE_ROUTES: dict[AnswerMode, tuple[bool, str]] = {
    "kb_qa": (True, "evidence_rag"),
    "memory_query": (True, "memory_rag"),
    "profile_query": (False, "profile"),
    "analysis_query": (False, "growth_analysis"),
    "general_chat": (False, "general_chat"),
}


def route_answer_mode(answer_mode: AnswerMode) -> QueryRouteDecision:
    requires_retrieval, target_pipeline = ANSWER_MODE_ROUTES[answer_mode]
    return QueryRouteDecision(
        query_type=answer_mode,
        requires_retrieval=requires_retrieval,
        target_pipeline=target_pipeline,
        confidence="high",
        reason="answer mode explicitly selected by the user",
    )


def retrieval_scope_for_answer_mode(answer_mode: AnswerMode) -> RetrievalScope:
    if answer_mode == "memory_query":
        return "memory_only"
    return "hybrid"
