# Memory Agent Concentrated Verification and Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the complete automated verification and answer-quality baseline after business implementation, prove the new service under failure and deletion conditions, then remove the legacy in-process RAG and memory query implementation.

**Architecture:** Contract, unit, integration, browser, migration, and evaluation checks are added together in this final phase, honoring the project rule that test files are untouched until business code is complete. Legacy removal happens only after the pre-removal suite passes and is followed by the same relevant checks.

**Tech Stack:** pytest, pytest-asyncio, FastAPI TestClient/HTTPX ASGI transport, PostgreSQL 17 with pgvector, Playwright, Vue/Vite, Docker Compose, Ruff, Alembic

## Global Constraints

- This is the only plan allowed to create or modify test files for the initiative.
- Use deterministic fake embedding and model providers in automated tests; no paid or network model calls.
- Test both databases independently and assert that neither service imports or queries the other's persistence modules.
- Do not delete legacy code until the pre-removal acceptance suite passes.
- Do not drop legacy database tables in this release; remove runtime code first and defer destructive schema contraction.

---

### Task 1: Add foundation, contract, and service-boundary tests

**Files:**
- Create: `tests/memory_agent/test_service_foundation.py`
- Create: `tests/memory_agent/test_event_contract.py`
- Create: `tests/memory_agent/test_service_auth.py`
- Create: `tests/memory_agent/test_inbox_idempotency.py`
- Create: `tests/test_memory_agent_boundary.py`
- Modify: `tests/test_docker_compose_contract.py`
- Modify: `tests/test_dependency_configuration.py`

**Interfaces:**
- Consumes: foundation contracts and Compose services from Plan 1.
- Produces: regression gates for isolated settings, auth, inbox, migrations, and imports.

- [ ] **Step 1: Test service import isolation**

Walk Agent Python AST imports and fail on `app.mneme.models`, `app.mneme.crud`, `app.mneme.conf.database`, or `app.mneme.tasks`. Walk Mneme imports and fail on `services.memory_agent.models`, repositories, database, or tasks.

- [ ] **Step 2: Test service-token claims**

Cover valid scope plus missing, expired, wrong issuer, wrong audience, and wrong-scope tokens. Assert user JWTs cannot access internal endpoints.

- [ ] **Step 3: Test inbox idempotency**

Post the same `event_id` concurrently and assert one row, one scheduled task, one 202 creator response, and successful duplicate responses.

- [ ] **Step 4: Test deployment contracts**

Assert independent database names, Redis DBs/queues, migration services, health checks, and `MEMORY_AGENT_ENABLED=false` default.

- [ ] **Step 5: Run focused tests and commit**

Run: `python -m pytest tests/memory_agent/test_service_foundation.py tests/memory_agent/test_event_contract.py tests/memory_agent/test_service_auth.py tests/memory_agent/test_inbox_idempotency.py tests/test_memory_agent_boundary.py tests/test_docker_compose_contract.py tests/test_dependency_configuration.py -q --basetemp .tmp/pytest-agent-foundation`

Expected: all selected tests pass.

```powershell
git add tests
git commit -m "test: verify memory agent service boundary"
```

### Task 2: Add projection, retrieval, memory, and deletion tests

**Files:**
- Create: `tests/memory_agent/test_projection_batches.py`
- Create: `tests/memory_agent/test_projection_atomic_swap.py`
- Create: `tests/memory_agent/test_scoped_retrieval.py`
- Create: `tests/memory_agent/test_memory_policy.py`
- Create: `tests/memory_agent/test_memory_reconciliation.py`
- Create: `tests/memory_agent/test_memory_deletion.py`
- Create: `tests/memory_agent/test_backfill.py`

**Interfaces:**
- Consumes: projection and memory APIs from Plan 2.
- Produces: gates for hash validation, tenant isolation, governance, history, and hard deletion.

- [ ] **Step 1: Cover projection completeness and atomicity**

Test out-of-order batches, duplicates, missing batch, wrong aggregate hash, retry after failure, concurrent finalization, and replacement of an existing active version. Assert the old version remains searchable until the new one is complete.

- [ ] **Step 2: Cover retrieval isolation and ranking**

