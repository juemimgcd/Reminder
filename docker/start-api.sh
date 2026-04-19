#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${APP_PORT:-8000}" \
  --workers "${UVICORN_WORKERS:-2}"
