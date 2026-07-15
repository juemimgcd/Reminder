#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec celery -A app.mneme.infra.celery_app:celery_app beat \
  --loglevel "${CELERY_LOG_LEVEL:-INFO}"
