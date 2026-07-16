# Agent Runtime Hardening Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with verification checkpoints. The repository policy forbids adding or modifying tests unless explicitly requested, so this plan uses existing tests, inline contract checks, migration checks, and builds.

**Goal:** Close the seven remaining Agent reliability, recovery, model resilience, architecture-boundary, retrieval, observability, and verification gaps on the real Memory Agent execution path.

**Architecture:** Keep Mneme as the durable orchestration, authorization, and chat-persistence boundary. Keep `services.memory_agent` as the sole online answer runtime, make requests idempotent and traceable, and retain Redis only as an explicitly configured coordination layer. Avoid adding registration, Agent-side RBAC, Provider management, Skills, or sub-Agent infrastructure.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy async, PostgreSQL, Redis, Celery, httpx, OpenAI-compatible APIs, Vue 3

---

### Task 1: Reproducible validation baseline

**Files:**
- Modify: `requirements/base.txt`
- Modify only if production compatibility requires it: `app/mneme/bootstrap/router_registry.py`
- Verify: existing backend tests and OpenAPI paths

- [ ] Rebuild a worktree-local Python 3.13 environment from the pinned requirements instead of using the stale root `.venv`.
- [ ] Confirm whether the `_IncludedRouter` failure reproduces with pinned FastAPI and Starlette.
- [ ] If it reproduces, preserve FastAPI router behavior and validate registered paths through the generated OpenAPI schema rather than mutating application routing semantics.
- [ ] Run the existing Agent and Memory Agent suite and record the exact baseline.

### Task 2: Cancellation, streaming events, and answer idempotency

**Files:**
- Modify: `app/mneme/agent/run_service.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/clients/memory_agent_client.py`
- Modify: `app/mneme/schemas/memory_agent.py`
- Modify: `services/memory_agent/api/answers.py`
- Modify: `services/memory_agent/contracts/answers.py`
- Modify: `services/memory_agent/runtime/orchestrator.py`
- Modify: `services/memory_agent/runtime/contracts.py`
- Modify: `services/memory_agent/repositories/runs.py`
- Modify: `services/memory_agent/models/answer_run.py`
- Create: `services/memory_agent/alembic/versions/20260716_01_harden_answer_runs.py`

- [ ] Propagate a stable trace ID and idempotency request ID from the durable Mneme run into Memory Agent.
- [ ] Make manual abort cancel the owning task so the in-flight HTTP/LLM request receives cancellation.
- [ ] Prevent assistant-message persistence after cancellation.
- [ ] Emit durable phase events during retrieval, generation, and citation validation; keep the final answer as a validated terminal payload.
- [ ] Add a unique request identity and persist the completed response payload so safe retries replay the same result.
- [ ] Return a stable in-progress error for duplicate requests that are not terminal yet.

### Task 3: Exhausted and stale run recovery plus Redis production policy

**Files:**
- Modify: `app/mneme/conf/config.py`
- Modify: `app/mneme/crud/agent_automation.py`
- Modify: `app/mneme/tasks/agent_tasks.py`
- Modify: `app/mneme/infra/agent_runs.py`
- Modify: `services/memory_agent/config.py`
- Modify: `services/memory_agent/repositories/runs.py`
- Modify: `services/memory_agent/api/health.py`

- [ ] Select stale Mneme runs whose attempts are exhausted under `FOR UPDATE SKIP LOCKED` and finalize them as failed.
- [ ] Remove exhausted runs from the Redis session queue and emit the existing failure event/notification path.
- [ ] Mark stale Memory Agent answer runs failed before accepting or reporting new work.
- [ ] Permit process-local run storage only when an explicit development fallback flag is enabled.
- [ ] Fail fast in production when Redis coordination cannot be initialized and allow reconnect attempts after transient failures.

### Task 4: Model retry and explicit fallback matrix

**Files:**
- Modify: `services/memory_agent/config.py`
- Modify: `services/memory_agent/providers/llm.py`
- Modify: `services/memory_agent/runtime/contracts.py`
- Modify: `services/memory_agent/repositories/runs.py`
- Modify: `services/memory_agent/models/answer_run.py`
- Modify: `services/memory_agent/alembic/versions/20260716_01_harden_answer_runs.py`

- [ ] Classify authentication, rate-limit, transient transport, provider 5xx, invalid structured output, and permanent errors.
- [ ] Retry only transient failures with bounded exponential backoff and `Retry-After` support.
- [ ] Support one explicitly configured service fallback model; never silently replace a user-selected model unless the request opts in.
- [ ] Persist sanitized model-attempt metadata, token counts, and the selected model without storing API keys.

### Task 5: Converge the online Agent boundary

**Files:**
- Modify: `app/mneme/agent/adapters/__init__.py`
- Modify: `app/mneme/agent/adapters/rag_answer.py`
- Modify: `app/mneme/agent/__init__.py`
- Modify: `docs/agent-module.md`
- Remove only after import verification: unused legacy runner/runtime/tool files under `app/mneme/agent/`

- [ ] Keep durable run models, public events, routing contracts, and action proposals that remain used by Mneme.
- [ ] Remove the unused `RuntimeAnswerEngine`/`build_mneme_agent` online-looking adapter path.
- [ ] Delete only legacy modules with no non-test production importers.
- [ ] Document `services.memory_agent` as the single answer runtime and Mneme as the orchestration boundary.

### Task 6: Parallel retrieval and model-aware context budget

**Files:**
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/schemas/memory_agent.py`
- Modify: `services/memory_agent/contracts/common.py`
- Modify: `services/memory_agent/runtime/retriever.py`
- Modify: `services/memory_agent/runtime/prompts.py`
- Modify: `services/memory_agent/providers/llm.py`
- Modify: `services/memory_agent/config.py`

- [ ] Propagate the selected model context window without exposing credentials.
- [ ] Execute independent document, memory, profile, and relation retrieval concurrently.
- [ ] Fuse source-local rankings with deterministic reciprocal-rank fusion while preserving scope filtering and deduplication.
- [ ] Derive the evidence character budget from context-window tokens, prompt reserve, and output reserve.

### Task 7: Cross-service observability and live evaluation entry

**Files:**
- Modify: `app/mneme/clients/memory_agent_client.py`
- Modify: `services/memory_agent/observability/context.py`
- Modify: `services/memory_agent/observability/metrics.py`
- Modify: `services/memory_agent/api/health.py`
- Modify: `services/memory_agent/eval/runner.py`
- Modify: `evals/memory_agent/README.md`
- Modify: `docs/agent-module.md`

- [ ] Propagate `X-Trace-ID` across Mneme and Memory Agent and bind it to request/run logs.
- [ ] Export stale-run, retry, fallback, phase-duration, token, and cost signals from persisted run data.
- [ ] Add an opt-in live evaluation mode that submits the versioned cases to a configured Memory Agent endpoint while keeping offline fixture mode deterministic.
- [ ] Document operational commands and alert signals.

### Task 8: Verification and handoff

- [ ] Run existing backend tests using the worktree-local pinned environment.
- [ ] Run Ruff and `compileall` on changed Python modules.
- [ ] Validate both Alembic heads and migration chains.
- [ ] Run Memory Agent offline evaluation and any configured live smoke mode without storing secrets.
- [ ] Run frontend lint/type checking and production build if the API contract changes affect generated types.
- [ ] Run `git diff --check`, inspect the scoped diff, and confirm only intended files changed.
