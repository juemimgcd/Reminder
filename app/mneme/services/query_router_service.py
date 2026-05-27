import re

from app.mneme.schemas.chat import QueryRouteDecision


GENERAL_CHAT_PATTERNS = [
    r"hello",
    r"\bhi\b",
    r"help",
    r"thanks",
]

ACTION_PATTERNS = [
    r"(upload|delete|create|rebuild|import|export|update|modify)",
]

PROFILE_PATTERNS = [
    r"profile",
    r"preference",
    r"ability",
    r"style",
]

ANALYSIS_PATTERNS = [
    r"growth report",
    r"trend",
    r"recent",
    r"analysis",
]

MEMORY_PATTERNS = [
    r"memory",
    r"remember",
    r"previous",
    r"history",
]


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def route_query(question: str) -> QueryRouteDecision:
    normalized = question.strip().lower()
    if not normalized:
        return QueryRouteDecision(
            query_type="general_chat",
            requires_retrieval=False,
            target_pipeline="general_chat",
            confidence="high",
            reason="empty query should not trigger retrieval",
        )

    if _matches_any(ACTION_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="action_request",
            requires_retrieval=False,
            target_pipeline="action_guidance",
            confidence="medium",
            reason="query asks the assistant to perform a system action",
        )

    if _matches_any(PROFILE_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="profile_query",
            requires_retrieval=False,
            target_pipeline="profile",
            confidence="medium",
            reason="query asks for a user/profile-level summary",
        )

    if _matches_any(ANALYSIS_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="analysis_query",
            requires_retrieval=False,
            target_pipeline="growth_analysis",
            confidence="medium",
            reason="query asks for trend, stage, or growth analysis",
        )

    if _matches_any(MEMORY_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="memory_query",
            requires_retrieval=True,
            target_pipeline="memory_rag",
            confidence="medium",
            reason="query asks about past memories or recorded facts",
        )

    if _matches_any(GENERAL_CHAT_PATTERNS, normalized):
        return QueryRouteDecision(
            query_type="general_chat",
            requires_retrieval=False,
            target_pipeline="general_chat",
            confidence="high",
            reason="query is assistant/help/greeting oriented",
        )

    return QueryRouteDecision(
        query_type="kb_qa",
        requires_retrieval=True,
        target_pipeline="evidence_rag",
        confidence="medium",
        reason="default knowledge-base answer path",
    )
