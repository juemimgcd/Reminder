# Mneme Memoria Module

## Durable automation runtime

User-initiated and autonomous runs share one execution path:

```text
HTTP / Heartbeat / domain hook
  -> PostgreSQL agent_runs commit
  -> Redis session FIFO + lease
  -> Celery agent_run worker
  -> Memoria HTTP contract
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

`app.mneme.memoria.server` is the independent online answer runtime. Mneme owns
authorization, chat/session persistence, and event publication; it calls the
Agent through `MemoryAgentClient` and never performs answer-time retrieval or
prompt construction in-process.

## Directory ownership

All in-process Agent orchestration is owned by `app/mneme/memoria`:

- `orchestrator.py`, `router.py`, and `service.py` own request orchestration.
- `contracts.py`, `events.py`, `ports.py`, and `actions.py` own runtime contracts.
- `run_models.py`, `run_service.py`, and `run_submission.py` own durable run flow.
- `api/`, `automation/`, and `tasks/` own Agent HTTP and background entrypoints.
- `clients/`, `chat_bridge.py`, and `memory_gateway.py` own Memoria integration.
- `configuration/`, `models/`, `persistence/`, and `schemas/` own Agent data and storage contracts.
- `projections/` and `cli/` own Agent projection and operational tooling.
- `server/` contains the independently deployed answer API and worker.

The surrounding layers retain only shared business and infrastructure concerns:

- `domains/documents` owns file ingestion, chunking, and indexing.
- `domains/memory` owns durable file-derived memory and memory governance.
- `domains/chat` owns sessions, messages, authorization context, and persistence.
- `domains/retrieval` owns shared context and citation utilities; online answer
  requests do not contain a second Agent implementation there.
- `domains/tasks/outbox.py` owns the shared transactional Outbox and dispatches
  Agent-specific delivery through `memoria/automation/http_outbox.py`.
- `models/base.py`, `conf/database.py`, and the main Alembic chain remain shared
  framework infrastructure; Agent model implementations live under `memoria/models`.

`app/mneme/memoria/server` is a Python subpackage for repository ownership,
but it remains a separate deployment process with its own API, Celery worker,
database, migrations, Redis databases, and service-token boundary.

Backend callers construct a scoped `MemoryAgentAnswerRequest`, submit it over
the service-token HTTP contract, and persist the validated response and run ID.
The Agent owns retrieval, answer modes, citations, memory policy, and answer
quality evaluation in its own database and worker.

`app.mneme.memoria` is the single code-ownership root for backend Agent
orchestration and the Memoria service. The old in-process prompt, history,
context, capability, and tool runtime was removed; online answer ownership is
no longer duplicated across shared backend domains and Memoria.

The Memoria answer contract is idempotent per owner and request ID. The
backend sends a stable request ID for durable-run retries, while explicit user
retries receive a new request ID. Completed responses can therefore be replayed
after a lost HTTP response without making a failed user retry permanently
unusable.

The streaming endpoint publishes validated phase transitions and a final
response. Cancellation propagates from the backend run through the HTTP stream
to the Memoria task, and the backend persists the assistant message only
after the final response arrives. Model attempts, selected provider/model,
fallback use, trace IDs, stale runs, and phase/token/cost metrics are persisted
or exported without logging prompts or answers.

## Operational checks

Use `/health/readiness` for the API/database boundary, `/health/worker` for the
queue consumer boundary, and `/metrics` for run outcomes. Production should
alert when `memory_agent_stale_runs` remains above zero for two recovery
intervals, when no Memoria worker is ready, or when the increase in
`memory_agent_failed_runs` is sustained. Track
`memory_agent_model_retries_total` and `memory_agent_model_fallbacks_total`
together: a rising fallback ratio is an early provider-health signal even when
answers still complete successfully. Phase-duration sum/count, token, and cost
series should be compared by answer mode so a retrieval slowdown is not hidden
inside model latency.

The backend must set `AGENT_RUN_ALLOW_MEMORY_FALLBACK=false` in production.
With that policy, loss of Redis coordination fails requests visibly and later
calls retry initialization instead of silently splitting session queues across
process-local stores.
