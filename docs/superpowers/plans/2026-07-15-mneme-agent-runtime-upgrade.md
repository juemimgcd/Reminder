# Mneme Agent Runtime Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Mneme from a single-turn answer adapter to a backend-integrated, multi-turn, tool-capable, streaming Agent runtime without duplicating backend authentication, authorization, or provider registration.

**Architecture:** Keep FastAPI and the chat domain responsible for authentication, session ownership, knowledge-base ownership, and persistence. Pass a trusted request-scoped context into a framework-neutral runner backed by the installed ChatOpenAI client, expose only four internal backend capabilities, and preserve the current synchronous `MnemeAgent.run()` contract while adding an event stream for SSE consumers.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, LangChain ChatOpenAI, SQLAlchemy async, PostgreSQL, existing LangChain RAG services

---

## Scope and constraints

- Do not add an Agent-side RBAC layer, provider registry, skill registry, or management API.
- Do not allow model-generated tool arguments to select `user_id`, `session_id`, or `knowledge_base_id`.
- Preserve the current `/kb/chat/sessions/{session_id}/messages` response shape.
- Preserve explicit `answer_mode` behavior by limiting the runtime capabilities available for that turn.
- Reuse the existing retrieval, citation validation, memory, profile, and growth services.
- Do not add or modify tests under the repository test-addition policy. Run existing tests and direct contract checks.
- Preserve all pre-existing uncommitted work in the current worktree.

### Task 1: Runtime contracts and trusted context

**Files:**
- Modify: `app/mneme/agent/contracts.py`
- Create: `app/mneme/agent/runtime_context.py`
- Create: `app/mneme/agent/events.py`
- Modify: `app/mneme/agent/ports.py`

- [ ] Extend `AgentRequest` with optional `session_id` and immutable history entries while retaining all existing fields.
- [ ] Define `AgentHistoryMessage`, `AgentToolCall`, and normalized response metadata as Pydantic models.
- [ ] Define `AgentRunContext` as the trusted request-scoped container for database session, user ID, session ID, knowledge-base ID, model configuration, and cancellation event.
- [ ] Define lifecycle, assistant, tool, compaction, and error stream event types with stable serialization.
- [ ] Keep framework and persistence imports out of core contracts and ports; SQLAlchemy belongs only in `runtime_context.py` and adapters.
- [ ] Verify with `python -m compileall app/mneme/agent` and the existing module-boundary test.

### Task 2: History and context budget

**Files:**
- Create: `app/mneme/agent/history.py`
- Create: `app/mneme/agent/context_manager.py`
- Modify: `app/mneme/crud/chat_message.py`

- [ ] Add a history adapter that converts persisted `ChatMessage` rows to runtime messages without exposing ORM objects to the Agent core.
- [ ] Load history before the current user message is persisted, avoiding duplication of the active question.
- [ ] Keep the newest messages within a deterministic character/token approximation budget.
- [ ] Prefer dropping old tool payloads and old messages while retaining the newest user/assistant exchange.
- [ ] Emit compaction metadata when history is reduced; do not add an LLM summary pass in this first implementation.
- [ ] Verify history ordering and pruning with direct Python contract checks against in-memory message values.

### Task 3: Internal backend tools

**Files:**
- Create: `app/mneme/agent/tools/__init__.py`
- Create: `app/mneme/agent/tools/contracts.py`
- Create: `app/mneme/agent/tools/backend.py`
- Modify: `app/mneme/agent/orchestrator.py`

- [ ] Define a normalized internal tool result carrying content, structured data, evidence, and error state.
- [ ] Expose `kb_search`, `memory_search`, `profile_get`, and `growth_analysis` as request-scoped tools.
- [ ] Bind trusted scope from `AgentRunContext`; tool schemas must not contain ownership identifiers.
- [ ] Reuse `build_query_context`, profile, and growth domain services instead of duplicating their implementations.
- [ ] Keep citation resolution in the existing evidence-answer path and propagate tool evidence into the final `AgentResponse`.
- [ ] Verify each callable imports and returns JSON-serializable data using existing domain fakes where available.

### Task 4: Tool-loop runner and compatibility facade

**Files:**
- Create: `app/mneme/agent/prompt_builder.py`
- Create: `app/mneme/agent/guards.py`
- Create: `app/mneme/agent/runner.py`
- Modify: `app/mneme/agent/service.py`
- Modify: `app/mneme/agent/adapters/rag_answer.py`
- Review: `requirements/ai.txt`

- [ ] Keep the runner behind Mneme-owned contracts; do not add a new framework dependency when dependency resolution is unavailable.
- [ ] Build one runtime prompt containing identity, current answer mode, recent history, available capabilities, evidence rules, and response requirements.
- [ ] Map the configured OpenAI-compatible provider into the existing ChatOpenAI model without leaking API keys into events or logs.
- [ ] Execute the model/tool loop with timeout, cancellation, maximum loop count, maximum tool-call count, and identical-call protection.
- [ ] Yield stream events during execution and aggregate them into the existing `AgentResponse` for `run()` callers.
- [ ] Preserve the old RAG answer adapter as a fallback for unsupported provider/model combinations or runtime-disabled configuration.
- [ ] Verify imports, a fake-model direct-answer run, a fake-model tool-call run, and existing Agent tests without changing test files.

### Task 5: Chat integration and SSE

**Files:**
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/domains/chat/router.py`
- Modify: `app/mneme/schemas/chat_session.py`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`

- [ ] Build `AgentRunContext` only after existing session and knowledge-base ownership checks succeed.
- [ ] Load persisted history and pass it to `AgentRequest`.
- [ ] Keep the current message creation endpoint as the compatibility path.
- [ ] Add a streaming message endpoint that emits serialized Agent events as SSE and persists the final assistant message once.
- [ ] Handle client disconnect by setting the runtime cancellation event.
- [ ] Add frontend stream consumption while preserving the existing preview adapter behavior.
- [ ] Verify the existing synchronous endpoint, SSE content type and event ordering, TypeScript checks, and production frontend build.

### Task 6: Final verification

**Files:**
- Review all modified files only; do not clean unrelated user changes.

- [ ] Run `python -m pytest tests/test_agent_module_boundary.py tests/test_chat_session_persistence.py -q`.
- [ ] Run the relevant existing backend test suite for chat, retrieval, memory, profile, and growth behavior.
- [ ] Run `python -m ruff check app/mneme/agent app/mneme/domains/chat`.
- [ ] Run the frontend production build.
- [ ] Inspect `git diff --check`, `git diff --stat`, and the full scoped diff.
- [ ] Report any verification that could not be run and why.
