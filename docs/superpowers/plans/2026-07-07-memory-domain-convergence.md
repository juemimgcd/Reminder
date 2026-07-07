# Memory Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move memory routing, memory library rebuilding/extraction helpers, and memory governance into `app/mneme/domains/memory/` without changing public API paths or memory behavior.

**Architecture:** This is a behavior-preserving migration. `domains/memory/` becomes the canonical memory boundary; old `services/memory_service.py`, old `services/memory_governance_service.py`, old forwarding shells, and old `routers/memory.py` are removed after all live imports are updated.

**Tech Stack:** Python, FastAPI, SQLAlchemy async sessions, LangChain document wrappers, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create or replace:

- `app/mneme/domains/memory/service.py`: memory library builders and memory entry extraction/rebuild orchestration, moved from `services/memory_service.py`.
- `app/mneme/domains/memory/governance.py`: canonical memory and relation governance, moved from `services/memory_governance_service.py`.
- `app/mneme/domains/memory/router.py`: real `/memory` router, moved from `routers/memory.py`.
- `tests/test_memory_domain_convergence.py`: convergence tests for module ownership and route stability.

Modify:

- `app/mneme/bootstrap/router_registry.py`
- `app/mneme/domains/documents/pipeline.py`
- `app/mneme/pipelines/memory_extract_pipeline.py`
- `app/mneme/pipelines/advice_pipeline.py`
- `app/mneme/pipelines/analysis_pipeline.py`
- `app/mneme/pipelines/companion_pipeline.py`
- `app/mneme/services/insight_service.py`
- `app/mneme/services/profile_tool_service.py`
- `scripts/debug_day13.py`

Delete after imports are updated:

- `app/mneme/routers/memory.py`
- `app/mneme/services/memory_service.py`
- `app/mneme/services/memory_governance_service.py`
- `app/mneme/domains/memory/entries.py`
- `app/mneme/domains/memory/canonical.py`

## Task 1: Add Failing Memory Convergence Tests

**Files:**
- Create: `tests/test_memory_domain_convergence.py`

- [x] **Step 1: Create convergence test file**

Create `tests/test_memory_domain_convergence.py`:

```python
import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class MemoryDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_memory_domain_router(self):
        legacy_memory_router = ".".join(("app", "mneme", "routers", "memory"))

        self.assertIn("app.mneme.domains.memory.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_memory_router, ROUTER_MODULE_NAMES)

    def test_memory_domain_modules_are_canonical(self):
        from app.mneme.domains.memory.governance import build_memory_governance_view
        from app.mneme.domains.memory.service import build_memory_library

        self.assertEqual(build_memory_library.__module__, "app.mneme.domains.memory.service")
        self.assertEqual(build_memory_governance_view.__module__, "app.mneme.domains.memory.governance")

    def test_memory_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/memory/knowledge-bases/{knowledge_base_id}/library", paths)
        self.assertIn("/memory/knowledge-bases/{knowledge_base_id}/governance", paths)
        self.assertIn("/memory/knowledge-bases/{knowledge_base_id}/rebuild", paths)
        self.assertIn("/memory/documents/{document_id}/library", paths)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify red state**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_memory_domain_convergence
```

Expected:

```text
FAIL: test_router_registry_uses_memory_domain_router
```

or:

```text
ModuleNotFoundError
```

At least one failure must prove memory convergence is incomplete.

## Task 2: Move Memory Domain Modules

**Files:**
- Create: `app/mneme/domains/memory/service.py`
- Replace: `app/mneme/domains/memory/governance.py`
- Create: `app/mneme/domains/memory/router.py`

- [x] **Step 1: Move memory service**

Copy `app/mneme/services/memory_service.py` into `app/mneme/domains/memory/service.py`.

- [x] **Step 2: Move memory governance**

Replace `app/mneme/domains/memory/governance.py` with the complete contents of `app/mneme/services/memory_governance_service.py`.

- [x] **Step 3: Move memory router**

Copy `app/mneme/routers/memory.py` into `app/mneme/domains/memory/router.py`.

In `app/mneme/domains/memory/router.py`, replace:

```python
from app.mneme.services.memory_governance_service import build_memory_governance_view
from app.mneme.services.memory_service import build_memory_library, rebuild_memory_entries_for_knowledge_base
```

With:

```python
from app.mneme.domains.memory.governance import build_memory_governance_view
from app.mneme.domains.memory.service import build_memory_library, rebuild_memory_entries_for_knowledge_base
```

- [x] **Step 4: Run memory import smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.memory.governance import build_memory_governance_view; from app.mneme.domains.memory.service import build_memory_library, rebuild_memory_entries_for_knowledge_base; from app.mneme.domains.memory.router import router; print('memory domain imports ok')"
```

Expected:

```text
memory domain imports ok
```

## Task 3: Update Router Registry and Callers

**Files:**
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/domains/documents/pipeline.py`
- Modify: `app/mneme/pipelines/memory_extract_pipeline.py`
- Modify: `app/mneme/pipelines/advice_pipeline.py`
- Modify: `app/mneme/pipelines/analysis_pipeline.py`
- Modify: `app/mneme/pipelines/companion_pipeline.py`
- Modify: `app/mneme/services/insight_service.py`
- Modify: `app/mneme/services/profile_tool_service.py`
- Modify: `scripts/debug_day13.py`

