# Graph Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move graph routing, graph payload building, Neo4j query/projection, graph admin, and GraphRAG planning into `app/mneme/domains/graph/` without changing public API paths or graph behavior.

**Architecture:** This is a behavior-preserving migration. `domains/graph/` becomes the canonical graph boundary; other domains and legacy services import graph capabilities from `app.mneme.domains.graph.*`. Old graph service files and the old graph router are deleted after all live imports are updated.

**Tech Stack:** Python, FastAPI, SQLAlchemy async sessions, Neo4j client adapter, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create or replace:

- `app/mneme/domains/graph/service.py`: graph node/edge and fallback payload builders, moved from `services/graph_service.py`.
- `app/mneme/domains/graph/query.py`: Neo4j read/query payload builders, moved from `services/graph_query_service.py`.
- `app/mneme/domains/graph/projection.py`: Neo4j projection write helpers, moved from `services/graph_projection_service.py`.
- `app/mneme/domains/graph/admin.py`: Neo4j health and projection rebuild orchestration, moved from `services/graph_admin_service.py`.
- `app/mneme/domains/graph/rag.py`: GraphRAG planning, replacing the current forwarding shell.
- `app/mneme/domains/graph/router.py`: real `/graph` router, replacing the current forwarding shell.
- `tests/test_graph_domain_convergence.py`: route/import convergence tests.

Modify:

- `app/mneme/bootstrap/router_registry.py`
- `app/mneme/routers/health.py`
- `app/mneme/routers/auth.py`
- `app/mneme/routers/users.py`
- `app/mneme/domains/documents/router.py`
- `app/mneme/services/document_service.py`
- `app/mneme/services/task_admin_service.py`
- `app/mneme/services/resource_service.py`
- `app/mneme/services/outbox_service.py`
- `app/mneme/services/memory_service.py`
- `app/mneme/pipelines/memory_extract_pipeline.py`
- `tests/test_graph_rag_service.py`
- `scripts/debug_day15.py`
- `scripts/rebuild_neo4j_graph.py`

Delete after imports are updated:

- `app/mneme/routers/graph.py`
- `app/mneme/services/graph_service.py`
- `app/mneme/services/graph_query_service.py`
- `app/mneme/services/graph_projection_service.py`
- `app/mneme/services/graph_admin_service.py`
- `app/mneme/services/graph_rag_service.py`

## Task 1: Add Failing Graph Convergence Tests

**Files:**
- Create: `tests/test_graph_domain_convergence.py`
- Modify: `tests/test_graph_rag_service.py`

- [x] **Step 1: Create convergence test file**

Create `tests/test_graph_domain_convergence.py`:

