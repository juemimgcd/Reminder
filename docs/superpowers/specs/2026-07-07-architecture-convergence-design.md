# Mneme Architecture Convergence Design

## Background

Mneme has already gone through one architecture refactor. The current codebase now contains both the original structure and the newer structure:

- Original structure: `routers/`, `services/`, `crud/`, `clients/`
- Newer structure: `bootstrap/`, `api/`, `domains/`, `infra/`, `pipelines/`, `workflow/`

The result is not a single clear architecture. Some new directories are real, while others are compatibility shells. For example, many files under `domains/` and `workflow/` only re-export old service modules with `import *`. This makes the project feel larger than it actually is and makes it harder to know where new code should go.

This design chooses a convergence refactor, not a feature expansion and not a full rewrite.

## Goal

Converge the backend into one primary architecture:

```text
bootstrap + api + domains + infra + models + schemas + crud
```

The main goal is to remove the mixed old/new structure by making `domains/` the real business boundary and gradually retiring old `routers/`, old broad `services/`, and empty compatibility wrappers.

## Non-Goals

This upgrade does not:

- Change public API paths.
- Change database tables or migrations.
- Change Docker, Celery, Nginx, or deployment topology.
- Split the app into microservices.
- Rewrite the frontend in the same phase.
- Replace SQLAlchemy, FastAPI, Milvus, Neo4j, or Celery.

The frontend has its own size issue, especially `app/mneme_frontend_v0.2.1/src/App.tsx`, but that should be handled after the backend convergence is stable.

## Target Backend Shape

```text
app/mneme/
  bootstrap/
    app_factory.py
    lifespan.py
    root_routes.py
    router_registry.py

  api/
    deps.py
    errors.py
    response.py

  domains/
    documents/
      router.py
      service.py
      pipeline.py

    retrieval/
      router.py
      query_service.py
      context_service.py
      fusion.py
      debug.py
      query_router.py

    graph/
      router.py
      service.py
      query.py
      projection.py
      rag.py
      admin.py

    memory/
      router.py
      service.py
      governance.py
      canonical.py

    profile/
      router.py
      service.py
      tools.py
      insight.py

    tasks/
      router.py
      service.py
      state.py

    analysis/
      router.py
      service.py

    advice/
      router.py
      service.py

    companion/
      router.py
      service.py

  infra/
    cache/
    graph_store/
    message_queue/
    relational_store/
    vector_store/
    celery_app.py
    circuit_breaker.py
    object_cache.py
    retry/
    task_queue.py

  models/
  schemas/
  crud/
  clients/
```

`crud/` and `clients/` remain for now. They are stable adapter layers and do not need to be moved just to satisfy a naming preference.

## Responsibility Rules

### `bootstrap/`

Owns process-level application setup:

- FastAPI app creation.
- Middleware registration.
- Lifespan hooks.
- Root/static frontend routes.
- Router registration.

It must not contain business logic.

### `api/`

Owns cross-cutting API helpers:

- Dependency aliases.
- Response envelopes.
- Error adapters.
- Common API utilities.

It must not know about a specific business domain unless the dependency is intentionally shared.

### `domains/`

Owns business behavior. New backend feature work should normally start here.

Each domain may own:

- `router.py`: FastAPI endpoints for that domain.
- `service.py`: application/domain orchestration.
- `pipeline.py`: multi-step domain workflows.
- Smaller modules such as `fusion.py`, `projection.py`, or `governance.py` when they are central to that domain.

Domain modules may use `crud/`, `clients/`, `infra/`, `models/`, and `schemas/`.

Domain modules should not import from old `services/` after their migration is complete.

### `infra/`

Owns technical adapters:

- PostgreSQL session wiring.
- Redis/cache/message queue adapters.
- Celery integration.
- Milvus adapter.
- Neo4j adapter.
- Retry and circuit breaker primitives.

It must not contain Mneme business rules such as memory governance, document graph projection, or retrieval ranking policy.

### `services/`

`services/` becomes a temporary migration source. It should shrink over time.

After a service module is migrated to `domains/<domain>/`, the old service module should be deleted rather than replaced with an `import *` forwarding shell.

### `routers/`

`routers/` becomes a temporary migration source. It should shrink over time.

After a router is migrated to `domains/<domain>/router.py`, the router registry should import the domain router directly and the old router file should be deleted.

## Migration Order

