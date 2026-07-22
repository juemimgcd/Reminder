# Mneme Runtime Contracts

## Purpose

This document records behavior that callers, workers and operators may rely on. It describes the
current contracts implemented under `app/mneme`; it is not an inventory of future roadmap ideas.

## Agent-run identity and durability

- `run_id` identifies one logical run and `trace_id` correlates its cross-service work.
- `(user_id, session_id, client_request_id)` is the idempotency boundary for run creation.
- The PostgreSQL `agent_runs` row is committed before the run is added to Redis or Celery.
- PostgreSQL is the recoverable fact source. Redis may expire and be reconstructed from a
  non-terminal durable run.
- Terminal statuses are `completed`, `failed`, and `aborted`. A terminal run is never returned to
  a non-terminal state.

The implementation boundary is split between `app/mneme/memoria/run_submission.py`,
`app/mneme/memoria/run_service.py`, and `app/mneme/memoria/persistence/runs.py`.

## Session execution and control

- Runs in one session are FIFO and execute one at a time.
- A Redis lease has an opaque token and must be renewed by its owner.
- Losing the lease cancels execution and records a stable failure event.
- `interrupt` stores abort intent for the target run.
- `steer` stores abort intent and submits a replacement run with the new direction.
- `followup` submits a later session turn without mutating the active run.
- Run and session ownership are checked for every read, stream, abort and control operation.

## Runtime event delivery

Canonical event names are defined by `AgentRunEventType` in `app/mneme/memoria/events.py`.

- Events are assigned a positive, monotonically increasing sequence per run.
- The sequence is allocated while the durable run row is locked.
- The PostgreSQL event is flushed before Redis stream acceleration is attempted.
- SSE cursors use the durable integer sequence; reconnecting with `Last-Event-ID` resumes after that
  sequence.
- Public payloads contain stable status and progress fields, not secrets or raw provider errors.
- Redis stream loss may reduce live acceleration but must not remove durable replay.

## Outbox contract

Outbox behavior is implemented in `app/mneme/domains/tasks/outbox.py`.

- An event idempotency key is
  `event_type:aggregate_type:aggregate_id:operation_id`.
- Inserting the same idempotency key returns the existing event.
- Dispatchable states are `pending` and retryable `failed`; `running`, `succeeded`, and
  `dead_letter` are not redispatched as new work.
- A successful side effect is followed by a durable `succeeded` transition.
- Retry delay and maximum attempts are bounded by configuration.
- Exhausted work becomes `dead_letter` and remains operator-visible.
- Payloads containing recognized credentials or private-key material are rejected or sanitized at
  the applicable boundary.

Outbox targets include Memoria HTTP delivery, Neo4j projection, in-app notification, internal
automation hooks and configured channel delivery. Target handlers must be idempotent because a
worker may fail after the side effect and before acknowledging success.

## Retrieval, context and evidence

- Answer mode selects the allowed retrieval plan; document retrieval requires a knowledge-base
  scope.
- Every retrieval request carries `owner_id`; private evidence from another owner is invalid.
- Evidence text and conversation text are untrusted data, not system instructions.
- Conversation history may resolve intent and references, but prior assistant claims are not
  evidence.
- Private answer modes may cite only evidence IDs supplied to the current generation run.
- Citation validation removes missing, duplicated or unsupported citations before completion.
- When available evidence is insufficient, the answer must say so rather than invent a source.
- General chat receives no private evidence and must not claim access to documents, profile, or
  memory.

### Context governance and compaction

Conversation context is assembled deterministically without a model or database call in the
governance layer. Sources use this precedence:

```text
system safety boundary
> explicit user directive
> unresolved approval
> cited evidence identifier
> material tool failure
> confirmed inferred memory
> recent conversation
> old conversation summary
```

Every supplied source receives an `included`, `preserved`, `truncated`, or `dropped` decision in
the versioned context assembly report. The report records character counts and estimated tokens,
contains no raw tool arguments, and is attached to `context.compacted` metadata. Existing
consumers may continue treating `AgentRequest.history_compaction` as an optional JSON object.

Critical items are individually bounded. API keys, bearer credentials, confirmation tokens,
passwords, and secret assignments are redacted before an item can enter assembled context.
Citation identifiers, pending approval summaries, and short stable tool-failure records may survive
ordinary-history compaction; successful tool payloads do not. If governance itself fails, the
runtime uses the original bounded conversation context rather than sending an empty context.

## Model calls and fallback

- Model credentials are internal fields and never appear in public responses or event payloads.
- Each reasoning loop has bounded model-call, prompt-token, completion-token, tool-call and step
  budgets.
- Provider errors are mapped to stable codes such as capacity, authentication, invalid response,
  timeout and unavailable.
- Only classified transient failures are retried.
- A fallback is used only when the request allows it and a distinct fallback model is configured.
- Provider cooldown is process-local optimization; durable answer-run attempts remain the audit
  source.
- Generated answers record selected provider/model, attempts, fallback use, token usage, stop
  reason and degraded multi-agent state where applicable.

## Tools and approvals

Tool execution is bounded by `app/mneme/memoria/server/runtime/tools.py`.

Canonical tool statuses are:

- `completed`
- `approval_required`
- `rejected`
- `failed`
- `budget_exceeded`

Read tools inherit the current owner, knowledge-base, answer-mode and top-k scope. Write-class tools
do not mutate state. They emit a bounded proposal that is persisted as a durable approval request.
The current approval record has `apply_enabled=false`; approval records the user's decision but does
not create an undocumented mutation path.

## Error and retry boundaries

- Validation errors expose stable client-safe codes.
- Dependency timeouts, capacity, authentication and availability failures are classified before
  crossing an API boundary.
- Public errors do not include exception text, provider bodies, SQL, credentials or retrieved
  private content.
- Workers persist failure state before rethrowing when the queue must observe failure.
- Retryable work has an attempt limit and transitions to a visible failed or dead-letter state.
- Cleanup errors may be suppressed only after the primary outcome is already known.

Detailed exception categories are maintained in `docs/exception-boundaries.md`.

## Health and metrics contracts

- Liveness checks process availability and avoids external dependencies.
- Readiness checks required dependencies for that service.
- Worker diagnostics remain separate from API liveness.
- Prometheus labels use bounded dimensions such as route templates, method and status; user IDs,
  run IDs and concrete URL values are not metric labels.
- Request and trace IDs are accepted only after safe-format validation and are echoed to callers.

The operator response contract is documented in `docs/operations-runbook.md` and alert expressions
are stored in `deploy/monitoring/mneme-alerts.yml`.

## Compatibility rules

- New request or event fields are optional for at least one compatibility release unless the
  endpoint is explicitly versioned.
- Event names are append-only; renaming an emitted event requires a migration and compatibility
  plan.
- Database schema changes use Alembic and must leave exactly one main migration head.
- A change to durability, ownership, idempotency, evidence, approval or error privacy must update
  this document and add a focused contract check.
