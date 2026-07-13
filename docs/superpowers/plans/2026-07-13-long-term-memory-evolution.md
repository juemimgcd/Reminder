# Long-Term Memory Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve file-derived memory history across reindexing while maintaining stable evidence links and a persisted, rebuildable canonical-memory governance projection.

**Architecture:** Existing `memory_entries` become lifecycle-aware observations without renaming the public model. Document reindexing reconciles extracted observations by deterministic fingerprint; canonical memories, evidence membership, and relations are persisted as a derived projection that can be rebuilt from active observations.

**Tech Stack:** Python 3.13, SQLAlchemy 2 async, PostgreSQL 17, Alembic, Pydantic 2, pytest

---

### Task 1: Extend the persistence model

**Files:**
- Modify: `app/mneme/models/memory.py`
- Modify: `app/mneme/models/__init__.py`
- Create: `alembic/versions/20260713_01_add_long_term_memory_evolution.py`
- Test: `tests/test_long_term_memory_evolution.py`

- [ ] Add observation lifecycle columns to `memory_entries`: `source_fingerprint`, `extraction_version`, `status`, `confidence`, `first_seen_at`, `last_seen_at`, `valid_from`, and `valid_to`.
- [ ] Add `canonical_memories`, `canonical_memory_evidence`, and `memory_relations` with knowledge-base ownership, cascade-safe evidence relations, stable IDs, and timestamps.
- [ ] Backfill existing observations as active with deterministic PostgreSQL fingerprints and current creation timestamps.
- [ ] Verify the migration revises Alembic head `20260711_01` and exposes a reversible downgrade.

### Task 2: Add deterministic observation identity

**Files:**
- Create: `app/mneme/domains/memory/identity.py`
- Modify: `app/mneme/schemas/memory_entry.py`
- Test: `tests/test_long_term_memory_evolution.py`

- [ ] Normalize extracted text without changing stored source text.
- [ ] Hash owner, knowledge base, document, chunk, type, name, summary, evidence, and extraction version into a stable SHA-256 fingerprint.
- [ ] Generate new observation IDs from the fingerprint and enrich legacy create payloads with lifecycle defaults.
- [ ] Verify identical inputs are stable and changed evidence produces a different identity.

### Task 3: Replace destructive rebuild with reconciliation

**Files:**
- Modify: `app/mneme/crud/memory_entry.py`
- Modify: `app/mneme/domains/memory/service.py`
- Test: `tests/test_long_term_memory_evolution.py`

- [ ] Make normal list/search queries return active observations only, with an explicit `include_inactive` option for document reconciliation.
- [ ] Match extracted observations to existing rows by source fingerprint.
- [ ] Refresh matching rows, insert new rows, and mark missing active rows `superseded` with `valid_to` instead of deleting them.
- [ ] Preserve the existing rebuild result keys; `deleted_entry_count` reports observations retired by reconciliation for response compatibility.

### Task 4: Persist the canonical-memory governance projection

**Files:**
- Create: `app/mneme/domains/memory/projection.py`
- Modify: `app/mneme/domains/memory/service.py`
- Test: `tests/test_long_term_memory_evolution.py`

- [ ] Reuse `build_memory_governance_view()` as the single governance classifier.
- [ ] Replace the knowledge base's derived canonical, evidence-membership, and relation rows in one database transaction after observation reconciliation.
- [ ] Preserve stable canonical and relation IDs from the existing governance functions.
- [ ] Keep the public governance response behavior unchanged while the persisted projection becomes available to future Agent memory tools.

### Task 5: Preserve deletion and compatibility semantics

**Files:**
- Modify: `app/mneme/domains/documents/resources.py`
- Modify: `app/mneme/pipelines/memory_extract_pipeline.py`
- Modify: `app/mneme/schemas/memory_library.py`
- Test: `tests/test_long_term_memory_evolution.py`

- [ ] Hard-delete observations when the user deletes their source document or knowledge base.
- [ ] Rebuild the remaining knowledge base governance projection after a document deletion.
- [ ] Route the legacy extraction pipeline through reconciliation rather than direct insertion.
- [ ] Keep existing public paths and response field names intact.

### Task 6: Verify after implementation

**Files:**
- Test: `tests/test_long_term_memory_evolution.py`

- [ ] Run focused memory, retrieval, Agent, and document tests with a workspace-local pytest temp directory.
- [ ] Run Ruff on all touched Python files.
- [ ] Run `python -m alembic heads` and assert the new revision is the single head.
- [ ] Run an offline Alembic SQL generation check for the new upgrade chain.
- [ ] Run the full backend suite and report pre-existing or environment-related failures separately.
