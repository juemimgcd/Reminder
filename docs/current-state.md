# Mneme Current State

## Objective

Make Mneme a professionally operated personal knowledge and memory system: durable under retries,
explicit about evidence and ownership, observable in production, and simple enough to evolve
without copying the complexity of a general enterprise agent framework.

## Completed

- Main FastAPI application and Vue workspace with authenticated, owner-scoped APIs.
- Knowledge-base and document ingestion with task records, retry and cancellation behavior.
- Default Memoria answer path using BGE-M3 and PostgreSQL pgvector.
- Governed memory candidates, canonical memory, revisions, relations, deletion fences and action
  audit.
- Explicit answer modes for knowledge base, memory, profile, analysis and general chat.
- Bounded reasoning, read tools, proposal-only write tools and optional bounded multi-agent
  retrieval.
- Durable PostgreSQL agent runs with idempotent submission, Redis session FIFO, renewable leases,
  abort, steer, follow-up and ordered event replay.
- PostgreSQL Outbox/Inbox delivery, dead-letter behavior, Neo4j projection and channel-delivery
  queues.
- Heartbeat jobs, event-triggered automation, approvals and in-app notifications.
- Primary/fallback model attempts, transient retry, provider cooldown and persisted answer-run
  audit.
- Shared HTTP correlation, Prometheus metrics, alert rules and an operations runbook.
- Deterministic Memoria evaluation gates and PostgreSQL/Redis integration execution in CI.
- Canonical architecture and runtime-contract entry points introduced by
  `docs/superpowers/plans/2026-07-22-atlasclaw-lessons-roadmap.md` Task 1.

## In Progress

- No runtime feature is partially enabled by this documentation change.
- The next planned track is context governance and compaction safeguards. It will add an additive
  assembly report and critical-context preservation without changing the public chat API.

## Risks and Decisions

- The main and Memoria databases are intentional ownership boundaries; cross-database reads are
  prohibited.
- Redis run state is ephemeral coordination. PostgreSQL remains the recovery source.
- Neo4j and optional Milvus state are derived and must remain rebuildable.
- Context compaction is currently bounded but does not yet guarantee preservation of every critical
  constraint, unresolved approval or material tool failure.
- Runtime events are durable but do not yet expose a general internal subscriber protocol.
- Grounding is enforced by answer-mode prompts, retrieval scope and citation validation; a single
  explicit grounding-decision contract is planned.
- Arbitrary script hooks, filesystem tools and multi-credential token pooling remain out of scope
  until concrete product and security requirements exist.
- New professionalization work must remain incremental; no phase may replace the durable queue,
  Outbox or approval foundations with an in-process shortcut.

## Next Step

Execute Task 2, context governance and compaction safeguards, from
`docs/superpowers/plans/2026-07-22-atlasclaw-lessons-roadmap.md` as an independent branch and pull
request. Start with failing cases for user directives, unresolved approvals, cited evidence, bounded
tool failures and complete source accounting.

## Last Verified

- Date: 2026-07-22
- Branch baseline: `codex/living-architecture-baseline`
- Backend baseline command: `python -m pytest --basetemp=.pytest_tmp_task1_baseline`
- Backend baseline result: 304 passed, 2 integration tests skipped because real services were not
  enabled, 7 existing warnings.
- Canonical documentation check: `tests/test_dependency_configuration.py`
- Full verification commands and their latest result must be updated in the pull request handoff,
  not copied into this document as permanent claims.
