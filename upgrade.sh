#!/usr/bin/env bash

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="${BRANCH:-master}"
ENABLE_NGINX_SYNC="${ENABLE_NGINX_SYNC:-1}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-reminder.conf}"
NGINX_CONF_SOURCE="${NGINX_CONF_SOURCE:-${APP_DIR}/nginx/reminder.conf}"
NGINX_AVAILABLE_PATH="${NGINX_AVAILABLE_PATH:-/etc/nginx/sites-available/${NGINX_SITE_NAME}}"
NGINX_ENABLED_PATH="${NGINX_ENABLED_PATH:-/etc/nginx/sites-enabled/${NGINX_SITE_NAME}}"

if [[ ${EUID} -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

cd "${APP_DIR}"

echo "[1/5] syncing git branch: ${BRANCH}"
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

echo "[2/5] rebuilding and restarting docker compose services"
docker compose up -d --build --remove-orphans

if [[ "${ENABLE_NGINX_SYNC}" == "1" ]]; then
  echo "[3/5] syncing nginx config"
  ${SUDO} install -D -m 644 "${NGINX_CONF_SOURCE}" "${NGINX_AVAILABLE_PATH}"
  ${SUDO} ln -sfn "${NGINX_AVAILABLE_PATH}" "${NGINX_ENABLED_PATH}"

  echo "[4/5] testing and reloading nginx"
  ${SUDO} nginx -t
  ${SUDO} systemctl reload nginx
else
  echo "[3/5] skipping nginx sync because ENABLE_NGINX_SYNC=${ENABLE_NGINX_SYNC}"
fi

echo "[5/5] current container status"
docker compose ps
