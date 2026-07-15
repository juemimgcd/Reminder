"""CLI for running the fixed answer-quality baseline.

Example:
    python -m services.memory_agent.eval.runner \
        --dataset evals/memory_agent/cases.jsonl \
        --output .tmp/memory-agent-eval.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from services.memory_agent.eval.contracts import EvalCase, EvaluationReport
from services.memory_agent.eval.metrics import GATE_REQUIREMENTS, check_gates, evaluate_case, summarize_metrics


def load_cases(path: str | Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            cases.append(EvalCase.from_mapping(json.loads(line)))
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid evaluation case at {path}:{line_number}: {exc}") from exc
    if not cases:
        raise ValueError(f"evaluation dataset {path} is empty")
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("evaluation case IDs must be unique")
    return cases


def run_evaluation(cases: Iterable[EvalCase], *, dataset_version: str = "v1") -> EvaluationReport:
    case_metrics = tuple(evaluate_case(case) for case in cases)
    overall, by_mode = summarize_metrics(case_metrics)
    return EvaluationReport(
        dataset_version=dataset_version,
        case_count=len(case_metrics),
        cases=case_metrics,
        overall=overall,
        by_mode=by_mode,
        gates=check_gates(overall),
        gate_requirements=GATE_REQUIREMENTS.copy(),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path, help="versioned JSONL evaluation dataset")
    parser.add_argument("--output", required=True, type=Path, help="JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cases = load_cases(args.dataset)
    dataset_version = "v1"
    report = run_evaluation(cases, dataset_version=dataset_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_json = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(report_json, encoding="utf-8")
    print(json.dumps({"case_count": report.case_count, "gates": report.gates}, sort_keys=True))
    return 0 if all(report.gates.values()) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
