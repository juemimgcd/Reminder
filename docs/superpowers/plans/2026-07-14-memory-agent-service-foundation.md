# Memory Agent Service Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a separately runnable Memory Agent service with its own PostgreSQL database, versioned contracts, authenticated event ingestion, Mneme HTTP client, reliable Outbox delivery, and deployment topology.

**Architecture:** `services/memory_agent` is an independent FastAPI/Celery application and never imports Mneme ORM, CRUD, database, or task modules. Mneme communicates through typed HTTP payloads; asynchronous changes are committed to Mneme's existing Outbox and delivered to the Agent's idempotent inbox.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2 async, PostgreSQL 17, pgvector, Alembic, HTTPX, Celery, Redis, Docker Compose

## Global Constraints

- Keep both services in the existing repository; do not create another Git repository.
- Use independent PostgreSQL databases, Alembic histories, Celery queues, and configuration namespaces.
- Do not introduce Kafka, a workflow engine, a dedicated vector database, or a multi-agent framework.
- Do not create or modify test files in this plan.
- Do not move current answer behavior yet; the new service is not on the user traffic path in this plan.
- Commit only the files named by each task and preserve unrelated worktree changes.

---

### Task 1: Scaffold the independent application and persistence boundary

**Files:**
- Create: `services/__init__.py`
- Create: `services/memory_agent/__init__.py`
- Create: `services/memory_agent/main.py`
- Create: `services/memory_agent/app.py`
- Create: `services/memory_agent/config.py`
- Create: `services/memory_agent/database.py`
- Create: `services/memory_agent/logging.py`
- Create: `services/memory_agent/models/base.py`
- Create: `services/memory_agent/models/__init__.py`
- Create: `services/memory_agent/alembic.ini`
- Create: `services/memory_agent/alembic/env.py`
- Create: `services/memory_agent/alembic/script.py.mako`
- Modify: `requirements/base.txt`

**Interfaces:**
- Produces: `settings: MemoryAgentSettings`, `Base`, `get_db()`, `open_read_session()`, `open_write_session()`, and `create_memory_agent_app() -> FastAPI`.

- [ ] **Step 1: Define service settings and database sessions**

Use a distinct environment prefix and reject accidental connection to the Mneme database by requiring an explicit Agent URL outside local defaults:

```python
class MemoryAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_AGENT_", env_file=".env", extra="ignore")
    DATABASE_URL: str = "postgresql+asyncpg://postgres:123456@localhost:5432/memory_agent"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8010
    SERVICE_JWT_SECRET: SecretStr
    SERVICE_JWT_AUDIENCE: str = "memory-agent"
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"
    CELERY_QUEUE: str = "memory_agent"
```

- [ ] **Step 2: Add the application factory and entry point**

`services/memory_agent/app.py` must construct FastAPI without importing `app.mneme`:

```python
def create_memory_agent_app() -> FastAPI:
    app = FastAPI(title="Mneme Memory Agent", version="1.0.0")
    app.include_router(health_router)
    app.include_router(event_router, prefix="/internal/v1")
    return app
```

- [ ] **Step 3: Create an independent Alembic environment**

Set `target_metadata = Base.metadata`, convert the async URL to a synchronous migration URL in `env.py`, and write revisions only under `services/memory_agent/alembic/versions/`.

- [ ] **Step 4: Add only required dependencies**

Add `httpx`, `PyJWT`, and `pgvector` if absent. Do not add another web framework, queue, or ORM.

- [ ] **Step 5: Run source checks**

Run: `python -m compileall -q services/memory_agent`

Expected: exit code 0.

Run: `python -m ruff check services/memory_agent`

Expected: no lint errors.

- [ ] **Step 6: Commit**

```powershell
git add services requirements/base.txt
git commit -m "feat: scaffold memory agent service"
```

### Task 2: Define versioned service contracts and authenticated event inbox

**Files:**
- Create: `services/memory_agent/contracts/common.py`
- Create: `services/memory_agent/contracts/answers.py`
- Create: `services/memory_agent/contracts/events.py`
- Create: `services/memory_agent/contracts/memories.py`
- Create: `services/memory_agent/security/service_tokens.py`
- Create: `services/memory_agent/models/inbox_event.py`
- Create: `services/memory_agent/repositories/inbox.py`
- Create: `services/memory_agent/api/dependencies.py`
- Create: `services/memory_agent/api/events.py`
- Create: `services/memory_agent/api/health.py`
- Create: `services/memory_agent/alembic/versions/20260714_01_create_memory_agent_core.py`
- Modify: `services/memory_agent/models/__init__.py`
- Modify: `services/memory_agent/app.py`

