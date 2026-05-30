#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/reminder}"

cd "$APP_DIR"
exec bash ./upgrade.sh
