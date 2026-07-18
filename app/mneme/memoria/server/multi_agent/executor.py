import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from app.mneme.memoria.server.contracts.answers import AnswerRequest
from app.mneme.memoria.server.multi_agent.budget import (
    MultiAgentBudgetExceeded,
    SharedMultiAgentBudget,
)
from app.mneme.memoria.server.multi_agent.contracts import (
    EvidenceBundle,
    MultiAgentBudgetLimits,
    MultiAgentExecutionResult,
    RoleAttempt,
    SourceAssignment,
)
from app.mneme.memoria.server.multi_agent.coordinator import RAGCoordinator
from app.mneme.memoria.server.multi_agent.evidence_judge import EvidenceJudge
from app.mneme.memoria.server.multi_agent.roles import (
    DocumentRetrievalAgent,
    MemoryRetrievalAgent,
    ProfileRetrievalAgent,
    RelationRetrievalAgent,
)
from app.mneme.memoria.server.runtime.contracts import RetrievalPlan, retrieval_request
from app.mneme.memoria.server.runtime.ports import EvidenceRetriever

MultiAgentEventCallback = Callable[
    [str, str, dict[str, Any]],
    Awaitable[None],
]

ROLE_TYPES = {
    "document_retriever": DocumentRetrievalAgent,
    "memory_retriever": MemoryRetrievalAgent,
    "profile_retriever": ProfileRetrievalAgent,
    "relation_retriever": RelationRetrievalAgent,
}


