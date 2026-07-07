# Documents Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the document API router and document indexing pipeline into `app/mneme/domains/documents/` without changing public API paths, Celery task names, or indexing behavior.

**Architecture:** This is a behavior-preserving migration. `domains/documents/` becomes the canonical home for document HTTP endpoints and the document indexing pipeline. Existing `services/document_service.py`, `services/resource_service.py`, and outbox/task modules remain in place for now because their ownership spans documents, tasks, graph projection, and resource cleanup.

**Tech Stack:** Python, FastAPI, SQLAlchemy async sessions, Celery, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create or replace:

- `app/mneme/domains/documents/router.py`: real `/kb/documents` router, moved from `app/mneme/routers/documents.py`.
- `app/mneme/domains/documents/pipeline.py`: document indexing pipeline, moved from `app/mneme/pipelines/document_index_pipeline.py`.

Modify:

- `app/mneme/bootstrap/router_registry.py`: register `app.mneme.domains.documents.router`.
- `app/mneme/tasks/index_tasks.py`: import `run_document_index_pipeline` from `domains/documents/pipeline.py`.
- `scripts2/debug_day11_pipeline.py`: import and patch domain pipeline paths.
- `scripts2/debug_day13_harness.py`: import domain pipeline.
- `scripts2/debug_day14_advanced_harness.py`: import domain pipeline.
- `tests/test_documents_domain_convergence.py`: new smoke tests for the domain router, pipeline, and router registry.

Delete after imports are updated:

- `app/mneme/routers/documents.py`
- `app/mneme/pipelines/document_index_pipeline.py`

Keep for now:

- `app/mneme/services/document_service.py`
- `app/mneme/services/resource_service.py`

## Task 1: Add Failing Domain Convergence Tests

**Files:**
- Create: `tests/test_documents_domain_convergence.py`

- [ ] **Step 1: Create test file**

Create `tests/test_documents_domain_convergence.py`:

```python
import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class DocumentsDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_documents_domain_router(self):
        self.assertIn("app.mneme.domains.documents.router", ROUTER_MODULE_NAMES)
        self.assertNotIn("app.mneme.routers.documents", ROUTER_MODULE_NAMES)

    def test_documents_pipeline_imports_from_domain(self):
        from app.mneme.domains.documents.pipeline import run_document_index_pipeline

        self.assertEqual(run_document_index_pipeline.__name__, "run_document_index_pipeline")

    def test_documents_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/kb/documents/upload", paths)
        self.assertIn("/kb/documents", paths)
        self.assertIn("/kb/documents/{document_id}/index", paths)
        self.assertIn("/kb/documents/{document_id}", paths)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify red state**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documents_domain_convergence
```

Expected:

```text
FAIL: test_router_registry_uses_documents_domain_router
```

or:

```text
ModuleNotFoundError: No module named 'app.mneme.domains.documents.pipeline'
```

At least one failure must prove the domain migration is not complete yet.

## Task 2: Move Document Router

**Files:**
- Replace: `app/mneme/domains/documents/router.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Delete later: `app/mneme/routers/documents.py`

- [ ] **Step 1: Replace forwarding shell with real router**

Replace the complete contents of `app/mneme/domains/documents/router.py` with the complete current contents of:

```text
app/mneme/routers/documents.py
```

- [ ] **Step 2: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.documents",
```

With:

```python
"app.mneme.domains.documents.router",
```

- [ ] **Step 3: Run router smoke test**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/kb/documents/upload' in paths; assert '/kb/documents/{document_id}/index' in paths; print('documents route smoke ok')"
```

Expected:

```text
documents route smoke ok
```

## Task 3: Move Document Index Pipeline

**Files:**
- Create: `app/mneme/domains/documents/pipeline.py`
- Modify: `app/mneme/tasks/index_tasks.py`
- Delete later: `app/mneme/pipelines/document_index_pipeline.py`

- [ ] **Step 1: Create domain pipeline**

Copy the complete current contents of:

```text
app/mneme/pipelines/document_index_pipeline.py
```

into:

```text
app/mneme/domains/documents/pipeline.py
```

- [ ] **Step 2: Update Celery task import**

In `app/mneme/tasks/index_tasks.py`, replace:

```python
from app.mneme.pipelines.document_index_pipeline import run_document_index_pipeline
```

With:

```python
from app.mneme.domains.documents.pipeline import run_document_index_pipeline
```

- [ ] **Step 3: Run import smoke test**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.documents.pipeline import run_document_index_pipeline; from app.mneme.tasks.index_tasks import run_index_document_task_async; print(run_document_index_pipeline.__name__, run_index_document_task_async.__name__)"
```