```python
import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class GraphDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_graph_domain_router(self):
        self.assertIn("app.mneme.domains.graph.router", ROUTER_MODULE_NAMES)
        self.assertNotIn("app.mneme.routers.graph", ROUTER_MODULE_NAMES)

    def test_graph_domain_modules_are_importable(self):
        from app.mneme.domains.graph.admin import rebuild_graph_projection_for_user
        from app.mneme.domains.graph.projection import sync_document_memory_projection
        from app.mneme.domains.graph.query import build_user_graph_payload_from_neo4j
        from app.mneme.domains.graph.rag import build_graph_rag_decision
        from app.mneme.domains.graph.service import build_user_graph_payload

        self.assertEqual(build_user_graph_payload.__name__, "build_user_graph_payload")
        self.assertEqual(build_user_graph_payload_from_neo4j.__name__, "build_user_graph_payload_from_neo4j")
        self.assertEqual(sync_document_memory_projection.__name__, "sync_document_memory_projection")
        self.assertEqual(rebuild_graph_projection_for_user.__name__, "rebuild_graph_projection_for_user")
        self.assertEqual(build_graph_rag_decision.__name__, "build_graph_rag_decision")

    def test_graph_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/graph", paths)
        self.assertIn("/graph/rebuild", paths)
        self.assertIn("/graph/documents/{document_id}", paths)
        self.assertIn("/graph/knowledge-bases/{knowledge_base_id}", paths)
        self.assertIn("/graph/knowledge-bases/{knowledge_base_id}/rag", paths)
        self.assertIn("/graph/knowledge-bases/{knowledge_base_id}/rebuild", paths)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Update GraphRAG test import to target domain**

In `tests/test_graph_rag_service.py`, replace:

```python
from app.mneme.services.graph_rag_service import (
```

With:

```python
from app.mneme.domains.graph.rag import (
```

- [x] **Step 3: Run tests to verify red state**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_graph_domain_convergence tests.test_graph_rag_service
```

Expected:

```text
FAIL: test_router_registry_uses_graph_domain_router
```

or:

```text
ModuleNotFoundError
```

At least one failure must prove graph convergence is incomplete.

## Task 2: Move Core Graph Payload Builders

**Files:**
- Create: `app/mneme/domains/graph/service.py`
- Delete later: `app/mneme/services/graph_service.py`

- [x] **Step 1: Create domain service**

Copy the complete current contents of:

```text
app/mneme/services/graph_service.py
```

into:

```text
app/mneme/domains/graph/service.py
```

- [x] **Step 2: Run import smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.graph.service import build_user_graph_payload, _build_related_document_edges; print(build_user_graph_payload.__name__, _build_related_document_edges.__name__)"
```

Expected:

```text
build_user_graph_payload _build_related_document_edges
```

## Task 3: Move Graph Query, Projection, Admin, and GraphRAG Modules

**Files:**
- Create: `app/mneme/domains/graph/query.py`
- Replace: `app/mneme/domains/graph/projection.py`
- Create: `app/mneme/domains/graph/admin.py`
- Replace: `app/mneme/domains/graph/rag.py`

- [x] **Step 1: Move graph query module**

Copy `app/mneme/services/graph_query_service.py` into `app/mneme/domains/graph/query.py`.

In `app/mneme/domains/graph/query.py`, replace:

```python
from app.mneme.services.graph_service import (
```

With:

```python
from app.mneme.domains.graph.service import (
```

- [x] **Step 2: Move graph projection module**

Replace `app/mneme/domains/graph/projection.py` with the complete contents of `app/mneme/services/graph_projection_service.py`.

In `app/mneme/domains/graph/projection.py`, replace:

```python
from app.mneme.services.graph_service import _build_related_document_edges
```

With:

```python
from app.mneme.domains.graph.service import _build_related_document_edges
```

- [x] **Step 3: Move graph admin module**

Copy `app/mneme/services/graph_admin_service.py` into `app/mneme/domains/graph/admin.py`.

In `app/mneme/domains/graph/admin.py`, replace:

```python
from app.mneme.services.graph_projection_service import (
```

With:

```python
from app.mneme.domains.graph.projection import (
```

- [x] **Step 4: Move GraphRAG module**

Replace `app/mneme/domains/graph/rag.py` with the complete contents of `app/mneme/services/graph_rag_service.py`.

In `app/mneme/domains/graph/rag.py`, replace:

```python
from app.mneme.services.graph_service import _build_related_document_edges
```

With:

```python
from app.mneme.domains.graph.service import _build_related_document_edges
```

- [x] **Step 5: Run graph import smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.graph.admin import rebuild_graph_projection_for_user; from app.mneme.domains.graph.query import build_user_graph_payload_from_neo4j; from app.mneme.domains.graph.projection import sync_document_memory_projection; from app.mneme.domains.graph.rag import build_graph_rag_decision; print('graph domain imports ok')"
```

Expected:

```text
graph domain imports ok
```

## Task 4: Move Graph Router

**Files:**
- Replace: `app/mneme/domains/graph/router.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Delete later: `app/mneme/routers/graph.py`

- [x] **Step 1: Replace graph router forwarding shell**

Replace `app/mneme/domains/graph/router.py` with the complete current contents of:

```text
app/mneme/routers/graph.py
```

- [x] **Step 2: Update router imports**

In `app/mneme/domains/graph/router.py`, replace:

```python
from app.mneme.services.graph_admin_service import (
```

With:

```python
from app.mneme.domains.graph.admin import (
```

Replace:

```python
from app.mneme.services.graph_query_service import (
```

With:

```python
from app.mneme.domains.graph.query import (
```

Replace:

```python
from app.mneme.services.graph_service import (
```

With:

```python
from app.mneme.domains.graph.service import (
```

Replace:

```python
from app.mneme.services.graph_rag_service import build_graph_rag_decision
```

With:

```python
from app.mneme.domains.graph.rag import build_graph_rag_decision
```

- [x] **Step 3: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.graph",
```

With:

```python
"app.mneme.domains.graph.router",
```

- [x] **Step 4: Run graph route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/graph' in paths; assert '/graph/rebuild' in paths; assert '/graph/knowledge-bases/{knowledge_base_id}/rag' in paths; print('graph route smoke ok')"
```

Expected:

```text
graph route smoke ok
```

## Task 5: Update Graph Callers

**Files:**
- Modify: `app/mneme/routers/health.py`
- Modify: `app/mneme/routers/auth.py`
- Modify: `app/mneme/routers/users.py`
- Modify: `app/mneme/domains/documents/router.py`
- Modify: `app/mneme/services/document_service.py`
- Modify: `app/mneme/services/task_admin_service.py`
- Modify: `app/mneme/services/resource_service.py`
- Modify: `app/mneme/services/outbox_service.py`
- Modify: `app/mneme/services/memory_service.py`
- Modify: `app/mneme/pipelines/memory_extract_pipeline.py`
- Modify: `scripts/debug_day15.py`
- Modify: `scripts/rebuild_neo4j_graph.py`

- [x] **Step 1: Update admin imports**

Replace:

```python
from app.mneme.services.graph_admin_service import
```

With:

```python
from app.mneme.domains.graph.admin import
```

in:

```text
app/mneme/routers/health.py
scripts/rebuild_neo4j_graph.py
```

- [x] **Step 2: Update projection imports**

Replace:

```python
from app.mneme.services.graph_projection_service import
```

With:

```python
from app.mneme.domains.graph.projection import
```

in:

```text
app/mneme/routers/auth.py
app/mneme/routers/users.py
app/mneme/domains/documents/router.py
app/mneme/services/document_service.py
app/mneme/services/task_admin_service.py
app/mneme/services/resource_service.py
app/mneme/services/outbox_service.py
app/mneme/services/memory_service.py
app/mneme/pipelines/memory_extract_pipeline.py
```

- [x] **Step 3: Update GraphRAG script import**

In `scripts/debug_day15.py`, replace:

```python
from app.mneme.services.graph_rag_service import build_graph_rag_decision, compare_graph_retrieval
```

With:

```python
from app.mneme.domains.graph.rag import build_graph_rag_decision, compare_graph_retrieval
```

- [x] **Step 4: Run live import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.(graph_service|graph_query_service|graph_projection_service|graph_admin_service|graph_rag_service)|app\.mneme\.routers\.graph|from app\.mneme\.routers\.graph" app tests scripts scripts2
```

Expected remaining matches:

- Only old graph service files and old `app/mneme/routers/graph.py` before deletion.

## Task 6: Delete Legacy Graph Files

**Files:**
- Delete: `app/mneme/routers/graph.py`
- Delete: `app/mneme/services/graph_service.py`
- Delete: `app/mneme/services/graph_query_service.py`
- Delete: `app/mneme/services/graph_projection_service.py`
- Delete: `app/mneme/services/graph_admin_service.py`
- Delete: `app/mneme/services/graph_rag_service.py`

- [x] **Step 1: Confirm no live imports point to legacy graph files**

Run:

```powershell
rg -n "from app\.mneme\.services\.(graph_service|graph_query_service|graph_projection_service|graph_admin_service|graph_rag_service)|app\.mneme\.routers\.graph|from app\.mneme\.routers\.graph" app tests scripts scripts2
```

Expected matches must be limited to the exact files listed for deletion.

- [x] **Step 2: Delete legacy graph files**

Delete:

```text
app/mneme/routers/graph.py
app/mneme/services/graph_service.py
app/mneme/services/graph_query_service.py
app/mneme/services/graph_projection_service.py
app/mneme/services/graph_admin_service.py
app/mneme/services/graph_rag_service.py
```

- [x] **Step 3: Confirm files are gone**

Run:

```powershell
Test-Path app\mneme\routers\graph.py; Test-Path app\mneme\services\graph_service.py; Test-Path app\mneme\services\graph_rag_service.py
```

Expected:

```text
False
False
False
```

## Task 7: Full Phase Verification

**Files:**
- No source changes unless verification reveals an issue.

- [x] **Step 1: Run graph tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_graph_domain_convergence tests.test_graph_rag_service
```

Expected:

```text
OK
```

- [x] **Step 2: Run previous phase regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [x] **Step 3: Run route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/graph' in paths; assert '/graph/rebuild' in paths; assert '/graph/knowledge-bases/{knowledge_base_id}/rag' in paths; assert '/kb/documents/upload' in paths; assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [x] **Step 4: Run legacy graph import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.(graph_service|graph_query_service|graph_projection_service|graph_admin_service|graph_rag_service)|app\.mneme\.routers\.graph|from app\.mneme\.routers\.graph" app tests scripts scripts2
```

Expected:

```text
```

No matches.

- [x] **Step 5: Run wildcard forwarding scan**

Run:

```powershell
rg -n "from app\.mneme\.services\..* import \*" app\mneme\domains\graph
```

Expected:

```text
```

No matches.

- [x] **Step 6: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected:

```text
```

No errors.

## Task 8: Commit Phase 3

**Files:**
- All files changed by Tasks 1-7.

- [x] **Step 1: Stage only Phase 3 files**

Run:

```powershell
git add app\mneme\domains\graph app\mneme\bootstrap\router_registry.py app\mneme\routers\health.py app\mneme\routers\auth.py app\mneme\routers\users.py app\mneme\domains\documents\router.py app\mneme\services\document_service.py app\mneme\services\task_admin_service.py app\mneme\services\resource_service.py app\mneme\services\outbox_service.py app\mneme\services\memory_service.py app\mneme\pipelines\memory_extract_pipeline.py tests\test_graph_domain_convergence.py tests\test_graph_rag_service.py scripts\debug_day15.py scripts\rebuild_neo4j_graph.py docs\superpowers\plans\2026-07-07-graph-domain-convergence.md
git add -u app\mneme\routers\graph.py app\mneme\services\graph_service.py app\mneme\services\graph_query_service.py app\mneme\services\graph_projection_service.py app\mneme\services\graph_admin_service.py app\mneme\services\graph_rag_service.py
```

- [x] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge graph domain"
```

Expected:

```text
refactor: converge graph domain
```

## Self-Review

- Spec coverage: This plan implements Phase 3 graph router, graph payload, graph query, graph projection, graph admin, and GraphRAG convergence. It does not migrate memory/profile/advice/companion ownership.
- Completion-marker scan: The plan contains no unfinished markers or open-ended implementation gaps.
- Type consistency: The target module paths are consistently `app.mneme.domains.graph.service`, `query`, `projection`, `admin`, `rag`, and `router`.