Seed two owners and two knowledge bases with overlapping text. Assert no cross-scope result, active-version filtering, deterministic reciprocal-rank fusion, exact `top_k`, and current-only memory default.

- [ ] **Step 3: Cover deterministic memory policy**

Test explicit low-risk promotion, secret rejection, sensitive pending status, confidence boundary `0.85`, duplicate reinforcement, conflict pending, confirmed temporal replacement, and historical retrieval.

- [ ] **Step 4: Cover hard deletion**

Delete a source with sole evidence and with shared evidence. Assert evidence content disappears, unsupported memory disappears, supported memory remains with recalculated confidence, and audit rows retain no deleted content.

Cover purge by source, knowledge base, and authenticated owner; assert cross-owner purge is impossible and purged values do not remain in revision rows.

- [ ] **Step 5: Cover backfill resume**

Assert dry-run writes nothing, checkpoints resume without duplicate projection versions, filters limit scope, and hash mismatch is reported rather than silently skipped.

- [ ] **Step 6: Run focused tests and commit**

Run: `python -m pytest tests/memory_agent/test_projection_batches.py tests/memory_agent/test_projection_atomic_swap.py tests/memory_agent/test_scoped_retrieval.py tests/memory_agent/test_memory_policy.py tests/memory_agent/test_memory_reconciliation.py tests/memory_agent/test_memory_deletion.py tests/memory_agent/test_backfill.py -q --basetemp .tmp/pytest-agent-memory`

Expected: all selected tests pass.

```powershell
git add tests/memory_agent
git commit -m "test: verify agent projection and memory lifecycle"
```

### Task 3: Add runtime, API, Outbox, and cutover tests

**Files:**
- Create: `tests/memory_agent/test_runtime_modes.py`
- Create: `tests/memory_agent/test_runtime_failures.py`
- Create: `tests/memory_agent/test_citation_validation.py`
- Create: `tests/memory_agent/test_memory_api.py`
- Create: `tests/test_memory_agent_client.py`
- Create: `tests/test_memory_agent_outbox_delivery.py`
- Create: `tests/test_memory_agent_chat_cutover.py`
- Modify: `tests/test_chat_session_persistence.py`

**Interfaces:**
- Consumes: runtime/API/cutover from Plan 3.
- Produces: five-mode capability, failure, authorization, retry, and rollback gates.

- [ ] **Step 1: Test exact mode capabilities**

Parameterize the five modes and spy on document, memory, profile, and relation ports. Assert each mode invokes exactly the sources allowed by `MODE_PLANS`; `general_chat` invokes none.

- [ ] **Step 2: Test bounded execution and citations**

Assert at most one retrieval expansion, per-phase timeout, invalid citation removal, confidence downgrade, no-evidence HTTP 200, and run persistence on success and failure.

- [ ] **Step 3: Test HTTP error semantics**

Cover unauthorized scope, provider timeout, Agent 503, malformed response, non-retried 4xx, retried 503, and stable Mneme error mapping. Assert failed user messages remain retryable and no assistant message is fabricated.

Also assert conversation extraction is skipped while automatic memory is disabled, settings events are idempotent, and explicit memory requests remain eligible while automatic conversation memory is off.

- [ ] **Step 4: Test the rollback flag**

With the flag false, assert only legacy runtime is called. With it true, assert only the Agent client is called. When the Agent client fails, assert legacy runtime is not called.

- [ ] **Step 5: Test Outbox delivery lifecycle**

Cover HTTP success, duplicate receipt, retryable status, permanent 4xx, max-attempt dead letter, pending recovery, and absence of source content in logs/errors.

- [ ] **Step 6: Run focused tests and commit**

Run: `python -m pytest tests/memory_agent/test_runtime_modes.py tests/memory_agent/test_runtime_failures.py tests/memory_agent/test_citation_validation.py tests/memory_agent/test_memory_api.py tests/test_memory_agent_client.py tests/test_memory_agent_outbox_delivery.py tests/test_memory_agent_chat_cutover.py tests/test_chat_session_persistence.py -q --basetemp .tmp/pytest-agent-runtime`

Expected: all selected tests pass.

