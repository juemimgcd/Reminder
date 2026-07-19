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

## Conversation context

Mneme owns conversation history, the rolling summary, and the message watermark
covered by that summary. Before an answer request, the chat domain creates a
bounded snapshot containing the summary plus recent user/assistant messages and
persists any newly compacted summary in the same transaction as the user
message. The Memory Agent receives this optional snapshot through its answer
contract and never reads Mneme chat tables directly.

Generation applies one model-window budget to the current question,
conversation snapshot, and retrieved evidence. In private answer modes,
conversation context may resolve intent and references, but prior assistant
text is not retrieved evidence, cannot support a citation, and cannot override
the current evidence-only answer policy. Callers that omit conversation context
retain the previous single-turn behavior.

The conversation-context layer itself does not execute tools or orchestrate
multiple Agents. The bounded model-review loop, controlled tool boundary, and
optional bounded Multi-Agent retrieval path are described below.

## Bounded reasoning loop

The Memory Agent may perform up to the configured number of model reasoning
steps after one retrieval pass and before citation validation. Every step must
return a complete candidate answer. A step may request another review only for
a material correctness, grounding, or completeness issue, and only a bounded
outcome-level progress note is carried into the next prompt. Hidden
chain-of-thought is neither requested nor persisted.

Execution stops when the model marks a candidate final, the step limit is
reached, or the aggregate completion-token budget is exhausted. Prompt and
completion usage is aggregated across successful steps. The existing
`model_attempts` record stores only provider/model, retry attempt, reasoning
step, decision, and terminal stop reason; it does not store prompts, progress
notes, candidate answers, or credentials.

The initial retrieval pass remains in place for latency and backward
compatibility. Before its final step, the model may additionally select a
source-specific read tool. The runtime intersects every request with the
answer-mode retrieval plan, owner ID, knowledge-base scope, and request top-k;
tool evidence is deduplicated into the same citation-validation boundary.

Tool execution shares the reasoning-step and aggregate token limits and also
has its own `ANSWER_TOOL_MAX_CALLS` hard cap. Only bounded status observations
cross model steps. Public traces contain tool name, risk, status, result count,
and proposal metadata where required; they do not contain read queries,
evidence text, prompts, hidden reasoning, or credentials.

Catalogued write tools are available only for requests tied to a durable chat
session and are proposal-only. Memoria returns
`approval_required`, and Mneme persists an idempotent approval row keyed by
user, message, and tool-call ID. Neither proposal creation nor an `approved`
decision applies a mutation while `apply_enabled=false`. Unknown, out-of-mode,
malformed, and over-budget tool requests are rejected or recorded as bounded
observations. No tool delegates work to another Agent.

## Optional bounded Multi-Agent retrieval

Multi-Agent execution is opt-in per chat. New chats default to the
single-agent path, and changing answer mode never enables Multi-Agent
implicitly. Mneme persists the selected preference on the chat session and
copies it into each durable run, so a queued request cannot change behavior
when the user later updates the chat.

The fixed Coordinator may assign document, memory, profile, and relation
retrieval roles only inside the parent owner and knowledge-base scope.
Retrieval is concurrent but bounded by deadline, source timeout, top-k, model
calls, tokens, and estimated cost. Retrieval roles cannot spawn Agents.
Evidence Judge then deduplicates and resolves conflicts before the existing
citation-validation boundary.

The service-level `memory_agent.multi_agent.enabled` value in `memoria.json`
is the rollout and emergency rollback boundary. Disabling it forces every
request onto the single-agent path even if a chat preference is enabled.
`rollout_percent` selects a stable user/session cohort, and `allowed_modes`
limits rollout to an explicit answer-mode allowlist.

## Configuration boundary

Backend and deployment configuration remains in `.env`: database and queue
URLs, JWT material, service ports, storage backends, and provider secrets.
Agent behavior lives in the project-root `memoria.json`: chat and Memory Agent
models, history and retrieval budgets, retry and answer limits, reasoning,
tools, and Multi-Agent rollout policy.

Like AtlasClaw's JSON configuration, string values may reference environment
secrets with the exact `${VAR_NAME}` form. The JSON file is validated at
startup and is authoritative for Agent fields, so legacy Agent environment
variables cannot silently override the checked-in policy. Set
`MEMORIA_CONFIG_PATH` only when a deployment needs a different JSON file
location.

## Agent quality evaluation

The deterministic evaluation runner scores both final-answer behavior and an
optional sanitized tool trajectory. Existing `gates` retain their stable answer
contract. Separate `agent_gates` cover tool selection precision/recall, call
budget compliance, expected stop reason, and zero action-safety violations.
Cases without trajectory expectations remain neutral, so the versioned
25-case answer baseline is backward compatible. Live evaluation captures the
`tool_calls` returned by `/v1/answers`; fixture cases may additionally specify
expected or forbidden tool names, proposal-only actions, maximum calls, and a
terminal stop reason.

Phase 4 adds a paired single-agent and Multi-Agent baseline. Its release report
checks route and source selection, duplicate and empty retrieval, conflict
detection, Evidence Judge decisions, citations, grounding, partial-failure
recovery, scope/action safety, and quality, latency, token, and cost deltas.
The CLI succeeds only when these Multi-Agent gates and the existing answer and
controlled-tool gates all pass.

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
