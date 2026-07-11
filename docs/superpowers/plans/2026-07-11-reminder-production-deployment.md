# Reminder Production Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Reminder frontend, API, Celery worker, and persistence services as one reboot-safe production deployment at `https://www.mneme.com.cn` while preserving the existing data volumes and keeping port 8000 private.

**Architecture:** Vue is built into the FastAPI image, so Nginx proxies one HTTPS origin to the application bound at `127.0.0.1:8000`. Docker Compose owns the application and dependencies under the existing `mneme` project name, while systemd owns lifecycle at boot and Certbot owns TLS renewal.

**Tech Stack:** Docker Compose v5, FastAPI/Uvicorn, Vue/Vite, Celery/Redis, PostgreSQL 17, Neo4j, Nginx, Certbot, systemd, Let's Encrypt

## Global Constraints

- Preserve the named volumes `mneme_postgres_data`, `mneme_redis_data`, and `mneme_neo4j_data`.
- Do not run `docker compose down -v`, `docker volume prune`, or any command that deletes named volumes.
- Keep the Compose project name exactly `mneme`.
- Keep Milvus, etcd, and MinIO disabled unless the vector profile is explicitly requested.
- Bind the application to `127.0.0.1:8000`; only ports 80 and 443 are public application ports.
- Issue TLS only after authoritative DNS resolves `www.mneme.com.cn` solely to `124.223.14.145`.
- Keep secrets only in `/root/project/Reminder/.env` and never print their values.

---

### Task 1: Lock the corrected container contract into the repository

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker/Dockerfile`
- Modify: `docker/start-migrate.sh`
- Modify: `requirements/ai.txt`
- Modify: `app/mneme/infra/celery_app.py`
- Modify: `tests/test_docker_compose_contract.py`
- Modify: `tests/test_dependency_configuration.py`

**Interfaces:**
- Consumes: the existing Compose stack, grouped requirements files, Alembic branches, and Celery task packages.
- Produces: a CPU-safe application image, deterministic migrations across all heads, correct task discovery, and a loopback-only production binding controlled by `.env`.

- [ ] **Step 1: Add failing deployment contract tests**

Add assertions that the Dockerfile copies the grouped requirements directory, the migration script executes all heads, Celery imports the fully qualified task modules, and the AI requirements reference the exact CPU wheel:

```python
assert "COPY requirements/ ./requirements/" in dockerfile
assert "alembic upgrade heads" in migrate_script
assert '"app.mneme.tasks.index_tasks"' in celery_source
assert '"app.mneme.tasks.outbox_tasks"' in celery_source
assert "download.pytorch.org/whl/cpu/torch-2.11.0%2Bcpu" in ai_requirements
```

- [ ] **Step 2: Run the focused tests and verify the current repository fails**

Run:

```powershell
python -m pytest tests/test_docker_compose_contract.py tests/test_dependency_configuration.py -q -p no:cacheprovider
```

Expected: at least one new assertion fails against the unfixed repository state.

- [ ] **Step 3: Apply the minimal production fixes**

Use these exact runtime contracts:

```dockerfile
COPY requirements.txt ./
COPY requirements/ ./requirements/
```

```sh
exec alembic upgrade heads
```

```python
imports=(
    "app.mneme.tasks.index_tasks",
    "app.mneme.tasks.outbox_tasks",
)
```

```text
torch @ https://download.pytorch.org/whl/cpu/torch-2.11.0%2Bcpu-cp312-cp312-manylinux_2_28_x86_64.whl
```

Set Neo4j to a verified, existing version compatible with the retained data; do not leave the nonexistent `neo4j:5.28` tag.

- [ ] **Step 4: Run focused tests and static build checks**

Run:

```powershell
python -m pytest tests/test_docker_compose_contract.py tests/test_dependency_configuration.py -q -p no:cacheprovider
python -m compileall app/mneme alembic main.py
Set-Location app/mneme_frontend_v0.2.1
npm run lint
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit only the production contract files**

```powershell
git add docker-compose.yml docker/Dockerfile docker/start-migrate.sh requirements/ai.txt app/mneme/infra/celery_app.py tests/test_docker_compose_contract.py tests/test_dependency_configuration.py
git commit -m "fix: harden Reminder production containers"
```

Expected: unrelated `package-lock.json` remains unstaged.

### Task 2: Make the server deployment reproducible and private

**Files:**
- Modify on server: `/root/project/Reminder/.env`
- Create on server: `/etc/systemd/system/reminder-compose.service`

**Interfaces:**
- Consumes: the existing `mneme` data volumes and corrected application image.
- Produces: one Compose lifecycle command and a loopback-only application endpoint.

- [ ] **Step 1: Back up non-versioned production configuration and record volume state**

Run over SSH:

```bash
cd /root/project/Reminder
cp .env /root/reminder-env-backup-20260711
docker volume ls --format '{{.Name}}' | grep '^mneme_'
```

Expected: the PostgreSQL, Redis, and Neo4j volumes are listed before any recreation.

- [ ] **Step 2: Set the private bind and production proxy trust values**

Update the existing keys without printing secret values:

```env
APP_HOST_PORT=127.0.0.1:8000
FORWARDED_ALLOW_IPS=127.0.0.1
TRUSTED_HOSTS=["www.mneme.com.cn","127.0.0.1","localhost"]
CORS_ALLOWED_ORIGINS=["https://www.mneme.com.cn"]
```

- [ ] **Step 3: Install the Compose systemd unit for the real deployment path**

Create:

```ini
[Unit]
Description=Reminder Docker Compose stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/project/Reminder
Environment=COMPOSE_PROJECT_NAME=mneme
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose stop
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: Reload systemd and recreate the application stack**

```bash
systemctl daemon-reload
systemctl enable reminder-compose.service
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose up -d --build
```

Expected: migration exits 0; app and storage services become healthy; worker stays running.

- [ ] **Step 5: Verify port privacy from the server and an external client**

```bash
ss -lntp | grep ':8000 '
curl -fsS http://127.0.0.1:8000/health
```

Expected: the listener is `127.0.0.1:8000`, local health returns success, and an external request to `124.223.14.145:8000` times out or is refused.

### Task 3: Install Nginx and configure the unified frontend/API origin

**Files:**
- Create on server: `/etc/nginx/sites-available/reminder.conf`
- Create symlink on server: `/etc/nginx/sites-enabled/reminder.conf`

**Interfaces:**
- Consumes: healthy HTTP traffic at `127.0.0.1:8000`.
- Produces: an HTTP virtual host for `www.mneme.com.cn` that is ready for Certbot.

- [ ] **Step 1: Install Nginx and Certbot packages**

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx
systemctl enable --now nginx
```

Expected: `systemctl is-active nginx` prints `active`.

- [ ] **Step 2: Write the pre-TLS reverse proxy configuration**

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name www.mneme.com.cn;

    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

- [ ] **Step 3: Enable only the Reminder site and validate Nginx**

```bash
ln -sfn /etc/nginx/sites-available/reminder.conf /etc/nginx/sites-enabled/reminder.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
curl -fsS -H 'Host: www.mneme.com.cn' http://127.0.0.1/health
```

Expected: syntax succeeds and the proxied health endpoint returns success.

### Task 4: Pass the DNS gate and enable HTTPS

**Files:**
- Modified by Certbot: `/etc/nginx/sites-available/reminder.conf`
- Managed by Certbot: `/etc/letsencrypt/live/www.mneme.com.cn/`

**Interfaces:**
- Consumes: public DNS and a working port-80 Nginx virtual host.
- Produces: trusted HTTPS with automatic HTTP redirection and renewal.

- [ ] **Step 1: Verify authoritative DNS no longer returns the removed server**

```bash
dig +short NS mneme.com.cn
dig +short @119.29.29.29 www.mneme.com.cn A
dig +short @1.1.1.1 www.mneme.com.cn A
dig +short @8.8.8.8 www.mneme.com.cn A
```

Expected: every resolver returns only `124.223.14.145`. If any returns `8.147.57.104`, wait for TTL expiry and do not run Certbot.

- [ ] **Step 2: Request and install the certificate**

```bash
certbot --nginx -d www.mneme.com.cn --redirect --non-interactive --agree-tos --register-unsafely-without-email
```

Expected: Certbot reports successful certificate deployment.

- [ ] **Step 3: Verify certificate renewal configuration**

```bash
systemctl enable --now certbot.timer
systemctl is-enabled certbot.timer
certbot renew --dry-run
```

Expected: the timer is enabled and the dry run succeeds.

### Task 5: Perform full production acceptance and reboot verification

**Files:**
- No file changes.

**Interfaces:**
- Consumes: the completed Compose, Nginx, TLS, and systemd deployment.
- Produces: fresh evidence that the complete frontend/backend deployment survives reboot.

- [ ] **Step 1: Verify application and dependency state**

```bash
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose ps -a
COMPOSE_PROJECT_NAME=mneme docker compose logs --since=2m app worker migrate
```

Expected: app and storage dependencies are healthy, migration exited 0, worker reports `ready`, and no service is in a restart loop.

- [ ] **Step 2: Verify all public routes and TLS**

```bash
curl -fsSI http://www.mneme.com.cn/
curl -fsS https://www.mneme.com.cn/ -o /dev/null
curl -fsS https://www.mneme.com.cn/docs -o /dev/null
curl -fsS https://www.mneme.com.cn/health
openssl s_client -connect www.mneme.com.cn:443 -servername www.mneme.com.cn </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

Expected: HTTP redirects to HTTPS, all HTTPS routes succeed, health reports running, and the certificate is valid for the hostname.

- [ ] **Step 3: Reboot and verify automatic recovery**

```bash
reboot
```

After SSH reconnects:

```bash
systemctl is-active docker reminder-compose nginx
systemctl is-enabled reminder-compose nginx certbot.timer
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose ps -a
curl -fsS https://www.mneme.com.cn/health
```

Expected: Docker, Compose, and Nginx are active; all three units are enabled; the stack is healthy without manual commands.

- [ ] **Step 4: Confirm the private application port remains inaccessible externally**

Run from the operator machine:

```powershell
Test-NetConnection 124.223.14.145 -Port 8000
Invoke-WebRequest -UseBasicParsing https://www.mneme.com.cn/health
```

Expected: `TcpTestSucceeded` is `False` for port 8000 and HTTPS health returns HTTP 200.
