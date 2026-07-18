import asyncio

import pytest

from app.mneme.memoria.server.contracts.answers import AnswerRequest
from app.mneme.memoria.server.multi_agent.budget import (
    MultiAgentBudgetExceeded,
    SharedMultiAgentBudget,
)
from app.mneme.memoria.server.multi_agent.contracts import (
    EvidenceBundle,
    MultiAgentBudgetLimits,
)
from app.mneme.memoria.server.multi_agent.coordinator import RAGCoordinator
from app.mneme.memoria.server.multi_agent.evidence_judge import EvidenceJudge
from app.mneme.memoria.server.multi_agent.executor import BoundedMultiAgentExecutor
from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence
from app.mneme.memoria.server.runtime.contracts import CitationResult, GeneratedAnswer
from app.mneme.memoria.server.runtime.orchestrator import MemoryAgent
from app.mneme.memoria.server.runtime.plans import MODE_PLANS


def _request(
    *,
    mode: str = "analysis_query",
    execution_mode: str = "auto",
    question: str = "compare evidence across sources",
) -> AnswerRequest:
    return AnswerRequest(
        request_id="request-multi-1",
        owner_id=7,
        knowledge_base_id="kb-1",
        session_id="session-1",
        message_id="message-1",
        question=question,
        answer_mode=mode,
        execution_mode=execution_mode,
        top_k=4,
    )


def _source(request) -> str:
    plan = request.plan
    selected = [
        source
        for source, enabled in (
            ("document", plan.document),
            ("memory", plan.memory),
            ("profile", plan.profile),
            ("relation", plan.relations),
        )
        if enabled
    ]
    assert len(selected) == 1
    return selected[0]


def _evidence(source: str, index: int = 1) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=f"{source}-evidence-{index}",
        source_type=source,
        source_id=f"{source}-source-{index}",
        content=f"{source} supported content {index}",
        score=1.0 - index / 100,
        metadata={},
    )


class _ConcurrentRetriever:
    def __init__(self, *, failing: set[str] | None = None, block: bool = False):
        self.failing = failing or set()
        self.block = block
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.cancelled = 0

    async def retrieve(self, request):
        source = _source(request)
        self.calls.append(request)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.block:
                await asyncio.Event().wait()
            else:
                await asyncio.sleep(0.01)
            if source in self.failing:
                raise RuntimeError("raw provider error must be sanitized")
            return [_evidence(source)]
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        finally:
            self.active -= 1


def test_coordinator_keeps_simple_questions_on_single_agent_fast_path():
    decision = RAGCoordinator().decide(
        _request(mode="kb_qa"),
        MODE_PLANS["kb_qa"],
        MultiAgentBudgetLimits(),
    )

    assert decision.execution_mode == "single"
    assert decision.assignments == []


def test_analysis_query_gets_four_fixed_roles_without_nested_spawning():
    decision = RAGCoordinator().decide(
        _request(),
        MODE_PLANS["analysis_query"],
        MultiAgentBudgetLimits(),
    )

    assert decision.execution_mode == "multi"
    assert [item.role for item in decision.assignments] == [
        "document_retriever",
        "memory_retriever",
        "profile_retriever",
        "relation_retriever",
    ]
    assert sum(item.top_k for item in decision.assignments) <= 24


def test_executor_runs_sources_concurrently_with_identical_owner_scope():
    retriever = _ConcurrentRetriever()
    executor = BoundedMultiAgentExecutor(retriever=retriever)

    result = asyncio.run(executor.execute(_request(), MODE_PLANS["analysis_query"]))

    assert retriever.max_active == 4
    assert {item.owner_id for item in retriever.calls} == {7}
    assert {item.knowledge_base_id for item in retriever.calls} == {"kb-1"}
    assert len(result.judged.evidence) == 4
    assert result.degraded is False
    assert result.budget_usage.retrieval_top_k <= executor.limits.max_retrieval_top_k


def test_nonessential_source_failure_returns_sanitized_degraded_result():
    retriever = _ConcurrentRetriever(failing={"profile"})
    executor = BoundedMultiAgentExecutor(retriever=retriever)

    result = asyncio.run(executor.execute(_request(), MODE_PLANS["analysis_query"]))
    serialized = result.model_dump_json()

    assert result.degraded is True
    assert result.judged.missing_sources == ["profile"]
    assert any(
        item.role == "profile_retriever"
        and item.error_code == "AGENT_RETRIEVAL_SOURCE_FAILED"
        for item in result.role_attempts
    )
    assert "raw provider error" not in serialized
    assert "compare evidence across sources" not in serialized


