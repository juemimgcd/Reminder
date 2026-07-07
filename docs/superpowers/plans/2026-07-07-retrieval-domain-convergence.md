# Retrieval Domain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the RAG/chat retrieval path from legacy `routers/` and `services/` modules into the real `domains/retrieval/` boundary without changing public API paths or response shapes.

**Architecture:** This is a behavior-preserving module migration. `domains/retrieval/` becomes the canonical home for query routing, context assembly, fusion, debug packets, RAG answer orchestration, and the `/kb/chat/query` router. Old retrieval service files and the old chat router are deleted after all imports point to the domain modules.

**Tech Stack:** Python, FastAPI, SQLAlchemy async sessions, LangChain, Pydantic v2, `unittest`, PowerShell.

---

## File Structure

Create or replace these domain files with real logic:

- `app/mneme/domains/retrieval/query_router.py`: query classification logic currently in `services/query_router_service.py`.
- `app/mneme/domains/retrieval/debug.py`: retrieval and answer debug packet builders currently in `services/retrieval_debug_service.py`.
- `app/mneme/domains/retrieval/fusion.py`: RRF fusion, heuristic rerank, and optional model rerank currently in `services/retrieval_fusion_service.py`.
- `app/mneme/domains/retrieval/context_service.py`: vector, keyword, and memory recall context assembly currently in `services/context_service.py`.
- `app/mneme/domains/retrieval/query_service.py`: RAG answer orchestration currently in `services/query_service.py`.
- `app/mneme/domains/retrieval/router.py`: `/kb/chat/query` FastAPI router currently in `routers/chat.py`.

Modify these existing files:

- `app/mneme/bootstrap/router_registry.py`: register `app.mneme.domains.retrieval.router` instead of `app.mneme.routers.chat`.
- `app/mneme/pipelines/companion_pipeline.py`: import `generate_rag_answer` from `domains/retrieval/query_service.py`.
- `app/mneme/routers/companion.py`: import `generate_rag_answer` from `domains/retrieval/query_service.py`.
- `tests/test_query_router_service.py`: import `route_query` from `domains/retrieval/query_router.py`.
- `tests/test_retrieval_debug_service.py`: import debug helpers from `domains/retrieval/debug.py`.
- `tests/test_retrieval_fusion_service.py`: import fusion helpers from `domains/retrieval/fusion.py` and patch `domains.retrieval.fusion.settings`.
- `scripts/debug_day6.py`: import retrieval context helper from `domains/retrieval/context_service.py`.
- `scripts/debug_day7.py`: import query router helper from `domains/retrieval/query_router.py`.
- `scripts/debug_day9.py`: import fusion helper from `domains/retrieval/fusion.py`.
- `scripts/debug_day10.py`: import query router, debug, and fusion helpers from `domains/retrieval/*`.
- `scripts2/debug_day9.py`: import context builder from `domains/retrieval/context_service.py`.
- `scripts2/debug_day13_harness.py`: import context helpers from `domains/retrieval/context_service.py`.
- `scripts2/debug_day14_advanced_harness.py`: import context builder from `domains/retrieval/context_service.py`.

Delete these files after all imports are updated and tests pass:

- `app/mneme/services/query_router_service.py`
- `app/mneme/services/retrieval_debug_service.py`
- `app/mneme/services/retrieval_fusion_service.py`
- `app/mneme/services/context_service.py`
- `app/mneme/services/query_service.py`
- `app/mneme/routers/chat.py`

Also delete obsolete forwarding shells in `domains/retrieval/` if they are no longer part of the target shape:

- `app/mneme/domains/retrieval/context_assembly.py`
- `app/mneme/domains/retrieval/rerank.py`

Keep:

- `app/mneme/domains/retrieval/__init__.py`

## Task 1: Add Domain Import Tests

**Files:**
- Modify: `tests/test_query_router_service.py`
- Modify: `tests/test_retrieval_debug_service.py`
- Modify: `tests/test_retrieval_fusion_service.py`

- [ ] **Step 1: Update query router test import to the target domain path**

Replace:

```python
from app.mneme.services.query_router_service import route_query
```

With:

```python
from app.mneme.domains.retrieval.query_router import route_query
```

- [ ] **Step 2: Update retrieval debug test import to the target domain path**

Replace:

```python
from app.mneme.services.retrieval_debug_service import (
    build_answer_debug,
    build_non_retrieval_debug,
    preview_text,
)
```

With:

```python
from app.mneme.domains.retrieval.debug import (
    build_answer_debug,
    build_non_retrieval_debug,
    preview_text,
)
```

- [ ] **Step 3: Update retrieval fusion test import and patch path**

Replace:

```python
from app.mneme.services.retrieval_fusion_service import (
    fuse_and_rerank_context_items,
    fuse_context_items_by_rrf,
    rerank_context_items,
)
```