### Phase 1: Retrieval Domain

Move the RAG query path into `domains/retrieval/`.

Initial file mapping:

```text
app/mneme/services/query_service.py
-> app/mneme/domains/retrieval/query_service.py

app/mneme/services/context_service.py
-> app/mneme/domains/retrieval/context_service.py

app/mneme/services/retrieval_fusion_service.py
-> app/mneme/domains/retrieval/fusion.py

app/mneme/services/retrieval_debug_service.py
-> app/mneme/domains/retrieval/debug.py

app/mneme/services/query_router_service.py
-> app/mneme/domains/retrieval/query_router.py

app/mneme/routers/chat.py
-> app/mneme/domains/retrieval/router.py
```

Expected outcome:

- Chat/RAG endpoints still expose the same public API path.
- Existing retrieval tests continue to pass.
- `domains/retrieval/*` contains real logic, not service re-exports.
- Old retrieval-related service files are removed after imports are updated.

Verification:

```powershell
python -m unittest tests.test_query_router_service tests.test_retrieval_fusion_service tests.test_retrieval_debug_service
```

### Phase 2: Documents Domain

Move document upload, listing, delete, indexing, and indexing pipeline orchestration into `domains/documents/`.

Initial file mapping:

```text
app/mneme/routers/documents.py
-> app/mneme/domains/documents/router.py

app/mneme/pipelines/document_index_pipeline.py
-> app/mneme/domains/documents/pipeline.py

document-related orchestration from services and tasks
-> app/mneme/domains/documents/service.py
```

Expected outcome:

- Document API paths stay unchanged.
- The indexing pipeline remains callable from Celery.
- Business status transitions stay in the documents/tasks domains.
- Milvus and Neo4j write details remain behind outbox/infra-facing adapters.

Verification:

```powershell
python -m unittest tests.test_citation_validation_service tests.test_retrieval_fusion_service
```

If document-specific tests are added during this phase, they become the primary verification command.

### Phase 3: Graph Domain

Move graph payload building, graph queries, graph projection, graph admin rebuilds, and GraphRAG planning into `domains/graph/`.

Initial file mapping:

```text
app/mneme/routers/graph.py
-> app/mneme/domains/graph/router.py

app/mneme/services/graph_service.py
-> app/mneme/domains/graph/service.py

app/mneme/services/graph_query_service.py
-> app/mneme/domains/graph/query.py

app/mneme/services/graph_projection_service.py
-> app/mneme/domains/graph/projection.py

app/mneme/services/graph_rag_service.py
-> app/mneme/domains/graph/rag.py

app/mneme/services/graph_admin_service.py
-> app/mneme/domains/graph/admin.py
```

Expected outcome:

- Graph endpoints keep the same public paths.
- Neo4j fallback behavior remains unchanged.
- GraphRAG planner remains covered by existing graph-related tests.
- Old graph service files are removed after imports are updated.

Verification:

```powershell
python -m unittest tests.test_graph_rag_service
```

### Phase 4: Memory, Profile, Analysis, Advice, Companion

Move dependent insight domains after retrieval and graph are stable.

Suggested mapping:

```text
memory_service.py
memory_governance_service.py
-> domains/memory/

profile_service.py
profile_tool_service.py
insight_service.py
-> domains/profile/

analytics_service.py
growth_service.py
eval_service.py as applicable
-> domains/analysis/ or domains/eval/

advice_service.py
-> domains/advice/

companion_service.py
-> domains/companion/
```

Expected outcome:

- Memory-derived features import from domains instead of old `services/`.
- Knowledge-base/user scope rules are easier to audit.
- Old forwarding shells under `domains/` are gone.

Verification:

```powershell
python -m unittest tests.test_eval_service
```

Additional focused tests should be added where existing tests do not cover moved logic.

### Phase 5: Tasks and Outbox Cleanup

Unify task state, task admin, queue dispatch, and outbox naming.

Suggested mapping:

```text
app/mneme/services/task_state_service.py
app/mneme/services/task_admin_service.py
-> app/mneme/domains/tasks/

app/mneme/workflow/*.py forwarding shells
-> delete after imports are moved

app/mneme/services/outbox_service.py
-> either app/mneme/domains/tasks/outbox.py
   or app/mneme/infra/message_queue/outbox.py
```

Decision rule for outbox:

- If the module contains business event handling such as document vector reindex or graph sync, keep the orchestration in a domain.
- If the module only contains generic queue mechanics, keep it in `infra`.

Expected outcome:

- No `workflow/*` file remains if it only forwards imports.
- Task status transitions have one canonical import path.
- Outbox event processing has a clear business-vs-infra boundary.

## Router Registry Target

The current router registry imports old `app.mneme.routers.*` modules. After migration, it should register domain routers:

```python
ROUTER_MODULE_NAMES = [
    "app.mneme.domains.health.router",
    "app.mneme.domains.auth.router",
    "app.mneme.domains.users.router",
    "app.mneme.domains.documents.router",
    "app.mneme.memoria.api.retrieval",
    "app.mneme.domains.memory.router",
    "app.mneme.domains.advice.router",
    "app.mneme.domains.analysis.router",
    "app.mneme.domains.profile.router",
    "app.mneme.domains.companion.router",
    "app.mneme.domains.tasks.router",
    "app.mneme.domains.graph.router",
]
```

`health`, `auth`, and `users` may be migrated later because they are smaller and less responsible for the current architectural bulk.

## Import Policy

The following patterns should be removed during migration:

```python
from app.mneme.services.some_service import *  # noqa: F401,F403
from app.mneme.infra.task_queue import *  # noqa: F401,F403
```

Allowed imports after convergence:

- Domain router importing from the same domain.
- Domain service importing from `crud/`, `clients/`, `infra/`, `models/`, and `schemas/`.
- Cross-domain imports only when the dependency is real and stable.

Cross-domain imports should be explicit:

```python
from app.mneme.domains.retrieval.context_service import build_query_context
```

Not:

```python
from app.mneme.domains.retrieval import *
```

## Deletion Policy

Delete old files only after all three conditions are true:

1. All imports have been updated.
2. The relevant focused tests pass.
3. The old file is not referenced by scripts, Celery task names, or deployment entrypoints.

Do not leave forwarding wrappers unless a temporary compatibility period is explicitly needed. The goal of this upgrade is to reduce duplicate structure.

## Testing Strategy

Each phase should be a small behavior-preserving migration.

Minimum verification per phase:

- Run focused unit tests for the moved domain.
- Run import smoke checks for FastAPI app creation.
- For router moves, verify routes are still registered.

Suggested smoke command:

```powershell
python - <<'PY'
from app.mneme.main import app
paths = sorted(route.path for route in app.routes)
for expected in ["/kb/chat/query", "/kb/documents/upload", "/graph"]:
    assert expected in paths, expected
print("route smoke ok")
PY
```

Because PowerShell heredoc syntax differs from bash, this can also be run as a small temporary script or with `python -c` during implementation.

## Success Criteria

The convergence is successful when:

- New business work has an obvious home under `domains/<area>/`.
- `domains/` no longer contains `import *` compatibility shells.
- Old `services/` has either disappeared or only contains explicitly retained shared services.
- Old `routers/` has disappeared or only contains explicitly retained small legacy routers.
- `workflow/` forwarding shells have been removed or replaced by real task/outbox modules.
- Public API paths remain stable.
- Existing focused tests pass after each migration phase.

## Risks and Controls

Risk: Import churn breaks runtime behavior.

Control: Migrate one domain at a time and run focused tests plus route smoke checks after each phase.

Risk: Celery tasks import old module paths.

Control: Check task names and task imports before deleting old files. Keep Celery task names stable even if Python modules move.

Risk: Graph and retrieval have hidden coupling.

Control: Migrate retrieval first, graph second, and update GraphRAG imports only after retrieval tests pass.

Risk: Scope grows into frontend refactor.

Control: Keep frontend out of this backend convergence phase. Document `App.tsx` split as a later phase.

## Recommended First Implementation Plan

Start with the retrieval domain because it has the clearest tests and the largest architectural payoff.

First implementation slice:

1. Move retrieval fusion/debug/query-router/context/query service logic into `domains/retrieval/`.
2. Move `routers/chat.py` into `domains/retrieval/router.py`.
3. Update imports in routers, tests, graph services, companion services, and any other callers.
4. Update `bootstrap/router_registry.py` to register `app.mneme.memoria.api.retrieval`.
5. Delete old retrieval service files and the old chat router after references are gone.
6. Run focused retrieval tests and route smoke checks.

This slice should not change response shapes or endpoint paths.