```powershell
git add tests
git commit -m "test: verify memory agent runtime and cutover"
```

### Task 4: Add browser tests for chat and Memory Center

**Files:**
- Create: `app/mneme_frontend_v0.2.1/tests/memory-center.spec.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/answer-regeneration.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`

**Interfaces:**
- Consumes: frontend behavior from Plan 3.
- Produces: desktop/mobile interaction and source-contract gates.

- [ ] **Step 1: Cover Memory Center workflows**

Use deterministic route fixtures to cover loading, empty, failure, pagination, filters, candidate confirm/reject, revision display, evidence display, edit, invalidate, hard-delete confirmation, and automatic-memory toggle.

- [ ] **Step 2: Cover chat mode persistence and retry**

Assert session mode restoration, mode-specific request payloads, regenerate-with-mode, run ID/source display, failed-message retention, and explicit retry.

- [ ] **Step 3: Cover responsive layouts**

Run the core Memory Center and regeneration flows at desktop and mobile viewports; assert controls remain reachable without relying on hover.

- [ ] **Step 4: Run frontend checks and commit**

Run: `npm run lint`

Run: `npm run build`

Run: `npx playwright test tests/memory-center.spec.ts tests/answer-regeneration.spec.ts`

Expected: lint/build succeed and all selected Playwright tests pass.

```powershell
git add app/mneme_frontend_v0.2.1/tests
git commit -m "test: verify memory center and answer modes"
```

### Task 5: Add the fixed answer-quality evaluation baseline

**Files:**
- Create: `evals/memory_agent/cases.jsonl`
- Create: `evals/memory_agent/README.md`
- Create: `services/memory_agent/eval/contracts.py`
- Create: `services/memory_agent/eval/runner.py`
- Create: `services/memory_agent/eval/metrics.py`
- Create: `tests/memory_agent/test_eval_runner.py`

**Interfaces:**
- Produces: `python -m services.memory_agent.eval.runner --dataset evals/memory_agent/cases.jsonl --output .tmp/memory-agent-eval.json`.

- [ ] **Step 1: Define versioned cases**

Include at least five deterministic cases per mode plus cases for no evidence, conflicting memory, historical versus current memory, unauthorized cross-scope evidence, and invalid citations. Store expected source IDs/types and required/forbidden claims; do not store real user data.

- [ ] **Step 2: Calculate deterministic metrics**

Report pipeline accuracy, source-scope violations, Recall@K, MRR, citation precision/coverage, unsupported-claim flags, and no-evidence behavior. Separate deterministic retrieval/citation metrics from optional model-judged prose metrics.

- [ ] **Step 3: Set initial gates**

Require pipeline accuracy 1.0, scope violations 0, citation precision 1.0, no-evidence behavior 1.0, and record retrieval metrics as a baseline rather than choosing an arbitrary pass threshold.

- [ ] **Step 4: Run evaluation tests and baseline**

Run: `python -m pytest tests/memory_agent/test_eval_runner.py -q --basetemp .tmp/pytest-agent-eval`

Run: `python -m services.memory_agent.eval.runner --dataset evals/memory_agent/cases.jsonl --output .tmp/memory-agent-eval.json`

Expected: deterministic gates pass and the JSON report contains per-mode metrics.

- [ ] **Step 5: Commit**

```powershell
git add evals services/memory_agent/eval tests/memory_agent/test_eval_runner.py
git commit -m "test: add memory agent evaluation baseline"
```

### Task 6: Run the pre-removal acceptance gate

**Files:**
- No source changes expected.

- [ ] **Step 1: Run backend lint and migrations**

Run: `python -m ruff check app/mneme services/memory_agent tests`

Run: `python -m alembic heads`

Run: `python -m alembic -c services/memory_agent/alembic.ini heads`

Expected: no lint errors and exactly one head per database.

- [ ] **Step 2: Run the complete backend suite**

Run: `python -m pytest tests -q --basetemp .tmp/pytest-all`

Expected: all tests pass. Stop and fix failures before legacy removal.

- [ ] **Step 3: Run frontend and Compose gates**

Run from frontend: `npm run lint; npm run build; npx playwright test`

