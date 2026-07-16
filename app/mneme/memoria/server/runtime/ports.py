from typing import Protocol

from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence
from app.mneme.memoria.server.runtime.contracts import (
    CitationResult,
    GeneratedAnswer,
    GenerationRequest,
    RetrievalRequest,
)


class EvidenceRetriever(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> list[RetrievedEvidence]: ...


class AnswerGenerator(Protocol):
    async def generate(self, request: GenerationRequest) -> GeneratedAnswer: ...


class CitationValidator(Protocol):
    def validate(
        self,
        answer: GeneratedAnswer,
        evidence: list[RetrievedEvidence],
    ) -> CitationResult: ...
