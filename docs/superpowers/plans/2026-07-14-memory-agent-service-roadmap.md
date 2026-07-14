# Memory Agent Service Delivery Roadmap

This roadmap implements the approved [Memory Agent Service design](../specs/2026-07-14-memory-agent-service-design.md) through four ordered plans. Execute them in order; each plan assumes the commits from the previous plan.

1. [Service foundation](2026-07-14-memory-agent-service-foundation.md) — independent application, database, contracts, service authentication, HTTP Outbox delivery, and deployment topology.
2. [Projection and memory 2.0](2026-07-14-memory-agent-projection-and-memory.md) — batched document projection, pgvector retrieval, governed memory, conversation extraction, deletion, and backfill.
3. [Runtime and product cutover](2026-07-14-memory-agent-runtime-and-product.md) — bounded answer runtime, five explicit modes, Mneme client cutover, Memory Center, observability, and rollback switch.
4. [Concentrated verification and cleanup](2026-07-14-memory-agent-verification-and-cleanup.md) — all test files, evaluation baseline, end-to-end verification, removal of the legacy runtime, and final release checks.

## Cross-plan rule

Plans 1–3 must not create or modify test files. Only source-level checks, lint, compilation, migration inspection, and deployment configuration validation are allowed. Plan 4 begins only after all business implementation in Plans 1–3 is complete; it then creates and runs the entire test and evaluation suite in one concentrated phase.

## Branch and review sequence

Use one feature branch, `feat/memory-agent-service`, with review checkpoints after each plan. Do not open separate PRs that can be merged out of order. The final PR should retain the task-level commits so reviewers can inspect the service boundary, data model, cutover, tests, and legacy cleanup independently.
