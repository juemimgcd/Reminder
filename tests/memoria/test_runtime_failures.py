import asyncio

import pytest

from app.mneme.memoria.server.contracts.answers import AnswerRequest
from app.mneme.memoria.server.runtime.contracts import CitationResult, GeneratedAnswer
from app.mneme.memoria.server.runtime.orchestrator import (
    AnswerRunExecutionError,
    MemoryAgent,
    PhaseTimeouts,
)


class _Runs:
    def __init__(self):
        self.rows = {}

    async def create(self, *, run_id, request, validation_duration_ms):
        self.rows[run_id] = {"status": "running", "phase": "validate", "error": None}

    async def begin_phase(self, run_id, *, previous, phase):
        self.rows[run_id]["phase"] = phase

    async def record_retrieval(self, run_id, **kwargs):
        self.rows[run_id].update(kwargs)

    async def record_generation(self, run_id, **kwargs):
        self.rows[run_id].update(kwargs)

    async def complete(self, run_id, **kwargs):
        self.rows[run_id].update(kwargs, status="completed", phase="complete")

    async def fail(self, run_id, *, phase, duration_ms, error_code):
        self.rows[run_id].update(status="failed", phase=phase, error=error_code)


class _Retriever:
    def __init__(self, items=None, error=None):
        self.items = items or []
        self.error = error
        self.calls = 0

    async def retrieve(self, _request):
        self.calls += 1
        if self.error:
            raise self.error
        return self.items


class _Generator:
    def __init__(self, answer=None, error=None):
        self.answer = answer or GeneratedAnswer(answer="ok", route="kb_qa", confidence=0.9)
        self.error = error

    async def generate(self, _request):
        if self.error:
            raise self.error
        return self.answer


class _Citations:
    def validate(self, _answer, _evidence):
        return CitationResult(confidence=0.8)


def _request(mode="kb_qa"):
    return AnswerRequest(
        request_id="request-1",
        owner_id=7,
        knowledge_base_id=None if mode == "general_chat" else "kb-1",
        session_id="session-1",
        message_id="message-1",
        question="question",
        answer_mode=mode,
    )


def test_no_evidence_is_successful_and_marked_insufficient():
    runs = _Runs()
    agent = MemoryAgent(retriever=_Retriever(), generator=_Generator(), citation_validator=_Citations(), runs=runs)

    response = asyncio.run(agent.run(_request()))

    assert response.insufficient_evidence is True
    assert response.run_id in runs.rows
    assert runs.rows[response.run_id]["status"] == "completed"


def test_provider_failure_persists_failed_run_and_does_not_fabricate_answer():
    runs = _Runs()
    agent = MemoryAgent(
        retriever=_Retriever(error=RuntimeError("provider unavailable")),
        generator=_Generator(),
        citation_validator=_Citations(),
        runs=runs,
    )

    with pytest.raises(AnswerRunExecutionError) as exc_info:
        asyncio.run(agent.run(_request()))

    assert exc_info.value.error_code == "AGENT_RETRIEVAL_FAILED"
    assert runs.rows[exc_info.value.run_id]["status"] == "failed"
    assert runs.rows[exc_info.value.run_id]["error"] == "AGENT_RETRIEVAL_FAILED"


def test_phase_timeout_is_bounded_and_retryable_error_is_stable():
    async def slow(self, _request):
        await asyncio.sleep(0.05)

    class SlowRetriever:
        retrieve = slow

    runs = _Runs()
    agent = MemoryAgent(
        retriever=SlowRetriever(),
        generator=_Generator(),
        citation_validator=_Citations(),
        runs=runs,
        timeouts=PhaseTimeouts(retrieve=0.001),
    )

    with pytest.raises(AnswerRunExecutionError) as exc_info:
        asyncio.run(agent.run(_request()))

    assert exc_info.value.error_code == "AGENT_RETRIEVAL_TIMEOUT"
    assert runs.rows[exc_info.value.run_id]["status"] == "failed"
