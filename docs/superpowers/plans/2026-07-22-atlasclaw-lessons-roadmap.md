# Mneme AtlasClaw Lessons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Selectively absorb AtlasClaw's strongest runtime-boundary and context-governance ideas while preserving Mneme's simpler product scope, durable PostgreSQL/Redis architecture, and existing public contracts.

**Architecture:** Deliver six independently releasable phases: living architecture documentation, context governance, durable runtime subscribers, grounding enforcement, a user-owned assistant manifest, and a bounded live-model canary. Reuse Mneme's existing `AgentEvent`, Outbox, approval, model fallback, and session lease mechanisms; do not introduce a second event bus, file-backed runtime state, arbitrary script execution, or a new model call on every request.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery, Vue 3, pytest, GitHub Actions, and the existing Memoria evaluation/runtime packages.

---

## Scope and success criteria

This roadmap is planning-only. Implementation must be split by phase and each phase must be independently testable, deployable, and reversible.

The roadmap is complete when:

- Mneme can explain which context sources were included, truncated, preserved, or dropped.
- Compaction cannot silently discard critical user constraints, unresolved approvals, cited evidence, or material tool failures.
- Durable runtime events can be consumed by permission-scoped, idempotent internal subscribers without modifying the core orchestrator.
- Answers that require private or tool-derived grounding cannot complete without matching evidence.
- User-authored assistant directives are separated from inferred memory and session context.
- A scheduled, cost-bounded live-model canary exercises the real model gateway without becoming a pull-request dependency.
- Canonical architecture and runtime-contract documents describe the code that actually runs.

## Non-goals and explicit anti-copy boundaries

- Do not copy AtlasClaw's large Runner/Mixin hierarchy.
- Do not replace Mneme's Redis FIFO and lease-based session execution with an in-process queue.
- Do not replace durable approvals with command-pattern auto-approval.
- Do not store hook state in per-user JSONL files.
- Do not enable arbitrary local script hooks in this roadmap.
- Do not add a hidden LLM classification request before every normal answer.
- Do not build a multi-key token pool until production usage demonstrates per-provider credential contention.
- Do not expose filesystem or shell tools until a separate sandbox threat model is approved.

## Delivery order

| Phase | Deliverable | Dependency | Release gate |
|---|---|---|---|
| 1 | Living architecture baseline | None | Documentation contracts pass |
| 2 | Context governance and compaction safeguards | Phase 1 vocabulary | Existing chat behavior plus governance tests pass |
| 3 | Durable internal runtime subscribers | Existing Outbox and runtime events | Idempotency, timeout and user-scope checks pass |
| 4 | Grounding requirement and evidence enforcement | Phase 2 context report | Eval gates and citation tests pass |
| 5 | User-owned assistant manifest | Phase 2 precedence model | API, prompt-budget and ownership checks pass |
| 6 | Scheduled live-model canary | Phases 2 and 4 telemetry | Manual run succeeds within cost/latency limits |

---

### Task 1: Establish a living architecture baseline

**Files:**
- Create: `docs/architecture.md`
- Create: `docs/runtime-contracts.md`
- Create: `docs/current-state.md`
- Modify: `README.md`
- Modify: `tests/test_dependency_configuration.py`

- [ ] **Step 1: Write the failing documentation contract**

