#!/usr/bin/env bash

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="${BRANCH:-master}"
REMOTE="${REMOTE:-origin}"
REQUESTED_TAG="${1:-}"
SEMVER_PATTERN='^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
ENABLE_NGINX_SYNC="${ENABLE_NGINX_SYNC:-1}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-reminder.conf}"
NGINX_CONF_SOURCE="${NGINX_CONF_SOURCE:-${APP_DIR}/nginx/reminder.conf}"
NGINX_AVAILABLE_PATH="${NGINX_AVAILABLE_PATH:-/etc/nginx/sites-available/${NGINX_SITE_NAME}}"
NGINX_ENABLED_PATH="${NGINX_ENABLED_PATH:-/etc/nginx/sites-enabled/${NGINX_SITE_NAME}}"

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [vX.Y.Z]" >&2
  exit 2
fi

if [[ ${EUID} -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

cd "$APP_DIR"

echo "[1/5] refreshing source and version tags"
git fetch --prune --prune-tags "$REMOTE" "$BRANCH" --tags

SELECTED_TAG="$REQUESTED_TAG"
if [[ -z "$SELECTED_TAG" ]]; then
  while IFS= read -r tag; do
    if [[ "$tag" =~ $SEMVER_PATTERN ]]; then
      SELECTED_TAG="$tag"
      break
    fi
  done < <(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname)
fi

if [[ -z "$SELECTED_TAG" ]] || ! [[ "$SELECTED_TAG" =~ $SEMVER_PATTERN ]]; then
  echo "Expected a version tag such as v1.2.3." >&2
  exit 2
fi

if ! git rev-parse --verify --quiet "refs/tags/$SELECTED_TAG^{commit}" >/dev/null; then
  echo "Version tag does not exist: $SELECTED_TAG" >&2
  exit 2
fi

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH" --track "$REMOTE/$BRANCH"
fi
git pull --ff-only "$REMOTE" "$BRANCH"

echo "[2/5] deploying image version $SELECTED_TAG"
IMAGE_TAG="$SELECTED_TAG" bash deploy/release-image.sh

if [[ "$ENABLE_NGINX_SYNC" == "1" ]]; then
  echo "[3/5] updating nginx"
  if ! NGINX_DUMP="$(${SUDO} nginx -T 2>&1)"; then
    echo "$NGINX_DUMP" >&2
    echo "Unable to inspect the active nginx configuration; refusing to overwrite it." >&2
    exit 1
  fi

  if grep -Eq '^[[:space:]]*(ssl_certificate|listen[[:space:]].*443)' <<< "$NGINX_DUMP"; then
    echo "Preserving the existing TLS-managed nginx configuration."
  else
    ${SUDO} install -D -m 644 "$NGINX_CONF_SOURCE" "$NGINX_AVAILABLE_PATH"
    ${SUDO} ln -sfn "$NGINX_AVAILABLE_PATH" "$NGINX_ENABLED_PATH"
  fi

  echo "[4/5] validating and reloading nginx"
  ${SUDO} nginx -t
  ${SUDO} systemctl reload nginx
else
  echo "[3/5] skipping nginx because ENABLE_NGINX_SYNC=$ENABLE_NGINX_SYNC"
fi

echo "[5/5] current container status"
docker compose ps
