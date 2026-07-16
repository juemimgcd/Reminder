from typing import Any

from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence
from app.mneme.memoria.server.runtime.contracts import CitationResult, GeneratedAnswer

SAFE_METADATA_KEYS = frozenset(
    {
        "file_name",
        "page_no",
        "section_path",
        "memory_type",
        "valid_from",
        "valid_to",
        "relation_type",
        "source_memory_id",
        "target_memory_id",
        "created_at",
    }
)


class EvidenceCitationValidator:
    def validate(
        self,
        answer: GeneratedAnswer,
        evidence: list[RetrievedEvidence],
    ) -> CitationResult:
        retrieved = {item.evidence_id: item for item in evidence}
        citations: list[dict[str, Any]] = []
        seen: set[str] = set()
        for draft in answer.citations:
            evidence_id = draft.get("evidence_id") if isinstance(draft, dict) else None
            if not isinstance(evidence_id, str) or evidence_id in seen:
                continue
            item = retrieved.get(evidence_id)
            if item is None:
                continue
            quote = draft.get("quote")
            if quote is not None and (
                not isinstance(quote, str) or not quote.strip() or quote not in item.content
            ):
                continue
            seen.add(evidence_id)
            metadata = {
                key: value
                for key, value in item.metadata.items()
                if key in SAFE_METADATA_KEYS and value is not None
            }
            citation = {
                "evidence_id": item.evidence_id,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "metadata": metadata,
            }
            if isinstance(quote, str):
                citation["quote"] = quote
            citations.append(citation)

        private_mode = answer.route != "general_chat"
        missing_support = private_mode and not citations
        confidence = answer.confidence
        uncertainty = answer.uncertainty
        if missing_support:
            confidence = min(confidence, 0.25)
            uncertainty = uncertainty or "The answer has no supported citation."
        elif len(citations) < len(answer.citations):
            confidence = min(confidence, 0.6)
            uncertainty = uncertainty or "Some citations could not be verified."

        return CitationResult(
            citations=citations,
            confidence=confidence,
            uncertainty=uncertainty,
            insufficient_evidence=answer.insufficient_evidence or missing_support,
        )