- [x] **Step 1: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.memory",
```

With:

```python
"app.mneme.domains.memory.router",
```

- [x] **Step 2: Update memory service imports**

Replace:

```python
from app.mneme.services.memory_service import
```

With:

```python
from app.mneme.domains.memory.service import
```

in:

```text
app/mneme/domains/documents/pipeline.py
app/mneme/pipelines/memory_extract_pipeline.py
app/mneme/pipelines/advice_pipeline.py
app/mneme/pipelines/analysis_pipeline.py
app/mneme/pipelines/companion_pipeline.py
app/mneme/services/insight_service.py
```

- [x] **Step 3: Update memory governance imports**

Replace:

```python
from app.mneme.services.memory_governance_service import
```

With:

```python
from app.mneme.domains.memory.governance import
```

in:

```text
app/mneme/services/profile_tool_service.py
scripts/debug_day13.py
```

- [x] **Step 4: Run live import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.(memory_service|memory_governance_service)|app\.mneme\.routers\.memory|from app\.mneme\.routers\.memory|from app\.mneme\.domains\.memory\.(entries|canonical) import" app tests scripts scripts2
```

Expected remaining matches:

- Only old memory service files, old memory router, and old `entries.py`/`canonical.py` forwarding shells before deletion.

## Task 4: Delete Legacy Memory Files

**Files:**
- Delete: `app/mneme/routers/memory.py`
- Delete: `app/mneme/services/memory_service.py`
- Delete: `app/mneme/services/memory_governance_service.py`
- Delete: `app/mneme/domains/memory/entries.py`
- Delete: `app/mneme/domains/memory/canonical.py`

- [x] **Step 1: Confirm no live imports point to legacy memory files**

Run:

```powershell
rg -n "from app\.mneme\.services\.(memory_service|memory_governance_service)|app\.mneme\.routers\.memory|from app\.mneme\.routers\.memory|from app\.mneme\.domains\.memory\.(entries|canonical) import" app tests scripts scripts2
```

Expected matches must be limited to the exact files listed for deletion.

- [x] **Step 2: Delete legacy memory files**

Delete:

```text
app/mneme/routers/memory.py
app/mneme/services/memory_service.py
app/mneme/services/memory_governance_service.py
app/mneme/domains/memory/entries.py
app/mneme/domains/memory/canonical.py
```

- [x] **Step 3: Confirm files are gone**

Run:

```powershell
Test-Path app\mneme\routers\memory.py; Test-Path app\mneme\services\memory_service.py; Test-Path app\mneme\services\memory_governance_service.py; Test-Path app\mneme\domains\memory\entries.py; Test-Path app\mneme\domains\memory\canonical.py
```

Expected:

```text
False
False
False
False
False
```

## Task 5: Full Phase Verification

**Files:**
- No source changes unless verification reveals an issue.

- [x] **Step 1: Run memory convergence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_memory_domain_convergence
```

Expected:

```text
OK
```

- [x] **Step 2: Run regression tests from completed convergence phases**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_memory_domain_convergence tests.test_graph_domain_convergence tests.test_graph_rag_service tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [x] **Step 3: Run route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/memory/knowledge-bases/{knowledge_base_id}/library' in paths; assert '/memory/knowledge-bases/{knowledge_base_id}/governance' in paths; assert '/memory/documents/{document_id}/library' in paths; assert '/graph' in paths; assert '/kb/documents/upload' in paths; assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [x] **Step 4: Run legacy memory import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.(memory_service|memory_governance_service)|app\.mneme\.routers\.memory|from app\.mneme\.routers\.memory|from app\.mneme\.domains\.memory\.(entries|canonical) import" app tests scripts scripts2
```

Expected:

```text
```

No matches.

- [x] **Step 5: Run wildcard forwarding scan**

Run:

```powershell
rg -n "from app\.mneme\.services\..* import \*" app\mneme\domains\memory
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

## Task 6: Commit Phase 4A

**Files:**
- All files changed by Tasks 1-5.

- [x] **Step 1: Stage only Phase 4A files**

Run:

```powershell
git add app\mneme\domains\memory app\mneme\bootstrap\router_registry.py app\mneme\domains\documents\pipeline.py app\mneme\pipelines\memory_extract_pipeline.py app\mneme\pipelines\advice_pipeline.py app\mneme\pipelines\analysis_pipeline.py app\mneme\pipelines\companion_pipeline.py app\mneme\services\insight_service.py app\mneme\services\profile_tool_service.py tests\test_memory_domain_convergence.py scripts\debug_day13.py docs\superpowers\plans\2026-07-07-memory-domain-convergence.md
git add -u app\mneme\routers\memory.py app\mneme\services\memory_service.py app\mneme\services\memory_governance_service.py app\mneme\domains\memory\entries.py app\mneme\domains\memory\canonical.py
```

- [x] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge memory domain"
```

Expected:

```text
refactor: converge memory domain
```

## Self-Review

- Spec coverage: This plan implements the memory part of Phase 4. It does not migrate profile, analysis, advice, or companion ownership beyond updating their imports to the canonical memory domain.
- Completion-marker scan: The plan contains no unfinished implementation markers.
- Type consistency: The target module paths are consistently `app.mneme.domains.memory.service`, `governance`, and `router`.
