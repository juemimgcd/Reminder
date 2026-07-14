#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec uvicorn services.memory_agent.main:app \
  --host "${MEMORY_AGENT_API_HOST:-0.0.0.0}" \
  --port "${MEMORY_AGENT_API_PORT:-8010}" \
  --workers "${MEMORY_AGENT_UVICORN_WORKERS:-2}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