Add one contract test that requires the three canonical documents, requires `README.md` to link them, and validates that every backticked `app/...` or `tests/...` path in those documents exists.

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/test_dependency_configuration.py`.

Expected: failure because the canonical documents do not exist.

- [ ] **Step 3: Write `docs/architecture.md`**

Document only current facts:

- FastAPI application boundaries.
- Main PostgreSQL, Memoria PostgreSQL, Redis, Milvus and Neo4j ownership.
- Synchronous request path versus Celery/Outbox paths.
- Chat-to-Memoria request flow.
- Durable agent-run FIFO and lease lifecycle.
- Runtime event persistence and streaming.
- Model primary/fallback health behavior.
- Deployment topology and health/metrics endpoints.

Include one compact Mermaid flow from `POST /kb/chat/runs` through queue claim, Memoria generation, citation validation, durable event append and channel delivery.

- [ ] **Step 4: Write `docs/runtime-contracts.md`**

Define the stable invariants for:

- `AgentEvent` names and delivery sequencing.
- Outbox idempotency and dead-letter behavior.
- tool statuses and approval-only write actions.
- context precedence and evidence provenance.
- abort, steer and follow-up run control.
- error-code privacy and retry classification.

- [ ] **Step 5: Write `docs/current-state.md`**

Use exactly these headings: `Objective`, `Completed`, `In Progress`, `Risks and Decisions`, `Next Step`, and `Last Verified`. Keep historical implementation detail in the existing plans and link to it instead of copying it.

- [ ] **Step 6: Link and verify**

Link all three files from `README.md`. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_dependency_configuration.py
.\.venv\Scripts\python.exe -m ruff check app tests
git diff --check
```

Expected: all checks pass and every canonical path reference resolves.

- [ ] **Step 7: Commit phase 1**

```powershell
git add README.md docs/architecture.md docs/runtime-contracts.md docs/current-state.md tests/test_dependency_configuration.py
git commit -m "docs: establish canonical architecture baseline"
```

---

### Task 2: Add context governance and compaction safeguards

**Files:**
- Create: `app/mneme/memoria/context_governance.py`
- Create: `tests/test_context_governance.py`
- Modify: `app/mneme/domains/chat/context.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/memoria/contracts.py`
- Modify: `app/mneme/memoria/events.py`
- Modify: `docs/runtime-contracts.md`

- [ ] **Step 1: Define the failing governance cases**

Write focused tests for these invariants:

- A user-authored directive is preserved before ordinary history.
- An unresolved approval is preserved before an old assistant answer.
- A cited source identifier survives compaction while unrelated tool payload is bounded.
- A failed tool result is retained as a short failure record without retaining secrets.
- The report accounts for every input source as included, truncated, preserved, or dropped.
- Governance failure returns the original safe conversation context rather than an empty context.

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/test_context_governance.py`.

Expected: collection fails because `app.mneme.memoria.context_governance` does not exist.

- [ ] **Step 3: Add focused contracts**

Implement these Pydantic contracts in `context_governance.py`:

```python
class ContextSourceDecision(BaseModel):
    source_id: str
    source_type: Literal[
        "system_policy", "user_directive", "approval", "tool_failure",
        "citation", "history_summary", "history_message", "inferred_memory",
    ]
    outcome: Literal["included", "preserved", "truncated", "dropped"]
    input_chars: int = Field(ge=0)
    output_chars: int = Field(ge=0)
    reason: str


class ContextAssemblyReport(BaseModel):
    schema_version: str = "1"
    token_budget: int = Field(ge=0)
    estimated_tokens_before: int = Field(ge=0)
    estimated_tokens_after: int = Field(ge=0)
    decisions: list[ContextSourceDecision] = Field(default_factory=list)
```

Keep selection deterministic. The module may classify and bound already-available context; it must not call an LLM or database.

- [ ] **Step 4: Preserve critical context before ordinary history**

Extend `prepare_conversation_context(...)` with optional, already-resolved critical items. Apply this precedence:

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

Use the existing token estimator. Bound every individual preserved item and never copy API keys, bearer tokens, confirmation tokens, or raw tool arguments into the summary.

- [ ] **Step 5: Propagate the report without breaking the public API**

Keep `AgentRequest.history_compaction` backward-compatible and store `ContextAssemblyReport.model_dump(mode="json")` there. Emit it as metadata on `context.compacted`; do not add a new required frontend field.

- [ ] **Step 6: Verify focused and regression behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_context_governance.py tests/test_phase5_runtime_experience.py tests/test_chat_session_persistence.py
.\.venv\Scripts\python.exe -m ruff check app tests
```

Expected: governance invariants pass and existing compaction behavior remains compatible.

- [ ] **Step 7: Commit phase 2**

