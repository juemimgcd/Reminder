# Mneme Professionalization Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current main branch reproducibly verifiable, reject unsafe production configuration, harden the runtime image, and present one consistent Mneme product/version identity.

**Architecture:** Keep the current modular monolith and deployment topology intact. Apply narrow compatibility and configuration changes at existing boundaries: tests inspect public OpenAPI output, CI invokes existing toolchains, settings validate production-only invariants, the container drops privileges after installation, and a root `VERSION` file becomes the release version source.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, pytest, Ruff, Vue 3, TypeScript, Vite, Node test runner, Docker Compose, GitHub Actions.

---

### Task 1: Restore the existing backend quality gate

**Files:**
- Modify: `tests/test_agent_automation_contract.py`
- Modify: `tests/test_channel_gateway_contract.py`
- Modify: `main.py`

- [ ] **Step 1: Reproduce the two route-contract failures**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_agent_automation_contract.py::test_agent_automation_routes_are_registered tests/test_channel_gateway_contract.py::test_channel_routes_and_delivery_tasks_are_registered
```

Expected: both tests fail because FastAPI 0.135 exposes included routers as `_IncludedRouter` objects without a public `.path` attribute.

- [ ] **Step 2: Change the tests to inspect the public OpenAPI contract**

Use `create_app().openapi()["paths"]` in both tests. This tests the intended public route registration contract without depending on FastAPI's private route container representation.

- [ ] **Step 3: Apply Ruff's import formatting to the root entry point**

Run:

```powershell
.\.venv\Scripts\python.exe -m ruff check main.py --fix
```

Expected: `main.py` is formatted and Ruff reports no remaining error for the file.

- [ ] **Step 4: Verify the focused tests and full Ruff check**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_agent_automation_contract.py::test_agent_automation_routes_are_registered tests/test_channel_gateway_contract.py::test_channel_routes_and_delivery_tasks_are_registered
.\.venv\Scripts\python.exe -m ruff check app main.py tests
```

Expected: two tests pass and Ruff reports `All checks passed!`.

### Task 2: Make CI execute the repository's complete lightweight checks

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/package.json`
- Modify: `.github/workflows/reminder-deploy.yml`

- [ ] **Step 1: Add a frontend contract-test script**

Add `"test:contracts": "node --test tests/*.test.mjs"` to `package.json`. Keep Playwright separate because it requires browser installation and belongs in a heavier integration job.

- [ ] **Step 2: Extend the frontend CI job**

After `npm run lint`, run `npm run test:contracts` and `npm run build` so pull requests validate both source contracts and the production bundle.

- [ ] **Step 3: Extend the backend CI job**

Install `requirements/dev.txt`, include it in the pip cache key, and run `python -m ruff check app main.py tests` before pytest.

- [ ] **Step 4: Verify all CI commands locally**

Run the exact Ruff, pytest, `npm run lint`, `npm run test:contracts`, and `npm run build` commands used by the workflow. Expected: every command exits zero.

### Task 3: Reject unsafe production settings at startup

**Files:**
- Modify: `app/mneme/conf/config.py`
- Modify: `.env-example`
- Modify: `deploy/env/backend.production.example`

- [ ] **Step 1: Introduce an explicit environment mode**

Add `APP_ENV: Literal["development", "test", "production"] = "development"` to `Settings`, document it in both environment templates, and set the production template to `production`.

- [ ] **Step 2: Separate development CORS defaults from production behavior**

Keep automatic localhost origins for development and test. In production, preserve only explicitly configured origins and origin regex values.

- [ ] **Step 3: Add production-only secret validation**

In the existing model validator, reject production startup when the JWT secret is shorter than 32 characters, the Memory Agent service secret is shorter than 32 characters, the two secrets are equal, the database URL contains the default `postgres:123456` credential, or enabled Neo4j uses its placeholder password.

- [ ] **Step 4: Verify configuration behavior with isolated processes**

Run one process with default development settings and one with `APP_ENV=production` plus placeholders. Expected: development loads; production exits with a Pydantic validation error naming the unsafe fields. Run another production process with safe values and expect successful settings construction.

### Task 4: Harden and stabilize the container definition

**Files:**
- Modify: `docker/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `.env-example`
- Modify: `deploy/env/backend.production.example`

- [ ] **Step 1: Pin mutable service image defaults**

Replace `neo4j:latest` and `redis:7-alpine` with explicit configurable defaults, using environment variables so operators can intentionally upgrade them.

- [ ] **Step 2: Create a non-root runtime user**

After copying and validating application files, create an `mneme` system user, grant it ownership only of `/app/storage`, and switch to `USER mneme`. Preserve host bind-mount usability by making the runtime UID/GID build arguments configurable.

- [ ] **Step 3: Document image and UID/GID controls**

Add the image version and runtime UID/GID variables to the environment templates.

- [ ] **Step 4: Validate statically and with Docker when available**

Run repository contract tests and `docker compose config --quiet`. Build the image if Docker is installed. If Docker is unavailable, report that exact verification gap rather than claiming a successful image build.

### Task 5: Establish one Mneme product and release identity

**Files:**
- Create: `VERSION`
- Create: `app/mneme/version.py`
- Modify: `app/mneme/conf/config.py`
- Modify: `app/mneme/bootstrap/root_routes.py`
- Modify: `app/mneme_frontend_v0.2.1/package.json`
- Modify: `app/mneme_frontend_v0.2.1/README.md`
- Modify: `README.md`
- Modify: `.env-example`
- Modify: `deploy/env/backend.production.example`
- Modify: `.github/workflows/reminder-deploy.yml`

- [ ] **Step 1: Add the release version source**

Create root `VERSION` containing `0.1.0`. Add `app/mneme/version.py` to read and validate that value once, and make backend settings default to it while still allowing an explicit `VERSION` environment override for compatibility.

- [ ] **Step 2: Align product-facing names**

Use `Mneme` in API metadata, root welcome output, the primary README, frontend README, environment templates, and GitHub Actions display/concurrency names. Keep existing deployment paths, volume names, service filenames, and published `reminder` image repository identifiers unchanged in this phase to avoid an implicit production migration.

- [ ] **Step 3: Align package metadata**

Set the frontend package version to `0.1.0`. The root `VERSION` remains authoritative for product releases; package metadata mirrors it and is checked during CI.

- [ ] **Step 4: Add a CI version consistency check**

Use a small inline Node command in the frontend job to compare `package.json` with the root `VERSION`, and a Python command in the backend job to compare the application version with the same file.

### Task 6: Final verification and scope review

**Files:**
- Review all modified files.

- [ ] **Step 1: Run the complete backend suite with a workspace-local basetemp**

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp/phase-one-pytest
```

Expected: all tests and subtests pass.

- [ ] **Step 2: Run all static and frontend checks**

```powershell
.\.venv\Scripts\python.exe -m ruff check app main.py tests
npm run lint
npm run test:contracts
npm run build
```

Expected: all commands exit zero.

- [ ] **Step 3: Review the diff and repository status**

Confirm every changed line maps to the five requested outcomes, no secrets were added, user-owned untracked files remain untouched, and any Docker verification limitation is documented.