def test_parent_cancellation_cancels_all_retrieval_roles():
    async def execute():
        retriever = _ConcurrentRetriever(block=True)
        executor = BoundedMultiAgentExecutor(retriever=retriever)
        task = asyncio.create_task(
            executor.execute(_request(), MODE_PLANS["analysis_query"])
        )
        while retriever.max_active < 4:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return retriever

    retriever = asyncio.run(execute())

    assert retriever.cancelled == 4


def test_shared_budget_rejects_retrieval_and_supplemental_overrun():
    budget = SharedMultiAgentBudget(
        MultiAgentBudgetLimits(
            max_retrieval_top_k=4,
            max_supplemental_rounds=0,
        )
    )
    budget.reserve_retrieval(4)

    with pytest.raises(MultiAgentBudgetExceeded):
        budget.reserve_retrieval(1)
    with pytest.raises(MultiAgentBudgetExceeded):
        budget.reserve_supplemental_round()


def test_evidence_judge_reports_deduplication_conflicts_and_budget_drops():
    first = _evidence("memory", 1)
    conflicting = first.model_copy(
        update={
            "evidence_id": "memory-evidence-conflict",
            "content": "a conflicting revision",
        }
    )
    duplicate = first.model_copy(update={"score": 0.2})
    bundles = [
        {
            "agent_role": "memory_retriever",
            "source_type": "memory",
            "query": "hidden",
            "evidence": [first, conflicting, duplicate],
            "coverage": 1,
            "elapsed_ms": 1,
        }
    ]

    judged = EvidenceJudge().judge(
        [EvidenceBundle.model_validate(item) for item in bundles],
        selected_sources=["memory"],
        final_top_k=1,
    )

    assert len(judged.evidence) == 1
    assert judged.conflicts
    assert {item.reason_code for item in judged.dropped} == {"duplicate", "budget"}


class _Runs:
    def __init__(self):
        self.rows = {}

    async def create(self, *, run_id, request, validation_duration_ms):
        self.rows[run_id] = {"status": "running", "phase": "validate"}

    async def begin_phase(self, run_id, *, previous, phase):
        self.rows[run_id]["phase"] = phase

    async def record_retrieval(self, run_id, **values):
        self.rows[run_id].update(values)

    async def record_generation(self, run_id, **values):
        self.rows[run_id].update(values)

    async def complete(self, run_id, **values):
        self.rows[run_id].update(values, status="completed", phase="complete")

    async def fail(self, run_id, **values):
        self.rows[run_id].update(values, status="failed")


class _Generator:
    def __init__(self):
        self.request = None

    async def generate(self, request):
        self.request = request
        return GeneratedAnswer(
            answer="bounded answer",
            route=request.mode,
            confidence=0.8,
            prompt_tokens=100,
            completion_tokens=50,
            model_attempts=[{"status": "completed"}],
        )


class _Citations:
    def __init__(self):
        self.evidence = []

    def validate(self, _answer, evidence):
        self.evidence = evidence
        return CitationResult(
            citations=[
                {"evidence_id": item.evidence_id}
                for item in evidence
            ],
            confidence=0.8,
        )


def test_memory_agent_persists_multi_agent_audit_and_cites_only_judged_evidence():
    retriever = _ConcurrentRetriever()
    generator = _Generator()
    citations = _Citations()
    runs = _Runs()
    events = []

    async def execute():
        agent = MemoryAgent(
            retriever=retriever,
            generator=generator,
            citation_validator=citations,
            runs=runs,
        )

        async def observe(phase, status, run_id, payload):
            events.append((phase, status, run_id, payload))

        return await agent.run(_request(), event_callback=observe)

    response = asyncio.run(execute())
    row = runs.rows[response.run_id]

    assert response.execution_mode == "multi"
    assert response.degraded is False
    assert generator.request.execution_mode == "multi"
    assert generator.request.tool_context is None
    assert len(citations.evidence) == 4
    assert row["execution_mode"] == "multi"
    assert row["role_attempts"]
    assert row["budget_usage"]["retrieval_top_k"] <= 24
    assert any(phase == "multi_agent.judge" for phase, *_ in events)
