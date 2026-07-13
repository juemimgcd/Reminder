#!/usr/bin/env bash

set -euo pipefail

IMAGE_TAG="${IMAGE_TAG:?set IMAGE_TAG to a version such as v1.2.3}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-ghcr.io/juemimgcd/reminder}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$APP_DIR/.env"
TIMEOUT_SECONDS=60

compose_with_image() {
  APP_IMAGE_REPOSITORY="$IMAGE_REPOSITORY" \
  APP_IMAGE_TAG="$IMAGE_TAG" \
  APP_IMAGE_PULL_POLICY="always" \
  docker compose "$@"
}

upsert_env() {
  local key="$1"
  local value="$2"
  local temp_file

  if [[ "$value" == *$'\n'* || "$value" == *$'\r'* ]]; then
    echo "Refusing to write a multiline value for $key." >&2
    return 1
  fi

  temp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
  awk -v key="$key" -v value="$value" '
    $0 ~ "^[[:space:]]*(export[[:space:]]+)?" key "=" {
      if (!written) {
        print key "=" value
        written = 1
      }
      next
    }
    { print }
    END {
      if (!written) {
        print key "=" value
      }
    }
  ' "$ENV_FILE" > "$temp_file"
  chmod --reference="$ENV_FILE" "$temp_file"
  mv "$temp_file" "$ENV_FILE"
}

wait_for_migration() {
  local container_id
  local status
  local deadline=$((SECONDS + TIMEOUT_SECONDS))

  container_id="$(docker compose ps -aq migrate)"
  if [[ -z "$container_id" ]]; then
    echo "Migration container was not created." >&2
    return 1
  fi

  while (( SECONDS < deadline )); do
    status="$(docker inspect -f '{{.State.Status}}:{{.State.ExitCode}}' "$container_id")"
    case "$status" in
      exited:0)
        return 0
        ;;
      exited:*|dead:*)
        echo "Migration failed with status $status." >&2
        docker compose logs migrate >&2
        return 1
        ;;
    esac
    sleep 2
  done

  echo "Timed out waiting for migration after ${TIMEOUT_SECONDS} seconds." >&2
  docker compose logs migrate >&2
  return 1
}

wait_for_health() {
  local deadline=$((SECONDS + TIMEOUT_SECONDS))

  while (( SECONDS < deadline )); do
    if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
      return 0
    fi
    sleep 2
  done

  echo "Timed out waiting for /health after ${TIMEOUT_SECONDS} seconds." >&2
  return 1
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Expected deployment environment file at $ENV_FILE." >&2
  exit 1
fi

cd "$APP_DIR"
echo "Pulling image ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
compose_with_image pull migrate app worker

COMPOSE_PROFILES="$(awk -F= '/^[[:space:]]*(export[[:space:]]+)?COMPOSE_PROFILES=/ { print substr($0, index($0, "=") + 1); exit }' "$ENV_FILE")"
upsert_env "APP_IMAGE_REPOSITORY" "$IMAGE_REPOSITORY"
upsert_env "APP_IMAGE_TAG" "$IMAGE_TAG"
upsert_env "APP_IMAGE_PULL_POLICY" "always"

echo "Deploying image ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
docker compose up -d postgres redis neo4j
if [[ ",$COMPOSE_PROFILES," == *",vector,"* ]]; then
  docker compose --profile vector up -d etcd minio milvus
fi
docker compose up -d --no-build --no-deps --force-recreate migrate
wait_for_migration
docker compose up -d --no-build --no-deps --force-recreate app worker
wait_for_health

echo "Deployment ready: ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
docker compose ps app worker
