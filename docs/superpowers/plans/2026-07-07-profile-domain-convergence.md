# Profile Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move profile routing, profile LLM generation, evidence-profile tooling, and insight orchestration into `app/mneme/domains/profile/` without changing public API paths or insight behavior.

**Architecture:** This is a behavior-preserving migration. `domains/profile/` becomes the canonical profile/insight boundary; advice, analysis, companion, and retrieval callers use the profile domain orchestration entry points. Old profile service files and forwarding shells are deleted after imports are updated.

**Tech Stack:** Python, FastAPI, SQLAlchemy async sessions, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create or replace:

- `app/mneme/domains/profile/service.py`: profile LLM generation, moved from `services/profile_service.py`.
- `app/mneme/domains/profile/tools.py`: evidence profile tooling, replacing the current forwarding shell.
- `app/mneme/domains/profile/insight.py`: profile/growth/advice orchestration, replacing the current `react_pipeline.py` forwarding shell intent.
- `app/mneme/domains/profile/router.py`: real `/profile` router, moved from `routers/profile.py`.
- `tests/test_profile_domain_convergence.py`: convergence tests for module ownership and route stability.

Modify:

- `app/mneme/bootstrap/router_registry.py`
- `app/mneme/domains/retrieval/query_service.py`
- `app/mneme/routers/advice.py`
- `app/mneme/routers/analysis.py`
- `app/mneme/routers/companion.py`
- `app/mneme/pipelines/advice_pipeline.py`
- `app/mneme/pipelines/analysis_pipeline.py`
- `app/mneme/pipelines/companion_pipeline.py`
- `scripts/day10_debug.py`
- `scripts/day11_debug.py`
- `scripts/debug_day14.py`

Delete after imports are updated:

- `app/mneme/routers/profile.py`
- `app/mneme/services/profile_service.py`
- `app/mneme/services/profile_tool_service.py`
- `app/mneme/services/insight_service.py`
- `app/mneme/domains/profile/snapshot.py`
- `app/mneme/domains/profile/react_pipeline.py`

## Task 1: Add Failing Profile Convergence Tests

**Files:**
- Create: `tests/test_profile_domain_convergence.py`

- [x] **Step 1: Create convergence test file**

Create `tests/test_profile_domain_convergence.py`:

```python
import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class ProfileDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_profile_domain_router(self):
        legacy_profile_router = ".".join(("app", "mneme", "routers", "profile"))

        self.assertIn("app.mneme.domains.profile.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_profile_router, ROUTER_MODULE_NAMES)

    def test_profile_domain_modules_are_canonical(self):
        from app.mneme.domains.profile.insight import build_profile_for_knowledge_base
        from app.mneme.domains.profile.service import build_personal_profile
        from app.mneme.domains.profile.tools import build_evidence_profile_from_entries

        self.assertEqual(build_personal_profile.__module__, "app.mneme.domains.profile.service")
        self.assertEqual(build_evidence_profile_from_entries.__module__, "app.mneme.domains.profile.tools")
        self.assertEqual(build_profile_for_knowledge_base.__module__, "app.mneme.domains.profile.insight")

    def test_profile_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/profile/knowledge-bases/{knowledge_base_id}", paths)
        self.assertIn("/profile/knowledge-bases/{knowledge_base_id}/evidence", paths)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run tests to verify red state**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_domain_convergence
```

Expected:

```text
FAIL: test_router_registry_uses_profile_domain_router
```

or:

```text
ModuleNotFoundError
```

At least one failure must prove profile convergence is incomplete.

## Task 2: Move Profile Domain Modules

**Files:**
- Create: `app/mneme/domains/profile/service.py`
- Replace: `app/mneme/domains/profile/tools.py`
- Create: `app/mneme/domains/profile/insight.py`
- Create: `app/mneme/domains/profile/router.py`

- [x] **Step 1: Move profile service**

Copy `app/mneme/services/profile_service.py` into `app/mneme/domains/profile/service.py`.

- [x] **Step 2: Move profile tools**

