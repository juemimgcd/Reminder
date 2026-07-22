#!/bin/sh
set -eu

python /app/docker/wait_for_services.py
mkdir -p /app/storage/celery

exec celery -A app.mneme.infra.celery_app:celery_app beat \
  --schedule /app/storage/celery/mneme-beat-schedule \
  --loglevel "${CELERY_LOG_LEVEL:-INFO}"