class BoundedMultiAgentExecutor:
    def __init__(
        self,
        *,
        retriever: EvidenceRetriever,
        limits: MultiAgentBudgetLimits | None = None,
        coordinator: RAGCoordinator | None = None,
        judge: EvidenceJudge | None = None,
    ) -> None:
        self._retriever = retriever
        self.limits = limits or MultiAgentBudgetLimits()
        self._coordinator = coordinator or RAGCoordinator()
        self._judge = judge or EvidenceJudge()

    def plan(self, request: AnswerRequest, plan: RetrievalPlan):
        return self._coordinator.decide(request, plan, self.limits)

    async def execute(
        self,
        request: AnswerRequest,
        plan: RetrievalPlan,
        *,
        event_callback: MultiAgentEventCallback | None = None,
    ) -> MultiAgentExecutionResult:
        budget = SharedMultiAgentBudget(self.limits)
        decision = self.plan(request, plan)
        if decision.execution_mode != "multi":
            raise ValueError("multi-agent executor received a single-agent plan")

        role_attempts = [
            RoleAttempt(
                role="rag_coordinator",
                status="completed",
                elapsed_ms=0,
                evidence_count=0,
            )
        ]
        await _emit(
            event_callback,
            "multi_agent.coordinate",
            "completed",
            {
                "event_name": "multi_agent.coordinator.completed",
                "source_count": len(decision.assignments),
                "sources": [item.source_type for item in decision.assignments],
                "reason_code": decision.reason_code,
            },
        )

        bundles, attempts = await self._run_assignments(
            request,
            plan,
            decision.assignments,
            budget=budget,
            event_callback=event_callback,
            supplemental_round=0,
        )
        role_attempts.extend(attempts)
        if bundles and all(bundle.error_code for bundle in bundles):
            raise RuntimeError("all multi-agent retrieval sources failed")

        judge_started = perf_counter()
        judged = self._judge.judge(
            bundles,
            selected_sources=[item.source_type for item in decision.assignments],
            final_top_k=request.top_k,
        )
        if (
            judged.needs_supplemental
            and decision.allow_supplemental
            and judged.missing_sources
        ):
            retry_assignments = [
                item
                for item in decision.assignments
                if item.source_type in judged.missing_sources
            ]
            try:
                budget.reserve_supplemental_round()
                supplemental, supplemental_attempts = await self._run_assignments(
                    request,
                    plan,
                    retry_assignments,
                    budget=budget,
                    event_callback=event_callback,
                    supplemental_round=1,
                )
            except MultiAgentBudgetExceeded:
                supplemental = []
                supplemental_attempts = []
            bundles.extend(supplemental)
            role_attempts.extend(supplemental_attempts)
            judged = self._judge.judge(
                bundles,
                selected_sources=[item.source_type for item in decision.assignments],
                final_top_k=request.top_k,
            )

        judge_elapsed = max(0, round((perf_counter() - judge_started) * 1000))
        role_attempts.append(
            RoleAttempt(
                role="evidence_judge",
                status="degraded" if judged.uncertainty else "completed",
                elapsed_ms=judge_elapsed,
                evidence_count=len(judged.evidence),
            )
        )
        await _emit(
            event_callback,
            "multi_agent.judge",
            "completed",
            {
                "event_name": "multi_agent.judge.completed",
                "kept_count": len(judged.evidence),
                "dropped_count": len(judged.dropped),
                "conflict_count": len(judged.conflicts),
                "coverage": judged.coverage,
                "missing_sources": judged.missing_sources,
            },
        )
        degraded = bool(judged.uncertainty) or any(
            item.status != "completed" for item in role_attempts
        )
        return MultiAgentExecutionResult(
            judged=judged,
            role_attempts=role_attempts,
            budget_usage=budget.snapshot(),
            degraded=degraded,
            stop_reason=(
                "multi_agent_degraded"
                if degraded
                else "multi_agent_completed"
            ),
        )

    async def _run_assignments(
        self,
        request: AnswerRequest,
        plan: RetrievalPlan,
        assignments: list[SourceAssignment],
        *,
        budget: SharedMultiAgentBudget,
        event_callback: MultiAgentEventCallback | None,
        supplemental_round: int,
    ) -> tuple[list[EvidenceBundle], list[RoleAttempt]]:
        for assignment in assignments:
            budget.reserve_retrieval(assignment.top_k)

        results: dict[str, EvidenceBundle] = {}

        async def run_one(assignment: SourceAssignment) -> None:
            await _emit(
                event_callback,
                "multi_agent.retrieve",
                "started",
                {
                    "event_name": "multi_agent.role.started",
                    "agent_role": assignment.role,
                    "source_type": assignment.source_type,
                    "supplemental_round": supplemental_round,
                },
            )
            started = perf_counter()
            try:
                agent_type = ROLE_TYPES[assignment.role]
                timeout_seconds = min(
                    self.limits.source_timeout_seconds,
                    budget.remaining_seconds,
                )
                if timeout_seconds <= 0:
                    raise TimeoutError
                bundle = await agent_type(
                    assignment=assignment,
                    retriever=self._retriever,
                ).run(
                    retrieval_request(
                        request,
                        plan,
                        expansion_index=supplemental_round,
                    ),
                    timeout_seconds=timeout_seconds,
                )
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                bundle = _failed_bundle(
                    assignment,
                    started,
                    "AGENT_RETRIEVAL_TIMEOUT",
                )
            except Exception:
                bundle = _failed_bundle(
                    assignment,
                    started,
                    "AGENT_RETRIEVAL_SOURCE_FAILED",
                )
            results[assignment.role] = bundle
            await _emit(
                event_callback,
                "multi_agent.retrieve",
                "failed" if bundle.error_code else "completed",
                {
                    "event_name": (
                        "multi_agent.role.failed"
                        if bundle.error_code
                        else "multi_agent.role.completed"
                    ),
                    "agent_role": bundle.agent_role,
                    "source_type": bundle.source_type,
                    "result_count": len(bundle.evidence),
                    "elapsed_ms": bundle.elapsed_ms,
                    "degraded": bundle.degraded,
                    "error_code": bundle.error_code,
                    "supplemental_round": supplemental_round,
                },
            )

        async with asyncio.TaskGroup() as group:
            for assignment in assignments:
                group.create_task(run_one(assignment))

        bundles = [results[item.role] for item in assignments]
        attempts = [
            RoleAttempt(
                role=bundle.agent_role,
                source_type=bundle.source_type,
                status=(
                    "failed"
                    if bundle.error_code
                    else "degraded"
                    if bundle.degraded
                    else "completed"
                ),
                elapsed_ms=bundle.elapsed_ms,
                evidence_count=len(bundle.evidence),
                error_code=bundle.error_code,
                supplemental_round=supplemental_round,
            )
            for bundle in bundles
        ]
        return bundles, attempts


def _failed_bundle(
    assignment: SourceAssignment,
    started: float,
    error_code: str,
) -> EvidenceBundle:
    return EvidenceBundle(
        agent_role=assignment.role,
        source_type=assignment.source_type,
        query=assignment.query,
        evidence=[],
        coverage=0,
        uncertainty=["source_unavailable"],
        elapsed_ms=max(0, round((perf_counter() - started) * 1000)),
        degraded=True,
        error_code=error_code,
    )


async def _emit(
    callback: MultiAgentEventCallback | None,
    phase: str,
    status: str,
    payload: dict[str, Any],
) -> None:
    if callback is None:
        return
    await callback(phase, status, payload)
