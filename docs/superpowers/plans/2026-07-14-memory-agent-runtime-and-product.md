# Memory Agent Runtime and Product Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve all five explicit answer modes from the independent Memory Agent, expose governed memory through Mneme, and deliver the chat and Memory Center user experience with observable, reversible cutover.

**Architecture:** A bounded Validate–Plan–Retrieve–Answer runtime maps user-selected modes to fixed tool permissions and persists every run. Mneme remains the only browser-facing API, proxies authorized memory operations, and switches between the unchanged legacy runtime and Agent client through a deployment flag until final cleanup.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, PostgreSQL/pgvector, HTTPX, Vue 3, TypeScript, Vite

## Global Constraints

- The selected answer mode is authoritative; do not infer or silently replace it.
- Permit at most one retrieval expansion; no open-ended tool loop.
- Agent failure is explicit and retryable; do not fall back to ordinary chat or legacy RAG inside one request.
- Mneme performs authorization before every Agent call; the Agent never expands supplied scope.
- Do not create or modify test files in this plan.

---

### Task 1: Persist answer runs and implement bounded orchestration

**Files:**
- Create: `services/memory_agent/models/answer_run.py`
- Create: `services/memory_agent/repositories/runs.py`
- Create: `services/memory_agent/runtime/contracts.py`
- Create: `services/memory_agent/runtime/plans.py`
- Create: `services/memory_agent/runtime/orchestrator.py`
- Create: `services/memory_agent/runtime/ports.py`
- Create: `services/memory_agent/alembic/versions/20260714_04_add_answer_runs.py`

**Interfaces:**
- Produces: `MemoryAgent.run(request: AnswerRequest) -> AnswerResponse` and `get_run(run_id: str) -> AnswerRunData`.

- [ ] **Step 1: Define fixed plans**

```python
MODE_PLANS = {
    "kb_qa": RetrievalPlan(document=True, memory=True, profile=False, relations=False, max_expansions=1),
    "memory_query": RetrievalPlan(document=False, memory=True, profile=False, relations=False, max_expansions=1),
    "profile_query": RetrievalPlan(document=False, memory=True, profile=True, relations=False, max_expansions=0),
    "analysis_query": RetrievalPlan(document=True, memory=True, profile=True, relations=True, max_expansions=1),
    "general_chat": RetrievalPlan(document=False, memory=False, profile=False, relations=False, max_expansions=0),
}
```

- [ ] **Step 2: Define ports without infrastructure imports**

```python
class EvidenceRetriever(Protocol):
    async def retrieve(self, request: RetrievalRequest) -> list[RetrievedEvidence]: ...

class AnswerGenerator(Protocol):
    async def generate(self, request: GenerationRequest) -> GeneratedAnswer: ...

class CitationValidator(Protocol):
    def validate(self, answer: GeneratedAnswer, evidence: list[RetrievedEvidence]) -> CitationResult: ...
```

- [ ] **Step 3: Persist every phase**

Create the run before retrieval; store mode, scope IDs, status, phase durations, source IDs, confidence, uncertainty, token counts, cost, error code, and timestamps. Never persist the full private prompt in `answer_runs`.

- [ ] **Step 4: Bound execution**

Validate, retrieve once, optionally expand once only when evidence is insufficient, generate, validate citations, and complete the run. A phase timeout records a stable error code and marks the run failed.

- [ ] **Step 5: Inspect migration and commit**

Run: `python -m alembic -c services/memory_agent/alembic.ini heads`

Expected: one head at `20260714_04`.

```powershell
git add services/memory_agent
git commit -m "feat: add bounded memory agent runtime"
```

### Task 2: Implement memory, profile, model, and citation adapters

**Files:**
- Create: `services/memory_agent/retrieval/memories.py`
- Create: `services/memory_agent/retrieval/profile.py`
- Create: `services/memory_agent/retrieval/relations.py`
- Create: `services/memory_agent/runtime/retriever.py`
- Create: `services/memory_agent/providers/llm.py`
- Create: `services/memory_agent/runtime/prompts.py`
- Create: `services/memory_agent/runtime/citations.py`
- Modify: `services/memory_agent/config.py`

**Interfaces:**
- Consumes: runtime ports from Task 1 and document retrieval from the previous plan.
- Produces: concrete `ScopedEvidenceRetriever`, `ConfiguredModelGateway`, and `EvidenceCitationValidator`.

- [ ] **Step 1: Scope all private retrieval**

Memory, profile, relation, and document queries must include owner and knowledge-base filters in SQL. `general_chat` must not instantiate or call any private retriever.

- [ ] **Step 2: Enforce current-versus-historical memory**

Default retrieval includes only active revisions valid at request time. Historical revisions are eligible only when the request explicitly sets `temporal_scope="history"`; the first version of the HTTP API keeps this internal and uses current scope.

- [ ] **Step 3: Port current prompts and provider behavior**

Move prompt construction and model-provider configuration into the Agent. Do not import `app.mneme.clients.llm_client` or `app.mneme.utils.prompt_builder`; copy only behavior required by current five modes and adapt it to Agent contracts.

