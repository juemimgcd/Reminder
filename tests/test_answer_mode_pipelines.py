import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import app.mneme.domains.retrieval.context_service as context_service
from app.mneme.agent.orchestrator import generate_rag_answer, get_evidence_prompt_for_mode
from app.mneme.agent.router import retrieval_scope_for_answer_mode


def test_answer_modes_use_fixed_retrieval_scopes():
    assert retrieval_scope_for_answer_mode("kb_qa") == "hybrid"
    assert retrieval_scope_for_answer_mode("memory_query") == "memory_only"


def test_memory_only_context_skips_document_retrieval(monkeypatch):
    vector_search = AsyncMock(return_value=[])
    chunk_search = AsyncMock(return_value=[])
    memory_search = AsyncMock(return_value=[])

    @asynccontextmanager
    async def fake_read_session():
        yield object()

    monkeypatch.setattr(context_service, "retrieve_documents_with_scores", vector_search)
    monkeypatch.setattr(context_service, "search_chunks_by_keywords", chunk_search)
    monkeypatch.setattr(context_service, "search_memory_entries_by_keywords", memory_search)
    monkeypatch.setattr(context_service, "open_read_session", fake_read_session)

    result = asyncio.run(
        context_service.build_query_context(
            query="What do you remember?",
            db=object(),
            user_id=7,
            knowledge_base_id="kb-1",
            retrieval_scope="memory_only",
        )
    )

    vector_search.assert_not_awaited()
    chunk_search.assert_not_awaited()
    memory_search.assert_awaited_once()
    assert result["vector_count"] == 0
    assert result["keyword_count"] == 0
    assert result["lexical_backend"] is None


def test_memory_answer_passes_memory_only_scope_to_context_builder(monkeypatch):
    captured = {}

    async def fake_build_query_context(**kwargs):
        captured.update(kwargs)
        return {
            "context_text": "",
            "sources": [],
            "raw_count": 0,
            "dedup_count": 0,
            "vector_count": 0,
            "keyword_count": 0,
            "lexical_backend": None,
            "memory_count": 0,
            "candidate_count": 0,
            "merged_count": 0,
            "fusion_count": 0,
            "rerank_count": 0,
            "final_count": 0,
            "debug": {"route": None, "answer_debug": None},
        }

    monkeypatch.setattr(
        "app.mneme.agent.orchestrator.build_query_context",
        fake_build_query_context,
    )

    asyncio.run(
        generate_rag_answer(
            "What do you remember?",
            db=object(),
            knowledge_base_id="kb-1",
            user_id=7,
            answer_mode="memory_query",
        )
    )

    assert captured["retrieval_scope"] == "memory_only"


def test_memory_mode_selects_long_term_memory_prompt():
    prompt = get_evidence_prompt_for_mode("memory_query", "FORMAT")
    system_text = prompt.messages[0].prompt.template

    assert "long-term memory" in system_text.lower()
    assert "FORMAT" in system_text


def test_knowledge_base_mode_keeps_evidence_prompt():
    prompt = get_evidence_prompt_for_mode("kb_qa", "FORMAT")
    system_text = prompt.messages[0].prompt.template

    assert "long-term memory" not in system_text.lower()
    assert "FORMAT" in system_text
