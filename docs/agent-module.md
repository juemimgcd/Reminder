# Mneme Agent Module

## Durable automation runtime

User-initiated and autonomous runs share one execution path:

```text
HTTP / Heartbeat / domain hook
  -> PostgreSQL agent_runs commit
  -> Redis session FIFO + lease
  -> Celery agent_run worker
  -> Memory Agent HTTP contract
  -> persisted chat exchange + runtime events
  -> Outbox
  -> in-app notification
```

The API process does not own Agent execution. PostgreSQL is the recovery source,
Redis is an ephemeral coordination and streaming layer, and Celery owns task
delivery. Beat scans stale queued/running rows and requeues them idempotently.

FastAPI routes do not use `BackgroundTasks`. External graph projections are
written to the transactional Outbox, while graph and memory rebuilds create
durable `task_records` and run on the `maintenance` queue. The frontend polls
`/tasks/{task_id}`, and Beat republishes stale maintenance work after a worker
or broker interruption.

Heartbeat jobs are user-owned, time-zone aware, constrained by active hours,
and use a hidden system-managed chat session by default. A job may also subscribe
to code-owned domain events such as `document.indexed`, `memory.updated`,
`profile.updated`, or `agent.run.failed`. Hook delivery is implemented through
the existing Outbox so an API/worker crash cannot silently discard the wake-up.

Write actions use a separate proposal catalog. Every proposal records a risk
level and explicit user decision. The first phase intentionally keeps all
actions at `apply_enabled=false`; approval records intent but does not execute a
mutation until an action-specific executor and revalidation boundary are added.

`services.memory_agent` is the independent online answer runtime. Mneme owns
authorization, chat/session persistence, and event publication; it calls the
Agent through `MemoryAgentClient` and never performs answer-time retrieval or
prompt construction in-process.

The surrounding domains retain their existing ownership:

- `domains/documents` owns file ingestion, chunking, and indexing.
- `domains/memory` owns durable file-derived memory and memory governance.
- `domains/chat` owns sessions, messages, authorization context, and persistence.
- `domains/retrieval` retains compatibility utilities during the cleanup
  window; online answer requests do not call them.

Backend callers construct a scoped `MemoryAgentAnswerRequest`, submit it over
the service-token HTTP contract, and persist the validated response and run ID.
The Agent owns retrieval, answer modes, citations, memory policy, and answer
quality evaluation in its own database and worker.

The old `app.mneme.agent` contracts and compatibility retrieval modules remain
only for migration-era tests and document-pipeline cleanup; they are not an
online fallback. Removing those compatibility files is a follow-up after the
remaining document/resource branches are migrated.

Within that compatibility layer, `agent/capabilities.py` indexes trusted
backend capabilities and records eligible, selected, and excluded capability
IDs. `agent/runtime_events.py` provides trace-aware structured logging,
bounded metrics, and best-effort PostgreSQL audit subscribers without storing
prompts, answers, tool arguments, or evidence payloads. Public SSE lifecycle
events carry the same trace and run identifiers while online answers continue
to use the independent Memory Agent service.