When Mneme supplies `ModelInvocationConfig`, use it only for the current synchronous model call. Reveal the `SecretStr` at the provider adapter boundary, never persist the API key in `answer_runs`, never enqueue it in Celery, and never include it in logs or exceptions. When it is absent, use the Agent's service-level default provider configuration.

- [ ] **Step 4: Validate citations against evidence IDs**

Reject citations whose evidence ID was not in the retrieved set, strip unauthorized metadata, lower confidence when citations are missing, and set `insufficient_evidence=True` when no supported private answer can be produced.

- [ ] **Step 5: Commit**

```powershell
git add services/memory_agent
git commit -m "feat: implement memory agent answer pipelines"
```

### Task 3: Expose answer, run, and memory APIs

**Files:**
- Create: `services/memory_agent/api/answers.py`
- Create: `services/memory_agent/api/runs.py`
- Create: `services/memory_agent/api/memories.py`
- Create: `services/memory_agent/services/memory_commands.py`
- Modify: `services/memory_agent/app.py`

**Interfaces:**
- Produces: `POST /v1/answers`, `GET /v1/runs/{run_id}`, `GET /v1/memories`, `GET /v1/memory-candidates`, `PATCH /v1/memories/{id}`, `DELETE /v1/memories/{id}`, and `POST /v1/memories/purge`.

- [ ] **Step 1: Authenticate all Mneme calls**

Use service tokens with distinct scopes `answers:write`, `runs:read`, `memories:read`, and `memories:write`. Read owner and knowledge-base scope from the validated request body and token claims; reject disagreement.

- [ ] **Step 2: Return stable answer errors**

Map validation/scope failures to 4xx. Map provider timeout, provider unavailable, capacity, and internal errors to stable JSON codes such as `AGENT_MODEL_TIMEOUT`, `AGENT_UNAVAILABLE`, and `AGENT_INTERNAL_ERROR`. No-evidence remains HTTP 200 with `insufficient_evidence=true`.

- [ ] **Step 3: Implement memory commands**

Candidate confirmation, rejection, memory revision, invalidation, and hard deletion each require an actor ID and reason. Return the updated canonical DTO; never expose raw prompts or internal sensitivity signals.

Implement `purge` with exactly one of `source_id`, `knowledge_base_id`, or `owner_id` plus an explicit confirmation token. It reuses hard-deletion semantics, reports deleted evidence/candidate/memory counts, and never retains purged values in revisions.

- [ ] **Step 4: Commit**

```powershell
git add services/memory_agent
git commit -m "feat: expose memory agent APIs"
```

### Task 4: Cut Mneme answer traffic over through the client

**Files:**
- Modify: `app/mneme/clients/memory_agent_client.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/domains/chat/router.py`
- Modify: `app/mneme/domains/retrieval/router.py`
- Modify: `app/mneme/pipelines/companion_pipeline.py`
- Modify: `app/mneme/models/chat_session.py`
- Modify: `app/mneme/models/chat_message.py`
- Modify: `app/mneme/schemas/chat.py`
- Modify: `app/mneme/schemas/chat_session.py`
- Create: `alembic/versions/20260714_01_add_chat_mode_and_agent_run.py`

**Interfaces:**
- Consumes: `POST /v1/answers`.
- Produces: session `answer_mode`, message `agent_run_id`, retryable failed-message behavior, and deployment switch `MEMORY_AGENT_ENABLED`.

- [ ] **Step 1: Persist selected mode and run ID**

Add `chat_sessions.answer_mode` with default `kb_qa` and `chat_messages.agent_run_id` nullable. Session creation and mode changes persist the explicit choice.

- [ ] **Step 2: Replace the active answer call**

When `MEMORY_AGENT_ENABLED=true`, build the Agent DTO only after ownership checks, resolve the user's selected AI model configuration into the ephemeral `ModelInvocationConfig`, save the user message, call `create_answer()`, then save the assistant message and run ID. On failure, keep the user message and return a retryable error containing its ID.

- [ ] **Step 3: Preserve an explicit rollback switch**

When the deployment flag is false, call the unchanged legacy path. Do not catch an Agent failure and invoke legacy code in the same request.

- [ ] **Step 4: Route every online consumer**

Chat sessions, stateless chat query, and Companion must all use the same client when enabled. No other online consumer may call the Agent orchestrator directly.

- [ ] **Step 5: Inspect migration and commit**

Run: `python -m alembic heads`

Expected: one Mneme head at the new revision.

```powershell
git add app/mneme alembic/versions/20260714_01_add_chat_mode_and_agent_run.py
git commit -m "feat: route answers through memory agent"
```

### Task 5: Proxy governed memory through authorized Mneme endpoints

**Files:**
- Create: `app/mneme/domains/memory_agent/router.py`
- Create: `app/mneme/domains/memory_agent/service.py`
- Create: `app/mneme/domains/memory_agent/__init__.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/clients/memory_agent_client.py`
- Modify: `app/mneme/schemas/memory_agent.py`

