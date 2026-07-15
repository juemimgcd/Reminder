# Session Consistency and Structured History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serialize Agent runs per chat session with idempotent creation and persistence, then preserve structured tool history while compacting long conversations without repeatedly summarizing the same messages.

**Architecture:** Extend the existing Redis-capable run store with a per-session FIFO and renewable owner lease; keep different sessions parallel and retain the in-process fallback for development. Persist an Agent run identifier on each chat exchange, rebuild valid AI/tool message pairs from stored evidence, and persist deterministic staged summaries on the chat session. This implements the minimal third/fourth priorities from `boost.md`; it does not add steering, a general queue framework, or Celery run execution.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy async, PostgreSQL/Alembic, redis.asyncio, LangChain messages, Vue 3/TypeScript

---

## Constraints and success criteria

- Do not add or modify test files under the current repository policy.
- Do not add Agent-side authentication, registration, RBAC, provider, or skill management.
- Preserve existing synchronous chat and SSE/run response compatibility.
- Exclude `.superpowers/` local artifacts from source control.
- The same session executes one run at a time in FIFO order; different sessions remain independent.
- Reusing `(user_id, session_id, client_request_id)` returns the original run and does not enqueue duplicate work.
- A recovered/retried run cannot persist a second user/assistant exchange.
- Rebuilt history contains valid tool-call/tool-result pairs, source identifiers, and tool failure reasons.
- Context governance trims raw tool payloads before conversational text and stores the summary watermark on the session.

### Task 1: Session FIFO and idempotent run creation

**Files:**
- Modify: `app/mneme/agent/run_models.py`
- Modify: `app/mneme/infra/agent_runs.py`
- Modify: `app/mneme/agent/run_service.py`
- Modify: `app/mneme/conf/config.py`
- Modify: `app/mneme/domains/chat/run_router.py`
- Modify: `app/mneme/schemas/chat_session.py`

- [ ] Add `client_request_id` and queue timing fields to `AgentRunRecord` without changing existing required API fields.
- [ ] Add an atomic Redis `create-or-get + RPUSH` operation keyed by user, session, and client request ID; mirror it under one asyncio lock for the memory backend.
- [ ] Add per-session FIFO claim, renewable lease, release, and queued-run removal operations.
- [ ] Make `execute_agent_run()` wait for its FIFO turn, honor abort while waiting, renew its lease while running, and always release the queue slot.
- [ ] Schedule background execution only when a run was newly created; return the existing record for duplicate client requests.
- [ ] Add configurable lease and poll durations with conservative defaults.

### Task 2: PostgreSQL exchange idempotency

**Files:**
- Create: `alembic/versions/20260715_02_session_consistency_history.py`
- Modify: `app/mneme/models/chat_message.py`
- Modify: `app/mneme/crud/chat_message.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/schemas/chat_session.py`

- [ ] Add nullable `agent_run_id` to chat messages and a unique `(agent_run_id, role)` constraint; existing null rows remain compatible.
- [ ] Load an already-persisted exchange by run ID before inserting messages.
- [ ] Pass `run_id` from background execution through streaming persistence and write it on both exchange rows.
- [ ] Keep synchronous non-run chat persistence unchanged by allowing `agent_run_id=None`.
- [ ] Expose optional `agent_run_id` in message detail responses for traceability.

### Task 3: Structured history reconstruction

**Files:**
- Modify: `app/mneme/agent/contracts.py`
- Modify: `app/mneme/agent/history.py`
- Modify: `app/mneme/agent/runner.py`

- [ ] Extend `AgentHistoryMessage` with message ID, tool calls, sources, and citations using empty compatible defaults.
- [ ] Persist `error_message` and source IDs in normalized tool-call records.
- [ ] Rebuild every stored successful or failed call as an `AIMessage(tool_calls=...)` followed by its matching `ToolMessage`.
- [ ] Put the historical assistant natural-language answer after reconstructed tool results.
- [ ] Generate deterministic fallback IDs for legacy tool calls that lack IDs and never emit orphan tool results.

### Task 4: Tool-aware staged compaction and summary persistence

**Files:**
- Modify: `app/mneme/agent/context_manager.py`
- Modify: `app/mneme/agent/runner.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/models/chat_session.py`
- Modify: `app/mneme/conf/config.py`

- [ ] Count structured tool/source payloads in context estimates.
- [ ] Soft-trim old source text first, hard-clear remaining raw source text only when needed, and retain tool outcomes, failure reasons, source IDs, and citation IDs.
- [ ] Summarize removed messages in stages while retaining decisions/questions as conversational text plus compact tool/source markers.
- [ ] Add `context_summary` and `context_summary_through_message_id` to chat sessions through the Task 2 migration.
- [ ] Merge new deterministic summaries with the existing stored summary and load only messages after the persisted watermark.
- [ ] Pass prepared summary/compaction metadata into the runner so the same removed messages are not summarized again.

### Task 5: Frontend idempotency and compatibility

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`

- [ ] Generate one `client_request_id` per submitted message and include it in run creation.
- [ ] Carry `client_request_id` in `AgentRunData` and preview run fixtures.
- [ ] Preserve current optimistic chat rendering and SSE consumption.

### Task 6: Verification without test-file changes

- [ ] Run scoped Ruff and Python `compileall` checks.
- [ ] Run inline contracts for duplicate run creation, same-session FIFO, different-session claims, queued abort, exchange idempotency helpers, tool-call pairing, and source-first compaction.
- [ ] Run Alembic head validation and inspect the generated migration chain.
- [ ] Run the complete existing backend suite with a workspace-local pytest basetemp.
- [ ] Run frontend `vue-tsc --noEmit`, production build, and existing Node contract tests.
- [ ] Run `git diff --check` and verify `.superpowers/` remains excluded.