Run from repository root: `docker compose config --quiet`

Expected: all commands pass.

- [ ] **Step 4: Run clean-stack smoke verification**

Start both databases, migrations, APIs, and workers in a disposable Compose project. Verify readiness, submit a projection, ask each mode, inspect a memory, delete its source, verify removal, and confirm no cross-scope citation. Record command output in the PR, not in committed source files.

### Task 7: Remove the legacy in-process answer and memory-query runtime

**Files:**
- Delete after reference audit: `app/mneme/agent/`
- Delete after reference audit: `app/mneme/domains/retrieval/query_service.py`
- Delete after reference audit: `app/mneme/domains/retrieval/query_router.py`
- Delete after reference audit: `app/mneme/domains/retrieval/context_service.py`
- Delete after reference audit: `app/mneme/domains/retrieval/vector_recall.py`
- Delete after reference audit: `app/mneme/domains/retrieval/keyword_recall.py`
- Delete after reference audit: `app/mneme/domains/retrieval/memory_recall.py`
- Delete after reference audit: `app/mneme/domains/retrieval/fusion.py`
- Delete after reference audit: `app/mneme/domains/retrieval/citation_validation.py`
- Delete after reference audit: `app/mneme/domains/retrieval/debug.py`
- Delete after reference audit: `app/mneme/utils/prompt_builder.py`
- Modify: `app/mneme/domains/retrieval/router.py`
- Modify: `app/mneme/domains/memory/router.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/conf/config.py`
- Modify: relevant tests that asserted the temporary in-process boundary

**Interfaces:**
- Consumes: proven Agent client and proxy routes.
- Produces: Mneme with no answer-time retrieval, memory-query, prompt-building, or answer-orchestration implementation.

- [ ] **Step 1: Audit every legacy reference before deleting**

Run: `rg -n "app\.mneme\.agent|generate_rag_answer|build_query_context|vector_recall|memory_recall|get_evidence_rag_prompt" app tests`

Classify every match as replace, delete, or retained non-answer use. Do not delete a shared utility until all remaining imports are understood.

- [ ] **Step 2: Remove only proven legacy files**

Delete the paths above only when the reference audit shows they are answer-time-only. Keep document parsing, chunk persistence during the migration window, Agent proxy routes, and legacy database tables.

- [ ] **Step 3: Remove the rollback flag and old branch**

Make the Agent client the sole online answer path. Remove `MEMORY_AGENT_ENABLED` and legacy-runtime conditional code; keep ordinary service availability settings and explicit retry behavior.

- [ ] **Step 4: Update boundary tests and documentation**

Change temporary tests that expected `app.mneme.agent` to assert its absence and assert all consumers use `MemoryAgentClient`.

- [ ] **Step 5: Commit**

```powershell
git add -A app/mneme tests README.md deploy
git commit -m "refactor: remove legacy in process rag runtime"
```

### Task 8: Run final verification and prepare release evidence

**Files:**
- Modify: `README.md`
- Modify: `deploy/DEPLOY.md`
- Modify: `docs/agent-module.md`

- [ ] **Step 1: Rerun all automated gates**

Run Ruff, both Alembic head checks, full backend pytest, frontend lint/build/Playwright, evaluation runner, and `docker compose config --quiet` using the commands from Tasks 4–6.

Expected: every gate passes after legacy removal.

- [ ] **Step 2: Rerun the clean-stack scenario**

Verify fresh migration, backfill, all five modes, candidate confirmation, memory revision, source deletion, Outbox retry, Agent restart, and rollback-by-previous-image instructions.

- [ ] **Step 3: Finalize docs**

Document final ownership, local development, deployment order, backfill, monitoring, privacy behavior, failure semantics, and the fact that runtime rollback now requires deploying the previous application image.

- [ ] **Step 4: Commit release documentation**

```powershell
git add README.md deploy/DEPLOY.md docs/agent-module.md
git commit -m "docs: finalize memory agent operations"
```

- [ ] **Step 5: Record PR evidence**

Include exact command results, migration heads, evaluation report summary, clean-stack scenario outcome, known limitations, and rollback command in the PR description. Do not claim completion if any required gate was skipped.
