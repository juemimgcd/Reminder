# Final Backend Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining old backend `routers/`, `services/`, and `workflow/` compatibility surface by moving the last modules into domain-owned locations.

**Architecture:** This is a behavior-preserving final convergence pass. Public API paths stay unchanged, Celery task names stay unchanged, and old Python import paths are deleted once every live caller points at `domains/*`.

**Tech Stack:** Python, FastAPI, SQLAlchemy async sessions, Celery task modules, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create or replace:

- `app/mneme/domains/health/router.py`, `app/mneme/domains/health/readiness.py`
- `app/mneme/domains/auth/router.py`
- `app/mneme/domains/users/router.py`
- `app/mneme/domains/documents/service.py`, `app/mneme/domains/documents/resources.py`
- `app/mneme/domains/analysis/router.py`, `app/mneme/domains/analysis/service.py`, `app/mneme/domains/analysis/growth.py`
- `app/mneme/domains/eval/service.py`
- `app/mneme/domains/retrieval/citation_validation.py`
- `app/mneme/domains/tasks/router.py`, `app/mneme/domains/tasks/state.py`, `app/mneme/domains/tasks/admin.py`, `app/mneme/domains/tasks/outbox.py`
- `tests/test_final_backend_convergence.py`

Modify:

- `app/mneme/bootstrap/router_registry.py`
- Live callers under `app/`, `scripts/`, `scripts2/`, and relevant tests that import remaining old services.

Delete:

- All remaining files under `app/mneme/routers/` except `__init__.py` if kept as an empty package marker.
- All remaining business files under `app/mneme/services/`.
- All forwarding files under `app/mneme/workflow/`.
- Old eval forwarding shells under `app/mneme/domains/eval/`.

## Tasks

- [x] **Step 1: Add failing final convergence test**

Create `tests/test_final_backend_convergence.py` with registry, route, canonical module, and old-file assertions.

- [x] **Step 2: Run final convergence test red**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_final_backend_convergence
```

Expected: failure proving remaining old modules are still wired.

- [x] **Step 3: Move remaining modules into domains**

Copy existing implementation files into their target domain modules and adjust intra-domain imports.

- [x] **Step 4: Update all live callers**

Replace `app.mneme.services.*`, `app.mneme.routers.*`, and `app.mneme.workflow.*` imports with canonical domain imports.

- [x] **Step 5: Delete old files**

Delete migrated service/router files and workflow forwarding shells after import scans are clean.

- [x] **Step 6: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_final_backend_convergence tests.test_companion_domain_convergence tests.test_advice_domain_convergence tests.test_profile_domain_convergence tests.test_memory_domain_convergence tests.test_graph_domain_convergence tests.test_graph_rag_service tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
.\.venv\Scripts\python.exe -m unittest tests.test_eval_service tests.test_citation_validation_service
.\.venv\Scripts\python.exe -c "from app.mneme.main import app; paths={route.path for route in app.routes}; required=['/health','/health/neo4j','/health/readiness','/auth/register','/auth/login','/auth/me','/users/{user_id}/knowledge-bases','/analysis/knowledge-bases/{knowledge_base_id}/growth','/analysis/knowledge-bases/{knowledge_base_id}/analytics','/tasks/{task_id}','/companion/knowledge-bases/{knowledge_base_id}/reply','/advice/knowledge-bases/{knowledge_base_id}','/profile/knowledge-bases/{knowledge_base_id}','/memory/knowledge-bases/{knowledge_base_id}/library','/graph','/kb/documents/upload','/kb/chat/query']; missing=[item for item in required if item not in paths]; assert not missing, missing; print('route smoke ok')"
rg -n "from app\.mneme\.services\.|app\.mneme\.routers\.|from app\.mneme\.routers\.|from app\.mneme\.workflow\.|app\.mneme\.workflow\." app tests scripts scripts2
rg -n "from app\.mneme\.(services|infra|tasks)\..* import \*" app\mneme\domains app\mneme\workflow
git diff --check
```

Expected: tests pass, route smoke passes, no old import hits, no wildcard forwarding hits, and no diff-check errors.

- [x] **Step 7: Commit**

Run:

```powershell
git add app tests scripts scripts2 docs/superpowers/plans/2026-07-07-final-backend-convergence.md
git commit -m "refactor: finish backend domain convergence"
```

## Self-Review

- Spec coverage: This plan covers the remaining routers, services, eval shells, and workflow forwarding shells.
- Completion-marker scan: No unfinished implementation markers remain in this plan.
- Type consistency: Canonical module paths consistently use `app.mneme.domains.*`.
