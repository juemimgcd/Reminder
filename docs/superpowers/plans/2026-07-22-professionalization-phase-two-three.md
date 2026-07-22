# Mneme Professionalization Phase Two and Three Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add production-operability gates and reduce a focused area of maintenance debt without changing Mneme's public API, data model, or deployment topology.

**Architecture:** Introduce a small shared observability package used by both FastAPI applications, promote the existing deterministic AI evaluation into CI, and add a separate PostgreSQL/Redis integration job. Refactoring is limited to extracting pure retrieval context-item transformations; operational exception handling is documented as an explicit boundary contract instead of broadly rewriting catches.

**Tech Stack:** FastAPI, Starlette middleware, Loguru, Python logging, pytest, asyncpg, redis-py, Alembic, GitHub Actions, Prometheus text exposition and alert rules.

---

### Task 1: Shared HTTP correlation and metrics

**Files:**
- Create: `app/mneme/observability/__init__.py`
- Create: `app/mneme/observability/context.py`
- Create: `app/mneme/observability/http.py`
- Create: `tests/test_http_observability.py`
- Modify: `app/mneme/conf/logging.py`
- Modify: `app/mneme/bootstrap/app_factory.py`
- Modify: `app/mneme/domains/health/router.py`
- Modify: `app/mneme/memoria/server/observability/context.py`
- Modify: `app/mneme/memoria/server/app.py`
- Modify: `app/mneme/memoria/server/api/health.py`

- [ ] **Step 1: Write failing middleware tests**

Create a minimal FastAPI app in `tests/test_http_observability.py`. Assert that a valid `X-Request-ID` and `X-Trace-ID` are available through `correlation_fields()` during the request, are echoed on the response, and produce bounded Prometheus rows using the route template rather than the concrete URL. Add an invalid-identifier case that expects generated safe values.

- [ ] **Step 2: Verify RED**

Run `python -m pytest -q tests/test_http_observability.py`. Expected: collection fails because `app.mneme.observability.http` does not exist.

- [ ] **Step 3: Implement the shared context and middleware**

Move request/run/event/trace context primitives into `app/mneme/observability/context.py`. Implement a lock-protected `HttpMetrics` accumulator, Prometheus renderer, and `configure_http_observability(app, metrics, emit)` middleware in `http.py`. Allow only sanitized identifiers and method, route template, status and duration metric dimensions.

- [ ] **Step 4: Integrate both applications**

Make the existing Memoria context module re-export shared correlation primitives while retaining its safe JSON formatter. Install the shared middleware in Mneme and Memoria, enrich `log_event` with active correlation fields, expose Mneme metrics at `/health/metrics`, and append HTTP metrics to Memoria's existing `/metrics` response.

- [ ] **Step 5: Verify GREEN**

Run the focused observability tests plus existing Memoria service-foundation tests. Expected: correlation headers, metric labels and existing health behavior all pass.

### Task 2: Real dependency integration lane

**Files:**
- Create: `tests/integration/test_runtime_dependencies.py`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/reminder-deploy.yml`
- Modify: `tests/test_dependency_configuration.py`

- [ ] **Step 1: Write the opt-in integration tests**

Mark tests with `pytest.mark.integration` and skip unless `RUN_INTEGRATION_TESTS=1`. Connect with asyncpg to verify the Alembic revision table and a rolled-back temporary transaction, then connect with redis-py asyncio to verify ping and an isolated set/get/delete round trip.

- [ ] **Step 2: Register the marker and CI services**

Add the marker to pytest configuration. Add an `integration-check` GitHub Actions job with pinned pgvector PostgreSQL and Redis services, run `alembic upgrade head`, and execute only `tests/integration` with explicit test DSNs. Make image publishing depend on this job.

- [ ] **Step 3: Add a workflow contract assertion**

Extend `tests/test_dependency_configuration.py` to assert the integration job runs migrations and the marked test directory.

- [ ] **Step 4: Verify locally without services**

Run the integration test file without `RUN_INTEGRATION_TESTS`; expected: explicit skips, not connection failures. Parse the workflow with PyYAML and run its static contract test. Actual database execution is delegated to GitHub Actions because Docker is unavailable locally.

### Task 3: Deterministic AI release gate and operations assets

**Files:**
- Modify: `.github/workflows/reminder-deploy.yml`
- Modify: `tests/test_dependency_configuration.py`
- Create: `deploy/monitoring/mneme-alerts.yml`
- Create: `docs/operations-runbook.md`
- Modify: `README.md`

- [ ] **Step 1: Execute the existing answer and Multi-Agent baseline**

Run the existing evaluation runner against `cases.jsonl` and `multi_agent_cases.jsonl`. Expected: process exits zero and reports all base, agent and Multi-Agent gates true.

- [ ] **Step 2: Add the deterministic command to backend CI**

Write the report under `.tmp/ci/memoria-eval.json`; the existing runner's exit code blocks regressions. Extend the workflow contract test to assert both datasets are included.

- [ ] **Step 3: Add alert rules**

Create syntactically valid Prometheus rules for Mneme/Memory Agent availability, HTTP 5xx ratio, sustained average request latency, Memory Agent dead letters, failed runs and projection lag. Use only metrics currently emitted by the applications.

- [ ] **Step 4: Add the operator runbook**

Document SLOs, dashboards, alert response, PostgreSQL/Redis/Neo4j backup, a disposable restore drill, release rollback, schema-forward rollback constraints, secret rotation and post-deploy validation. Commands must use explicit named volumes/databases and warn before destructive restore actions.

### Task 4: Focused retrieval module extraction

**Files:**
- Create: `app/mneme/domains/retrieval/context_items.py`
- Modify: `app/mneme/domains/retrieval/context_service.py`
- Modify: `tests/test_retrieval_fusion_service.py`

- [ ] **Step 1: Add a failing boundary test**

Assert the pure query-term, ContextItem construction and merge helpers are importable from `context_items`, and that `context_service` re-exports the same callables for compatibility.

- [ ] **Step 2: Verify RED**

Run the focused retrieval test. Expected: import failure because `context_items.py` does not exist.

- [ ] **Step 3: Move only pure transformations**

Move `dedupe_preserve_order`, `extract_query_terms`, the three `build_context_item_*` functions and ContextItem merge helpers into the new module. Import and re-export them from `context_service`; do not change algorithms, schemas or call sites.

- [ ] **Step 4: Verify behavior preservation**

Run retrieval fusion, debug, query-router, graph-RAG and answer-mode tests. Expected: all existing outputs remain unchanged.

### Task 5: Exception, dependency and repository hygiene audit

**Files:**
- Create: `docs/exception-boundaries.md`
- Modify: `requirements/base.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Classify broad exception boundaries**

Document allowed categories: transaction rollback then re-raise, worker terminal-state recording then re-raise, external dependency classification, cleanup-only suppression, and batch isolation with a failure counter/log. Identify any current broad catches that violate these invariants without rewriting unrelated workflows.

- [ ] **Step 2: Remove the unused OpenTelemetry dependency island**

Confirm no application/test import uses OpenTelemetry and remove the API, SDK, exporter, proto and semantic-convention entries that only require each other. Preserve Loguru and all dependencies with an observed application import.

- [ ] **Step 3: Ignore generated local work artifacts**

Add `.pytest_tmp_*/` and `.superpowers/` to `.gitignore`. Do not delete existing user-owned untracked directories.

- [ ] **Step 4: Verify dependency and repository state**

Run `pip check`, Ruff, the complete pytest suite, frontend checks, `git diff --check`, and confirm only requested source/docs/config files are changed.