Expected:

```text
run_document_index_pipeline run_index_document_task_async
```

## Task 4: Update Debug Harness Imports

**Files:**
- Modify: `scripts2/debug_day11_pipeline.py`
- Modify: `scripts2/debug_day13_harness.py`
- Modify: `scripts2/debug_day14_advanced_harness.py`

- [ ] **Step 1: Update direct imports**

Replace every direct import:

```python
from app.mneme.pipelines.document_index_pipeline import run_document_index_pipeline
```

With:

```python
from app.mneme.domains.documents.pipeline import run_document_index_pipeline
```

- [ ] **Step 2: Update mock patch paths in `scripts2/debug_day11_pipeline.py`**

Replace these strings:

```text
pipelines.document_index_pipeline.update_document_status_with_projection
pipelines.document_index_pipeline.load_langchain_documents
pipelines.document_index_pipeline.split_documents
pipelines.document_index_pipeline.persist_chunks_for_document
pipelines.document_index_pipeline.rebuild_memory_entries_for_document
pipelines.document_index_pipeline.add_documents_to_vector_store_in_batches
```

With:

```text
domains.documents.pipeline.update_document_status_with_projection
domains.documents.pipeline.load_langchain_documents
domains.documents.pipeline.split_documents
domains.documents.pipeline.persist_chunks_for_document
domains.documents.pipeline.rebuild_memory_entries_for_document
domains.documents.pipeline.add_documents_to_vector_store_in_batches
```

- [ ] **Step 3: Run scan**

Run:

```powershell
rg -n "pipelines\.document_index_pipeline|routers\.documents|app\.mneme\.routers\.documents" app tests scripts scripts2
```

Expected remaining matches:

- Only `app/mneme/routers/documents.py`
- Only `app/mneme/pipelines/document_index_pipeline.py`
- Historical docs or comments under scripts that are not live imports

## Task 5: Delete Legacy Documents Files

**Files:**
- Delete: `app/mneme/routers/documents.py`
- Delete: `app/mneme/pipelines/document_index_pipeline.py`

- [ ] **Step 1: Confirm live imports no longer point to legacy files**

Run:

```powershell
rg -n "from app\.mneme\.pipelines\.document_index_pipeline|app\.mneme\.routers\.documents|routers\.documents" app tests scripts scripts2
```

Expected:

```text
```

No live import matches.

- [ ] **Step 2: Delete legacy files**

Delete:

```text
app/mneme/routers/documents.py
app/mneme/pipelines/document_index_pipeline.py
```

- [ ] **Step 3: Confirm forwarding shell is gone**

Run:

```powershell
Test-Path app\mneme\routers\documents.py; Test-Path app\mneme\pipelines\document_index_pipeline.py
```

Expected:

```text
False
False
```

## Task 6: Full Phase Verification

**Files:**
- No source changes unless verification reveals an issue.

- [ ] **Step 1: Run documents convergence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documents_domain_convergence
```

Expected:

```text
OK
```

- [ ] **Step 2: Run existing focused regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [ ] **Step 3: Run app route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/kb/documents/upload' in paths; assert '/kb/documents/{document_id}/index' in paths; assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [ ] **Step 4: Run legacy import scan**

Run:

```powershell
rg -n "from app\.mneme\.pipelines\.document_index_pipeline|app\.mneme\.routers\.documents|routers\.documents" app tests scripts scripts2
```

Expected:

```text
```

No live import matches.

- [ ] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected:

```text
```

No errors.

## Task 7: Commit Phase 2

**Files:**
- All files changed by Tasks 1-6.

- [ ] **Step 1: Stage only Phase 2 files**

Run:

```powershell
git add app\mneme\domains\documents app\mneme\bootstrap\router_registry.py app\mneme\tasks\index_tasks.py scripts2\debug_day11_pipeline.py scripts2\debug_day13_harness.py scripts2\debug_day14_advanced_harness.py tests\test_documents_domain_convergence.py docs\superpowers\plans\2026-07-07-documents-domain-convergence.md
git add -u app\mneme\routers\documents.py app\mneme\pipelines\document_index_pipeline.py
```

- [ ] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge documents domain"
```

Expected:

```text
refactor: converge documents domain
```

## Self-Review

- Spec coverage: This plan implements the documents router and index pipeline part of Phase 2. It intentionally leaves document resource cleanup, document task submission, outbox, and graph projection ownership for later phases.
- Completion-marker scan: The plan contains no unfinished markers or open-ended implementation gaps.
- Type consistency: The target module path is consistently `app.mneme.domains.documents.pipeline` and the target router path is consistently `app.mneme.domains.documents.router`.
