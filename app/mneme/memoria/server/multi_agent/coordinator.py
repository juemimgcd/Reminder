import hashlib

from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.contracts.answers import AnswerRequest
from app.mneme.memoria.server.multi_agent.contracts import (
    CoordinatorDecision,
    EvidenceSource,
    MultiAgentBudgetLimits,
    RetrievalRole,
    SourceAssignment,
)
from app.mneme.memoria.server.runtime.contracts import RetrievalPlan

SOURCE_ROLES: dict[EvidenceSource, RetrievalRole] = {
    "document": "document_retriever",
    "memory": "memory_retriever",
    "profile": "profile_retriever",
    "relation": "relation_retriever",
}


class RAGCoordinator:
    """Deterministic bounded policy; it never retrieves, writes, or spawns."""

    def decide(
        self,
        request: AnswerRequest,
        plan: RetrievalPlan,
        limits: MultiAgentBudgetLimits,
    ) -> CoordinatorDecision:
        enabled = [
            source
            for source, selected in (
                ("document", plan.document),
                ("memory", plan.memory),
                ("profile", plan.profile),
                ("relation", plan.relations),
            )
            if selected
        ]
        requested = request.execution_mode
        allowed_modes = {item.strip() for item in settings.MULTI_AGENT_ALLOWED_MODES.split(",") if item.strip()}
        rollout_key = f"{request.owner_id}:{request.session_id or request.request_id}"
        rollout_bucket = int(hashlib.sha256(rollout_key.encode("utf-8")).hexdigest()[:8], 16) % 100
        rollout_enabled = rollout_bucket < settings.MULTI_AGENT_ROLLOUT_PERCENT
        use_multi = (
            settings.MULTI_AGENT_FEATURE_ENABLED
            and rollout_enabled
            and request.answer_mode in allowed_modes
            and requested == "multi"
            and len(enabled) >= 2
        )
        if not use_multi:
            return CoordinatorDecision(
                execution_mode="single",
                reason_code=(
                    "explicit_single"
                    if requested == "single"
                    else (
                        "feature_disabled"
                        if requested == "multi" and not settings.MULTI_AGENT_FEATURE_ENABLED
                        else (
                            "rollout_excluded"
                            if requested == "multi" and not rollout_enabled
                            else (
                                "mode_not_enabled"
                                if requested == "multi" and request.answer_mode not in allowed_modes
                                else "single_source_or_fast_path"
                            )
                        )
                    )
                ),
            )

        total = min(limits.max_retrieval_top_k, request.top_k * len(enabled))
        base, extra = divmod(total, len(enabled))
        assignments = [
            SourceAssignment(
                role=SOURCE_ROLES[source],
                source_type=source,
                query=request.question,
                top_k=max(1, min(10, base + (1 if index < extra else 0))),
            )
            for index, source in enumerate(enabled)
        ]
        return CoordinatorDecision(
            execution_mode="multi",
            reason_code="explicit_multi",
            assignments=assignments,
            allow_supplemental=limits.max_supplemental_rounds == 1,
        )
