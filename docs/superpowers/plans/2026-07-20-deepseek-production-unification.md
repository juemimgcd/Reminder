# DeepSeek Production Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the active Qwen runtime configuration, make DeepSeek the only configured default, publish the current deployment fixes, and restore production AI chat.

**Architecture:** Keep the provider compatibility layer unchanged, but point every committed runtime model slot at DeepSeek through `memoria.json`. Fix the Docker-only Agent Run coordination address in Compose, publish only the intended deployment/runtime files, then rebuild and validate the production request path.

**Tech Stack:** Python 3.12, FastAPI, Celery, Redis, PostgreSQL/pgvector, Docker Compose, GitHub

---

### Task 1: Unify the active model configuration

**Files:**
- Modify: `memoria.json`
- Modify: `.env-example`

- [ ] **Step 1: Replace the chat model with DeepSeek**

Set `chat.model` to provider `deepseek`, model `deepseek-v4-flash`, base URL `https://api.deepseek.com`, and API key reference `${DEEPSEEK_API_KEY}`.

- [ ] **Step 2: Replace Memory Agent models with DeepSeek**

Apply the same DeepSeek values to `memory_agent.extraction_model` and `memory_agent.answer_model`.

- [ ] **Step 3: Remove the inactive Qwen secret placeholder**

Delete `DASHSCOPE_API_KEY` from `.env-example`; keep `DEEPSEEK_API_KEY`.

### Task 2: Repair container Agent Run coordination

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add the Docker Redis endpoint**

Set `AGENT_RUN_REDIS_URL: redis://redis:6379/2` in the shared application environment.

- [ ] **Step 2: Validate rendered Compose configuration**

Run `docker compose config --quiet`.

Expected: exit code 0.

### Task 3: Validate and publish the intended runtime changes

**Files:**
- Modify: the existing deployment/runtime hotfix files already present in the working tree
- Create: `app/mneme/infra/async_runner.py`
- Create: `docker/Postgres.Dockerfile`

- [ ] **Step 1: Run the existing focused configuration tests**

Run `pytest tests/test_llm_provider_config.py tests/test_memoria_agent_config.py -q`.

Expected: all selected tests pass.

- [ ] **Step 2: Run repository static checks**

Run the repository's existing Ruff and test commands appropriate to the changed Python files.

Expected: exit code 0.

- [ ] **Step 3: Stage only the intended files**

Explicitly stage the DeepSeek configuration, Compose, pgvector image, async runner, and their current call-site changes. Do not stage the unrelated `.superpowers/` directory.

- [ ] **Step 4: Commit and push**

Commit with a terse deployment-fix message and push `master` to `origin`.

### Task 4: Deploy and verify production

**Files:**
- Remote checkout: `/root/project/Reminder`

- [ ] **Step 1: Fast-forward the server checkout**

Fetch GitHub and fast-forward the production checkout to the pushed commit without overwriting server secrets.

- [ ] **Step 2: Rebuild and recreate services**

Build the application image and recreate migrations, API, workers, scheduler, and Memory Agent services using the existing production `.env`.

- [ ] **Step 3: Verify effective configuration**

Confirm the application sees `redis://redis:6379/2`, all active model slots resolve to DeepSeek, and both app and Memory Agent see a non-empty DeepSeek key without printing it.

- [ ] **Step 4: Verify the AI path**

Run health/readiness checks and execute one authenticated AI conversation through the production API. Confirm that the Agent Run is queued, processed, and returns a model response without Redis or missing-key errors.
