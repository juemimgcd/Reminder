# Reminder 部署说明

本文档基于当前仓库的推荐部署方式整理：单台 Linux 服务器、Docker Compose 启动全套服务、Nginx 对外代理、根目录 `upgrade.sh` 负责升级。

## 1. 部署模型

当前推荐的是这条链路：

```text
本地开发 -> git push -> 服务器执行 bash upgrade.sh
```

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

## 3. 克隆项目

```bash
sudo mkdir -p /opt/reminder
sudo chown -R $USER:$USER /opt/reminder
git clone <your-repo-url> /opt/reminder
cd /opt/reminder
```

如果仓库是私有仓库，建议先配置 deploy key 或服务器 SSH key，再执行 `git clone`。

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

## 5. 首次启动

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

默认启动不再包含 Milvus standalone，因此不会拉起 `milvus + etcd + minio` 这组三个高磁盘占用服务。需要文档向量索引和 RAG 检索时，使用：

```bash
COMPOSE_PROFILES=vector docker compose up -d --build
```

如果你希望应用和 worker 在启动时也等待 Milvus ready，可以在 `.env` 中同时配置：

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

安装：

```bash
sudo cp deploy/systemd/reminder-compose.service /etc/systemd/system/reminder-compose.service
sudo systemctl daemon-reload
sudo systemctl enable --now reminder-compose.service
sudo systemctl status reminder-compose.service
```

如果你的项目目录不是 `/opt/reminder`，先修改 service 文件里的 `WorkingDirectory`。

## 8. 日常升级

代码更新推荐统一走根目录脚本：

```bash
cd /opt/reminder
bash upgrade.sh
```

这个脚本会自动完成：

1. 拉取最新代码
2. 重新构建并重启 Compose 服务
3. 同步 `nginx/reminder.conf`
4. 检查并重载 Nginx
5. 输出容器状态

如果你这次只想更新容器，不想覆盖 Nginx：

```bash
cd /opt/reminder
ENABLE_NGINX_SYNC=0 bash upgrade.sh
```

`deploy/scripts/update_server.sh` 现在只是兼容入口，本质上会转到根目录 `upgrade.sh`。

## 9. GitHub Actions 自动部署

如果你不想每次手动 SSH 到服务器执行 `bash upgrade.sh`，也可以开启仓库里的 GitHub Actions 自动部署。

相关文件：

- [.github/deploy/github-actions.deploy.sh](../.github/deploy/github-actions.deploy.sh)
- [.github/deploy/github-actions.secrets.example](../.github/deploy/github-actions.secrets.example)
- `.github/workflows/reminder-deploy.yml`

说明：

- 真正的 workflow 文件必须放在 `.github/workflows/`
- `.github/deploy/github-actions.deploy.sh` 会在服务器上调用 `upgrade.sh`
- `.github/deploy/github-actions.secrets.example` 用来说明 GitHub 仓库需要配置哪些 Secrets 和 Variables

至少需要在 GitHub 仓库里配置这些认证 Secrets 之一：

- `DEPLOY_SSH_KEY` 或 `DEPLOY_PASSWORD`

推荐配置这些 Variables：

- `DEPLOY_HOST=your-server-ip-or-domain`
- `DEPLOY_PORT=22`
- `DEPLOY_USER=your-server-user`
- `DEPLOY_APP_DIR=/opt/reminder`
- `DEPLOY_BRANCH=master`
- `DEPLOY_ENABLE_NGINX_SYNC=1`

`DEPLOY_HOST`、`DEPLOY_PORT`、`DEPLOY_USER` 现在既支持放在 Variables，也支持放在 Secrets；更推荐放在 Variables，管理起来更直观。

默认行为：

- push 到 `master` 时自动执行前端类型检查和后端编译检查
- 也支持在 GitHub Actions 页面手动触发
- 先做 Vue 前端类型检查和后端源码编译检查
- 只有手动触发并把 `run_deploy` 选成 `true` 时，检查通过后才会 SSH 到服务器执行部署脚本

如果你当前服务器还是 FinalShell 这类“用户名 + 密码”登录方式，也可以先直接配置：

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PASSWORD`

这时 workflow 会自动切到密码登录模式，不强制要求先准备 SSH key。

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

如果升级失败，优先检查：

- `git remote -v` 是否正确
- 服务器 SSH key 是否有拉取权限
- 当前目录是不是仓库根目录
- `.env` 是否还在
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
