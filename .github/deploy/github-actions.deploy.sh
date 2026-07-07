#!/usr/bin/env bash

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/reminder}"
BRANCH="${BRANCH:-master}"
ENABLE_NGINX_SYNC="${ENABLE_NGINX_SYNC:-1}"

cd "${APP_DIR}"
BRANCH="${BRANCH}" ENABLE_NGINX_SYNC="${ENABLE_NGINX_SYNC}" bash ./upgrade.sh