Replace `app/mneme/domains/profile/tools.py` with the complete contents of `app/mneme/services/profile_tool_service.py`.

- [x] **Step 3: Move insight orchestration**

Copy `app/mneme/services/insight_service.py` into `app/mneme/domains/profile/insight.py`.

In `app/mneme/domains/profile/insight.py`, replace:

```python
from app.mneme.services.profile_service import build_personal_profile
from app.mneme.services.profile_tool_service import build_evidence_profile_from_entries
```

With:

```python
from app.mneme.domains.profile.service import build_personal_profile
from app.mneme.domains.profile.tools import build_evidence_profile_from_entries
```

- [x] **Step 4: Move profile router**

Copy `app/mneme/routers/profile.py` into `app/mneme/domains/profile/router.py`.

In `app/mneme/domains/profile/router.py`, replace:

```python
from app.mneme.services.insight_service import build_evidence_profile_for_knowledge_base, build_profile_for_knowledge_base
```

With:

```python
from app.mneme.domains.profile.insight import build_evidence_profile_for_knowledge_base, build_profile_for_knowledge_base
```

- [x] **Step 5: Run profile import smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.domains.profile.insight import build_profile_for_knowledge_base; from app.mneme.domains.profile.service import build_personal_profile; from app.mneme.domains.profile.tools import build_evidence_profile_from_entries; from app.mneme.domains.profile.router import router; print('profile domain imports ok')"
```

Expected:

```text
profile domain imports ok
```

## Task 3: Update Router Registry and Callers

**Files:**
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/domains/retrieval/query_service.py`
- Modify: `app/mneme/routers/advice.py`
- Modify: `app/mneme/routers/analysis.py`
- Modify: `app/mneme/routers/companion.py`
- Modify: `app/mneme/pipelines/advice_pipeline.py`
- Modify: `app/mneme/pipelines/analysis_pipeline.py`
- Modify: `app/mneme/pipelines/companion_pipeline.py`
- Modify: `scripts/day10_debug.py`
- Modify: `scripts/day11_debug.py`
- Modify: `scripts/debug_day14.py`

- [x] **Step 1: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.profile",
```

With:

```python
"app.mneme.domains.profile.router",
```

- [x] **Step 2: Update insight imports**

Replace:

```python
from app.mneme.services.insight_service import
```

With:

```python
from app.mneme.domains.profile.insight import
```

in:

```text
app/mneme/domains/retrieval/query_service.py
app/mneme/routers/advice.py
app/mneme/routers/analysis.py
app/mneme/routers/companion.py
```

- [x] **Step 3: Update profile service imports**

Replace:

```python
from app.mneme.services.profile_service import
```

With:

```python
from app.mneme.domains.profile.service import
```

in:

```text
app/mneme/pipelines/advice_pipeline.py
app/mneme/pipelines/analysis_pipeline.py
app/mneme/pipelines/companion_pipeline.py
scripts/day10_debug.py
scripts/day11_debug.py
```

- [x] **Step 4: Update profile tool imports**

Replace:

```python
from app.mneme.services.profile_tool_service import
```

With:

```python
from app.mneme.domains.profile.tools import
```

in:

```text
scripts/debug_day14.py
```

- [x] **Step 5: Run live import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.(profile_service|profile_tool_service|insight_service)|app\.mneme\.routers\.profile|from app\.mneme\.routers\.profile|from app\.mneme\.domains\.profile\.(snapshot|react_pipeline) import" app tests scripts scripts2
```

Expected remaining matches:

- Only old profile service files, old profile router, and old profile forwarding shells before deletion.

## Task 4: Delete Legacy Profile Files

**Files:**
- Delete: `app/mneme/routers/profile.py`
- Delete: `app/mneme/services/profile_service.py`
- Delete: `app/mneme/services/profile_tool_service.py`
- Delete: `app/mneme/services/insight_service.py`
- Delete: `app/mneme/domains/profile/snapshot.py`
- Delete: `app/mneme/domains/profile/react_pipeline.py`

- [x] **Step 1: Confirm no live imports point to legacy profile files**

