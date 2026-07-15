#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec celery -A app.mneme.infra.celery_app:celery_app worker \
  --loglevel "${CELERY_LOG_LEVEL:-INFO}" \
  --concurrency "${CELERY_WORKER_CONCURRENCY:-2}" \
  --queues "${CELERY_INDEX_QUEUE:-document_index},${CELERY_OUTBOX_QUEUE:-outbox_projection},${CELERY_AGENT_QUEUE:-agent_run},${CELERY_AUTOMATION_QUEUE:-agent_automation},${CELERY_MAINTENANCE_QUEUE:-maintenance}" \
  --hostname "worker@%h"
