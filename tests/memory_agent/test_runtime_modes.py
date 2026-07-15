import asyncio

import pytest

from services.memory_agent.retrieval.contracts import RetrievedEvidence
from services.memory_agent.runtime.contracts import RetrievalRequest
from services.memory_agent.runtime.plans import MODE_PLANS
from services.memory_agent.runtime.retriever import ScopedEvidenceRetriever


def _evidence(source_type: str) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=f"{source_type}-evidence",
        source_type=source_type,
        source_id=f"{source_type}-1",
        content="supported content",
        score=1.0,
        metadata={},
    )


class _SpyRetriever:
    def __init__(self, source_type: str, calls: list[str]):
        self.source_type = source_type
        self.calls = calls

    async def search(self, *args, **kwargs):
        self.calls.append(self.source_type)
        return [_evidence(self.source_type)]


@pytest.mark.parametrize(
    "mode,allowed",
    [
        (
            name,
            tuple(
                source
                for source, enabled in (
                    ("document", plan.document),
                    ("memory", plan.memory),
                    ("profile", plan.profile),
                    ("relation", plan.relations),
                )
                if enabled
            ),
        )
        for name, plan in MODE_PLANS.items()
    ],
)
def test_scoped_retriever_invokes_only_sources_allowed_by_mode(mode, allowed):
    calls: list[str] = []
    retriever = ScopedEvidenceRetriever(
        documents_factory=lambda: _SpyRetriever("document", calls),
        memories_factory=lambda: _SpyRetriever("memory", calls),
        profile_factory=lambda: _SpyRetriever("profile", calls),
        relations_factory=lambda: _SpyRetriever("relation", calls),
    )
    plan = MODE_PLANS[mode]
    request = RetrievalRequest(
        request_id="request-1",
        owner_id=7,
        knowledge_base_id="kb-1",
        mode=mode,
        question="question",
        top_k=4,
        plan=plan,
    )

    asyncio.run(retriever.retrieve(request))

    assert tuple(calls) == allowed
    assert set(calls) == set(allowed)


def test_general_chat_does_not_require_private_scope_or_instantiate_retrievers():
    def fail_factory():
        raise AssertionError("private retriever must not be created for general chat")

    retriever = ScopedEvidenceRetriever(
        documents_factory=fail_factory,
        memories_factory=fail_factory,
        profile_factory=fail_factory,
        relations_factory=fail_factory,
    )
    request = RetrievalRequest(
        request_id="request-1",
        owner_id=7,
        knowledge_base_id=None,
        mode="general_chat",
        question="hello",
        top_k=4,
        plan=MODE_PLANS["general_chat"],
    )

    assert asyncio.run(retriever.retrieve(request)) == []
