# Versioned GHCR Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish protected, versioned Docker images to GitHub Container Registry and let the production host deploy or roll back a selected release tag without pulling source code or building images.

**Architecture:** Docker Compose will resolve the app image from non-secret `APP_IMAGE_REPOSITORY` and `APP_IMAGE_TAG` environment variables, while retaining the local `reminder-app:local` build default. A tag-triggered GitHub Actions workflow will test, build, and publish `vX.Y.Z` and commit-SHA GHCR tags. A server-side script will persist the selected tag in the existing ignored `.env`, pull only the app image, run migrations, restart app/worker, and verify `/health`.

**Tech Stack:** Docker Compose v2, Docker Buildx, GitHub Actions, GitHub Container Registry, Bash, pytest.

---

### Task 1: Define the image-delivery contract

**Files:**
- Create: `tests/test_versioned_image_delivery.py`
- Modify: `docker-compose.yml:3-24`

- [ ] **Step 1: Write failing contract tests**

```python
def test_compose_resolves_app_image_from_repository_and_tag_variables():
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    app_base = compose["x-app-base"]
    assert app_base["image"] == "${APP_IMAGE_REPOSITORY:-reminder-app}:${APP_IMAGE_TAG:-local}"
    assert app_base["pull_policy"] == "${APP_IMAGE_PULL_POLICY:-missing}"


def test_release_script_pulls_a_requested_tag_without_git_commands():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")
    assert 'IMAGE_TAG="${IMAGE_TAG:?set IMAGE_TAG to a version such as v1.2.3}"' in script
    assert 'docker compose pull migrate app worker' in script
    assert "git pull" not in script
```

- [ ] **Step 2: Run the tests and confirm RED**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-red`

Expected: FAIL because the image variables and release script do not exist.

- [ ] **Step 3: Add the Compose image variables**

```yaml
x-app-base: &app-base
  image: ${APP_IMAGE_REPOSITORY:-reminder-app}:${APP_IMAGE_TAG:-local}
  pull_policy: ${APP_IMAGE_PULL_POLICY:-missing}
  build:
    context: .
```

Keep the existing build block so local `docker compose up --build` remains supported.

- [ ] **Step 4: Run the contract tests and confirm the Compose assertion passes**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-compose`

Expected: the Compose-image assertion passes; the release-script assertion remains red.

### Task 2: Add the server image release and rollback script

**Files:**
- Create: `deploy/release-image.sh`
- Modify: `tests/test_versioned_image_delivery.py`

- [ ] **Step 1: Extend the failing test with required deployment behavior**

```python
def test_release_script_persists_the_selected_tag_then_migrates_and_checks_health():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")
    assert 'upsert_env "APP_IMAGE_REPOSITORY" "$IMAGE_REPOSITORY"' in script
    assert 'upsert_env "APP_IMAGE_TAG" "$IMAGE_TAG"' in script
    assert 'docker compose up -d --no-build --no-deps --force-recreate migrate' in script
    assert 'docker compose up -d --no-build --no-deps --force-recreate app worker' in script
    assert 'curl -fsS http://127.0.0.1:8000/health' in script
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-script-red`

Expected: FAIL because `deploy/release-image.sh` is absent.

- [ ] **Step 3: Implement the script**

Implement `upsert_env()` with `awk` plus an atomic temporary file, require `IMAGE_TAG`, default `IMAGE_REPOSITORY` to `ghcr.io/juemimgcd/reminder`, persist only image-selection variables to `.env`, pull `migrate`, `app`, and `worker`, recreate migration then app/worker without building, and poll `/health` for at most 60 seconds. Print the selected protected release tag without printing `.env` values.

- [ ] **Step 4: Run the release-script contract tests and shell syntax check**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-script-green; bash -n deploy/release-image.sh`

Expected: PASS; Bash syntax exits 0.

### Task 3: Publish versioned images from Git tags

**Files:**
- Modify: `.github/workflows/reminder-deploy.yml`
- Modify: `tests/test_versioned_image_delivery.py`

- [ ] **Step 1: Add failing workflow contract tests**

```python
def test_release_workflow_publishes_ghcr_images_for_version_tags_only():
    workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
    assert "tags:" in workflow and "- 'v*'" in workflow
    assert "packages: write" in workflow
    assert "docker/build-push-action@v6" in workflow
    assert "ghcr.io/${{ github.repository_owner }}/reminder:${{ github.ref_name }}" in workflow
    assert "ghcr.io/${{ github.repository_owner }}/reminder:sha-${{ github.sha }}" in workflow
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-workflow-red`

Expected: FAIL because the workflow currently only runs checks and source-based SSH deployment.

- [ ] **Step 3: Replace source-based deploy jobs with a publish-image job**

Keep frontend and backend checks. Trigger them on `master` pushes and `v*` tags. Add `publish-image`, dependent on both checks and guarded by `startsWith(github.ref, 'refs/tags/v')`; give it `packages: write`, log into `ghcr.io` using `GITHUB_TOKEN`, set up Buildx, and push the two explicit version and source-SHA tags with the existing Dockerfile. Remove the old SSH source-pull deploy jobs so GitHub Actions cannot silently return to the old deployment model.

- [ ] **Step 4: Run workflow contract tests**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-workflow-green`

