# Production Hardening Implementation Plan

**Goal:** Restore reliable production AI conversations and remove the deployment/runtime defects found after the DeepSeek migration.

**Success criteria:**

- Outbox events dispatch without detached SQLAlchemy instances and the existing production backlog drains.
- General-chat session deletion accepts a nullable knowledge-base ID.
- Invalid or blank LLM provider configuration falls back to DeepSeek, never Qwen.
- The Memory Agent loads BGE-M3 once per service process from a persistent cache and is ready before serving traffic.
- The production host runs one Memory Agent API worker and one Celery worker to fit its memory budget.
- Release deployment updates every application service, uses a pullable versioned pgvector image, and keeps Redis coordination namespaces separate.
- Existing verification passes apart from any independently confirmed baseline environment mismatch.
- GitHub and production run the same verified commit; production health checks and focused conversation checks pass.

## Implementation

- [x] In `app/mneme/domains/tasks/outbox.py`, introduce an immutable scalar snapshot and ensure no ORM object leaves a database-session scope.
- [x] In `app/mneme/domains/tasks/outbox.py`, copy batch event IDs before closing the read session.
- [x] In the conversation-deletion enqueue path, accept `knowledge_base_id=None`, use a stable empty sentinel only for deterministic ID generation, and keep the payload nullable.
- [x] In `app/mneme/clients/llm_client.py`, make DeepSeek the normalization fallback for blank or invalid providers.
- [x] In Memory Agent settings and embedding service, add explicit cache/path/local-only/preload controls and load the model before readiness.
- [x] Mount `./storage` into Memory Agent services and default API/Celery process counts to one.
- [x] In `docker-compose.yml`, move Agent Run coordination to Redis DB 4.
- [x] Replace the local-only PostgreSQL build with the official versioned `pgvector/pgvector:0.8.5-pg17-bookworm` image.
- [x] Extend `deploy/release-image.sh` to migrate, recreate, wait for, and health-check app, beat, and all Memory Agent services.
- [x] Run formatting/static checks, existing tests, and disposable focused regression scripts without modifying the repository test suite.
- [ ] Commit the isolated branch, update GitHub, back up production PostgreSQL, deploy the verified revision, and validate health and AI paths.
- [ ] After successful deployment, remove only confirmed-unused build cache and obsolete application images while preserving the active and immediate rollback images.

## Verification commands

```powershell
& D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest
docker compose config
git diff --check
```

Production verification will check Docker service health, `/health/readiness`, `/memory-agent/health/readiness`, Outbox backlog movement, a general-chat request, a knowledge-base request, and nullable-knowledge-base session deletion.
