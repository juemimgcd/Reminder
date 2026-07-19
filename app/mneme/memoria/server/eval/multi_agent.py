"""Deterministic single-agent versus bounded multi-agent release evaluation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping


def _ratio_increase(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0 if candidate <= 0 else 1.0
    return round((candidate - baseline) / baseline, 6)


def _precision(expected: set[str], actual: list[str]) -> float:
    return 1.0 if not actual else len(expected.intersection(actual)) / len(actual)


def _recall(expected: set[str], actual: list[str]) -> float:
    return 1.0 if not expected else len(expected.intersection(actual)) / len(expected)


@dataclass(frozen=True)
class EvaluationVariant:
    route: str
    source_types: tuple[str, ...]
    retrieved_source_ids: tuple[str, ...]
    agent_result_counts: tuple[int, ...]
    detected_conflict_ids: tuple[str, ...]
    kept_source_ids: tuple[str, ...]
    dropped_source_ids: tuple[str, ...]
    citation_count: int
    valid_citation_count: int
    grounded: bool
    partial_failure_recovered: bool
    latency_ms: int
    total_tokens: int
    estimated_cost: float
    source_scope_violations: int
    action_safety_violations: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvaluationVariant":
        citations = tuple(value.get("citations", ()))
        return cls(
            route=str(value.get("route", "single")),
            source_types=tuple(str(item) for item in value.get("source_types", ())),
            retrieved_source_ids=tuple(
                str(item) for item in value.get("retrieved_source_ids", ())
            ),
            agent_result_counts=tuple(
                int(item) for item in value.get("agent_result_counts", ())
            ),
            detected_conflict_ids=tuple(
                str(item) for item in value.get("detected_conflict_ids", ())
            ),
            kept_source_ids=tuple(str(item) for item in value.get("kept_source_ids", ())),
            dropped_source_ids=tuple(
                str(item) for item in value.get("dropped_source_ids", ())
            ),
            citation_count=len(citations),
            valid_citation_count=sum(
                bool(item.get("valid", True))
                for item in citations
                if isinstance(item, Mapping)
            ),
            grounded=bool(value.get("grounded", False)),
            partial_failure_recovered=bool(
                value.get("partial_failure_recovered", False)
            ),
            latency_ms=max(0, int(value.get("latency_ms", 0))),
            total_tokens=max(0, int(value.get("total_tokens", 0))),
            estimated_cost=max(0.0, float(value.get("estimated_cost", 0.0))),
            source_scope_violations=max(
                0, int(value.get("source_scope_violations", 0))
            ),
            action_safety_violations=max(
                0, int(value.get("action_safety_violations", 0))
            ),
        )

    @property
    def citation_validity(self) -> float:
        if self.citation_count == 0:
            return 1.0 if self.grounded else 0.0
        return self.valid_citation_count / self.citation_count

    @property
    def quality_score(self) -> float:
        return fmean((float(self.grounded), self.citation_validity))


@dataclass(frozen=True)
class MultiAgentEvalCase:
    case_id: str
    expected_route: str
    expected_source_types: tuple[str, ...]
    expected_conflict_ids: tuple[str, ...]
    expected_keep_ids: tuple[str, ...]
    expected_drop_ids: tuple[str, ...]
    expects_partial_failure: bool
    baseline: EvaluationVariant
    candidate: EvaluationVariant

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MultiAgentEvalCase":
        expected = value.get("expected") or {}
        expected_route = str(expected.get("route", "single"))
        if expected_route not in {"single", "multi"}:
            raise ValueError(f"{value.get('case_id')}: expected route must be single or multi")
        return cls(
            case_id=str(value["case_id"]),
            expected_route=expected_route,
            expected_source_types=tuple(
                str(item) for item in expected.get("source_types", ())
            ),
            expected_conflict_ids=tuple(
                str(item) for item in expected.get("conflict_ids", ())
            ),
            expected_keep_ids=tuple(
                str(item) for item in expected.get("keep_source_ids", ())
            ),
            expected_drop_ids=tuple(
                str(item) for item in expected.get("drop_source_ids", ())
            ),
            expects_partial_failure=bool(expected.get("partial_failure", False)),
            baseline=EvaluationVariant.from_mapping(value.get("baseline") or {}),
            candidate=EvaluationVariant.from_mapping(value.get("candidate") or {}),
        )


@dataclass(frozen=True)
class MultiAgentCaseMetrics:
    case_id: str
    expected_route: str
    route_accuracy: float
    source_selection_precision: float
    source_selection_recall: float
    duplicate_retrieval_ratio: float
    empty_agent_ratio: float
    evidence_conflict_detection_rate: float
    judge_keep_precision: float
    judge_drop_precision: float
    citation_validity: float
    grounded_answer_rate: float
    partial_failure_recovery_rate: float
    quality_gain_vs_single_agent: float
    latency_increase_vs_single_agent: float
    token_increase_vs_single_agent: float
    cost_increase_vs_single_agent: float
    source_scope_violations: int
    action_safety_violations: int


def evaluate_multi_agent_case(case: MultiAgentEvalCase) -> MultiAgentCaseMetrics:
    candidate = case.candidate
    expected_sources = set(case.expected_source_types)
    actual_sources = list(candidate.source_types)
    duplicate_count = len(candidate.retrieved_source_ids) - len(
        set(candidate.retrieved_source_ids)
    )
    conflict_ids = set(case.expected_conflict_ids)
    detected_conflicts = list(candidate.detected_conflict_ids)
    return MultiAgentCaseMetrics(
        case_id=case.case_id,
        expected_route=case.expected_route,
        route_accuracy=float(candidate.route == case.expected_route),
        source_selection_precision=round(
            _precision(expected_sources, actual_sources), 6
        ),
        source_selection_recall=round(_recall(expected_sources, actual_sources), 6),
        duplicate_retrieval_ratio=round(
            duplicate_count / len(candidate.retrieved_source_ids)
            if candidate.retrieved_source_ids
            else 0.0,
            6,
        ),
        empty_agent_ratio=round(
            sum(count == 0 for count in candidate.agent_result_counts)
            / len(candidate.agent_result_counts)
            if candidate.agent_result_counts
            else 0.0,
            6,
        ),
        evidence_conflict_detection_rate=round(
            _recall(conflict_ids, detected_conflicts), 6
        ),
        judge_keep_precision=round(
            _precision(set(case.expected_keep_ids), list(candidate.kept_source_ids)),
            6,
        ),
        judge_drop_precision=round(
            _precision(set(case.expected_drop_ids), list(candidate.dropped_source_ids)),
            6,
        ),
        citation_validity=round(candidate.citation_validity, 6),
        grounded_answer_rate=float(candidate.grounded),
        partial_failure_recovery_rate=float(
            not case.expects_partial_failure or candidate.partial_failure_recovered
        ),
        quality_gain_vs_single_agent=round(
            candidate.quality_score - case.baseline.quality_score, 6
        ),
        latency_increase_vs_single_agent=_ratio_increase(
            candidate.latency_ms, case.baseline.latency_ms
        ),
        token_increase_vs_single_agent=_ratio_increase(
            candidate.total_tokens, case.baseline.total_tokens
        ),
        cost_increase_vs_single_agent=_ratio_increase(
            candidate.estimated_cost, case.baseline.estimated_cost
        ),
        source_scope_violations=candidate.source_scope_violations,
        action_safety_violations=candidate.action_safety_violations,
    )


MULTI_AGENT_GATE_REQUIREMENTS: dict[str, float | int] = {
    "route_accuracy": 1.0,
    "source_selection_precision": 1.0,
    "source_selection_recall": 1.0,
    "citation_validity": 1.0,
    "grounded_answer_rate": 1.0,
    "partial_failure_recovery_rate": 1.0,
    "quality_gain_vs_single_agent": 0.0,
    "latency_increase_vs_single_agent_max": 2.0,
    "token_increase_vs_single_agent_max": 2.0,
    "cost_increase_vs_single_agent_max": 2.0,
    "source_scope_violations": 0,
    "action_safety_violations": 0,
}


def load_multi_agent_cases(path: str | Path) -> list[MultiAgentEvalCase]:
    cases: list[MultiAgentEvalCase] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            cases.append(MultiAgentEvalCase.from_mapping(json.loads(line)))
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"invalid multi-agent evaluation case at {path}:{line_number}: {exc}"
            ) from exc
    if not cases:
        raise ValueError(f"multi-agent evaluation dataset {path} is empty")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("multi-agent evaluation case IDs must be unique")
    return cases


def run_multi_agent_evaluation(cases: list[MultiAgentEvalCase]) -> dict[str, Any]:
    metrics = [evaluate_multi_agent_case(case) for case in cases]

    def mean(name: str) -> float:
        return round(fmean(float(getattr(item, name)) for item in metrics), 6)

    overall: dict[str, float | int] = {
        name: mean(name)
        for name in (
            "route_accuracy",
            "source_selection_precision",
            "source_selection_recall",
            "duplicate_retrieval_ratio",
            "empty_agent_ratio",
            "evidence_conflict_detection_rate",
            "judge_keep_precision",
            "judge_drop_precision",
            "citation_validity",
            "grounded_answer_rate",
            "partial_failure_recovery_rate",
            "quality_gain_vs_single_agent",
            "latency_increase_vs_single_agent",
            "token_increase_vs_single_agent",
            "cost_increase_vs_single_agent",
        )
    }
    overall["source_scope_violations"] = sum(
        item.source_scope_violations for item in metrics
    )
    overall["action_safety_violations"] = sum(
        item.action_safety_violations for item in metrics
    )
    gates = {
        "route_accuracy": overall["route_accuracy"] >= 1.0,
        "source_selection_precision": overall["source_selection_precision"] >= 1.0,
        "source_selection_recall": overall["source_selection_recall"] >= 1.0,
        "citation_validity": overall["citation_validity"] >= 1.0,
        "grounded_answer_rate": overall["grounded_answer_rate"] >= 1.0,
        "partial_failure_recovery_rate": overall[
            "partial_failure_recovery_rate"
        ]
        >= 1.0,
        "quality_gain_vs_single_agent": overall["quality_gain_vs_single_agent"] >= 0,
        "latency_budget": overall["latency_increase_vs_single_agent"] <= 2.0,
        "token_budget": overall["token_increase_vs_single_agent"] <= 2.0,
        "cost_budget": overall["cost_increase_vs_single_agent"] <= 2.0,
        "source_scope": overall["source_scope_violations"] == 0,
        "action_safety": overall["action_safety_violations"] == 0,
    }
    return {
        "case_count": len(metrics),
        "cases": [asdict(item) for item in metrics],
        "overall": overall,
        "gates": gates,
        "gate_requirements": MULTI_AGENT_GATE_REQUIREMENTS.copy(),
        "release_ready": all(gates.values()),
    }
