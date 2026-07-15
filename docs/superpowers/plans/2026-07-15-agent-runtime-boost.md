# Mneme Agent Runtime Boost Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining `boost.md` architecture by adding static tool contracts, durable run control, context-window governance, and execution-evidence enforcement.

**Architecture:** Keep backend authentication and ownership checks authoritative. Add a static, code-owned tool catalog without management APIs; persist short-lived run state and ordered events through a Redis-capable store with an in-process development fallback; continue persisting final chat answers and tool evidence in PostgreSQL.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, LangChain ChatOpenAI, SQLAlchemy async, PostgreSQL, redis.asyncio, Vue 3

---

## Constraints

- Do not add Provider, Skill, Agent registration management, or Agent-side RBAC.
- Tool schemas must never expose user, session, or knowledge-base ownership identifiers.
- Keep the synchronous message API and direct SSE endpoint compatible.
- Do not add or modify tests; verify through existing suites and inline contract checks.
- Preserve all pre-existing uncommitted work.

### Task 1: Static tool contracts and policy

**Files:**
- Create: `app/mneme/agent/tools/base.py`
- Create: `app/mneme/agent/tools/registry.py`
- Create: `app/mneme/agent/tools/policy.py`
- Modify: `app/mneme/agent/tools/backend.py`
- Modify: `app/mneme/agent/tools/contracts.py`

- [ ] Define immutable `ToolMetadata`, `ToolErrorKind`, and normalized success/error results.
- [ ] Declare the four Mneme capabilities in a static catalog with read-only, evidence, scope, and timeout metadata.
- [ ] Resolve the `answer_mode` preference to exactly one eligible tool without adding a mutable registration system.
- [ ] Convert backend exceptions into retryable, business, unavailable, or aborted tool outcomes.
- [ ] Block mandatory-tool turns from returning ungrounded answers when execution fails.

### Task 2: Run state and ordered event store

**Files:**
- Create: `app/mneme/agent/run_models.py`
- Create: `app/mneme/infra/agent_runs.py`
- Modify: `app/mneme/conf/config.py`

- [ ] Define queued, running, completed, failed, and aborted run states.
- [ ] Store run records, ordered events, terminal errors, and abort flags with TTL.
- [ ] Use Redis streams when reachable and a concurrency-safe process-local fallback for local development.
- [ ] Support event reads strictly after a `Last-Event-ID` cursor.
- [ ] Never store API keys, raw trusted context, or database sessions in run state.

### Task 3: Run lifecycle API

**Files:**
- Create: `app/mneme/agent/run_service.py`
- Modify: `app/mneme/domains/chat/router.py`
- Modify: `app/mneme/schemas/chat_session.py`

- [ ] Add `POST /kb/chat/sessions/{session_id}/runs` after ownership and archive checks.
- [ ] Add `GET /kb/chat/runs/{run_id}/stream` with ownership checks and cursor resume.
- [ ] Add `GET /kb/chat/runs/{run_id}` for status.
- [ ] Add `POST /kb/chat/runs/{run_id}/abort` to persist cancellation intent.
- [ ] Execute each background run in its own database session and persist the final exchange once.

### Task 4: Context-window governance

**Files:**
- Modify: `app/mneme/domains/settings/ai_models.py`
- Modify: `app/mneme/agent/context_manager.py`
- Modify: `app/mneme/agent/runner.py`
- Modify: `app/mneme/conf/config.py`

- [ ] Propagate the configured model context window into the request runtime.
- [ ] Reserve configurable output tokens and estimate prompt/history tokens.
- [ ] Keep the newest configured number of turns and never trim the current question or system prompt.
- [ ] Produce a deterministic summary of removed history and inject it as context.
- [ ] Emit before/after token estimates and the compaction reason.

### Task 5: PostgreSQL tool evidence

**Files:**
- Create: `alembic/versions/20260715_01_add_chat_tool_evidence.py`
- Modify: `app/mneme/models/chat_message.py`
- Modify: `app/mneme/crud/chat_message.py`
- Modify: `app/mneme/schemas/chat_session.py`
- Modify: `app/mneme/domains/chat/service.py`

- [ ] Add nullable `tool_calls_json` to existing chat messages.
- [ ] Persist normalized tool name, arguments, outcome, loop index, and evidence counts without secrets.
- [ ] Return persisted tool evidence in chat-session detail responses.
- [ ] Keep existing rows and old clients compatible through an empty-list default.

### Task 6: Frontend run API consumption

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`

- [ ] Start a run and consume ordered events by `run_id`.
- [ ] Preserve incremental assistant rendering and tool-status banners.
- [ ] Refresh persisted messages after terminal events.
- [ ] Keep preview mode deterministic and compatible.

### Task 7: Verification

- [ ] Run the full existing backend suite with a workspace-local pytest basetemp.
- [ ] Run scoped Ruff checks, compileall, Alembic head validation, and OpenAPI path checks.
- [ ] Run inline contracts for static tool policy, cursor ordering, abort propagation, compaction metadata, and evidence blocking.
- [ ] Run frontend `vue-tsc --noEmit` and the production build.
- [ ] Inspect `git diff --check`, scoped diff, migration chain, and final worktree status.
