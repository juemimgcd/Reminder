# Reminder 部署说明

本文档基于当前仓库的推荐部署方式整理：单台 Linux 服务器、Docker Compose 启动全套服务、Nginx 对外代理，以及 GitHub Container Registry（GHCR）发布带版本号的镜像。

## 1. 部署模型

日常生产发布推荐使用这条链路：

```text
本地开发 -> git push tag vX.Y.Z -> GitHub Actions 构建并发布 GHCR 镜像 -> 服务器拉取该版本镜像
```

推送 `vX.Y.Z` 标签会触发 GitHub Actions。服务器在正常发布时不执行 `git pull`，也不在本机重新构建镜像；只拉取指定版本的 GHCR 镜像并重启 Compose 服务。

版本标签是发布标识符，不是镜像 digest；它们通过仓库访问控制和标签保护来管理，包括 `protected Git release tags`。为避免已发布版本被重新指向其他代码，`version tags are not overwritten`。

线上只有一个公开入口：

- Nginx 监听 `80/443`
- Nginx 把所有请求代理到 `127.0.0.1:8000`
- Vue 前端页面和后端 API 都由 `reminder-app` 统一提供

这意味着你不需要再单独部署一套前端静态站点。

## 2. 服务器依赖

以下示例基于 Ubuntu：

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin nginx certbot python3-certbot-nginx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

执行完 `usermod` 后重新登录一次服务器。

## 3. 获取部署配置（仅首次）

```bash
sudo mkdir -p /opt/reminder
sudo chown -R $USER:$USER /opt/reminder
git clone <your-repo-url> /opt/reminder
cd /opt/reminder
```

此克隆只用于保存 Compose 文件、部署脚本和运行时 `.env`，不用于在服务器构建应用镜像。仓库为私有时，建议先配置 deploy key 或服务器 SSH key，再执行 `git clone`。

## 4. 配置环境变量

复制生产环境模板：

```bash
cp deploy/env/backend.production.example .env
```

至少要修改这些值：

- `APP_HOST_PORT=127.0.0.1:8000`
- `FORWARDED_ALLOW_IPS=127.0.0.1`
- `TRUSTED_HOSTS=["your-domain.com","www.your-domain.com","127.0.0.1","localhost"]`
- `CORS_ALLOWED_ORIGINS=["https://your-domain.com","http://your-domain.com"]`
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_PASSWORD`
- `NEO4J_PASSWORD`
- `LLM_PROVIDER`
- `DASHSCOPE_API_KEY` / `MIMO_API_KEY` / `KIMI_API_KEY` / `GLM_API_KEY` / `DEEPSEEK_API_KEY`
- `JWT_SECRET`
- 如果你要启用交叉编码器重排，建议配置 `RERANKER_ENABLED=true`

说明：

- `APP_HOST_PORT=127.0.0.1:8000` 表示应用只暴露给本机，公网访问统一走 Nginx。
- `FORWARDED_ALLOW_IPS=127.0.0.1` 表示仅信任来自本机 Nginx 的 `X-Forwarded-*` 头。
- `TRUSTED_HOSTS` 应包含你的正式域名，避免错误 Host 头直接打到应用。
- Compose 内部会自动使用 `postgres`、`redis`、`neo4j` 这些容器名互连；启用 `vector` profile 后，应用也会通过 `milvus` 容器名访问向量库。
- 当前生产模板默认把 `MILVUS_MEMORY_LIMIT` 收敛到 `2g`，更适合中小规格机器。
- 当前模板已经预留 `RERANKER_*` 和 `RETRIEVAL_*` 参数，可用来打开 `BAAI/bge-reranker-v2-m3` 和放大召回候选池。
- `LLM_PROVIDER` 支持 `qwen`、`mimo`、`kimi`、`glm`、`deepseek`，生产模板默认是 `deepseek`。可以配置对应的 provider key，也可以统一使用 `LLM_API_KEY`；`LLM_BASE_URL` 和 `LLM_MODEL_NAME` 留空时会使用 provider 默认值。

## 5. 首次启动（从 GHCR 拉取镜像）

### Memory Agent 独立服务边界

Compose 文件定义了 Mneme 和 Memory Agent 两套服务，但本阶段不切换用户流量：`MEMORY_AGENT_ENABLED=false` 必须保持不变，Nginx 仍然只代理 `127.0.0.1:8000` 的 Mneme 应用。Memory Agent API 仅在 Compose 网络内监听 `memory-agent-api:8010`，不映射宿主机端口。

两套服务的运行资源必须保持隔离：

- Mneme 使用 `${POSTGRES_DB:-agentic}`，Memory Agent 使用 `${MEMORY_AGENT_POSTGRES_DB:-memory_agent}`；`memory-agent-db-init` 会幂等创建后者。
- Mneme 的 Celery broker/result backend 使用 Redis DB 0/1 和现有队列，Memory Agent 使用 Redis DB 2/3 和独立的 `${MEMORY_AGENT_CELERY_QUEUE:-memory_agent}` 队列。
- 两个服务通过 HTTP 事件契约通信。禁止任一服务直接读取或连接另一服务拥有的数据库，也禁止跨数据库 join。
- `JWT_SECRET` 用于 Mneme 用户令牌；`MEMORY_AGENT_SERVICE_JWT_SECRET` 是 Mneme 与 Memory Agent 之间的服务令牌密钥。两者必须使用不同的长随机值，并且只保存在服务器 `.env` 中。

启动顺序为：PostgreSQL 健康后创建 Agent 数据库，`memory-agent-migrate` 执行独立 Alembic 历史，随后启动 `memory-agent-api` 和 `memory-agent-worker`。Mneme 的 `app` 服务不依赖 Memory Agent readiness，因此 Agent 故障不会阻止当前用户入口启动。

健康检查地址：

- Mneme：`http://127.0.0.1:8000/health`
- Memory Agent liveness（Compose 网络内）：`http://memory-agent-api:8010/health`
- Memory Agent readiness（包含其数据库检查）：`http://memory-agent-api:8010/health/readiness`

