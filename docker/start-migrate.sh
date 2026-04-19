#!/bin/sh
set -eu

python /app/docker/wait_for_services.py

exec alembic upgrade head