Run:

```powershell
rg -n "from app\.mneme\.services\.(profile_service|profile_tool_service|insight_service)|app\.mneme\.routers\.profile|from app\.mneme\.routers\.profile|from app\.mneme\.domains\.profile\.(snapshot|react_pipeline) import" app tests scripts scripts2
```

Expected matches must be limited to the exact files listed for deletion.

- [x] **Step 2: Delete legacy profile files**

Delete:

```text
app/mneme/routers/profile.py
app/mneme/services/profile_service.py
app/mneme/services/profile_tool_service.py
app/mneme/services/insight_service.py
app/mneme/domains/profile/snapshot.py
app/mneme/domains/profile/react_pipeline.py
```

- [x] **Step 3: Confirm files are gone**

Run:

```powershell
Test-Path app\mneme\routers\profile.py; Test-Path app\mneme\services\profile_service.py; Test-Path app\mneme\services\profile_tool_service.py; Test-Path app\mneme\services\insight_service.py; Test-Path app\mneme\domains\profile\snapshot.py; Test-Path app\mneme\domains\profile\react_pipeline.py
```

Expected:

```text
False
False
False
False
False
False
```

## Task 5: Full Phase Verification

**Files:**
- No source changes unless verification reveals an issue.

- [x] **Step 1: Run profile convergence tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_domain_convergence
```

Expected:

```text
OK
```

- [x] **Step 2: Run regression tests from completed convergence phases**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_profile_domain_convergence tests.test_memory_domain_convergence tests.test_graph_domain_convergence tests.test_graph_rag_service tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [x] **Step 3: Run route smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; assert '/profile/knowledge-bases/{knowledge_base_id}' in paths; assert '/profile/knowledge-bases/{knowledge_base_id}/evidence' in paths; assert '/memory/knowledge-bases/{knowledge_base_id}/library' in paths; assert '/graph' in paths; assert '/kb/documents/upload' in paths; assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [x] **Step 4: Run legacy profile import scan**

Run:

```powershell
rg -n "from app\.mneme\.services\.(profile_service|profile_tool_service|insight_service)|app\.mneme\.routers\.profile|from app\.mneme\.routers\.profile|from app\.mneme\.domains\.profile\.(snapshot|react_pipeline) import" app tests scripts scripts2
```

Expected:

```text
```

No matches.

- [x] **Step 5: Run wildcard forwarding scan**

Run:

```powershell
rg -n "from app\.mneme\.services\..* import \*" app\mneme\domains\profile
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

## Task 6: Commit Phase 4B

**Files:**
- All files changed by Tasks 1-5.

- [x] **Step 1: Stage only Phase 4B files**

Run:

```powershell
git add app\mneme\domains\profile app\mneme\bootstrap\router_registry.py app\mneme\domains\retrieval\query_service.py app\mneme\routers\advice.py app\mneme\routers\analysis.py app\mneme\routers\companion.py app\mneme\pipelines\advice_pipeline.py app\mneme\pipelines\analysis_pipeline.py app\mneme\pipelines\companion_pipeline.py tests\test_profile_domain_convergence.py scripts\day10_debug.py scripts\day11_debug.py scripts\debug_day14.py docs\superpowers\plans\2026-07-07-profile-domain-convergence.md
git add -u app\mneme\routers\profile.py app\mneme\services\profile_service.py app\mneme\services\profile_tool_service.py app\mneme\services\insight_service.py app\mneme\domains\profile\snapshot.py app\mneme\domains\profile\react_pipeline.py
```

- [x] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge profile domain"
```

Expected:

```text
refactor: converge profile domain
```

## Self-Review

- Spec coverage: This plan implements the profile/insight part of Phase 4. It updates advice, analysis, companion, and retrieval imports to the canonical profile domain but does not migrate those routers/services yet.
- Completion-marker scan: The plan contains no unfinished implementation markers.
- Type consistency: The target module paths are consistently `app.mneme.domains.profile.service`, `tools`, `insight`, and `router`.
