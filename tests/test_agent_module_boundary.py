import asyncio
from pathlib import Path

import pytest

from app.mneme.agent.adapters.rag_answer import RagAnswerEngine
from app.mneme.agent.contracts import AgentRequest, AgentResponse
from app.mneme.agent.router import route_query as agent_route_query
from app.mneme.agent.service import MnemeAgent
from app.mneme.domains.retrieval.query_router import route_query as legacy_route_query

ROOT = Path(__file__).resolve().parents[1]
AGENT_CORE_FILES = (
    ROOT / "app/mneme/agent/contracts.py",
    ROOT / "app/mneme/agent/ports.py",
    ROOT / "app/mneme/agent/service.py",
)
ONLINE_AGENT_CONSUMERS = (
    ROOT / "app/mneme/domains/chat/service.py",
    ROOT / "app/mneme/domains/retrieval/router.py",
    ROOT / "app/mneme/domains/companion/router.py",
    ROOT / "app/mneme/pipelines/companion_pipeline.py",
)


class FakeAnswerEngine:
    def __init__(self, response: AgentResponse):
        self.response = response
        self.requests: list[AgentRequest] = []

    async def generate(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return self.response


def test_agent_request_preserves_empty_question_routing_compatibility():
    request = AgentRequest(
        question="",
        knowledge_base_id="kb_1",
        user_id=7,
    )

    assert request.question == ""


def test_agent_run_uses_the_answer_engine_boundary():
    response = AgentResponse(
        answer="grounded answer",
        sources=[],
        citations=[],
        confidence="high",
    )
    engine = FakeAnswerEngine(response)
    agent = MnemeAgent(answer_engine=engine)
    request = AgentRequest(
        question="What did I write?",
        knowledge_base_id="kb_1",
        user_id=7,
        top_k=5,
        llm_config={"provider": "deepseek"},
    )

    result = asyncio.run(agent.run(request))

    assert result is response
    assert engine.requests == [request]


def test_agent_core_does_not_import_backend_framework_or_storage_layers():
    forbidden_imports = (
        "fastapi",
        "sqlalchemy",
        "app.mneme.crud",
        "app.mneme.models",
        "app.mneme.conf.database",
    )

    for path in AGENT_CORE_FILES:
        source = path.read_text(encoding="utf-8").lower()
        for forbidden_import in forbidden_imports:
            assert forbidden_import not in source, f"{path.name} imports {forbidden_import}"


def test_rag_adapter_preserves_request_and_raw_response_fields(monkeypatch):
    captured: dict = {}

    async def fake_generate_rag_answer(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "answer",
            "sources": [
                {
                    "source_id": "S1",
                    "document_id": "doc_1",
                    "chunk_id": "chunk_1",
                    "text": "evidence",
                    "source_chunk_ids": ["chunk_1", "chunk_2"],
                }
            ],
            "citations": [],
            "confidence": "medium",
            "uncertainty": None,
            "route": {"query_type": "kb_qa"},
            "debug": {"counts": {"final_count": 1}},
        }

    monkeypatch.setattr(
        "app.mneme.agent.adapters.rag_answer.generate_rag_answer",
        fake_generate_rag_answer,
    )
    db = object()
    request = AgentRequest(
        question="question",
        knowledge_base_id="kb_1",
        user_id=9,
        top_k=6,
        llm_config={"model_name": "model_1"},
    )

    response = asyncio.run(RagAnswerEngine(db).generate(request))

    assert captured == {
        "question": "question",
        "db": db,
        "knowledge_base_id": "kb_1",
        "user_id": 9,
        "top_k": 6,
        "llm_config": {"model_name": "model_1"},
    }
    assert response.sources[0]["source_chunk_ids"] == ["chunk_1", "chunk_2"]
    assert response.to_legacy_result()["debug"] == {"counts": {"final_count": 1}}


@pytest.mark.parametrize(
    "question",
    [
        "hello",
        "please upload this file",
        "describe my profile",
        "show my recent trend",
        "what do you remember",
        "explain the architecture",
    ],
)
def test_agent_router_preserves_legacy_routing_behavior(question):
    assert agent_route_query(question) == legacy_route_query(question)


def test_online_answer_consumers_use_the_agent_entry_point():
    for path in ONLINE_AGENT_CONSUMERS:
        source = path.read_text(encoding="utf-8")
        assert "build_mneme_agent" in source, f"{path.name} does not build the Agent"
        assert "AgentRequest" in source, f"{path.name} does not use the Agent contract"
        assert "domains.retrieval.query_service import generate_rag_answer" not in source
