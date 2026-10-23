"""Validate generated citations against evidence retrieved for the current answer run.

Unknown evidence identifiers and quotes absent from the source text are rejected before delivery.
"""

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


def resolve_citations(
    drafts: list[dict[str, Any]], evidence: list[RetrievedEvidence],
) -> list[dict[str, Any]]:
    """Apply the same ID/quote checks before planning and at final delivery."""
    retrieved = {item.evidence_id: item for item in evidence}
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for draft in drafts:
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

    return citations


def citation_coverage_satisfied(answer: GeneratedAnswer, citations: list[dict[str, Any]]) -> bool:
    """Every requirement must retain at least one citation after final filtering."""
    cited_ids = {item["evidence_id"] for item in citations}
    return all(cited_ids.intersection(group) for group in answer.required_citation_groups)


class EvidenceCitationValidator:
    """Enforce that generated citations refer to evidence from the current run.

    Validation is identifier- and quote-based. It does not claim that every
    answer sentence is semantically entailed by the cited source.
    """
    def validate(
        self,
        answer: GeneratedAnswer,
        evidence: list[RetrievedEvidence],
    ) -> CitationResult:
        """Filter citations and derive confidence from the remaining support.

        Unknown IDs, duplicates, empty quotes, and quotes absent from source
        text are removed. Private answer modes without valid support are marked
        insufficient rather than returned with model-supplied confidence.
        """
        citations = resolve_citations(answer.citations, evidence)

        private_mode = answer.route != "general_chat"
        missing_support = (private_mode and not citations) or not citation_coverage_satisfied(answer, citations)
        confidence = answer.confidence
        uncertainty = answer.uncertainty
        if missing_support:
            confidence = min(confidence, 0.25)
            uncertainty = uncertainty or "The validated citations do not cover the required evidence."
        elif len(citations) < len(answer.citations):
            confidence = min(confidence, 0.6)
            uncertainty = uncertainty or "Some citations could not be verified."

        return CitationResult(
            citations=citations,
            confidence=confidence,
            uncertainty=uncertainty,
            insufficient_evidence=answer.insufficient_evidence or missing_support,
        )
