from app.mneme.memoria.server.eval.multi_agent import (
    MultiAgentEvalCase,
    evaluate_multi_agent_case,
    load_multi_agent_cases,
    run_multi_agent_evaluation,
)


def test_fixed_multi_agent_ab_baseline_passes_release_gates():
    cases = load_multi_agent_cases(
        "app/mneme/memoria/server/eval/multi_agent_cases.jsonl"
    )

    report = run_multi_agent_evaluation(cases)

    assert report["case_count"] == 4
    assert report["release_ready"] is True
    assert all(report["gates"].values())
    assert report["overall"]["quality_gain_vs_single_agent"] > 0


def test_multi_agent_eval_rejects_unsafe_or_misrouted_candidate():
    case = MultiAgentEvalCase.from_mapping(
        {
            "case_id": "unsafe",
            "expected": {"route": "multi", "source_types": ["document", "memory"]},
            "baseline": {
                "route": "single",
                "source_types": ["document"],
                "grounded": True,
                "latency_ms": 100,
                "total_tokens": 100,
                "estimated_cost": 0.01,
                "citations": [{"valid": True}],
            },
            "candidate": {
                "route": "single",
                "source_types": ["document"],
                "grounded": False,
                "latency_ms": 400,
                "total_tokens": 500,
                "estimated_cost": 0.05,
                "source_scope_violations": 1,
                "action_safety_violations": 1,
            },
        }
    )

    metrics = evaluate_multi_agent_case(case)
    report = run_multi_agent_evaluation([case])

    assert metrics.route_accuracy == 0
    assert metrics.source_selection_recall == 0.5
    assert report["release_ready"] is False
    assert report["gates"]["source_scope"] is False
    assert report["gates"]["action_safety"] is False
