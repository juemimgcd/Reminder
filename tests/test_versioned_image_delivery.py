import re
from pathlib import Path

import yaml

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "docker-compose.yml"
RELEASE_SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "release-image.sh"
UPGRADE_SCRIPT = Path(__file__).resolve().parents[1] / "upgrade.sh"
SYSTEMD_SERVICE = (
    Path(__file__).resolve().parents[1]
    / "deploy"
    / "systemd"
    / "reminder-compose.service"
)
WORKFLOW_FILE = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "reminder-deploy.yml"
PRODUCTION_ENV_TEMPLATE = (
    Path(__file__).resolve().parents[1] / "deploy" / "env" / "backend.production.example"
)
DEPLOY_DOCUMENTATION = Path(__file__).resolve().parents[1] / "deploy" / "DEPLOY.md"


def test_compose_resolves_app_image_from_repository_and_tag_variables():
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    app_base = compose["x-app-base"]

    assert app_base["image"] == "${APP_IMAGE_REPOSITORY:-reminder-app}:${APP_IMAGE_TAG:-local}"
    assert app_base["pull_policy"] == "${APP_IMAGE_PULL_POLICY:-missing}"


def test_release_script_pulls_a_requested_tag_without_git_commands():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")

    assert 'IMAGE_TAG="${IMAGE_TAG:?set IMAGE_TAG to a version such as v1.2.3}"' in script
    assert "compose_with_image pull migrate app worker" in script
    assert "git pull" not in script


def test_release_script_persists_the_selected_tag_then_migrates_and_checks_health():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")

    assert 'upsert_env "APP_IMAGE_REPOSITORY" "$IMAGE_REPOSITORY"' in script
    assert 'upsert_env "APP_IMAGE_TAG" "$IMAGE_TAG"' in script
    assert "docker compose up -d --no-build --no-deps --force-recreate migrate" in script
    assert "docker compose up -d --no-build --no-deps --force-recreate app worker" in script
    assert "curl -fsS http://127.0.0.1:8000/health" in script


def test_release_script_pre_pulls_the_requested_image_before_updating_dotenv():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")

    helper = '''compose_with_image() {
  APP_IMAGE_REPOSITORY="$IMAGE_REPOSITORY" \\
  APP_IMAGE_TAG="$IMAGE_TAG" \\
  APP_IMAGE_PULL_POLICY="always" \\
  docker compose "$@"
}'''
    pull = "compose_with_image pull migrate app worker"
    first_upsert = 'upsert_env "APP_IMAGE_REPOSITORY" "$IMAGE_REPOSITORY"'

    assert helper in script
    assert pull in script
    assert script.index(pull) < script.index(first_upsert)


def test_upgrade_script_defaults_to_latest_version_tag_and_accepts_an_override():
    script = UPGRADE_SCRIPT.read_text(encoding="utf-8")

    assert 'REQUESTED_TAG="${1:-}"' in script
    assert "git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname" in script
    assert "SEMVER_PATTERN='^v(0|[1-9][0-9]*)" in script
    assert 'IMAGE_TAG="$SELECTED_TAG" bash deploy/release-image.sh' in script


def test_upgrade_script_updates_deployment_files_and_safely_reloads_nginx():
    script = UPGRADE_SCRIPT.read_text(encoding="utf-8")

    assert 'git fetch --prune --prune-tags "$REMOTE" "$BRANCH" --tags' in script
    assert 'git pull --ff-only "$REMOTE" "$BRANCH"' in script
    assert 'NGINX_DUMP="$(${SUDO} nginx -T 2>&1)"' in script
    assert (
        "grep -Eq '^[[:space:]]*(ssl_certificate|listen[[:space:]].*443)'"
        in script
    )
    assert '${SUDO} nginx -t' in script
    assert '${SUDO} systemctl reload nginx' in script
    assert "docker compose up -d --build" not in script


def test_systemd_service_restarts_the_stack_without_building_images():
    service = SYSTEMD_SERVICE.read_text(encoding="utf-8")

    expected_command = "/usr/bin/docker compose up -d --no-build --remove-orphans"
    assert f"ExecStart={expected_command}" in service
    assert f"ExecReload={expected_command}" in service
    assert "--build" not in service


def test_release_script_starts_prerequisites_before_running_migrations():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")

    prerequisites = "docker compose up -d postgres redis neo4j"
    migration = "docker compose up -d --no-build --no-deps --force-recreate migrate"
    assert prerequisites in script
    assert script.index(prerequisites) < script.index(migration)


def test_release_script_starts_vector_prerequisites_when_enabled_before_migration():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")

    migration = "docker compose up -d --no-build --no-deps --force-recreate migrate"
    vector_prerequisites = "docker compose --profile vector up -d etcd minio milvus"

    assert re.search(
        r'awk\b(?s:.*?)COMPOSE_PROFILES(?s:.*?)"\$ENV_FILE"', script
    )
    assert re.search(r'if\s+\[\[(?s:.*?)COMPOSE_PROFILES(?s:.*?)vector', script)
    assert vector_prerequisites in script
    assert script.index(vector_prerequisites) < script.index(migration)


def test_release_workflow_publishes_versioned_ghcr_images_from_validated_tags_only():
    workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
    workflow_config = yaml.safe_load(workflow)
    jobs = workflow_config["jobs"]

    assert 'tags:\n      - "v*"' in workflow
    assert workflow_config.get("permissions", {}).get("packages") != "write"
    assert jobs["publish-image"]["permissions"]["packages"] == "write"
    assert all(
        job.get("permissions", {}).get("packages") != "write"
        for name, job in jobs.items()
        if name != "publish-image"
    )
    assert "^v[0-9]+\\.[0-9]+\\.[0-9]+$" in workflow
    assert "docker/login-action@v3" in workflow
    assert "docker/build-push-action@v6" in workflow
    assert "ghcr.io/${{ github.repository_owner }}/reminder:${{ github.ref_name }}" in workflow
    assert "ghcr.io/${{ github.repository_owner }}/reminder:sha-${{ github.sha }}" in workflow


def test_production_template_and_docs_explain_versioned_ghcr_image_deployment():
    template = PRODUCTION_ENV_TEMPLATE.read_text(encoding="utf-8")
    docs = DEPLOY_DOCUMENTATION.read_text(encoding="utf-8")

    assert "APP_IMAGE_REPOSITORY=ghcr.io/juemimgcd/reminder" in template
    assert "APP_IMAGE_TAG=" in template
    assert "APP_IMAGE_PULL_POLICY=always" in template
    assert "docker login ghcr.io" in docs
    assert "IMAGE_TAG=v1.2.3 bash deploy/release-image.sh" in docs
    assert "IMAGE_TAG=v1.2.2" in docs
    assert "protected Git release tags" in docs
    assert "version tags are not overwritten" in docs
