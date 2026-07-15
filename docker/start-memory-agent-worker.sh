#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec celery -A services.memory_agent.celery_app:celery_app worker \
  --beat \
  --loglevel "${CELERY_LOG_LEVEL:-INFO}" \
  --concurrency "${MEMORY_AGENT_WORKER_CONCURRENCY:-2}" \
  --queues "${MEMORY_AGENT_CELERY_QUEUE:-memory_agent}" \
  --hostname "memory-agent-worker@%h"
