# Mneme operations runbook

This runbook covers the production Compose deployment described in
`deploy/DEPLOY.md`. Run commands from the deployment directory and record the
Git SHA, image tag, operator, timestamp, and resulting artifact checksum for
every backup, restore drill, and rollback.

## Service objectives

| Signal | Initial objective | Primary evidence |
| --- | --- | --- |
| Mneme API availability | 99.5% monthly | `/health`, Prometheus `up` |
| Memory Agent availability | 99.0% monthly | `/health/readiness`, Prometheus `up` |
| Mneme HTTP errors | 5xx ratio below 1% over 30 minutes | `mneme_http_requests_total` |
| Mneme latency | average below 2 seconds over 10 minutes | HTTP duration sum/count |
| Projection freshness | lag below 5 minutes | `memory_agent_projection_lag_seconds` |
| Event durability | zero dead letters | `memory_agent_dead_letters` |

The initial HTTP metrics are process-local. Prometheus must scrape every API
replica and aggregate with `sum`; do not interpret one worker as the whole
service.

Metrics endpoints:

- Mneme: `GET /health/metrics`
- Memory Agent: `GET /metrics` on the internal port 8010
- Alert rules: `deploy/monitoring/mneme-alerts.yml`

## Availability

1. Run `docker compose ps` and identify the unhealthy or restarting service.
2. Read bounded logs: `docker compose logs --tail 300 app memory-agent-api`.
3. Check migrations: `docker compose ps migrate memory-agent-migrate`.
4. Check dependencies with `docker compose exec` using `pg_isready`,
   `redis-cli ping`, and `cypher-shell 'RETURN 1'`.
5. If the incident follows a release, use the rollback procedure below before
   attempting data repair.

## HTTP errors and latency

Break down `mneme_http_requests_total` and duration metrics by `route`, not by
raw URL. Correlate the alert window with the `request_id` and `trace_id` fields
returned in response headers. Check database saturation, queue backlog, model
timeouts, and external dependency circuit-breaker events before scaling API
workers.

## Memory Agent backlog and failures

1. Inspect `/metrics` for inbox backlog, oldest age, projection lag, failed
   runs, model retries and fallbacks.
2. Correlate the affected run/event identifier with structured JSON logs.
3. Confirm PostgreSQL and Redis health before retrying work.
4. Never delete inbox, outbox, audit, or answer-run rows to clear an alert.
   Requeue through the supported recovery task or repair the dependency and
   allow the periodic dispatcher to retry.

## PostgreSQL backup

Create an owner-only directory and dump both databases:

```bash
install -d -m 0700 backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/mneme-${stamp}.dump"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "${MEMORY_AGENT_POSTGRES_DB:-memory_agent}" -Fc' > "backups/memory-agent-${stamp}.dump"
sha256sum "backups/mneme-${stamp}.dump" "backups/memory-agent-${stamp}.dump" > "backups/postgres-${stamp}.sha256"
```

Copy the dump and checksum to storage outside the server. A backup is not
accepted until the restore drill succeeds.

## PostgreSQL restore drill

The following uses a dedicated disposable database. Verify the target name
before every destructive command; never substitute the production database.

```bash
drill_db="mneme_restore_drill"
test "$drill_db" = "mneme_restore_drill"
docker compose exec -T postgres createdb -U postgres "$drill_db"
docker compose exec -T postgres pg_restore -U postgres -d "$drill_db" --clean --if-exists < backups/mneme-YYYYMMDDTHHMMSSZ.dump
docker compose exec -T postgres psql -U postgres -d "$drill_db" -c 'SELECT count(*) FROM alembic_version;'
docker compose exec -T postgres dropdb -U postgres "$drill_db"
```

Record restore duration, schema revision, representative row counts, and an
application smoke test against the restored copy.

## Redis snapshot

Redis is not the source of truth for durable runs, but its snapshot shortens
recovery time:

```bash
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
before="$(docker compose exec -T redis redis-cli --raw LASTSAVE)"
docker compose exec -T redis redis-cli BGSAVE
until [ "$(docker compose exec -T redis redis-cli --raw LASTSAVE)" -gt "$before" ]; do sleep 1; done
docker cp reminder-redis:/data/dump.rdb "backups/redis-${stamp}.rdb"
sha256sum "backups/redis-${stamp}.rdb" > "backups/redis-${stamp}.sha256"
```

Restore Redis only during a planned outage and only after PostgreSQL has been
restored. Prefer allowing durable PostgreSQL state to repopulate ephemeral
coordination data.

## Neo4j backup

Neo4j Community dump requires a maintenance window. Stop Neo4j, dump the
explicit database from the named Compose volume, then restart and verify
health:

```bash
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose stop neo4j
docker run --rm \
  -v reminder_neo4j_data:/data \
  -v "${PWD}/backups:/backups" \
  neo4j:2026.06.0-community \
  neo4j-admin database dump neo4j --to-path=/backups --overwrite-destination=true
mv backups/neo4j.dump "backups/neo4j-${stamp}.dump"
docker compose start neo4j
docker compose exec -T neo4j cypher-shell -u neo4j -p 'replace-with-current-password' 'RETURN 1;'
```

Replace the placeholder password in the verification command with the current
Neo4j credential from the deployment secret store.

Test Neo4j restores into a separately named volume; never overwrite
`reminder_neo4j_data` during a drill.

## Release rollback

1. Identify the last healthy immutable `sha-<git-sha>` image.
2. Back up PostgreSQL before changing application versions.
3. Set `APP_IMAGE_TAG=sha-<healthy-sha>` in `.env`.
4. Run `docker compose pull app worker beat memory-agent-api memory-agent-worker`.
5. Recreate application processes without deleting volumes:

   ```bash
   docker compose up -d --no-build --force-recreate app worker beat memory-agent-api memory-agent-worker
   ```

6. Validate `/health`, `/health/readiness`, login, document retrieval and a
   cited answer.

Alembic migrations are forward-only unless a migration explicitly documents a
safe downgrade. Rolling back the image does not roll back the schema. If the
older image is incompatible with the migrated schema, restore the pre-release
database backup into a separately validated environment and perform a planned
cutover.

## Secret rotation

Rotate `JWT_SECRET` and `MEMORY_AGENT_SERVICE_JWT_SECRET` independently and keep
them different. JWT rotation invalidates existing tokens unless an overlap/key
ring mechanism is introduced. Rotate database, Neo4j and provider credentials,
recreate only dependent services, then confirm logs and metrics contain no
secret material.

## Post-deploy checklist

- Image tag and `/health` version match the release.
- Mneme and Memory Agent readiness are healthy.
- Both Alembic heads are at the expected revision.
- Redis queues and outbox/inbox backlog are stable.
- Deterministic AI evaluation gates pass for the released commit.
- A login, document query, citation, memory update and background task complete.
- No availability, 5xx, dead-letter, failed-run, or projection-lag alert fires.