可从 Mneme 容器检查内部 Agent readiness：

```bash
docker compose exec app python -c "from urllib.request import urlopen; print(urlopen('http://memory-agent-api:8010/health/readiness').read().decode())"
```

```bash
docker login ghcr.io
cd /opt/reminder
IMAGE_TAG=v1.2.3 bash deploy/release-image.sh
```

`docker login ghcr.io` 使用具有 package read 权限的 GitHub token；私有 GHCR 镜像首次拉取前只需登录一次。`IMAGE_TAG` 必须是已经由 GitHub Actions 发布的版本标签。

`deploy/release-image.sh` 当前只管理 Mneme 的 `migrate`、`app` 和 `worker`，尚未拉起或更新 Memory Agent。脚本成功后必须继续执行以下补充序列；每条 `docker compose run` 都会把数据库初始化或迁移失败作为非零退出码返回，失败时不要继续启动 Agent API/worker：

```bash
set -euo pipefail
docker compose pull memory-agent-db-init memory-agent-migrate memory-agent-api memory-agent-worker
docker compose up -d postgres redis
docker compose run --rm --no-deps memory-agent-db-init
docker compose run --rm --no-deps memory-agent-migrate
docker compose up -d --wait --wait-timeout 180 --no-build --no-deps --force-recreate memory-agent-api memory-agent-worker
docker compose exec memory-agent-api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/readiness').read().decode())"
```

最后一条命令必须返回 `{"status":"ready"}`。它从 Agent API 容器内部访问 readiness，不会把 8010 暴露到宿主机或公网。

默认启动不再包含 Milvus standalone，因此不会拉起 `milvus + etcd + minio` 这组三个高磁盘占用服务。需要文档向量索引和 RAG 检索时，在 `.env` 中设置：

```env
COMPOSE_PROFILES=vector
```

如果你希望应用和 worker 在启动时也等待 Milvus ready，可以在 `.env` 中同时配置以下值，然后重新运行相同的 `IMAGE_TAG=vX.Y.Z bash deploy/release-image.sh` 命令：

```env
COMPOSE_PROFILES=vector
WAIT_FOR_HOSTS=postgres:5432,redis:6379,neo4j:7687,milvus:19530
WAIT_FOR_URLS=http://milvus:9091/healthz
```

如果 `health` 返回正常，说明：

- 数据库迁移容器已经跑完
- 应用容器已经启动
- Vue 前端已经打包进镜像
- 后端和嵌入式 Vue 前端都可以通过 `127.0.0.1:8000` 访问

这时本机访问：

- `http://127.0.0.1:8000/` 是应用首页
- `http://127.0.0.1:8000/docs` 是 API 文档

## 6. Nginx 配置

仓库已经提供了单机代理模板：

