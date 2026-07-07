# Advice Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move advice routing and growth-advice generation into `app/mneme/domains/advice/` without changing public API paths or advice behavior.

**Architecture:** This is a behavior-preserving migration. `domains/advice/` becomes the canonical advice boundary while profile insight and advice pipeline callers import advice generation from the domain. Old advice service/router files are deleted after all live imports are updated.

**Tech Stack:** Python, FastAPI, LangChain output parser, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create:

- `app/mneme/domains/advice/__init__.py`: advice domain package marker.
- `app/mneme/domains/advice/service.py`: growth-advice generation, moved from `services/advice_service.py`.
- `app/mneme/domains/advice/router.py`: real `/advice` router, moved from `routers/advice.py`.
- `tests/test_advice_domain_convergence.py`: convergence tests for module ownership and route stability.

Modify:

- `app/mneme/bootstrap/router_registry.py`
- `app/mneme/domains/profile/insight.py`
- `app/mneme/pipelines/advice_pipeline.py`
- `scripts/day13_debug.py`

Delete after imports are updated:

- `app/mneme/routers/advice.py`
- `app/mneme/services/advice_service.py`

## Task 1: Add Failing Advice Convergence Tests

**Files:**
- Create: `tests/test_advice_domain_convergence.py`

- [x] **Step 1: Create convergence test file**

Create `tests/test_advice_domain_convergence.py`:

```python
import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class AdviceDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_advice_domain_router(self):
        legacy_advice_router = ".".join(("app", "mneme", "routers", "advice"))

        self.assertIn("app.mneme.domains.advice.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_advice_router, ROUTER_MODULE_NAMES)

    def test_advice_domain_service_is_canonical(self):
        from app.mneme.domains.advice.service import build_growth_advice

        self.assertEqual(build_growth_advice.__module__, "app.mneme.domains.advice.service")

    def test_advice_router_keeps_public_path(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/advice/knowledge-bases/{knowledge_base_id}", paths)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify red state**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_advice_domain_convergence
```

Expected:

```text
FAIL: test_router_registry_uses_advice_domain_router
```

or:

```text
ModuleNotFoundError
```

At least one failure must prove advice convergence is incomplete.

## Task 2: Move Advice Domain Modules

**Files:**
- Create: `app/mneme/domains/advice/__init__.py`
- Create: `app/mneme/domains/advice/service.py`
- Create: `app/mneme/domains/advice/router.py`

- [x] **Step 1: Create advice domain package**

Create `app/mneme/domains/advice/__init__.py`:

```python
"""Advice domain."""
```

- [x] **Step 2: Move advice service**

Copy `app/mneme/services/advice_service.py` into `app/mneme/domains/advice/service.py`.

- [x] **Step 3: Move advice router**

Copy `app/mneme/routers/advice.py` into `app/mneme/domains/advice/router.py`.

The router already imports profile orchestration from:

```python
from app.mneme.domains.profile.insight import build_advice_for_knowledge_base
```

Keep that import unchanged.

- [x] **Step 4: Run advice import smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.advice.service import build_growth_advice; from app.mneme.domains.advice.router import router; print('advice domain imports ok')"
```

Expected:

```text
advice domain imports ok
```

## Task 3: Update Router Registry and Callers

**Files:**
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/domains/profile/insight.py`
- Modify: `app/mneme/pipelines/advice_pipeline.py`
- Modify: `scripts/day13_debug.py`

- [x] **Step 1: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.advice",
```

With:

```python
"app.mneme.domains.advice.router",
```

- [x] **Step 2: Update advice service imports**

Replace:

```python
from app.mneme.services.advice_service import
```

With:

```python
from app.mneme.domains.advice.service import
```

in:

```text
app/mneme/domains/profile/insight.py
app/mneme/pipelines/advice_pipeline.py
scripts/day13_debug.py
```

- [x] **Step 3: Run live import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.advice_service|app\.mneme\.routers\.advice|from app\.mneme\.routers\.advice" app tests scripts scripts2
```

Expected remaining matches:

- Only old advice service file and old advice router before deletion.

## Task 4: Delete Legacy Advice Files

**Files:**
- Delete: `app/mneme/routers/advice.py`
- Delete: `app/mneme/services/advice_service.py`

- [x] **Step 1: Confirm no live imports point to legacy advice files**

Run:

```powershell
rg -n "from app\.mneme\.services\.advice_service|app\.mneme\.routers\.advice|from app\.mneme\.routers\.advice" app tests scripts scripts2
```

Expected matches must be limited to the exact files listed for deletion.

- [x] **Step 2: Delete legacy advice files**

Delete:

```text
app/mneme/routers/advice.py
app/mneme/services/advice_service.py
```

- [x] **Step 3: Confirm files are gone**

Run:

```powershell
Test-Path app\mneme\routers\advice.py; Test-Path app\mneme\services\advice_service.py
```

Expected:

```text
False
False
```

## Task 5: Full Phase Verification

**Files:**
- No source changes unless verification reveals an issue.

- [x] **Step 1: Run advice convergence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_advice_domain_convergence
```

Expected:

```text
OK
```

- [x] **Step 2: Run regression tests from completed convergence phases**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_advice_domain_convergence tests.test_profile_domain_convergence tests.test_memory_domain_convergence tests.test_graph_domain_convergence tests.test_graph_rag_service tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [x] **Step 3: Run route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/advice/knowledge-bases/{knowledge_base_id}' in paths; assert '/profile/knowledge-bases/{knowledge_base_id}' in paths; assert '/memory/knowledge-bases/{knowledge_base_id}/library' in paths; assert '/graph' in paths; assert '/kb/documents/upload' in paths; assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [x] **Step 4: Run legacy advice import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.advice_service|app\.mneme\.routers\.advice|from app\.mneme\.routers\.advice" app tests scripts scripts2
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

## Task 6: Commit Phase 4C

**Files:**
- All files changed by Tasks 1-5.

- [x] **Step 1: Stage only Phase 4C files**

Run:

```powershell
git add app\mneme\domains\advice app\mneme\bootstrap\router_registry.py app\mneme\domains\profile\insight.py app\mneme\pipelines\advice_pipeline.py tests\test_advice_domain_convergence.py scripts\day13_debug.py docs\superpowers\plans\2026-07-07-advice-domain-convergence.md
git add -u app\mneme\routers\advice.py app\mneme\services\advice_service.py
```

- [x] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge advice domain"
```

Expected:

```text
refactor: converge advice domain
```

## Self-Review

- Spec coverage: This plan implements the advice part of Phase 4. It does not migrate analysis, companion, or growth service ownership.
- Completion-marker scan: The plan contains no unfinished implementation markers.
- Type consistency: The target module paths are consistently `app.mneme.domains.advice.service` and `router`.
