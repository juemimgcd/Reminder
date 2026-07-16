"""CLI for running the fixed answer-quality baseline.

Example:
    python -m app.mneme.memoria.server.eval.runner \
        --dataset app/mneme/memoria/server/eval/cases.jsonl \
        --output .tmp/memory-agent-eval.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import httpx

from app.mneme.memoria.server.eval.contracts import Citation, EvalCase, EvaluationReport, Evidence
from app.mneme.memoria.server.eval.metrics import GATE_REQUIREMENTS, check_gates, evaluate_case, summarize_metrics


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
    parser.add_argument("--live-endpoint", help="opt-in Memoria base URL for live predictions")
    parser.add_argument(
        "--service-token-env",
        default="MEMORY_AGENT_EVAL_TOKEN",
        help="environment variable containing a scoped service token",
    )
    parser.add_argument("--knowledge-base-id", help="knowledge-base scope for non-general live cases")
    return parser


async def run_live_predictions(
    cases: list[EvalCase],
    *,
    endpoint: str,
    service_token: str,
    knowledge_base_id: str | None,
) -> list[EvalCase]:
    if any(case.mode != "general_chat" for case in cases) and not knowledge_base_id:
        raise ValueError("--knowledge-base-id is required for private-source live cases")
    predictions: list[EvalCase] = []
    async with httpx.AsyncClient(base_url=endpoint.rstrip("/"), timeout=120.0) as client:
        for case in cases:
            response = await client.post(
                "/v1/answers",
                headers={
                    "Authorization": f"Bearer {service_token}",
                    "X-Request-ID": f"eval_{case.case_id}",
                    "X-Trace-ID": f"trace_eval_{case.case_id}",
                },
                json={
                    "request_id": f"eval_{case.case_id}_{uuid4().hex}",
                    "trace_id": f"trace_eval_{case.case_id}",
                    "owner_id": case.owner_id,
                    "knowledge_base_id": knowledge_base_id if case.mode != "general_chat" else None,
                    "message_id": f"eval_message_{case.case_id}",
                    "question": case.question,
                    "answer_mode": case.mode,
                    "top_k": case.top_k,
                    "allow_model_fallback": True,
                },
            )
            response.raise_for_status()
            payload = response.json()
            citation_rows = [
                item for item in payload.get("citations", []) if isinstance(item, dict)
            ]
            citations = tuple(Citation.from_mapping(item) for item in citation_rows)
            retrieved = tuple(
                Evidence(
                    source_id=str(item.get("source_id") or item.get("evidence_id") or ""),
                    source_type=str(item.get("source_type") or ""),
                    owner_id=case.owner_id,
                    rank=index,
                )
                for index, item in enumerate(citation_rows, 1)
            )
            predictions.append(
                replace(
                    case,
                    actual_mode=str(payload.get("mode", "")),
                    answer=str(payload.get("answer", "")),
                    insufficient_evidence=bool(payload.get("insufficient_evidence", False)),
                    retrieved=retrieved,
                    citations=citations,
                )
            )
    return predictions


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cases = load_cases(args.dataset)
    if args.live_endpoint:
        service_token = os.getenv(args.service_token_env, "")
        if not service_token:
            raise ValueError(f"{args.service_token_env} is required for live evaluation")
        cases = asyncio.run(
            run_live_predictions(
                cases,
                endpoint=args.live_endpoint,
                service_token=service_token,
                knowledge_base_id=args.knowledge_base_id,
            )
        )
    dataset_version = "v1"
    report = run_evaluation(cases, dataset_version=dataset_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_json = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(report_json, encoding="utf-8")
    print(json.dumps({"case_count": report.case_count, "gates": report.gates}, sort_keys=True))
    return 0 if all(report.gates.values()) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