- [nginx/reminder.conf](../nginx/reminder.conf)

安装方式：

```bash
sudo cp nginx/reminder.conf /etc/nginx/sites-available/reminder.conf
sudo ln -sfn /etc/nginx/sites-available/reminder.conf /etc/nginx/sites-enabled/reminder.conf
```

然后把模板里的：

```nginx
server_name _;
```

改成你的真实域名，之后检查并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

如果已经完成域名解析，可以继续签 HTTPS：

```bash
sudo certbot --nginx -d your-domain.com
```

## 7. systemd 开机自启

仓库里已经有 Compose 服务模板：

- [deploy/systemd/reminder-compose.service](systemd/reminder-compose.service)

对于已有的源码构建部署，执行这一次最终源码更新和 systemd 安装；此后日常发布只拉取 GHCR 镜像，不再更新服务器上的应用源码：

```bash
cd /opt/reminder
git pull --ff-only
sudo cp deploy/systemd/reminder-compose.service /etc/systemd/system/reminder-compose.service
sudo systemctl daemon-reload
sudo systemctl enable --now reminder-compose.service
sudo systemctl status reminder-compose.service
```

如果你的项目目录不是 `/opt/reminder`，先修改 service 文件里的 `WorkingDirectory`。

## 8. 日常发布与回滚

首次启动步骤中的 `docker login ghcr.io` 使用具有 package read 权限的 GitHub token；登录状态可供后续版本拉取复用。

运行时密钥只保存在服务器的 `.env`，包括 `JWT_SECRET`、数据库密码和 LLM provider API key；不要将它们提交到 GitHub，也不要写入镜像。

发布新版本时，在开发机提交代码并推送版本标签：

```bash
git tag v1.2.3
git push origin v1.2.3
```

推送 `vX.Y.Z` 标签会触发 GitHub Actions 构建和发布同名 GHCR 镜像。发布完成后，在服务器执行：

```bash
cd /opt/reminder
IMAGE_TAG=v1.2.3 bash deploy/release-image.sh
```

`release-image.sh` 尚不管理 Memory Agent。每次 Mneme 发布脚本成功后，都要执行与首次启动相同的 Agent 补充序列，保证 Agent 不会继续运行旧镜像：

```bash
set -euo pipefail
docker compose pull memory-agent-db-init memory-agent-migrate memory-agent-api memory-agent-worker
docker compose up -d postgres redis
docker compose run --rm --no-deps memory-agent-db-init
docker compose run --rm --no-deps memory-agent-migrate
docker compose up -d --wait --wait-timeout 180 --no-build --no-deps --force-recreate memory-agent-api memory-agent-worker
docker compose exec memory-agent-api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/readiness').read().decode())"
```

正常发布不需要在服务器执行 `git pull` 或 `docker compose build`。如需回滚，重新选择已发布的旧版本：

```bash
cd /opt/reminder
IMAGE_TAG=v1.2.2 bash deploy/release-image.sh
```

回滚 Mneme 后同样必须用已经写回 `.env` 的旧镜像标签重新拉取、迁移并强制重建 Agent 服务，否则 Agent 会停留在新版本镜像：

```bash
set -euo pipefail
docker compose pull memory-agent-db-init memory-agent-migrate memory-agent-api memory-agent-worker
docker compose up -d postgres redis
docker compose run --rm --no-deps memory-agent-db-init
docker compose run --rm --no-deps memory-agent-migrate
docker compose up -d --wait --wait-timeout 180 --no-build --no-deps --force-recreate memory-agent-api memory-agent-worker
docker compose exec memory-agent-api python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/health/readiness').read().decode())"
```

脚本和上述补充序列会分别更新 Mneme 与 Memory Agent；发布或回滚后检查：

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

### Memory Agent rebuild and deletion operations

Take a Mneme database backup before a large backfill. Preview, then enqueue the
rebuild from the Mneme application container; no Agent records are written by dry-run:

```bash
docker compose exec app python -m app.mneme.cli.export_agent_projection --dry-run --owner-id 42 --knowledge-base-id kb_123 --batch-size 50
docker compose exec app python -m app.mneme.cli.export_agent_projection --owner-id 42 --knowledge-base-id kb_123 --batch-size 50 --checkpoint /tmp/memory-agent-backfill.json
```