With:

```python
from app.mneme.domains.retrieval.fusion import (
    fuse_and_rerank_context_items,
    fuse_context_items_by_rrf,
    rerank_context_items,
)
```

Replace:

```python
with patch("app.mneme.services.retrieval_fusion_service.settings.RERANKER_ENABLED", False):
```

With:

```python
with patch("app.mneme.domains.retrieval.fusion.settings.RERANKER_ENABLED", False):
```

- [ ] **Step 4: Run tests to verify they fail before implementation**

Run:

```powershell
python -m unittest tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
ModuleNotFoundError: No module named 'app.mneme.domains.retrieval.query_router'
```

or equivalent missing-domain-module failures.

## Task 2: Move Query Router and Debug Helpers

**Files:**
- Create: `app/mneme/domains/retrieval/query_router.py`
- Create: `app/mneme/domains/retrieval/debug.py`
- Delete later: `app/mneme/services/query_router_service.py`
- Delete later: `app/mneme/services/retrieval_debug_service.py`

- [ ] **Step 1: Create `query_router.py` with existing query routing logic**

Copy the complete contents of `app/mneme/services/query_router_service.py` into:

```text
app/mneme/domains/retrieval/query_router.py
```

The resulting file must define:

```python
def route_query(question: str) -> QueryRouteDecision:
    ...
```

and keep these constants:

```python
GENERAL_CHAT_PATTERNS
ACTION_PATTERNS
PROFILE_PATTERNS
ANALYSIS_PATTERNS
MEMORY_PATTERNS
```

- [ ] **Step 2: Create `debug.py` with existing retrieval debug logic**

Copy the complete contents of `app/mneme/services/retrieval_debug_service.py` into:

```text
app/mneme/domains/retrieval/debug.py
```

The resulting file must define:

```python
def preview_text(text: str, *, max_chars: int = 160) -> str:
    ...

def build_non_retrieval_debug(*, route: QueryRouteDecision, reason: str) -> dict[str, Any]:
    ...

def build_retrieval_debug_packet(...) -> dict[str, Any]:
    ...

def build_answer_debug(...) -> dict[str, Any]:
    ...
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m unittest tests.test_query_router_service tests.test_retrieval_debug_service
```

Expected:

```text
OK
```

## Task 3: Move Retrieval Fusion

**Files:**
- Replace: `app/mneme/domains/retrieval/fusion.py`
- Delete later: `app/mneme/services/retrieval_fusion_service.py`

- [ ] **Step 1: Replace forwarding shell with real fusion logic**

Replace the entire contents of `app/mneme/domains/retrieval/fusion.py`.

Current forwarding shell:

```python
from app.mneme.services.retrieval_fusion_service import *  # noqa: F401,F403
```

New file contents should be the complete current contents of:

```text
app/mneme/services/retrieval_fusion_service.py
```

The resulting file must define:

```python
def fuse_context_items_by_rrf(...) -> list[ContextItem]:
    ...

def rerank_context_items(...) -> list[ContextItem]:
    ...

async def fuse_and_rerank_context_items(...) -> list[ContextItem]:
    ...
```

- [ ] **Step 2: Run focused fusion test**

Run:

```powershell
python -m unittest tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

## Task 4: Move Context Assembly

**Files:**
- Create: `app/mneme/domains/retrieval/context_service.py`
- Delete later: `app/mneme/services/context_service.py`
- Delete later: `app/mneme/domains/retrieval/context_assembly.py`

- [ ] **Step 1: Create `context_service.py` with existing context logic**

Copy the complete contents of:

```text
app/mneme/services/context_service.py
```

into:

```text
app/mneme/domains/retrieval/context_service.py
```

- [ ] **Step 2: Update intra-domain imports in the new file**

In `app/mneme/domains/retrieval/context_service.py`, replace:

```python
from app.mneme.services.retrieval_debug_service import build_retrieval_debug_packet
from app.mneme.services.retrieval_fusion_service import fuse_and_rerank_context_items
```

With:

```python
from app.mneme.domains.retrieval.debug import build_retrieval_debug_packet
from app.mneme.domains.retrieval.fusion import fuse_and_rerank_context_items
```

- [ ] **Step 3: Add import smoke test through Python command**

Run:

```powershell
python -c "from app.mneme.domains.retrieval.context_service import build_query_context, retrieve_documents_with_scores; print('context import ok')"
```

Expected:

```text
context import ok
```

## Task 5: Move Query Service and Chat Router

**Files:**
- Create: `app/mneme/domains/retrieval/query_service.py`
- Replace: `app/mneme/domains/retrieval/router.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Delete later: `app/mneme/services/query_service.py`
- Delete later: `app/mneme/routers/chat.py`

- [ ] **Step 1: Create domain query service**

Copy the complete contents of:

```text
app/mneme/services/query_service.py
```

into:

```text
app/mneme/domains/retrieval/query_service.py
```

- [ ] **Step 2: Update intra-domain imports in query service**

In `app/mneme/domains/retrieval/query_service.py`, replace:

```python
from app.mneme.services.context_service import build_query_context
from app.mneme.services.query_router_service import route_query
from app.mneme.services.retrieval_debug_service import build_answer_debug, build_non_retrieval_debug
```

With:

```python
from app.mneme.domains.retrieval.context_service import build_query_context
from app.mneme.domains.retrieval.query_router import route_query
from app.mneme.domains.retrieval.debug import build_answer_debug, build_non_retrieval_debug
```

- [ ] **Step 3: Replace retrieval router forwarding shell with chat router logic**

Replace the entire contents of `app/mneme/domains/retrieval/router.py`.

Current forwarding shell:

```python
from app.mneme.services.query_router_service import *  # noqa: F401,F403
```

New file contents should be the complete current contents of:

```text
app/mneme/routers/chat.py
```

- [ ] **Step 4: Update router import to use the domain query service**

In `app/mneme/domains/retrieval/router.py`, replace:

```python
from app.mneme.services.query_service import generate_rag_answer
```

With:

```python
from app.mneme.domains.retrieval.query_service import generate_rag_answer
```

- [ ] **Step 5: Update router registry**

In `app/mneme/bootstrap/router_registry.py`, replace:

```python
"app.mneme.routers.chat",
```

With:

```python
"app.mneme.domains.retrieval.router",
```

- [ ] **Step 6: Run route smoke check**

Run:

```powershell
python -c "from app.mneme.main import app; paths = sorted(route.path for route in app.routes); assert '/kb/chat/query' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

## Task 6: Update Remaining Import Callers

**Files:**
- Modify: `app/mneme/pipelines/companion_pipeline.py`
- Modify: `app/mneme/routers/companion.py`
- Modify: `scripts/debug_day6.py`
- Modify: `scripts/debug_day7.py`
- Modify: `scripts/debug_day9.py`
- Modify: `scripts/debug_day10.py`
- Modify: `scripts2/debug_day9.py`
- Modify: `scripts2/debug_day13_harness.py`
- Modify: `scripts2/debug_day14_advanced_harness.py`

- [ ] **Step 1: Update companion pipeline import**

In `app/mneme/pipelines/companion_pipeline.py`, replace:

```python
from app.mneme.services.query_service import generate_rag_answer
```

With:

```python
from app.mneme.domains.retrieval.query_service import generate_rag_answer
```

- [ ] **Step 2: Update companion router import**

In `app/mneme/routers/companion.py`, replace:

```python
from app.mneme.services.query_service import generate_rag_answer
```

With:

```python
from app.mneme.domains.retrieval.query_service import generate_rag_answer
```

- [ ] **Step 3: Update debug script imports**

In `scripts/debug_day6.py`, replace:

```python
from app.mneme.services.context_service import retrieve_documents_with_scores
```

With:

```python
from app.mneme.domains.retrieval.context_service import retrieve_documents_with_scores
```

In `scripts/debug_day7.py`, replace:

```python
from app.mneme.services.query_router_service import route_query
```

With:

```python
from app.mneme.domains.retrieval.query_router import route_query
```

In `scripts/debug_day9.py`, replace:

```python
from app.mneme.services.retrieval_fusion_service import fuse_and_rerank_context_items
```

With:

```python
from app.mneme.domains.retrieval.fusion import fuse_and_rerank_context_items
```

In `scripts/debug_day10.py`, replace:

```python
from app.mneme.services.query_router_service import route_query
from app.mneme.services.retrieval_debug_service import build_answer_debug, build_retrieval_debug_packet
from app.mneme.services.retrieval_fusion_service import fuse_and_rerank_context_items
```

With:

```python
from app.mneme.domains.retrieval.query_router import route_query
from app.mneme.domains.retrieval.debug import build_answer_debug, build_retrieval_debug_packet
from app.mneme.domains.retrieval.fusion import fuse_and_rerank_context_items
```

- [ ] **Step 4: Update scripts2 debug harness imports**

In `scripts2/debug_day9.py`, replace:

```python
from app.mneme.services.context_service import build_query_context
```

With:

```python
from app.mneme.domains.retrieval.context_service import build_query_context
```

In `scripts2/debug_day13_harness.py`, replace:

```python
from app.mneme.services.context_service import (
```

With:

```python
from app.mneme.domains.retrieval.context_service import (
```

In `scripts2/debug_day14_advanced_harness.py`, replace:

```python
from app.mneme.services.context_service import build_query_context
```

With:

```python
from app.mneme.domains.retrieval.context_service import build_query_context
```

If `scripts2/debug_day14_advanced_harness.py` prints the old source file path, replace:

```python
print("context_budget_source=services/context_service.py")
```

With:

```python
print("context_budget_source=domains/retrieval/context_service.py")
```

- [ ] **Step 5: Verify no app/test/script imports still point to old retrieval services**

Run:

```powershell
rg -n "services\.(query_service|context_service|retrieval_fusion_service|retrieval_debug_service|query_router_service)|routers\.chat" app tests scripts scripts2
```

Expected:

```text
```

No matches.

## Task 7: Delete Legacy Retrieval Files

**Files:**
- Delete: `app/mneme/services/query_router_service.py`
- Delete: `app/mneme/services/retrieval_debug_service.py`
- Delete: `app/mneme/services/retrieval_fusion_service.py`
- Delete: `app/mneme/services/context_service.py`
- Delete: `app/mneme/services/query_service.py`
- Delete: `app/mneme/routers/chat.py`
- Delete: `app/mneme/domains/retrieval/context_assembly.py`
- Delete: `app/mneme/domains/retrieval/rerank.py`

- [ ] **Step 1: Confirm no old imports remain**

Run:

```powershell
rg -n "services\.(query_service|context_service|retrieval_fusion_service|retrieval_debug_service|query_router_service)|routers\.chat" app tests scripts scripts2
```

Expected:

```text
```

No matches.

- [ ] **Step 2: Delete old files**

Delete these files:

```text
app/mneme/services/query_router_service.py
app/mneme/services/retrieval_debug_service.py
app/mneme/services/retrieval_fusion_service.py
app/mneme/services/context_service.py
app/mneme/services/query_service.py
app/mneme/routers/chat.py
app/mneme/domains/retrieval/context_assembly.py
app/mneme/domains/retrieval/rerank.py
```

- [ ] **Step 3: Confirm forwarding shells are gone**

Run:

```powershell
rg -n "from app\.mneme\.services\..* import \*|from app\.mneme\.infra\.task_queue import \*" app\mneme\domains\retrieval
```

Expected:

```text
```

No matches.

## Task 8: Full Phase Verification

**Files:**
- No source changes unless verification reveals a bug.

- [ ] **Step 1: Run focused retrieval tests**

Run:

```powershell
python -m unittest tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service
```

Expected:

```text
OK
```

- [ ] **Step 2: Run route smoke check**

Run:

```powershell
python -c "from app.mneme.main import app; paths = sorted(route.path for route in app.routes); assert '/kb/chat/query' in paths; assert '/graph' in paths; print('route smoke ok')"
```

Expected:

```text
route smoke ok
```

- [ ] **Step 3: Run import scan**

Run:

```powershell
rg -n "services\.(query_service|context_service|retrieval_fusion_service|retrieval_debug_service|query_router_service)|routers\.chat" app tests scripts scripts2
```

Expected:

```text
```

No matches.

- [ ] **Step 4: Review changed files**

Run:

```powershell
git diff -- app\mneme tests scripts docs\superpowers
```

Expected:

- Retrieval logic moved into `app/mneme/domains/retrieval/`.
- Public `/kb/chat/query` route still registered.
- Old retrieval services and old chat router removed.
- Tests import from domain modules.
- No unrelated frontend or deployment files changed.

## Task 9: Commit Phase 1

**Files:**
- All files changed by Tasks 1-8.

- [ ] **Step 1: Stage only Phase 1 files**

Run:

```powershell
git add app\mneme\domains\retrieval app\mneme\bootstrap\router_registry.py app\mneme\pipelines\companion_pipeline.py app\mneme\routers\companion.py tests\test_query_router_service.py tests\test_retrieval_debug_service.py tests\test_retrieval_fusion_service.py scripts\debug_day6.py scripts\debug_day7.py scripts\debug_day9.py scripts\debug_day10.py docs\superpowers\plans\2026-07-07-retrieval-domain-convergence.md docs\superpowers\specs\2026-07-07-architecture-convergence-design.md
git add -u app\mneme\services app\mneme\routers app\mneme\domains\retrieval
```

Expected:

- Only Phase 1 backend retrieval files, tests, scripts, and docs are staged.
- Existing unrelated untracked frontend output remains unstaged.

- [ ] **Step 2: Commit**

Run:

```powershell
git commit -m "refactor: converge retrieval domain"
```

Expected:

```text
[branch <hash>] refactor: converge retrieval domain
```

If Git cannot create `.git/index.lock` because the workspace exposes `.git` as read-only, report the exact error and leave the working tree changes unstaged.

## Self-Review

- Spec coverage: This plan implements Phase 1 from the architecture convergence spec. It does not attempt documents, graph, memory, tasks, or frontend work.
- Completion-marker scan: The plan contains no unfinished markers or open-ended implementation gaps.
- Type consistency: The target module paths are consistent across tests, app imports, scripts, and the router registry.
