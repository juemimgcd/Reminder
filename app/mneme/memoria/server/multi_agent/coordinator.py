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
        use_multi = (
            requested == "multi"
            or (requested == "auto" and request.answer_mode == "analysis_query")
        ) and len(enabled) >= 2
        if not use_multi:
            return CoordinatorDecision(
                execution_mode="single",
                reason_code=(
                    "explicit_single"
                    if requested == "single"
                    else "single_source_or_fast_path"
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
            reason_code=(
                "explicit_multi"
                if requested == "multi"
                else "analysis_requires_cross_source_coverage"
            ),
            assignments=assignments,
            allow_supplemental=limits.max_supplemental_rounds == 1,
        )
