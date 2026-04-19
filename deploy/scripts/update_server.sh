#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mneme}"
BRANCH="${BRANCH:-master}"

cd "$APP_DIR"

echo "[1/3] syncing git branch: $BRANCH"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "[2/3] rebuilding and restarting docker compose services"
docker compose up -d --build --remove-orphans

echo "[3/3] current container status"
docker compose ps