```powershell
git add app/mneme/memoria/context_governance.py app/mneme/domains/chat/context.py app/mneme/domains/chat/service.py app/mneme/memoria/contracts.py app/mneme/memoria/events.py tests/test_context_governance.py docs/runtime-contracts.md
git commit -m "feat(context): add governed compaction reporting"
```

---

### Task 3: Introduce durable internal runtime subscribers

**Files:**
- Create: `app/mneme/memoria/subscribers/__init__.py`
- Create: `app/mneme/memoria/subscribers/contracts.py`
- Create: `app/mneme/memoria/subscribers/registry.py`
- Create: `app/mneme/memoria/subscribers/dispatcher.py`
- Create: `tests/test_runtime_subscribers.py`
- Modify: `app/mneme/memoria/automation/outbox.py`
- Modify: `app/mneme/memoria/automation/service.py`
- Modify: `docs/runtime-contracts.md`

- [ ] **Step 1: Write failing subscriber contract tests**

Cover:

- only explicitly subscribed event types are delivered;
- handlers receive the event's `user_id`, `run_id`, `event_type`, idempotency key and sanitized payload;
- duplicate Outbox delivery produces one logical subscriber result;
- one failing or timed-out subscriber does not skip later subscribers;
- a subscriber cannot return an unsupported action;
- subscriber actions cannot target another user.

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/test_runtime_subscribers.py`.

Expected: collection fails because the subscriber package does not exist.

- [ ] **Step 3: Define the minimal internal protocol**

Use contracts equivalent to:

```python
SubscriberActionType = Literal[
    "create_approval", "add_context_candidate", "send_notification"
]


class RuntimeSubscriberEvent(BaseModel):
    event_id: str
    event_type: str
    user_id: int
    run_id: str | None = None
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SubscriberAction(BaseModel):
    type: SubscriberActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeSubscriber(Protocol):
    name: str
    event_types: frozenset[str]
    timeout_seconds: float

    async def handle(self, event: RuntimeSubscriberEvent) -> list[SubscriberAction]: ...
```

The registry is process-local and contains code-owned handlers only. Configuration may enable or disable registered names, but may not specify executable commands or import paths.

- [ ] **Step 4: Dispatch through the existing Outbox boundary**

Extend `apply_internal_hook_event(...)` to call the subscriber dispatcher and the existing event-triggered heartbeat path. Use the Outbox idempotency key as the subscriber action idempotency prefix. Apply supported actions through existing approval, notification and governed-memory candidate services rather than writing database rows directly from handlers.

- [ ] **Step 5: Enforce isolation**

Wrap each handler with `asyncio.timeout`. Sanitize event payloads using the existing secret-detection boundary before dispatch. Record handler name, status, duration and stable error type; never persist exception text that may contain provider responses or credentials.

- [ ] **Step 6: Verify subscriber and Outbox behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_runtime_subscribers.py tests/test_agent_automation_contract.py tests/test_memory_agent_outbox_delivery.py
.\.venv\Scripts\python.exe -m ruff check app tests
```

Expected: subscriber failures are isolated, duplicate events are idempotent, and existing heartbeat hooks still run.

- [ ] **Step 7: Commit phase 3**

```powershell
git add app/mneme/memoria/subscribers app/mneme/memoria/automation/outbox.py app/mneme/memoria/automation/service.py tests/test_runtime_subscribers.py docs/runtime-contracts.md
git commit -m "feat(runtime): add durable internal event subscribers"
```

---

### Task 4: Enforce grounding requirements and tool evidence

**Files:**
- Create: `app/mneme/memoria/server/runtime/grounding.py`
- Create: `tests/memoria/test_grounding_enforcement.py`
- Modify: `app/mneme/memoria/server/runtime/contracts.py`
- Modify: `app/mneme/memoria/server/runtime/orchestrator.py`
- Modify: `app/mneme/memoria/server/runtime/prompts.py`
- Modify: `app/mneme/memoria/events.py`
- Modify: `app/mneme/memoria/server/eval/cases.jsonl`
- Modify: `docs/runtime-contracts.md`

- [ ] **Step 1: Write failing grounding tests**

Cover these decisions:

