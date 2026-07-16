import asyncio
from pathlib import Path

import pytest

from app.mneme.memoria.adapters.rag_answer import RagAnswerEngine
from app.mneme.memoria.contracts import AgentRequest, AgentResponse
from app.mneme.memoria.router import route_answer_mode
from app.mneme.memoria.service import MemoriaAgent

ROOT = Path(__file__).resolve().parents[1]
AGENT_CORE_FILES = (
    ROOT / "app/mneme/memoria/contracts.py",
    ROOT / "app/mneme/memoria/ports.py",
    ROOT / "app/mneme/memoria/service.py",
)
ONLINE_AGENT_CONSUMERS = (
    ROOT / "app/mneme/memoria/chat_bridge.py",
    ROOT / "app/mneme/memoria/api/retrieval.py",
    ROOT / "app/mneme/domains/chat/service.py",
    ROOT / "app/mneme/domains/companion/router.py",
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
    assert request.answer_mode == "kb_qa"


def test_agent_run_uses_the_answer_engine_boundary():
    response = AgentResponse(
        answer="grounded answer",
        sources=[],
        citations=[],
        confidence="high",
    )
    engine = FakeAnswerEngine(response)
    agent = MemoriaAgent(answer_engine=engine)
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
        "app.mneme.memoria.adapters.rag_answer.generate_rag_answer",
        fake_generate_rag_answer,
    )
    db = object()
    request = AgentRequest(
        question="question",
        knowledge_base_id="kb_1",
        user_id=9,
        top_k=6,
        answer_mode="memory_query",
        llm_config={"model_name": "model_1"},
    )

    response = asyncio.run(RagAnswerEngine(db).generate(request))

    assert captured == {
        "question": "question",
        "db": db,
        "knowledge_base_id": "kb_1",
        "user_id": 9,
        "top_k": 6,
        "answer_mode": "memory_query",
        "llm_config": {"model_name": "model_1"},
    }
    assert response.sources[0]["source_chunk_ids"] == ["chunk_1", "chunk_2"]
    assert response.to_legacy_result()["debug"] == {"counts": {"final_count": 1}}


@pytest.mark.parametrize(
    ("answer_mode", "target_pipeline", "requires_retrieval"),
    [
        ("kb_qa", "evidence_rag", True),
        ("memory_query", "memory_rag", True),
        ("profile_query", "profile", False),
        ("analysis_query", "growth_analysis", False),
        ("general_chat", "general_chat", False),
    ],
)
def test_agent_routes_the_user_selected_answer_mode(answer_mode, target_pipeline, requires_retrieval):
    route = route_answer_mode(answer_mode)

    assert route.query_type == answer_mode
    assert route.target_pipeline == target_pipeline
    assert route.requires_retrieval is requires_retrieval


def test_online_answer_consumers_use_the_agent_entry_point():
    for path in ONLINE_AGENT_CONSUMERS:
        source = path.read_text(encoding="utf-8")
        assert "answer_via_memory_agent" in source, f"{path.name} does not use the Memory Agent client"
        assert "build_mneme_agent" not in source, f"{path.name} retains the in-process Agent"
        assert "AgentRequest" not in source, f"{path.name} retains the in-process Agent contract"
        assert "domains.retrieval.query_service import generate_rag_answer" not in source