**Interfaces:**
- Consumes: `get_db()` and `Base` from Task 1.
- Produces: `AgentEventEnvelope`, `AnswerRequest`, `AnswerResponse`, `MemoryData`, `POST /internal/v1/events`, `/health`, and `/health/readiness`.

- [ ] **Step 1: Define exact envelopes**

```python
EventType = Literal[
    "document.projection.upserted", "document.deleted", "knowledge_base.deleted",
    "conversation.completed", "conversation.deleted", "user.memory_requested",
    "user.memory_settings.changed",
]

class AgentEventEnvelope(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    schema_version: Literal["1"] = "1"
    occurred_at: datetime
    owner_id: int
    knowledge_base_id: str | None = None
    payload: dict[str, Any]

class AnswerRequest(BaseModel):
    request_id: str
    owner_id: int
    knowledge_base_id: str
    session_id: str | None = None
    message_id: str
    question: str = Field(min_length=1)
    answer_mode: Literal["kb_qa", "memory_query", "profile_query", "analysis_query", "general_chat"]
    top_k: int = Field(default=4, ge=1, le=10)
    model: ModelInvocationConfig | None = None

class ModelInvocationConfig(BaseModel):
    provider: str
    base_url: str
    model_name: str
    api_key: SecretStr
    temperature: float = 0.0
```

`ModelInvocationConfig` is an ephemeral service-to-service input for the existing user-selected model setting. The Agent must mark it excluded from serialization in logs, answer runs, task payloads, and error details.

- [ ] **Step 2: Persist idempotent inbox events**

Create `InboxEvent` with unique `event_id`, JSON payload, `received_at`, `status`, `attempt_count`, `processed_at`, and `last_error`. Implement:

```python
async def accept_event(db: AsyncSession, envelope: AgentEventEnvelope) -> tuple[InboxEvent, bool]:
    """Return (row, created); duplicate event_id returns the existing row and False."""
```