- `general_chat` permits a final answer without private evidence and forbids claims of private access.
- `kb_qa` requires document or governed-memory evidence.
- `memory_query` requires governed-memory evidence.
- `profile_query` requires governed profile/memory evidence.
- `analysis_query` requires at least one configured analysis source.
- a required source that returns no evidence produces an insufficient-evidence response;
- a required tool that was not executed cannot be reported as executed;
- tool evidence from another owner or run is rejected.

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/memoria/test_grounding_enforcement.py`.

Expected: collection fails because `runtime.grounding` does not exist.

- [ ] **Step 3: Define deterministic grounding contracts**

Implement:

```python
class GroundingRequirement(BaseModel):
    required: bool
    required_source_types: frozenset[str] = frozenset()
    required_tool_names: frozenset[str] = frozenset()
    allow_ungrounded_final: bool = False
    reason: str


class GroundingDecision(BaseModel):
    satisfied: bool
    evidence_ids: list[str] = Field(default_factory=list)
    missing_source_types: list[str] = Field(default_factory=list)
    missing_tool_names: list[str] = Field(default_factory=list)
    reason: str
```

Map existing answer modes to requirements with a static, reviewable policy. Do not add keyword routing or an extra model classifier.

- [ ] **Step 4: Enforce after retrieval and before accepting a final answer**

Evaluate source ownership and source type after retrieval. After generation, compare required tool names with completed tool traces. When unsatisfied, return the existing insufficient-evidence contract with zero fabricated citations and emit a typed grounding decision event.

- [ ] **Step 5: Strengthen the prompt without relying on it for enforcement**

Include the resolved requirement in the system prompt as a short policy statement, but keep enforcement in Python. Tool observations remain untrusted data and cannot override the requirement.

- [ ] **Step 6: Extend deterministic Eval**

Add cases covering missing required sources, a claimed-but-unexecuted lookup, wrong-owner evidence rejection, and general-chat no-private-access behavior. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/memoria/test_grounding_enforcement.py tests/memoria/test_citation_validation.py tests/memoria/test_eval_runner.py
.\.venv\Scripts\python.exe -m app.mneme.memoria.server.eval.runner --dataset app/mneme/memoria/server/eval/cases.jsonl --multi-agent-dataset app/mneme/memoria/server/eval/multi_agent_cases.jsonl --output .tmp/grounding-eval.json
```

Expected: all grounding tests and every deterministic Eval gate pass.

- [ ] **Step 7: Commit phase 4**

```powershell
git add app/mneme/memoria/server/runtime/grounding.py app/mneme/memoria/server/runtime/contracts.py app/mneme/memoria/server/runtime/orchestrator.py app/mneme/memoria/server/runtime/prompts.py app/mneme/memoria/events.py app/mneme/memoria/server/eval/cases.jsonl tests/memoria/test_grounding_enforcement.py docs/runtime-contracts.md
git commit -m "feat(runtime): enforce grounding requirements"
```

---

### Task 5: Add a user-owned assistant manifest

**Files:**
- Create: `alembic/versions/20260722_01_add_assistant_manifests.py`
- Create: `app/mneme/memoria/models/assistant_manifest.py`
- Create: `app/mneme/memoria/configuration/manifest_repository.py`
- Create: `app/mneme/memoria/configuration/manifest_service.py`
- Create: `app/mneme/memoria/schemas/assistant_manifest.py`
- Create: `app/mneme/memoria/api/manifest.py`
- Create: `tests/test_assistant_manifest.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/memoria/chat_bridge.py`
- Modify: `app/mneme/memoria/schemas/memory_agent.py`
- Modify: `app/mneme/memoria/server/contracts/answers.py`
- Modify: `app/mneme/memoria/server/runtime/prompts.py`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/views/SettingsView.vue`
- Modify: `docs/runtime-contracts.md`

- [ ] **Step 1: Write failing ownership and precedence tests**

Test that:

- every user has at most one manifest;
- a user cannot read or update another user's manifest;
- display name, tone, response preferences and explicit directives are length-bounded;
- empty fields use product defaults;
- explicit directives are included after system safety policy but before inferred memory;
- manifest text is bounded by a fixed prompt budget;
- manifest changes do not mutate canonical or inferred memories.

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/test_assistant_manifest.py`.

