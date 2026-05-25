# Mneme 服务器部署说明

这套仓库更适合用下面这条链路部署：

本地开发机：
`git add` -> `git commit` -> `git push origin master`

云服务器：
`git pull` -> `docker compose up -d --build`

GitHub 只负责中转代码，云服务器负责拉代码、构建镜像、启动服务。

## 1. 先把本地代码推到 GitHub

第一次推送：

```bash
git remote add origin git@github.com:your-name/your-repo.git
git branch -M master
git add .
git commit -m "prepare deployment"
git push -u origin master
```

如果仓库里已经把 `storage/`、前端 `node_modules/`、模型缓存之类的大文件跟踪进 Git 了，建议先从索引里移除，再提交一次：

```bash
git rm -r --cached storage frontend_build/mneme_frontend/node_modules frontend_build/mneme_frontend/dist
git rm --cached sentence_transformers.zip
git commit -m "stop tracking local artifacts"
git push
```

上面只会取消 Git 跟踪，不会删除你本地磁盘上的文件。

## 2. 云服务器安装基础环境

以下命令以 Ubuntu 为例：

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin nginx certbot python3-certbot-nginx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

执行完 `usermod` 后重新登录一次服务器。

## 3. 给云服务器配置 GitHub 拉代码权限

如果仓库是私有仓库，推荐在服务器上用 deploy key：

```bash
ssh-keygen -t ed25519 -C "mneme-deploy"
cat ~/.ssh/id_ed25519.pub
```

把公钥加到：
`GitHub -> 仓库 -> Settings -> Deploy keys -> Add deploy key`

然后测试：

```bash
ssh -T git@github.com
```

## 4. 在服务器上克隆项目

```bash
sudo mkdir -p /opt/mneme
sudo chown -R $USER:$USER /opt/mneme
git clone git@github.com:your-name/your-repo.git /opt/mneme
cd /opt/mneme
```

## 5. 配置后端环境变量

复制模板：

```bash
cp deploy/env/backend.production.example .env
```

你至少要改这些值：

- `APP_HOST_PORT=127.0.0.1:8000`
- `CORS_ALLOWED_ORIGINS=["https://your-domain.com"]`
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_PASSWORD`
- `DASHSCOPE_API_KEY`
- `JWT_SECRET`

说明：

- `APP_HOST_PORT=127.0.0.1:8000` 表示后端只监听服务器本机，外网访问交给 Nginx。
- `docker-compose.yml` 会让容器内应用使用 `postgres`、`redis`、`milvus`、`neo4j` 这些容器名互连，你不用手工改容器内部地址。

## 6. 首次启动后端服务

```bash
cd /opt/mneme
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

如果 `health` 正常返回，说明后端、数据库、Redis、Milvus、Neo4j、迁移链路都起来了。

## 7. 配置 systemd 开机自启

先把模板复制到系统目录：

```bash
sudo cp deploy/systemd/mneme-compose.service /etc/systemd/system/mneme-compose.service
```

如果你的项目目录不是 `/opt/mneme`，先改这个文件里的 `WorkingDirectory`。

然后启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mneme-compose.service
sudo systemctl status mneme-compose.service
```

以后常用命令：

```bash
sudo systemctl restart mneme-compose.service
sudo systemctl reload mneme-compose.service
sudo journalctl -u mneme-compose.service -n 100 --no-pager
```

## 8. 如果要部署前端

先安装 Node.js 20 以上，然后在服务器执行：

```bash
cd /opt/mneme/frontend_build/mneme_frontend
cp ../../deploy/env/frontend.production.example .env.production.local
npm ci
npm run build
sudo mkdir -p /var/www/mneme-frontend
sudo cp -r dist/. /var/www/mneme-frontend/
```

前端生产环境模板里已经把 API 地址设成了 `/api`，配合下面的 Nginx 反向代理即可。

## 9. 配置 Nginx

复制模板：

```bash
sudo cp deploy/nginx/mneme.conf /etc/nginx/sites-available/mneme.conf
sudo ln -s /etc/nginx/sites-available/mneme.conf /etc/nginx/sites-enabled/mneme.conf
```

把模板里的：

- `server_name your-domain.com;`
- `root /var/www/mneme-frontend;`

改成你的实际域名和前端目录。

检查并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

如果已经绑定域名，再签 HTTPS：

```bash
sudo certbot --nginx -d your-domain.com
```

## 10. 以后更新代码

本地：

```bash
git add .
git commit -m "your update"
git push origin master
```

服务器：

```bash
cd /opt/mneme
bash deploy/scripts/update_server.sh
```

这个脚本会：

- 拉取最新代码
- 重新构建并重启 Compose 服务
- 输出当前容器状态

## 双服务器部署示例

如果你按下面这套分工部署：

- 腾讯云 `124.223.14.145`：后端
- 阿里云 `8.147.57.104`：前端

那就按这个思路配置。

### 后端服务器 `124.223.14.145`

后端 `.env` 里建议至少确认这些值：

```env
APP_HOST_PORT=8000
CORS_ALLOWED_ORIGINS=["http://8.147.57.104","http://8.147.57.104:80","https://8.147.57.104"]
```

解释：

- `APP_HOST_PORT=8000` 表示 Docker 会把后端服务暴露到公网 `124.223.14.145:8000`
- 前端最终是用户浏览器直接访问后端，所以跨域要放行前端页面所在的源，也就是 `8.147.57.104`

同时你要在腾讯云控制台放行安全组端口：

- `8000/tcp`：给前端和浏览器访问后端 API

如果以后你改成域名访问，再把 `CORS_ALLOWED_ORIGINS` 改成正式域名即可。

### 前端服务器 `8.147.57.104`

前端构建时，把 `frontend_build/mneme_frontend/.env.production.local` 配成：

```env
VITE_API_BASE_URL=http://124.223.14.145:8000
VITE_API_PREFIX=
VITE_USE_MOCKS=false
```

这样前端打包后，浏览器会直接请求：

```text
http://124.223.14.145:8000/...
```

这种双机部署下，前端服务器的 Nginx 只负责托管静态文件，不需要反向代理 `/api`。
可直接使用：

- `deploy/nginx/mneme.frontend-static.conf`

阿里云控制台要放行端口：

- `80/tcp`：给用户访问前端页面
- `443/tcp`：如果后面你要上 HTTPS

### 你现在这套双机部署的关键点

- 不是阿里云服务器去请求腾讯云服务器，而是用户浏览器加载前端后，再去请求腾讯云后端
- 所以后端必须对公网可访问，不能只绑定 `127.0.0.1`
- 跨域放行的是前端页面的来源 `http://8.147.57.104`
- 如果前端走 HTTPS，而后端还是 HTTP，浏览器后面可能会拦 mixed content；长期建议两边都挂域名并上 HTTPS

## 11. 常见排查

看容器状态：

```bash
docker compose ps
```

看应用日志：

```bash
docker compose logs app --tail=200
docker compose logs worker --tail=200
docker compose logs migrate --tail=200
```

看 Nginx 日志：

```bash
sudo tail -f /var/log/nginx/error.log
```

如果 `git pull` 失败，优先检查：

- 服务器 SSH key 是否加到了 GitHub
- 服务器当前目录是不是正确的仓库目录
- 远端分支是不是 `master`
- 本地是否把部署所需文件都提交到了 GitHub
