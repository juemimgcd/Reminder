# Capability Index and Runtime Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed answer-mode/tool branch with a lightweight capability projection and add a traceable internal runtime event layer for run, model, tool, and persistence activity.

**Architecture:** Keep `answer_mode` as the API's intent hint, but resolve it through an immutable capability index that emits an explicit minimal projection. Add a per-run dispatcher over a shared event bus; subscribers provide structured logging, aggregate metrics, and best-effort PostgreSQL audit persistence, while an SSE adapter preserves the existing public event contract.

**Tech Stack:** Python 3.13, Pydantic v2, FastAPI, LangChain messages, SQLAlchemy async ORM, Alembic, PostgreSQL, Redis-backed run state.

---

### Task 1: Add the lightweight capability index

**Files:**
- Create: `app/mneme/agent/capabilities.py`
- Modify: `app/mneme/agent/tools/base.py`
- Modify: `app/mneme/agent/tools/registry.py`
- Modify: `app/mneme/agent/tools/policy.py`
- Modify: `app/mneme/agent/tools/backend.py`
- Modify: `app/mneme/agent/tools/builtin/kb_search.py`
- Modify: `app/mneme/agent/tools/builtin/memory_search.py`
- Modify: `app/mneme/agent/tools/builtin/profile_get.py`
- Modify: `app/mneme/agent/tools/builtin/growth_analysis.py`

- [ ] **Step 1: Define immutable capability contracts**

  Add `CapabilityMetadata`, `CapabilityExclusion`, and `CapabilityProjection`. The projection must serialize `eligible_capability_ids`, `selected_capability_ids`, `excluded_capabilities`, `exclusion_reason`, and selected tool names.

- [ ] **Step 2: Build projection from the complete local catalog**

  Match the request's `answer_mode` against each capability's `answer_modes`, reject capabilities that require a missing knowledge base, and select only eligible tool-backed capabilities. General chat produces an empty selected set with a direct-answer reason.

- [ ] **Step 3: Route tool schemas and policy through the projection**

  Change schema generation, policy checks, and fallback tool selection to accept the projection rather than indexing a hard-coded `answer_mode -> tool` map.

- [ ] **Step 4: Verify the projection contract without adding test files**

  Run an inline Python probe that projects every current answer mode and asserts the selected tool IDs, excluded reasons, and general-chat direct-answer result.

### Task 2: Add runtime event contracts and consumers

**Files:**
- Create: `app/mneme/agent/runtime_events.py`
- Create: `app/mneme/models/agent_runtime_event.py`
- Create: `alembic/versions/20260715_03_agent_runtime_events.py`
- Modify: `app/mneme/models/__init__.py`
- Modify: `app/mneme/conf/config.py`

- [ ] **Step 1: Define uniform runtime events**

  Every internal event carries `trace_id`, `run_id`, `session_id`, `user_id`, `loop_index`, `tool_call_id`, `duration_ms`, `input_tokens`, `output_tokens`, `error_kind`, and `selected_capability_ids`, plus a small sanitized payload.

- [ ] **Step 2: Implement isolated subscribers**

  Add a structured logger subscriber, a bounded per-trace metrics collector, and a best-effort SQL audit subscriber. Subscriber failures are logged and must not change the agent result.

- [ ] **Step 3: Add durable audit storage**

  Create `agent_runtime_events` with indexes on trace, run, session, user, and event type. Store only structured metadata; do not persist prompts, model output, tool payloads, secrets, or raw evidence.

- [ ] **Step 4: Add SSE enrichment adapter**

  Preserve existing `AgentEvent` types and phases while attaching the runtime trace identity and selected capability IDs.

### Task 3: Thread trace identity through execution

**Files:**
- Modify: `app/mneme/agent/contracts.py`
- Modify: `app/mneme/agent/run_models.py`
- Modify: `app/mneme/agent/runtime_context.py`
- Modify: `app/mneme/agent/adapters/rag_answer.py`
- Modify: `app/mneme/domains/chat/run_router.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/agent/run_service.py`

- [ ] **Step 1: Generate one trace per run or direct request**

  Persist `trace_id` with `AgentRunRecord`, pass `run_id` and `trace_id` through `AgentRequest`, and construct one runtime dispatcher in `AgentRunContext`.

- [ ] **Step 2: Reuse the trace during retries and recovery**

  Idempotent requests reuse the stored run and its trace. Recovered queued runs must not generate a new trace.

- [ ] **Step 3: Emit persistence completion after commit**

  After user/assistant messages are committed, publish a metadata-only persistence event containing message count and the same trace/run identity.

### Task 4: Instrument the Runner

**Files:**
- Modify: `app/mneme/agent/runner.py`

- [ ] **Step 1: Emit run and context lifecycle events**

  Publish `run.started`, `context.ready`, `capability.projected`, and exactly one terminal run event for completed, failed, timed-out, or aborted execution.

- [ ] **Step 2: Measure model calls**

  Publish requested/completed/failed events around every model invocation, record monotonic duration, and read token counts from LangChain usage metadata when providers return them.

- [ ] **Step 3: Measure tool calls**

  Publish started/completed/failed events with tool call ID, loop index, duration, failure kind, and selected capability IDs. Do not include tool arguments or evidence bodies.

- [ ] **Step 4: Expose safe trace summaries**

  Include trace ID, capability projection, model/tool counts, durations, and token totals in `debug.agent_runtime`. Keep final answers, sources, citations, and existing SSE phases unchanged.

### Task 5: Verify the branch

**Files:**
- No test files are added or modified under the repository test policy.

- [ ] **Step 1: Run Python structural checks**

  Run `python -m compileall -q app/mneme`, Ruff on changed Python files, `alembic heads`, and `git diff --check`.

- [ ] **Step 2: Run the existing backend suite**

  Run `.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider` with a unique repository-local `--basetemp`; expected result is the existing suite with zero failures.

- [ ] **Step 3: Run existing frontend checks**

  Run `npm run lint`, `npm run build`, and `node --test tests/*.test.mjs` in `app/mneme_frontend_v0.2.1`; no frontend source change is expected.

- [ ] **Step 4: Run inline runtime probes**

  Use short one-off Python commands to confirm subscriber isolation, metrics aggregation, SSE trace enrichment, token extraction, capability projection, and audit model serialization without creating test artifacts.

- [ ] **Step 5: Inspect scope**

  Confirm `git status`, `git diff --stat`, and `git diff --check`; `.superpowers/` must remain untracked and excluded.
