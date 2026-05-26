#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec celery -A app.mneme.infra.celery_app:celery_app worker \
  --loglevel "${CELERY_LOG_LEVEL:-INFO}" \
  --concurrency "${CELERY_WORKER_CONCURRENCY:-2}" \
  --queues "${CELERY_INDEX_QUEUE:-document_index}" \
  --hostname "worker@%h"
