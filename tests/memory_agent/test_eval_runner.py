import json
from pathlib import Path

import pytest

from services.memory_agent.eval.contracts import EvalCase
from services.memory_agent.eval.metrics import evaluate_case
from services.memory_agent.eval.runner import load_cases, main, run_evaluation


DATASET = Path(__file__).parents[2] / "evals" / "memory_agent" / "cases.jsonl"


def test_fixed_dataset_has_five_cases_per_mode_and_special_coverage():
    cases = load_cases(DATASET)

    assert len(cases) == 25
    assert {case.mode for case in cases} == {
        "kb_qa",
        "memory_query",
        "profile_query",
        "analysis_query",
        "general_chat",
    }
    assert all(sum(case.mode == mode for case in cases) == 5 for mode in {case.mode for case in cases})
    tags = {tag for case in cases for tag in case.tags}
    assert {"no-evidence", "conflict", "historical", "unauthorized", "invalid-citations"}.issubset(tags)
    assert any(case.rejected_citations for case in cases)


def test_baseline_gates_and_per_mode_metrics_pass():
    report = run_evaluation(load_cases(DATASET), dataset_version="v1")

    assert report.case_count == 25
    assert all(report.gates.values())
    assert report.overall["pipeline_accuracy"] == 1.0
    assert report.overall["source_scope_violations"] == 0
    assert report.overall["citation_precision"] == 1.0
    assert report.overall["no_evidence_behavior"] == 1.0
    assert {mode: result["case_count"] for mode, result in report.by_mode.items()} == {
        "analysis_query": 5,
        "general_chat": 5,
        "kb_qa": 5,
        "memory_query": 5,
        "profile_query": 5,
    }


def test_metrics_flag_scope_leak_and_invalid_citation():
    case = EvalCase.from_mapping(
        {
            "case_id": "negative-1",
            "version": "v1",
            "mode": "memory_query",
            "question": "q",
            "owner_id": 7,
            "expected": {"source_ids": ["m1"], "required_claims": ["answer"]},
            "prediction": {
                "actual_mode": "memory_query",
                "answer": "answer",
                "retrieved": [{"source_id": "m1", "source_type": "memory", "owner_id": 99}],
                "citations": [{"source_id": "m1", "source_type": "document"}],
            },
        }
    )

    result = evaluate_case(case)

    assert result.source_scope_violations == 1
    assert result.citation_precision == 0.0
    assert result.citation_coverage == 0.0


def test_prediction_mode_is_explicitly_required():
    with pytest.raises(ValueError, match="prediction.actual_mode is required"):
        EvalCase.from_mapping(
            {
                "case_id": "missing-mode",
                "mode": "general_chat",
                "question": "q",
                "prediction": {"answer": "a"},
            }
        )


def test_cli_writes_json_report(tmp_path):
    output = tmp_path / "report.json"

    assert main(["--dataset", str(DATASET), "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["case_count"] == 25
    assert report["gates"] == {
        "citation_precision": True,
        "no_evidence_behavior": True,
        "pipeline_accuracy": True,
        "source_scope_violations": True,
    }
