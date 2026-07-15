"""Pure deterministic metrics and gates used by the evaluation runner."""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Iterable

from services.memory_agent.eval.contracts import CaseMetrics, EvalCase


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return round(fmean(values), 6) if values else 0.0


def _recall(expected: set[str], retrieved: list[str]) -> float:
    return 1.0 if not expected else len(expected.intersection(retrieved)) / len(expected)


def _mrr(expected: set[str], retrieved: list[str]) -> float:
    if not expected:
        return 1.0
    for rank, source_id in enumerate(retrieved, 1):
        if source_id in expected:
            return 1.0 / rank
    return 0.0


def evaluate_case(case: EvalCase) -> CaseMetrics:
    retrieved = list(case.retrieved)
    retrieved_ids = [item.source_id for item in retrieved]
    expected_ids = set(case.expected_source_ids)
    expected_types = set(case.expected_source_types)
    actual_mode = case.actual_mode or case.mode
    pipeline_accuracy = 1.0 if actual_mode == case.mode else 0.0

    scope_violations = sum(item.owner_id != case.owner_id for item in retrieved)
    # An unauthorized case is deliberately present in the fixed set.  It must
    # remain visible to the metric even if a future fixture forgets owner IDs.
    if case.unauthorized and not scope_violations:
        scope_violations = sum(item.source_id not in expected_ids for item in retrieved)

    valid_citations = 0
    cited_expected: set[str] = set()
    for citation in case.citations:
        evidence = next((item for item in retrieved if item.source_id == citation.source_id), None)
        source_type_ok = (
            (citation.source_type is None or not evidence or citation.source_type == evidence.source_type)
            and (not expected_types or not evidence or evidence.source_type in expected_types)
        )
        supported = evidence is not None and citation.valid and source_type_ok and citation.source_id in expected_ids
        if supported:
            valid_citations += 1
            cited_expected.add(citation.source_id)
    citation_count = len(case.citations)
    citation_precision = (
        1.0
        if not citation_count and not expected_ids
        else (valid_citations / citation_count if citation_count else 0.0)
    )
    citation_coverage = 1.0 if not expected_ids else len(cited_expected) / len(expected_ids)

    unsupported_claim_flags = sum(
        1 for claim in case.required_claims if claim.casefold() not in case.answer.casefold()
    )
    unsupported_claim_flags += sum(
        1 for claim in case.forbidden_claims if claim.casefold() in case.answer.casefold()
    )
    no_evidence_behavior = 1.0 if case.insufficient_evidence == case.no_evidence else 0.0
    if case.no_evidence and case.citations:
        no_evidence_behavior = 0.0

    return CaseMetrics(
        case_id=case.case_id,
        mode=case.mode,
        pipeline_accuracy=pipeline_accuracy,
        source_scope_violations=scope_violations,
        recall_at_k=_recall(expected_ids, retrieved_ids[: case.top_k]),
        mrr=_mrr(expected_ids, retrieved_ids[: case.top_k]),
        citation_precision=round(citation_precision, 6),
        citation_coverage=round(citation_coverage, 6),
        unsupported_claim_flags=unsupported_claim_flags,
        no_evidence_behavior=no_evidence_behavior,
    )


def summarize_metrics(cases: Iterable[CaseMetrics]) -> tuple[dict[str, float | int], dict[str, dict[str, float | int]]]:
    case_metrics = list(cases)

    def summarize(items: list[CaseMetrics]) -> dict[str, float | int]:
        return {
            "case_count": len(items),
            "pipeline_accuracy": _mean(item.pipeline_accuracy for item in items),
            "source_scope_violations": sum(item.source_scope_violations for item in items),
            "recall_at_k": _mean(item.recall_at_k for item in items),
            "mrr": _mean(item.mrr for item in items),
            "citation_precision": _mean(item.citation_precision for item in items),
            "citation_coverage": _mean(item.citation_coverage for item in items),
            "unsupported_claim_flags": sum(item.unsupported_claim_flags for item in items),
            "no_evidence_behavior": _mean(item.no_evidence_behavior for item in items),
        }

    grouped: dict[str, list[CaseMetrics]] = defaultdict(list)
    for item in case_metrics:
        grouped[item.mode].append(item)
    return summarize(case_metrics), {mode: summarize(items) for mode, items in sorted(grouped.items())}


GATE_REQUIREMENTS: dict[str, float | int] = {
    "pipeline_accuracy": 1.0,
    "source_scope_violations": 0,
    "citation_precision": 1.0,
    "no_evidence_behavior": 1.0,
}


def check_gates(overall: dict[str, float | int]) -> dict[str, bool]:
    return {
        "pipeline_accuracy": float(overall["pipeline_accuracy"]) >= 1.0,
        "source_scope_violations": int(overall["source_scope_violations"]) == 0,
        "citation_precision": float(overall["citation_precision"]) >= 1.0,
        "no_evidence_behavior": float(overall["no_evidence_behavior"]) >= 1.0,
    }
