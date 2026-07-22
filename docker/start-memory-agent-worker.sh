#!/bin/sh
set -eu

python /app/docker/wait_for_services.py
mkdir -p /app/storage/celery

exec celery -A app.mneme.memoria.server.celery_app:celery_app worker \
  --beat \
  --schedule /app/storage/celery/memory-agent-beat-schedule \
  --loglevel "${CELERY_LOG_LEVEL:-INFO}" \
  --concurrency "${MEMORY_AGENT_WORKER_CONCURRENCY:-1}" \
  --queues "${MEMORY_AGENT_CELERY_QUEUE:-memory_agent}" \
  --hostname "memory-agent-worker@%h"
