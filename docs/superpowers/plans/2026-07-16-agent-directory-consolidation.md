# Agent Directory Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Place every Agent-owned implementation under `app/mneme/memoria` while preserving the independent Memory Agent deployment boundary and the behavior of shared Mneme domains.

**Architecture:** `app/mneme/memoria` becomes the single ownership root for Agent HTTP endpoints, automation, configuration, clients, persistence, schemas, tasks, projections, CLI tools, and the independently deployed Memory Agent service. Shared chat, documents, retrieval utilities, outbox, health, database configuration, and the Mneme Alembic chain remain in their domain or infrastructure packages and depend only on Agent public modules.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Alembic, Celery, Docker Compose, Ruff, Pytest

---

### Task 1: Move the independent Memory Agent service

**Files:**
- Move: `services/memory_agent/**` -> `app/mneme/memoria/server/**`
- Move: `evals/memory_agent/README.md` -> `app/mneme/memoria/server/eval/README.md`
- Move: `evals/memory_agent/cases.jsonl` -> `app/mneme/memoria/server/eval/cases.jsonl`
- Delete: `services/__init__.py`

- [x] Move the service tree without changing runtime behavior.
- [x] Replace `services.memory_agent` with `app.mneme.memoria.server` in source and current operational documentation.
- [x] Replace `/app/services/memory_agent` with `/app/app/mneme/memoria/server` in Compose and Docker checks.
- [x] Keep `app/mneme/memoria/__init__.py` dependency-light so importing the service does not initialize Mneme integration code.

### Task 2: Consolidate Mneme Agent-owned integration modules

**Files:**
- Move: `app/mneme/clients/memory_agent_client.py` -> `app/mneme/memoria/clients/memory_agent.py`
- Move: `app/mneme/crud/agent_automation.py` -> `app/mneme/memoria/persistence/automation.py`
- Move: `app/mneme/infra/agent_runs.py` -> `app/mneme/memoria/persistence/runs.py`
- Move: `app/mneme/models/agent_automation.py` -> `app/mneme/memoria/models/automation.py`
- Move: `app/mneme/models/agent_runtime_event.py` -> `app/mneme/memoria/models/runtime_event.py`
- Move: `app/mneme/schemas/agent_automation.py` -> `app/mneme/memoria/schemas/automation.py`
- Move: `app/mneme/schemas/memory_agent.py` -> `app/mneme/memoria/schemas/memory_agent.py`
- Move: `app/mneme/tasks/agent_tasks.py` -> `app/mneme/memoria/tasks/runs.py`
- Move: `app/mneme/tasks/heartbeat_tasks.py` -> `app/mneme/memoria/tasks/heartbeats.py`
- Move: `app/mneme/domains/documents/agent_projection.py` -> `app/mneme/memoria/projections/documents.py`
- Move: `app/mneme/cli/export_agent_projection.py` -> `app/mneme/memoria/cli/export_projection.py`
- Move: `app/mneme/cli/memory_agent_ops.py` -> `app/mneme/memoria/cli/operations.py`
- Move: `app/mneme/domains/tasks/outbox_http.py` -> `app/mneme/memoria/automation/http_outbox.py`
- Extract: Memory Agent request translation from `app/mneme/domains/chat/service.py` -> `app/mneme/memoria/chat_bridge.py`
- Delete: `app/mneme/pipelines/companion_pipeline.py`

- [x] Create small ownership subpackages with package docstrings only.
- [x] Move files mechanically and update imports without compatibility wrappers.
- [x] Keep shared cache, chat persistence, document pipeline, and Outbox modules in their existing layers.

### Task 3: Consolidate Agent APIs, automation, and model configuration

**Files:**
- Move: `app/mneme/domains/chat/run_router.py` -> `app/mneme/memoria/api/runs.py`
- Move: `app/mneme/domains/automation/router.py` -> `app/mneme/memoria/api/automation.py`
- Move: `app/mneme/domains/memory_agent/router.py` -> `app/mneme/memoria/api/memory.py`
- Move: `app/mneme/domains/retrieval/router.py` -> `app/mneme/memoria/api/retrieval.py`
- Move: `app/mneme/domains/automation/service.py` -> `app/mneme/memoria/automation/service.py`
- Move: `app/mneme/domains/automation/outbox.py` -> `app/mneme/memoria/automation/outbox.py`
- Move: `app/mneme/domains/memory_agent/service.py` -> `app/mneme/memoria/memory_gateway.py`
- Move: `app/mneme/domains/settings/router.py` -> `app/mneme/memoria/configuration/router.py`
- Move: `app/mneme/domains/settings/ai_models.py` -> `app/mneme/memoria/configuration/service.py`
- Move: `app/mneme/crud/ai_model_config.py` -> `app/mneme/memoria/configuration/repository.py`
- Move: `app/mneme/models/ai_model_config.py` -> `app/mneme/memoria/models/ai_model_config.py`
- Move: `app/mneme/schemas/ai_model_config.py` -> `app/mneme/memoria/configuration/schemas.py`

- [x] Update FastAPI dynamic router registration to the four Agent API/configuration modules.
- [x] Update Agent automation and gateway imports to their new ownership paths.
- [x] Preserve all public HTTP paths and response contracts.

### Task 4: Update entrypoints and boundary checks

**Files:**
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/infra/celery_app.py`
- Modify: `app/mneme/models/__init__.py`
- Modify: `docker-compose.yml`
- Modify: `docker/Dockerfile`
- Modify: `docker/start-memory-agent-api.sh`
- Modify: `docker/start-memory-agent-worker.sh`
- Modify: `README.md`
- Modify: `deploy/DEPLOY.md`
- Modify: `docs/agent-module.md`
- Modify: `docs/superpowers/specs/2026-07-14-memory-agent-service-design.md`
- Modify: existing tests that import or locate moved modules

- [x] Update Celery imports while preserving registered task names and queues.
- [x] Update model registration while preserving SQLAlchemy table metadata.
- [x] Update Memory Agent API, worker, migration, CLI, and evaluation commands.
- [x] Update the boundary test to exclude the nested independent service when scanning Mneme integration code.
- [x] Remove the now-empty `services`, `evals`, and Agent-specific domain paths.

### Task 5: Verify behavior and packaging

- [x] Confirm no active source, test, deployment file, or current documentation references `services.memory_agent` or `/services/memory_agent`.
- [x] Import every FastAPI router and both Celery applications.
- [x] Run both Alembic history checks.
- [ ] Run Docker Compose config validation (Docker CLI is unavailable in the current environment; Compose contract tests pass).
- [x] Run Ruff on changed Python files and compile all Python packages.
- [x] Run the complete existing test suite with a worktree-local pytest temporary directory.
- [x] Run `git diff --check` and review the final status/diff for unrelated changes.
