# Memoria answer-quality baseline

`cases.jsonl` is a versioned, deterministic fixture set. It contains five
cases for each explicit answer mode (`kb_qa`, `memory_query`, `profile_query`,
`analysis_query`, and `general_chat`). Predictions are fixtures in the file so
the baseline never calls a model, network service, PostgreSQL, or Redis.

The set includes no-evidence abstention, conflicting current and historical
values, historical retrieval, scope-filtered unauthorized evidence, and the
citation contract, including a rejected citation fixture. The unauthorized fixtures represent evidence that was
filtered before answer generation; a future implementation that returns an
evidence item owned by another owner will increment `source_scope_violations`
and fail the gate.

Run it from the repository root:

```powershell
python -m app.mneme.memoria.server.eval.runner `
  --dataset app/mneme/memoria/server/eval/cases.jsonl `
  --output .tmp/memory-agent-eval.json
```

The JSON report has per-case, per-mode, and overall metrics:

- `pipeline_accuracy`: selected mode matches the deterministic route.
- `source_scope_violations`: evidence owned by a different user (must be 0).
- `recall_at_k` and `mrr`: retrieval baseline, reported without a pass threshold.
- `citation_precision` and `citation_coverage`: supported citations and expected-source coverage.
- `unsupported_claim_flags`: required claims missing or forbidden claims present.
- `no_evidence_behavior`: correct abstention/no-citation behaviour.
- `tool_selection_precision` and `tool_selection_recall`: expected tool choice.
- `tool_budget_compliance` and `trajectory_efficiency`: bounded, non-redundant calls.
- `stop_correctness`: expected terminal reason when a fixture declares one.
- `action_safety_violations`: forbidden tools or write tools that bypass proposal status.

Initial release gates are deliberately small and explicit: pipeline accuracy
must be 1.0, scope violations must be 0, citation precision must be 1.0, and
no-evidence behaviour must be 1.0. Retrieval and prose quality remain baseline
signals until a reviewed model-judged set is added.

The report also contains a separate `agent_gates` object. It requires perfect
tool selection for declared expectations, full call-budget and stop compliance,
and zero action-safety violations. Cases that do not declare trajectory
expectations are neutral, so the original answer gates and fixed dataset remain
stable. Optional fixture fields are:

```json
{
  "expected": {
    "tool_names": ["search_memories"],
    "forbidden_tool_names": ["search_documents"],
    "approval_required_actions": ["memory_review.propose"],
    "max_tool_calls": 2,
    "stop_reason": "model_final"
  },
  "prediction": {
    "tool_calls": [
      {"name": "search_memories", "risk_level": "read", "status": "completed"}
    ],
    "stop_reason": "model_final"
  }
}
```

To evaluate a running Memoria instead of the stored fixture predictions,
provide the service endpoint and a service-token environment variable:

```powershell
$env:MEMORY_AGENT_EVAL_TOKEN = "replace-with-service-token"
python -m app.mneme.memoria.server.eval.runner `
  --dataset app/mneme/memoria/server/eval/cases.jsonl `
  --output .tmp/memory-agent-live-eval.json `
  --live-endpoint http://localhost:8010 `
  --service-token-env MEMORY_AGENT_EVAL_TOKEN `
  --knowledge-base-id replace-with-eval-knowledge-base-id
```

Live mode keeps the same deterministic gates and replaces the fixture's
predicted answer, mode, citations, confidence, evidence flags, and sanitized
tool calls with the validated `/v1/answers` response. Each call receives its own request and trace IDs, so the
result can be correlated with answer-run metrics and structured logs.

## Multi-Agent A/B release evaluation

Phase 4 adds a paired baseline that compares the existing single-agent path
with the bounded Multi-Agent candidate. It is deterministic and does not
require credentials:

```powershell
uv run python -m app.mneme.memoria.server.eval.runner `
  --dataset app/mneme/memoria/server/eval/cases.jsonl `
  --multi-agent-dataset app/mneme/memoria/server/eval/multi_agent_cases.jsonl `
  --output .tmp/memoria-eval.json
```

The `multi_agent` report includes route accuracy, source-selection
precision/recall, duplicate and empty-agent ratios, conflict detection,
Evidence Judge keep/drop precision, citation validity, grounded-answer and
partial-failure recovery rates, plus quality, latency, token, and cost deltas
against the single-agent baseline.

Release succeeds only when the existing answer and agent gates and all
Multi-Agent gates pass. Multi-Agent remains an explicit per-chat preference
that defaults to off. Operators can force the single-agent path immediately by
setting `memory_agent.multi_agent.enabled` to `false` in `memoria.json`.
Operators may stage the rollout with `rollout_percent` and `allowed_modes` in
the same section.
