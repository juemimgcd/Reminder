# Project Structure Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove files that have no runtime, registration, CLI, migration, or test consumers, while keeping Agent orchestration concentrated in `app/mneme/memoria` and preserving framework-owned integration layers.

**Architecture:** Executable Agent orchestration, contracts, routing, run lifecycle, and adapters remain under `app/mneme/memoria`. Framework-owned persistence, migrations, route registration, and task entrypoints stay in their conventional layers; all Agent-owned variants and the independently deployed service live below `app/mneme/memoria`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Celery, Ruff, Pytest

---

### Task 1: Remove proven-unused Python modules

- [x] Delete compatibility re-export modules with no imports.
- [x] Delete the superseded retrieval query service and recall aliases.
- [x] Delete unused advice/analysis pipeline wrappers and obsolete schemas.
- [x] Confirm dynamic router and Celery registration targets remain intact.

### Task 2: Remove stale repository artifacts

- [x] Delete the obsolete Agentic RAG roadmap and scratch HTTP request file.
- [x] Delete stale generic planning/flow documents that describe removed paths.
- [x] Delete unreferenced ER diagram image exports.
- [x] Preserve current product docs, deployment docs, migration history, and implementation-plan history.

### Task 3: Make the Agent ownership boundary explicit

- [x] Add a concise ownership map to the Agent package and module documentation.
- [x] Document why persistence, delivery, and the independent memory service remain outside that package.

### Task 4: Verify the cleanup

- [x] Search for references to every deleted module and file.
- [x] Run Ruff against changed Python files.
- [x] Compile the Python packages.
- [x] Run the existing test suite without modifying tests.
- [x] Review the final diff for accidental or unrelated changes.