Expected: collection fails because the manifest model and API do not exist.

- [ ] **Step 3: Add the database model and migration**

Create one `assistant_manifests` row per `user_id` with:

- `display_name` up to 120 characters;
- `tone` up to 120 characters;
- `response_preferences` JSON object with a serialized limit of 4,000 characters;
- `directives` text up to 4,000 characters;
- `created_at` and `updated_at` timezone-aware timestamps;
- a unique foreign key to `users.id` with cascade deletion.

Use Alembic revision `20260722_01` with `down_revision = "20260719_01"`.

- [ ] **Step 4: Add scoped API and service behavior**

Expose `GET /agent/manifest` and `PUT /agent/manifest`. Derive `user_id` only from the authenticated principal. Normalize whitespace, reject control characters, and return a stable Pydantic response.

- [ ] **Step 5: Inject the manifest with explicit precedence**

Resolve the manifest in `chat_bridge.py` and pass it through the internal Memory Agent request. In `prompts.py`, render it as a bounded `assistant_preferences` section below the non-overridable system safety and evidence policy. Label inferred memory separately and never merge it into the stored manifest.

- [ ] **Step 6: Add the settings UI**

Add an `Assistant` section to `SettingsView.vue` with display name, tone, response preference and directives inputs. Save explicitly; do not autosave every keystroke. Preview mode must use the same default shape.

- [ ] **Step 7: Verify backend, migration and frontend**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_assistant_manifest.py tests/test_chat_session_persistence.py
.\.venv\Scripts\python.exe -m alembic upgrade head
npm run lint --prefix app/mneme_frontend_v0.2.1
npm run test:contracts --prefix app/mneme_frontend_v0.2.1
npm run build --prefix app/mneme_frontend_v0.2.1
```

Expected: migration reaches one head, ownership and precedence tests pass, and the frontend builds.

- [ ] **Step 8: Commit phase 5**

```powershell
git add alembic/versions/20260722_01_add_assistant_manifests.py app/mneme/memoria/models/assistant_manifest.py app/mneme/memoria/configuration/manifest_repository.py app/mneme/memoria/configuration/manifest_service.py app/mneme/memoria/schemas/assistant_manifest.py app/mneme/memoria/api/manifest.py app/mneme/bootstrap/router_registry.py app/mneme/memoria/chat_bridge.py app/mneme/memoria/schemas/memory_agent.py app/mneme/memoria/server/contracts/answers.py app/mneme/memoria/server/runtime/prompts.py app/mneme_frontend_v0.2.1/src/lib/api.ts app/mneme_frontend_v0.2.1/src/lib/previewApi.ts app/mneme_frontend_v0.2.1/src/types.ts app/mneme_frontend_v0.2.1/src/views/SettingsView.vue tests/test_assistant_manifest.py docs/runtime-contracts.md
git commit -m "feat(profile): add user-owned assistant manifest"
```

---

### Task 6: Add a bounded scheduled live-model canary

**Files:**
- Create: `app/mneme/memoria/server/eval/live_canary.py`
- Create: `tests/live/test_model_gateway_canary.py`
- Create: `.github/workflows/memoria-live-canary.yml`
- Modify: `pyproject.toml`
- Modify: `docs/operations-runbook.md`

- [ ] **Step 1: Write the opt-in canary test**

Register `live` and `llm` pytest markers. Skip unless `MNEME_LIVE_CANARY=1`. Exercise `ConfiguredModelGateway` with:

- one bounded `general_chat` response;
- one grounded response using fixed local evidence;
- one invalid primary configuration with a valid fallback configuration;
- assertions for non-empty answer, token ceilings, selected provider/model, fallback flag, and maximum elapsed time.

Do not call Feishu or mutate external systems in this first canary.

- [ ] **Step 2: Verify local skip behavior**

Run `python -m pytest -q tests/live/test_model_gateway_canary.py` without credentials.

Expected: explicit skips, not failures or network attempts.

- [ ] **Step 3: Add a cost-bounded CLI report**

Write JSON containing case name, status, selected model, fallback use, prompt tokens, completion tokens and duration. Exit non-zero when any case exceeds:

- 3 model calls total;
- 12,000 prompt tokens total;
- 2,000 completion tokens total;
- 120 seconds per case;
- the configured `MNEME_LIVE_CANARY_MAX_COST`.

Never write prompts, answers or API keys into the artifact.

- [ ] **Step 4: Add scheduled and manual GitHub Actions execution**

Create a workflow with:

- `workflow_dispatch` and one nightly schedule;
- `concurrency` preventing overlapping canaries;
- a 10-minute job timeout;
- environment-scoped API-key secrets;
- no execution on pull requests;
- report artifact upload even on failure;
- no deployment dependency.

- [ ] **Step 5: Document operation and disable procedure**

Add the exact manual trigger, secret names, expected report fields, cost ceiling and emergency disable procedure to `docs/operations-runbook.md`.

- [ ] **Step 6: Verify static behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/live/test_model_gateway_canary.py tests/test_dependency_configuration.py
.\.venv\Scripts\python.exe -m ruff check app tests
@'
from pathlib import Path
import yaml
yaml.safe_load(Path('.github/workflows/memoria-live-canary.yml').read_text(encoding='utf-8'))
print('workflow yaml: OK')
'@ | .\.venv\Scripts\python.exe -
```

