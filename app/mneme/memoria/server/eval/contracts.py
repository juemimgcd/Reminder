"""Contracts for the versioned, model-free answer-quality evaluation set.

The evaluation dataset intentionally contains a deterministic prediction fixture
alongside each case.  This lets CI check retrieval and citation behaviour without
network calls, credentials, a database, or a particular model provider.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

ANSWER_MODES = frozenset(
    {"kb_qa", "memory_query", "profile_query", "analysis_query", "general_chat"}
)


@dataclass(frozen=True)
class Evidence:
    source_id: str
    source_type: str
    owner_id: int
    rank: int = 0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], rank: int) -> "Evidence":
        return cls(
            source_id=str(value.get("source_id", "")),
            source_type=str(value.get("source_type", "")),
            owner_id=int(value.get("owner_id", 0)),
            rank=int(value.get("rank", rank)),
        )


@dataclass(frozen=True)
class Citation:
    source_id: str
    source_type: str | None = None
    valid: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Citation":
        return cls(
            source_id=str(value.get("source_id", "")),
            source_type=(str(value["source_type"]) if value.get("source_type") is not None else None),
            valid=bool(value.get("valid", True)),
        )


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    version: str
    mode: str
    question: str
    owner_id: int
    expected_source_ids: tuple[str, ...] = ()
    expected_source_types: tuple[str, ...] = ()
    required_claims: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    no_evidence: bool = False
    historical: bool = False
    conflict: bool = False
    unauthorized: bool = False
    actual_mode: str | None = None
    answer: str = ""
    insufficient_evidence: bool = False
    retrieved: tuple[Evidence, ...] = ()
    citations: tuple[Citation, ...] = ()
    rejected_citations: tuple[Citation, ...] = ()
    top_k: int = 5
    tags: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvalCase":
        expected = value.get("expected") or {}
        prediction = value.get("prediction") or value
        retrieved_raw = prediction.get("retrieved", value.get("retrieved", ()))
        citations_raw = prediction.get("citations", value.get("citations", ()))
        rejected_citations_raw = prediction.get("rejected_citations", value.get("rejected_citations", ()))
        source_ids = expected.get("source_ids", value.get("expected_source_ids", ()))
        source_types = expected.get("source_types", value.get("expected_source_types", ()))
        required = expected.get("required_claims", value.get("required_claims", ()))
        forbidden = expected.get("forbidden_claims", value.get("forbidden_claims", ()))
        no_evidence = bool(expected.get("no_evidence", value.get("no_evidence", False)))
        historical = bool(expected.get("historical", value.get("historical", False)))
        conflict = bool(expected.get("conflict", value.get("conflict", False)))
        unauthorized = bool(expected.get("unauthorized", value.get("unauthorized", False)))
        mode = str(value.get("mode", ""))
        if mode not in ANSWER_MODES:
            raise ValueError(f"{value.get('case_id', '<unknown>')}: unsupported answer mode {mode!r}")
        if "actual_mode" not in prediction:
            raise ValueError(f"{value.get('case_id', '<unknown>')}: prediction.actual_mode is required")
        if no_evidence and "insufficient_evidence" not in prediction:
            raise ValueError(
                f"{value.get('case_id', '<unknown>')}: prediction.insufficient_evidence "
                "is required for no-evidence cases"
            )
        top_k = int(value.get("top_k", 5))
        if top_k < 1:
            raise ValueError(f"{value.get('case_id', '<unknown>')}: top_k must be positive")
        return cls(
            case_id=str(value["case_id"]),
            version=str(value.get("version", "v1")),
            mode=mode,
            question=str(value.get("question", "")),
            owner_id=int(value.get("owner_id", expected.get("owner_id", 1))),
            expected_source_ids=tuple(str(item) for item in source_ids),
            expected_source_types=tuple(str(item) for item in source_types),
            required_claims=tuple(str(item) for item in required),
            forbidden_claims=tuple(str(item) for item in forbidden),
            no_evidence=no_evidence,
            historical=historical,
            conflict=conflict,
            unauthorized=unauthorized,
            actual_mode=str(prediction["actual_mode"]),
            answer=str(prediction.get("answer", value.get("answer", ""))),
            insufficient_evidence=bool(
                prediction.get("insufficient_evidence", value.get("insufficient_evidence", no_evidence))
            ),
            retrieved=tuple(Evidence.from_mapping(item, index) for index, item in enumerate(retrieved_raw, 1)),
            citations=tuple(Citation.from_mapping(item) for item in citations_raw),
            rejected_citations=tuple(Citation.from_mapping(item) for item in rejected_citations_raw),
            top_k=top_k,
            tags=tuple(str(item) for item in value.get("tags", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CaseMetrics:
    case_id: str
    mode: str
    pipeline_accuracy: float
    source_scope_violations: int
    recall_at_k: float
    mrr: float
    citation_precision: float
    citation_coverage: float
    unsupported_claim_flags: int
    no_evidence_behavior: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationReport:
    dataset_version: str
    case_count: int
    cases: tuple[CaseMetrics, ...]
    overall: dict[str, float | int]
    by_mode: dict[str, dict[str, float | int]]
    gates: dict[str, bool]
    gate_requirements: dict[str, float | int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "case_count": self.case_count,
            "cases": [item.to_dict() for item in self.cases],
            "overall": self.overall,
            "by_mode": self.by_mode,
            "gates": self.gates,
            "gate_requirements": self.gate_requirements,
        }
