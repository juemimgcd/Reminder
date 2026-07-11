# Reminder Production Deployment Design

## Objective

Serve the Reminder frontend and API together at `https://www.mneme.com.cn`, keep application dependencies private, preserve the existing PostgreSQL, Redis, and Neo4j data volumes, and restore the full stack automatically after a server reboot.

## Architecture

Nginx is the only public application entry point and listens on ports 80 and 443. Port 80 redirects to HTTPS. Port 443 terminates TLS and proxies requests to the Reminder application on `127.0.0.1:8000`. FastAPI serves both the built Vue frontend and API routes, so no separate frontend process or static-site deployment is required.

Docker Compose runs the FastAPI application, Celery worker, migration job, PostgreSQL, Redis, and Neo4j. The existing Compose project name `mneme` remains in use so the deployment reuses the current named data volumes. Milvus, etcd, and MinIO remain disabled unless the vector profile is explicitly enabled because the server has limited memory and the base deployment does not require them to boot.

## Components

- `www.mneme.com.cn`: the only supported public hostname. Its sole A record must resolve to `124.223.14.145` before certificate issuance.
- Nginx: redirects HTTP to HTTPS, proxies all application traffic, forwards the original host and client IP headers, and applies practical request-size and timeout limits for document uploads and long-running API calls.
- Certbot: obtains a Let's Encrypt certificate for `www.mneme.com.cn`, installs it into Nginx, and enables automatic renewal through the packaged systemd timer.
- Docker Compose: binds the application only to `127.0.0.1:8000`; database, Redis, and Neo4j ports remain loopback-only.
- systemd: starts the Compose stack after Docker and the network are available and restarts it on reboot using the actual deployment path `/root/project/Reminder`.

## Startup and Upgrade Flow

The Compose migration service waits for PostgreSQL, Redis, and Neo4j, applies every Alembic head, and exits successfully. Only then do the application and worker start. Nginx serves traffic after the application health endpoint returns HTTP 200.

Routine startup uses:

```bash
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose up -d
```

The systemd service executes the equivalent command automatically at boot. Repository upgrades must retain the production `.env`, the `mneme` Compose project name, and the server-side fixes already required for the Docker image, CPU-only PyTorch, multi-head migrations, and Celery task imports.

## Security

- Public inbound application traffic is limited to ports 80 and 443; SSH remains on port 22.
- Port 8000 is bound to loopback and must not be publicly reachable.
- PostgreSQL, Redis, Neo4j, Milvus, etcd, and MinIO are never exposed publicly.
- TLS uses the Let's Encrypt certificate managed by Certbot.
- Secrets remain in the server `.env` and are never copied into Nginx or committed to Git.

## Failure Handling

- Certificate issuance is blocked until authoritative DNS returns only `124.223.14.145`.
- Nginx configuration is validated with `nginx -t` before reload.
- Compose health checks gate dependent services, and the migration container must exit with status 0.
- Existing named volumes are never deleted or recreated as part of configuration.
- If HTTPS setup fails, the running Compose stack remains available locally while the DNS or certificate issue is corrected.

## Verification

Deployment is complete only when all of the following are freshly verified:

- Authoritative DNS resolves `www.mneme.com.cn` only to `124.223.14.145`.
- Nginx configuration passes `nginx -t` and listens on ports 80 and 443.
- HTTP redirects to HTTPS.
- `https://www.mneme.com.cn/`, `/docs`, and `/health` return successful responses with a valid certificate.
- The application, PostgreSQL, Redis, and Neo4j are healthy; the migration service exited 0; the Celery worker is ready without restart loops.
- `124.223.14.145:8000` is not publicly reachable.
- The Compose systemd unit and Certbot renewal timer are enabled.