Use PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`, then select by `event_id`.

- [ ] **Step 3: Authenticate internal requests**

Implement HS256 service tokens containing `iss="mneme-backend"`, `aud="memory-agent"`, `iat`, `exp`, and `scope="events:write"`. Reject missing, expired, wrong-audience, or wrong-scope tokens with HTTP 401/403. Never accept a user access token on `/internal/v1/events`.

- [ ] **Step 4: Accept before scheduling**

`POST /internal/v1/events` validates and persists first, returns HTTP 202 with `{event_id, accepted, duplicate}`, and schedules processing only after the transaction commits. A duplicate returns HTTP 200 and is not scheduled twice.

- [ ] **Step 5: Add liveness and readiness**

`/health` returns process liveness. `/health/readiness` executes `SELECT 1` and returns 503 when the Agent database is unavailable; it must not claim worker health.

- [ ] **Step 6: Inspect the migration and source**

Run: `python -m alembic -c services/memory_agent/alembic.ini heads`

Expected: exactly `20260714_01 (head)`.

Run: `python -m ruff check services/memory_agent`

Expected: no lint errors.

- [ ] **Step 7: Commit**

```powershell
git add services/memory_agent
git commit -m "feat: add memory agent contracts and event inbox"
```

### Task 3: Add Agent-owned Celery processing

**Files:**
- Create: `services/memory_agent/celery_app.py`
- Create: `services/memory_agent/tasks/events.py`
- Create: `services/memory_agent/services/event_dispatcher.py`
- Create: `docker/start-memory-agent-api.sh`
- Create: `docker/start-memory-agent-worker.sh`
- Modify: `services/memory_agent/api/events.py`

**Interfaces:**
- Consumes: persisted `InboxEvent.id`.
- Produces: `process_inbox_event_task(event_id: str)` and `dispatch_inbox_event(event_id: str) -> EventProcessResult`.

- [ ] **Step 1: Configure the isolated queue**

```python
celery_app = Celery(
    "memory_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_default_queue=settings.CELERY_QUEUE,
    task_routes={"memory_agent.process_event": {"queue": settings.CELERY_QUEUE}},
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 2: Add a deliberately narrow dispatcher**

Initially support every contract type with a named handler that records `succeeded` without performing projections. Do not use a dynamic import or model-selected handler. The next plan replaces each no-op with business processing.

- [ ] **Step 3: Enqueue after commit**

Call `process_inbox_event_task.delay(event_id=row.event_id)` only when `created is True` and the request transaction has completed. If broker submission fails, keep the inbox row pending for a periodic recovery task.

- [ ] **Step 4: Add recovery dispatch**

Add `memory_agent.dispatch_pending_events` to enqueue pending rows older than 30 seconds, with a configurable batch limit of 100.

- [ ] **Step 5: Run source checks and commit**

Run: `python -m compileall -q services/memory_agent`

Expected: exit code 0.

```powershell
git add services/memory_agent docker/start-memory-agent-*.sh
git commit -m "feat: add memory agent event worker"
```

### Task 4: Add the Mneme client and HTTP Outbox target

**Files:**
- Create: `app/mneme/clients/memory_agent_client.py`
- Create: `app/mneme/schemas/memory_agent.py`
- Create: `app/mneme/domains/tasks/outbox_http.py`
- Modify: `app/mneme/conf/config.py`
- Modify: `app/mneme/domains/tasks/outbox.py`
- Modify: `app/mneme/infra/celery_app.py`

**Interfaces:**
- Consumes: `/internal/v1/events` and the answer/event Pydantic shapes from Task 2, duplicated as transport DTOs rather than imported across service boundaries.
- Produces: `MemoryAgentClient.submit_event()`, `MemoryAgentClient.create_answer()`, and target backend `memory_agent_http`.

- [ ] **Step 1: Add Mneme-side settings**

Add `MEMORY_AGENT_BASE_URL`, `MEMORY_AGENT_SERVICE_JWT_SECRET`, `MEMORY_AGENT_TIMEOUT_SECONDS=30`, `MEMORY_AGENT_ENABLED=False`, and `MEMORY_AGENT_OUTBOX_TARGET="memory_agent_http"`.

- [ ] **Step 2: Implement the client**

Use one `httpx.AsyncClient`, service tokens with a maximum five-minute lifetime, `X-Request-ID`, JSON timeouts, and typed error mapping:

```python
class MemoryAgentUnavailable(BusinessException): ...
class MemoryAgentRejected(BusinessException): ...

class MemoryAgentClient:
    async def submit_event(self, event: MemoryAgentEvent) -> EventReceipt: ...
    async def create_answer(self, request: MemoryAgentAnswerRequest) -> MemoryAgentAnswerResponse: ...
```

Retry connection errors and HTTP 502/503/504 only. Do not retry 4xx responses.

- [ ] **Step 3: Route only the new target over HTTP**

Refactor `apply_outbox_event()` so existing Milvus and Neo4j behavior is unchanged, while `target_backend == "memory_agent_http"` calls `submit_event()`. Do not put HTTP code into `outbox.py`.

Refactor `enqueue_outbox_event()` to accept an optional caller-owned `AsyncSession`. Business services pass their active write session so the domain change and Outbox row commit atomically; command-line and recovery callers may omit it and use the existing managed-session behavior.

- [ ] **Step 4: Preserve dead-letter behavior**

Store the Agent HTTP status and bounded response detail in `last_error`; never store event source text in logs. Existing max-attempt and next-attempt semantics remain authoritative.

- [ ] **Step 5: Run source checks and commit**

Run: `python -m ruff check app/mneme/clients/memory_agent_client.py app/mneme/schemas/memory_agent.py app/mneme/domains/tasks/outbox.py app/mneme/domains/tasks/outbox_http.py app/mneme/conf/config.py`

Expected: no lint errors.

```powershell
git add app/mneme/clients app/mneme/schemas/memory_agent.py app/mneme/domains/tasks app/mneme/conf/config.py app/mneme/infra/celery_app.py
git commit -m "feat: deliver outbox events to memory agent"
```

### Task 5: Add dual-service deployment without switching traffic

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker/Dockerfile`
- Modify: `docker/wait_for_services.py`
- Modify: `deploy/env/backend.production.example`
- Modify: `deploy/DEPLOY.md`
- Modify: `README.md`

**Interfaces:**
- Produces: Compose services `memory-agent-migrate`, `memory-agent-api`, and `memory-agent-worker`.

- [ ] **Step 1: Provision the second database**

Add a PostgreSQL initialization script or an idempotent init service that creates `${MEMORY_AGENT_POSTGRES_DB:-memory_agent}`. Do not reuse `${POSTGRES_DB:-agentic}`.

- [ ] **Step 2: Add Agent services**

Use port 8010 internally, Redis databases 2 and 3, the independent migration command, and a worker command importing `services.memory_agent.celery_app:celery_app`. The Mneme app receives `MEMORY_AGENT_BASE_URL=http://memory-agent-api:8010` but keeps `MEMORY_AGENT_ENABLED=false`.

- [ ] **Step 3: Add health and dependency ordering**

`memory-agent-api` depends on `memory-agent-migrate`; the worker depends on migration and Redis. The Mneme app does not depend on Agent readiness until the later cutover plan.

- [ ] **Step 4: Document configuration and ownership**

Document both databases, queues, API ports, secrets, health endpoints, and the rule prohibiting cross-database reads.

- [ ] **Step 5: Validate configuration**

Run: `docker compose config --quiet`

Expected: exit code 0.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 6: Commit**

```powershell
git add docker-compose.yml docker deploy README.md
git commit -m "feat: deploy independent memory agent service"
```
