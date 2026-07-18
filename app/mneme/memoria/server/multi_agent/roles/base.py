import asyncio
from time import perf_counter

from app.mneme.memoria.server.multi_agent.contracts import (
    EvidenceBundle,
    SourceAssignment,
)
from app.mneme.memoria.server.runtime.contracts import RetrievalRequest
from app.mneme.memoria.server.runtime.ports import EvidenceRetriever


class SourceRetrievalAgent:
    def __init__(self, *, assignment: SourceAssignment, retriever: EvidenceRetriever) -> None:
        self.assignment = assignment
        self._retriever = retriever

    async def run(
        self,
        request: RetrievalRequest,
        *,
        timeout_seconds: float,
    ) -> EvidenceBundle:
        started = perf_counter()
        scoped_request = request.model_copy(
            update={
                "question": self.assignment.query,
                "top_k": self.assignment.top_k,
                "plan": request.plan.for_source(self.assignment.source_type),
            }
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                evidence = await self._retriever.retrieve(scoped_request)
        except asyncio.CancelledError:
            raise
        elapsed_ms = max(0, round((perf_counter() - started) * 1000))
        return EvidenceBundle(
            agent_role=self.assignment.role,
            source_type=self.assignment.source_type,
            query=self.assignment.query,
            evidence=evidence,
            coverage=min(1.0, len(evidence) / self.assignment.top_k),
            uncertainty=[] if evidence else ["source_returned_no_evidence"],
            elapsed_ms=elapsed_ms,
            degraded=not evidence,
        )
