# Memoria Namespace Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `app/mneme/memoria` the single ownership root for the Memoria Agent subsystem inside the Mneme backend project.

**Architecture:** Mneme remains the backend application namespace and Memoria becomes the Agent product namespace. Existing Agent integration modules move from `app/mneme/agent` to `app/mneme/memoria`; the independently deployed Agent API and worker move from the redundant `memoria/memory_agent` nesting to `memoria/server`. Internal Python imports and operational paths adopt the Memoria namespace, while environment variables, Docker service names, HTTP routes, and persisted contracts remain compatible in this structural pass.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Alembic, Celery, Docker Compose, Ruff, Pytest

---

### Task 1: Establish the Memoria ownership root

**Files:**
- Move: `app/mneme/agent/**` -> `app/mneme/memoria/**`
- Move: `app/mneme/memoria/memory_agent/**` -> `app/mneme/memoria/server/**`

- [x] Verify both move targets are inside the active worktree and do not already exist.
- [x] Move the package trees without changing runtime behavior.
- [x] Keep `app/mneme/memoria/__init__.py` dependency-light.

### Task 2: Update internal imports and entrypoints

**Files:**
- Modify: `app/**`
- Modify: `alembic/env.py`
- Modify: `docker-compose.yml`
- Modify: `docker/**`
- Modify: `scripts/**`

- [x] Replace `app.mneme.agent.memory_agent` imports with `app.mneme.memoria.server`.
- [x] Replace remaining `app.mneme.agent` imports with `app.mneme.memoria`.
- [x] Update filesystem paths and executable entrypoints to the new namespace.
- [x] Preserve `MEMORY_AGENT_*`, Docker service names, public HTTP paths, and persistence contracts.

### Task 3: Align documentation and boundary checks

**Files:**
- Move: `docs/agent-module.md` -> `docs/memoria-module.md`
- Modify: `README.md`
- Modify: `deploy/DEPLOY.md`
- Modify: `docs/superpowers/specs/**`
- Modify: current `docs/superpowers/plans/2026-07-16-*.md`
- Modify: `tests/**`

- [x] Use Memoria as the Agent subsystem name in current documentation.
- [x] Update existing test imports, source paths, and ownership-prefix assertions.
- [x] Assert that no active source package remains under `app/mneme/agent`.

### Task 4: Verify the migration

- [x] Run Ruff on changed Python files.
- [x] Compile the application packages and import all FastAPI/Celery entrypoints.
- [x] Run the full existing Pytest suite.
- [x] Validate both Alembic histories and the Memoria evaluation baseline.
- [x] Run `git diff --check` and scan for stale Agent namespace references.
- [x] Record Docker Compose validation as unavailable if the local Docker CLI remains absent.
