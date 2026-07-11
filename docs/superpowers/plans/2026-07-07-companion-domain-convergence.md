# Companion Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move companion routing and companion response generation into `app/mneme/domains/companion/` without changing public API paths or companion behavior.

**Architecture:** This is a behavior-preserving migration. `domains/companion/` becomes the canonical companion boundary while companion pipeline and debug callers import response generation from the domain. Old companion service/router files are deleted after all live imports are updated.

**Tech Stack:** Python, FastAPI, LangChain output parser, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create:

- `app/mneme/domains/companion/__init__.py`: companion domain package marker.
- `app/mneme/domains/companion/service.py`: companion response generation, moved from `services/companion_service.py`.
- `app/mneme/domains/companion/router.py`: real `/companion` router, moved from `routers/companion.py`.
- `tests/test_companion_domain_convergence.py`: convergence tests for module ownership and route stability.

Modify:

- `app/mneme/bootstrap/router_registry.py`
- `app/mneme/pipelines/companion_pipeline.py`
- `scripts/day12_debug.py`

Delete after imports are updated:

- `app/mneme/routers/companion.py`
- `app/mneme/services/companion_service.py`

## Task 1: Add Failing Companion Convergence Tests

**Files:**
- Create: `tests/test_companion_domain_convergence.py`

- [x] **Step 1: Create convergence test file**

Create `tests/test_companion_domain_convergence.py`:

```python
import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class CompanionDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_companion_domain_router(self):
        legacy_companion_router = ".".join(("app", "mneme", "routers", "companion"))

        self.assertIn("app.mneme.domains.companion.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_companion_router, ROUTER_MODULE_NAMES)

    def test_companion_domain_service_is_canonical(self):
        from app.mneme.domains.companion.service import build_companion_response

        self.assertEqual(build_companion_response.__module__, "app.mneme.domains.companion.service")

    def test_companion_router_keeps_public_path(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/companion/knowledge-bases/{knowledge_base_id}/reply", paths)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify red state**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_companion_domain_convergence
```

Expected:

```text
FAIL: test_router_registry_uses_companion_domain_router
```

or:

```text
ModuleNotFoundError
```

At least one failure must prove companion convergence is incomplete.

## Task 2: Move Companion Domain Modules

**Files:**
- Create: `app/mneme/domains/companion/__init__.py`
- Create: `app/mneme/domains/companion/service.py`
- Create: `app/mneme/domains/companion/router.py`

- [x] **Step 1: Create companion domain package**

Create `app/mneme/domains/companion/__init__.py`:

```python
"""Companion domain."""
```

- [x] **Step 2: Move companion service**

Copy `app/mneme/services/companion_service.py` into `app/mneme/domains/companion/service.py`.

- [x] **Step 3: Move companion router**

Copy `app/mneme/routers/companion.py` into `app/mneme/domains/companion/router.py`.

In `app/mneme/domains/companion/router.py`, replace:

```python
from app.mneme.services.companion_service import build_companion_response
```

With:

```python
from app.mneme.domains.companion.service import build_companion_response
```

- [x] **Step 4: Run companion import smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.companion.service import build_companion_response; from app.mneme.domains.companion.router import router; print('companion domain imports ok')"
```

Expected:

```text
companion domain imports ok
```

## Task 3: Update Router Registry and Callers

**Files:**
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/pipelines/companion_pipeline.py`
- Modify: `scripts/day12_debug.py`

- [x] **Step 1: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.companion",
```

With:

```python
"app.mneme.domains.companion.router",
```

- [x] **Step 2: Update companion service imports**

Replace:

```python
from app.mneme.services.companion_service import
```

With:

```python
from app.mneme.domains.companion.service import
```

in:

```text
app/mneme/pipelines/companion_pipeline.py
scripts/day12_debug.py
```

- [x] **Step 3: Run live import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.companion_service|app\.mneme\.routers\.companion|from app\.mneme\.routers\.companion" app tests scripts scripts2
```

Expected remaining matches:

- Only old companion service file and old companion router before deletion.

## Task 4: Delete Legacy Companion Files

**Files:**
- Delete: `app/mneme/routers/companion.py`
- Delete: `app/mneme/services/companion_service.py`

- [x] **Step 1: Confirm no live imports point to legacy companion files**

Run:

```powershell
rg -n "from app\.mneme\.services\.companion_service|app\.mneme\.routers\.companion|from app\.mneme\.routers\.companion" app tests scripts scripts2
```

Expected matches must be limited to the exact files listed for deletion.

- [x] **Step 2: Delete legacy companion files**

Delete:

```text
app/mneme/routers/companion.py
app/mneme/services/companion_service.py
```

- [x] **Step 3: Confirm files are gone**

Run:

```powershell
Test-Path app\mneme\routers\companion.py; Test-Path app\mneme\services\companion_service.py
```

Expected:

```text
False
False
```

## Task 5: Full Phase Verification

**Files:**
- No source changes unless verification reveals an issue.

- [x] **Step 1: Run companion convergence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_companion_domain_convergence
```

Expected:

```text
OK
```

- [x] **Step 2: Run regression tests from completed convergence phases**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_companion_domain_convergence tests.test_advice_domain_convergence tests.test_profile_domain_convergence tests.test_memory_domain_convergence tests.test_graph_domain_convergence tests.test_graph_rag_service tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [x] **Step 3: Run route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/companion/knowledge-bases/{knowledge_base_id}/reply' in paths; assert '/advice/knowledge-bases/{knowledge_base_id}' in paths; assert '/profile/knowledge-bases/{knowledge_base_id}' in paths; assert '/memory/knowledge-bases/{knowledge_base_id}/library' in paths; assert '/graph' in paths; assert '/kb/documents/upload' in paths; assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [x] **Step 4: Run legacy companion import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.companion_service|app\.mneme\.routers\.companion|from app\.mneme\.routers\.companion" app tests scripts scripts2
```

Expected:

```text
```

No matches.

- [x] **Step 5: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected:

```text
```

No errors.

## Task 6: Commit Phase 4D

**Files:**
- All files changed by Tasks 1-5.

- [x] **Step 1: Stage only Phase 4D files**

Run:

```powershell
git add app\mneme\domains\companion app\mneme\bootstrap\router_registry.py app\mneme\pipelines\companion_pipeline.py tests\test_companion_domain_convergence.py scripts\day12_debug.py docs\superpowers\plans\2026-07-07-companion-domain-convergence.md
git add -u app\mneme\routers\companion.py app\mneme\services\companion_service.py
```

- [x] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge companion domain"
```

Expected:

```text
refactor: converge companion domain
```

## Self-Review

- Spec coverage: This plan implements the companion part of Phase 4. It does not migrate analysis, growth service, tasks, outbox, or workflow ownership.
- Completion-marker scan: The plan contains no unfinished implementation markers.
- Type consistency: The target module paths are consistently `app.mneme.domains.companion.service` and `router`.
