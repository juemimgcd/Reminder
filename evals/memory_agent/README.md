# Memory Agent answer-quality baseline

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
python -m services.memory_agent.eval.runner `
  --dataset evals/memory_agent/cases.jsonl `
  --output .tmp/memory-agent-eval.json
```

The JSON report has per-case, per-mode, and overall metrics:

- `pipeline_accuracy`: selected mode matches the deterministic route.
- `source_scope_violations`: evidence owned by a different user (must be 0).
- `recall_at_k` and `mrr`: retrieval baseline, reported without a pass threshold.
- `citation_precision` and `citation_coverage`: supported citations and expected-source coverage.
- `unsupported_claim_flags`: required claims missing or forbidden claims present.
- `no_evidence_behavior`: correct abstention/no-citation behaviour.

Initial release gates are deliberately small and explicit: pipeline accuracy
must be 1.0, scope violations must be 0, citation precision must be 1.0, and
no-evidence behaviour must be 1.0. Retrieval and prose quality remain baseline
signals until a reviewed model-judged set is added.