Expected: live tests skip safely without secrets and the workflow parses. Execute the first real run manually before enabling the schedule.

- [ ] **Step 7: Commit phase 6**

```powershell
git add app/mneme/memoria/server/eval/live_canary.py tests/live/test_model_gateway_canary.py .github/workflows/memoria-live-canary.yml pyproject.toml docs/operations-runbook.md
git commit -m "ci(eval): add bounded live model canary"
```

---

## Deferred capability gates

The following are documented but intentionally excluded from implementation:

### Filesystem or script tools

Start a separate security design only when a product requirement needs local file or process execution. That design must require a per-user workspace, resolved-path containment, minimal environment, process timeout, output-size limit, secret stripping and explicit approval for mutation. Until then, do not add a generic work-directory guard or script runtime merely for architectural symmetry with AtlasClaw.

### Multi-credential token pooling

Start only when metrics show one provider/model needs multiple active credentials or tenant-level quotas. Reuse the current provider health registry and add credential identity without logging secrets. Required evidence before starting: observed 429 saturation, credential-level cooldown requirements, or contractual tenant isolation.

### Arbitrary external subscribers

Do not load Python import paths or shell commands from configuration. Revisit only after internal subscribers are stable and a sandbox, signing model, permission manifest and operator installation workflow have separate approval.

## Final roadmap verification

After all six phases, run:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp_atlasclaw_roadmap
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m app.mneme.memoria.server.eval.runner --dataset app/mneme/memoria/server/eval/cases.jsonl --multi-agent-dataset app/mneme/memoria/server/eval/multi_agent_cases.jsonl --output .tmp/atlasclaw-roadmap-eval.json
npm run lint --prefix app/mneme_frontend_v0.2.1
npm run test:contracts --prefix app/mneme_frontend_v0.2.1
npm run build --prefix app/mneme_frontend_v0.2.1
git diff --check
```

Expected:

- all non-live tests pass;
- live tests skip unless explicitly enabled;
- exactly one Alembic head exists;
- deterministic evaluation gates remain green;
- frontend type checks, contracts and production build pass;
- no filesystem/script execution or new default model-classifier call has been introduced.

## Rollout and rollback

- Release every task separately; do not combine all phases into one pull request.
- Keep context reporting additive and backward-compatible for one release before making any field required.
- Enable subscribers with an empty default registry, then activate one built-in subscriber at a time.
- Put grounding enforcement behind an application setting for one observation release, but emit decisions in both observe and enforce modes.
- Treat assistant manifest absence as product defaults so rollback does not require deleting rows.
- Keep the live canary independent from deployment and disable it by removing the schedule or environment approval, not by changing production code.