Expected: PASS.

### Task 4: Document first-time registry access and normal release operations

**Files:**
- Modify: `deploy/env/backend.production.example`
- Modify: `deploy/DEPLOY.md`
- Modify: `.github/deploy/github-actions.secrets.example`
- Modify: `tests/test_versioned_image_delivery.py`

- [ ] **Step 1: Add failing documentation/configuration contract tests**

```python
def test_production_template_and_docs_describe_versioned_image_deployments():
    env_template = ENV_TEMPLATE.read_text(encoding="utf-8")
    docs = DEPLOY_DOC.read_text(encoding="utf-8")
    assert "APP_IMAGE_REPOSITORY=ghcr.io/juemimgcd/reminder" in env_template
    assert "APP_IMAGE_TAG=" in env_template
    assert "docker login ghcr.io" in docs
    assert "IMAGE_TAG=v1.2.3 bash deploy/release-image.sh" in docs
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-docs-red`

Expected: FAIL because production configuration and docs describe source pulls and builds.

- [ ] **Step 3: Update templates and documentation**

Add non-secret `APP_IMAGE_REPOSITORY`, `APP_IMAGE_TAG`, and `APP_IMAGE_PULL_POLICY` defaults to the production template. Rewrite the deployment model and daily upgrade sections to: create/push `vX.Y.Z`, wait for the GHCR workflow, run a one-time read-only `docker login ghcr.io` for private images, then execute `IMAGE_TAG=vX.Y.Z bash deploy/release-image.sh`; show the same command with an older tag as rollback. Remove obsolete `DEPLOY_BRANCH` and source-upgrade configuration from the GitHub Actions secrets example, retaining only GHCR/package and runtime-secret guidance.

- [ ] **Step 4: Run documentation contract tests and review the diff**

Run: `python -m pytest tests/test_versioned_image_delivery.py -q -p no:cacheprovider --basetemp .tmp/pytest-versioned-image-docs-green; git diff --check`

Expected: PASS and no whitespace errors.

### Task 5: Verify the full release contract

**Files:**
- Test: `tests/test_versioned_image_delivery.py`
- Test: `tests/test_docker_compose_contract.py`
- Test: `app/mneme_frontend_v0.2.1/package.json`

- [ ] **Step 1: Run focused backend deployment tests**

Run: `python -m pytest tests/test_versioned_image_delivery.py tests/test_docker_compose_contract.py -q -p no:cacheprovider --basetemp .tmp/pytest-release-contract`

Expected: PASS.

- [ ] **Step 2: Validate Compose interpolation**

Run: `APP_IMAGE_REPOSITORY=ghcr.io/juemimgcd/reminder APP_IMAGE_TAG=v1.2.3 docker compose config --no-interpolate`

Expected: configuration parses successfully and contains the expected image variable contract.

- [ ] **Step 3: Run frontend type checking**

Run: `npm --prefix app/mneme_frontend_v0.2.1 run lint`

Expected: exit 0.

- [ ] **Step 4: Commit the delivery standard**

Run: `git add docker-compose.yml deploy/release-image.sh deploy/env/backend.production.example deploy/DEPLOY.md .github/workflows/reminder-deploy.yml .github/deploy/github-actions.secrets.example tests/test_versioned_image_delivery.py docs/superpowers/plans/2026-07-13-versioned-ghcr-deployment.md && git commit -m "feat: publish versioned images to ghcr"`

Expected: one focused commit with no secrets.

## Plan Review

- Spec coverage: protected version-tag GHCR artifacts, tag-triggered publishing, server pull/deploy, rollback, registry authentication, and non-secret configuration are covered by Tasks 1-4.
- Placeholder scan: all changed files, commands, and expected results are named; no implementation placeholders remain.
- Type consistency: `APP_IMAGE_REPOSITORY`, `APP_IMAGE_TAG`, `APP_IMAGE_PULL_POLICY`, `IMAGE_REPOSITORY`, and `IMAGE_TAG` are used consistently across Compose, script, tests, and documentation.
