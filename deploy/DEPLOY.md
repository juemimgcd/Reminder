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
- 前端页面和后端 API 都由 `reminder-app` 统一提供

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
- `CORS_ALLOWED_ORIGINS=["https://your-domain.com","http://your-domain.com"]`
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_PASSWORD`
- `NEO4J_PASSWORD`
- `DASHSCOPE_API_KEY`
- `JWT_SECRET`

说明：

- `APP_HOST_PORT=127.0.0.1:8000` 表示应用只暴露给本机，公网访问统一走 Nginx。
- Compose 内部会自动使用 `postgres`、`redis`、`milvus`、`neo4j` 这些容器名互连，不需要你手工改容器间地址。

## 5. 首次启动

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

如果 `health` 返回正常，说明：

- 数据库迁移容器已经跑完
- 应用容器已经启动
- 前端已经打包进镜像
- 后端和嵌入式前端都可以通过 `127.0.0.1:8000` 访问

这时本机访问：

- `http://127.0.0.1:8000/` 是应用首页
- `http://127.0.0.1:8000/docs` 是 API 文档

## 6. Nginx 配置

仓库已经提供了单机代理模板：

- [deploy/nginx/reminder.conf](/E:/python_files/agentic_rag/deploy/nginx/reminder.conf)

安装方式：

```bash
sudo cp deploy/nginx/reminder.conf /etc/nginx/sites-available/reminder.conf
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

- [deploy/systemd/reminder-compose.service](/E:/python_files/agentic_rag/deploy/systemd/reminder-compose.service)

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
3. 同步 `deploy/nginx/reminder.conf`
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

- [github-actions.deploy.sh](/E:/python_files/agentic_rag/github-actions.deploy.sh)
- [github-actions.secrets.example](/E:/python_files/agentic_rag/github-actions.secrets.example)
- `.github/workflows/reminder-deploy.yml`

说明：

- 真正的 workflow 文件必须放在 `.github/workflows/`
- 根目录 `github-actions.deploy.sh` 会在服务器上调用 `upgrade.sh`
- 根目录 `github-actions.secrets.example` 用来说明 GitHub 仓库需要配置哪些 Secrets 和 Variables

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

- push 到 `master` 时自动执行
- 也支持在 GitHub Actions 页面手动触发
- 先做前端检查和后端源码编译检查
- 检查通过后再 SSH 到服务器执行部署脚本

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