Persist the checkpoint outside an ephemeral container if the job must survive
container replacement. It is atomically advanced after every durable batch/event;
re-running from the checkpoint is safe because projection events and Outbox rows are
idempotent. The checkpoint binds the document version, snapshot hash, projection batch
count, and event index. A new projection for the same document restarts at batch zero;
an identity or batch-count conflict under the same projection ID aborts. Explicit
resume accepts a document or projection ID and optional completed
batch index:

```bash
docker compose exec app python -m app.mneme.cli.export_agent_projection --resume-from PROJECTION_ID --resume-batch-index 3 --batch-size 50 --checkpoint /tmp/memory-agent-backfill.json
```

Inspect Agent state without bypassing event contracts or changing data:

```bash
docker compose exec memory-agent-api python -m services.memory_agent.cli.backfill --owner-id 42 --knowledge-base-id kb_123 --batch-size 100
docker compose exec memory-agent-api python -m services.memory_agent.cli.backfill --resume-from PROJECTION_ID --batch-size 100
```

Source deletion is asynchronous after Mneme commits its deletion event. Keep the
Outbox worker and Memory Agent worker running and monitor dead letters before treating
privacy deletion as complete. The event contains only owner/knowledge-base/session or
document identifiers, stable message identifiers, source version/time, and no source
text. The complete message-ID list is carried without an arbitrary item cap, including
for large conversations. Agent replay is an idempotent success. Legacy backfill uses
the same strict online `document.memory.observed` event, retains real document/chunk
provenance and original time, applies non-explicit governance, and skips secret-matching
evidence; it cannot reconstruct Mneme content that
was already deleted.

Memory Agent migration `20260714_04` adds persistent source-deletion fences and verified
document identity on evidence. Run the Agent migration before enabling the new workers.
Fence order is the envelope `(occurred_at, event_id)`; source version is provenance only.
Old/equal source events are idempotent skips, while strictly newer valid events may
proceed. Knowledge-base fences cover every document, conversation, and explicit-request
source in that owner/KB scope. Observation delivery may race projection delivery: a
missing projection batch is transient and remains pending for retry, while a mismatched
projection/document/chunk/version/hash binding is terminal. Do not purge deletion-fence
rows during ordinary backfill or projection rebuild operations.

## 9. GitHub Actions 镜像发布

相关文件：

- `.github/workflows/reminder-deploy.yml`
- [.github/deploy/github-actions.secrets.example](../.github/deploy/github-actions.secrets.example)

GitHub Actions 使用仓库自带的 `GITHUB_TOKEN` 发布 GHCR 镜像；不需要为源码 SSH 部署配置 `DEPLOY_*` 凭据。服务器拉取私有镜像所需的只读 package 凭据与 Actions 发布凭据相互独立，详见 secrets 示例文件。

## 10. 常用排查命令

看容器状态：

```bash
docker compose ps
```

看应用日志：

```bash
docker compose logs -f app
docker compose logs -f worker
docker compose logs -f migrate
```

看 Nginx 错误日志：

```bash
sudo tail -f /var/log/nginx/error.log
```

如果镜像发布或拉取失败，优先检查：

- GitHub Actions 对应 `vX.Y.Z` 标签的构建是否完成
- `APP_IMAGE_REPOSITORY` 和 `APP_IMAGE_TAG` 是否正确
- 服务器是否已执行 `docker login ghcr.io` 并拥有 package read 权限
- 服务器 `.env` 是否还在
- `docker compose ps` 里是不是有未健康的基础服务

### Milvus 占用磁盘太大

Milvus standalone 本身需要 `milvus`、`etcd`、`minio` 三个服务；这个部署形态适合完整向量检索，但对小机器不轻量。当前 Compose 已经改成默认不启动 Milvus，只有设置 `COMPOSE_PROFILES=vector` 才启动。

如果你之前已经启动过旧版 Compose，旧数据卷还会留在 Docker 里。确认不再需要历史向量索引后，可以清理：

```bash
docker compose down
docker volume rm reminder_milvus_data reminder_minio_data reminder_etcd_data
```

这会删除已有 Milvus 数据；后续如果重新启用 `vector` profile，需要重新索引文档。

## 11. 直接公网暴露的情况

如果你不准备使用 Nginx，也可以把：

```env
APP_HOST_PORT=8000
```

这样 `docker compose` 会把应用直接暴露到宿主机公网 `:8000`。

但在正式环境里，还是更建议保留：

```env
APP_HOST_PORT=127.0.0.1:8000
```

然后把 TLS、域名和公网流量入口统一交给 Nginx。