**Interfaces:**
- Produces browser-facing `/api/v1/memory-agent/memories`, `/candidates`, `/settings`, `/purge`, and command endpoints.

- [ ] **Step 1: Check ownership before proxying**

Resolve the current user and knowledge base in Mneme for every request. Never accept an arbitrary owner ID from the browser.

- [ ] **Step 2: Add paginated reads**

Expose status/type/source filters and cursor pagination. Map Agent DTOs into Mneme response envelopes without leaking service-token details.

- [ ] **Step 3: Add explicit commands**

Proxy confirm, reject, revise, invalidate, hard-delete, and auto-conversation-memory setting updates. Every destructive action requires a confirmation token generated by Mneme and expires after five minutes.

Expose purge scopes only after Mneme resolves the requested source or knowledge base as owned by the current user. Account-wide purge derives `owner_id` exclusively from the authenticated user.

- [ ] **Step 4: Commit**

```powershell
git add app/mneme/domains/memory_agent app/mneme/bootstrap/router_registry.py app/mneme/clients/memory_agent_client.py app/mneme/schemas/memory_agent.py
git commit -m "feat: expose governed memory controls"
```

### Task 6: Add chat regeneration and Memory Center UI

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/views/MemoryCenterView.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/memory/MemoryList.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/memory/CandidateInbox.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/memory/MemoryDetail.vue`
- Create: `app/mneme_frontend_v0.2.1/src/composables/useMemoryCenter.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/views/AiLabView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`

**Interfaces:**
- Consumes: Mneme proxy APIs from Task 5.
- Produces: Memory Center navigation, candidate actions, memory history/evidence, session mode persistence, and regenerate-with-mode.

- [ ] **Step 1: Add exact frontend DTOs and API methods**

Define `CanonicalMemory`, `MemoryCandidate`, `MemoryRevision`, `MemoryEvidence`, and paginated response types. Add list, detail, confirm, reject, revise, invalidate, delete, and settings methods to both real and preview APIs.

- [ ] **Step 2: Build Memory Center states**

Provide loading, empty, error, list, detail, and destructive-confirmation states. Default to active canonical memories; show pending candidate count in navigation.

- [ ] **Step 3: Expose explainability and control**

Show memory type, current value, validity, confidence, source label/time, revision history, and evidence excerpt. Support confirm/reject/edit/invalidate/hard-delete and the automatic-conversation-memory toggle.

Add “clear by source”, “clear this knowledge base”, and “clear all my memory” actions with progressively stronger confirmation copy; the final API payload must not contain a browser-supplied owner ID.

- [ ] **Step 4: Complete chat ergonomics**

Restore each session's mode, display answer source types and memory timestamps, show `agent_run_id`, retain failed user messages, and add “regenerate” with an explicit mode selector.

- [ ] **Step 5: Run non-test frontend checks**

Run: `npm run lint`

Expected: exit code 0.

Run: `npm run build`

Expected: Vite production build succeeds.

- [ ] **Step 6: Commit**

```powershell
git add app/mneme_frontend_v0.2.1/src
git commit -m "feat: add memory center and answer regeneration"
```

### Task 7: Add observability, rollout, and rollback operations

**Files:**
- Create: `services/memory_agent/observability/metrics.py`
- Create: `services/memory_agent/observability/context.py`
- Modify: `services/memory_agent/api/health.py`
- Modify: `services/memory_agent/runtime/orchestrator.py`
- Modify: `docker-compose.yml`
- Modify: `deploy/env/backend.production.example`
- Modify: `deploy/DEPLOY.md`
- Modify: `README.md`

**Interfaces:**
- Produces correlated request/run/event logs, metrics, worker readiness reporting, and documented cutover procedure.

- [ ] **Step 1: Correlate without logging content**

Bind `request_id`, `run_id`, and `event_id` to structured logs. Explicitly exclude questions, prompts, document chunks, conversation excerpts, and memory values.

- [ ] **Step 2: Record operational metrics**

Record answer latency by mode/phase, evidence insufficiency, token/cost/error counts, Outbox age, dead letters, inbox backlog, projection lag, and memory governance action counts.

- [ ] **Step 3: Separate readiness signals**

API readiness reports database/model configuration. Add a separate worker/queue diagnostic endpoint or command; do not conflate it with HTTP liveness.

- [ ] **Step 4: Document rollout and rollback**

Document: deploy Agent disabled, migrate, backfill, compare counts/hashes/samples, enable flag, monitor, disable flag and pause Agent consumption on rollback. Do not document automatic runtime fallback.

- [ ] **Step 5: Run plan-level source verification**

Run: `python -m compileall -q services/memory_agent app/mneme`

Expected: exit code 0.

Run: `python -m ruff check services/memory_agent app/mneme`

Expected: no lint errors.

Run: `docker compose config --quiet`

Expected: exit code 0.

- [ ] **Step 6: Commit**

```powershell
git add services/memory_agent docker-compose.yml deploy README.md
git commit -m "feat: operationalize memory agent cutover"
```
