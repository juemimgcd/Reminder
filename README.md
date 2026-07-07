# Reminder

> 面向个人长期内容沉淀的记忆型 RAG 系统

`Reminder` 不是单纯的“上传文档 + 问答”示例项目，而是一个围绕 **用户、知识库、文档、记忆条目、画像分析** 设计的记忆型 RAG 系统。它的目标是把个人长期写作、笔记、复盘和经历，逐步沉淀为可检索、可分析、可追踪的个人记忆库。

当前仓库已经完成一条可用主链路：

```text
注册 / 登录
-> 创建默认知识库
-> 上传文档
-> 文档切分与索引
-> 向量检索
-> 基于知识库的 RAG 问答
```

在此基础上，项目还提供了记忆库组织、个人画像、成长分析、建议生成、陪伴回复、图谱分析等能力，并且现在已经补上了可直接使用的前端工作台。

---

## 项目定位

Reminder 的核心不是一次性回答问题，而是让系统随着内容积累，逐步形成对用户的长期理解。

与普通问答型 RAG 相比，这个项目更强调：

- **用户域与知识库域隔离**：不同用户、不同知识库的数据边界明确
- **检索优先**：先索引、再召回、后生成，避免把长文本直接塞进上下文
- **长期沉淀**：不仅保留原文，还尝试组织出记忆条目、画像和成长线索
- **工程化系统结构**：具备数据库模型、鉴权、迁移、任务队列、容器化与向量库接入

---

## 当前架构

当前仓库已经不是只有后端接口的形态，而是前后端一体的完整工程：

- **后端**：`app/mneme` 下的 FastAPI 服务已经收敛为 `bootstrap + domains + clients/infra + schemas/models` 的分层结构
- **前端**：`app/mneme_frontend_v0.2.1` 下的 Vue 3 + Vite 工作台已经从页面原型升级为真实 API 驱动的 workspace
- **本地开发启动**：根目录 `start.sh` 会同时启动后端和前端构建监听，访问入口统一为后端首页
- **Docker 部署**：`Dockerfile` 会先构建前端，再把 `dist` 打进 Python 镜像，最终由后端统一托管页面
- **生产入口**：推荐 `docker compose` + Nginx，Nginx 把所有流量反向代理到 `127.0.0.1:8000`

可以把当前访问链路理解为：

```text
浏览器
-> Nginx
-> FastAPI
-> domain routers / services
-> PostgreSQL / Redis / Milvus / Neo4j / LLM provider
```

前端页面本身也由 FastAPI 返回，因此线上不需要再单独维护一套静态站点目录。

### 后端分层

后端入口由 `app/mneme/bootstrap/app_factory.py` 创建 FastAPI 应用，统一配置 CORS、TrustedHost、异常处理、根路由、业务路由和前端静态托管。`app/mneme/bootstrap/router_registry.py` 只注册 domain router，不再把业务路由散落在旧的 `routers/` 层。

当前 domain 边界如下：

- `domains/auth`：注册、登录、当前用户鉴权
- `domains/users`：用户与知识库管理
- `domains/documents`：文档上传、解析、索引入口
- `domains/retrieval`：聊天问答、query router、上下文组装、融合召回、引用校验
- `domains/memory`：记忆库、文档记忆、治理与重建
- `domains/graph`：Neo4j 图投影、图查询、GraphRAG 扩展
- `domains/profile`：画像、画像证据与 profile 工具
- `domains/analysis`：成长报告与知识库分析
- `domains/advice`：成长建议生成
- `domains/companion`：陪伴式回复
- `domains/tasks`：异步任务查询、取消、重试
- `domains/health`：服务健康、Neo4j 健康和生产就绪检查

横向基础能力放在更底层：

- `clients/`：LLM、embedding、reranker、Neo4j、向量库、文档加载等外部客户端封装
- `infra/`：Celery、缓存、消息队列、限流、断路器、数据库/图/向量存储适配
- `models/` 和 `schemas/`：SQLAlchemy ORM 与 Pydantic API contract
- `pipelines/` 和 `tasks/`：文档索引、记忆抽取、分析、建议、陪伴回复等异步/编排流程

### 前端分层

前端是一个 Vue 3 单页 workspace：

- `src/App.vue`：工作台外壳和主要视图，包含 Dashboard、Notes、Graph、AI Chat、Settings
- `src/composables/useMnemeWorkspace.ts`：集中管理登录态、当前知识库、文档、图谱、记忆、画像、成长分析、建议和聊天状态
- `src/lib/api.ts`：真实后端 API client，统一处理 base URL、JWT header、JSON 包装响应和 GET 请求去重
- `src/lib/previewApi.ts`：预览模式 mock API，用于没有后端服务时做前端布局检查
- `src/types.ts`：前端共享 API 数据类型

前端在独立开发模式下通过 Vite dev server 访问后端；在默认本地联动和 Docker 部署模式下，`npm run dev:embed` / `npm run build` 生成 `dist`，由 FastAPI fallback 路由统一托管。

### 数据与任务流

```text
用户登录
-> Vue workspace 保存 JWT 和当前知识库
-> domain API 处理知识库、文档、图谱、记忆、画像、分析、聊天请求
-> 文档索引任务进入 Celery worker
-> PostgreSQL 保存业务数据和任务记录
-> Milvus 保存向量索引
-> Neo4j 保存图投影
-> LLM provider 生成问答、画像、建议、陪伴回复
-> FastAPI 统一返回 API 数据或前端页面
```

---

## 当前能力概览

### 已实现且主链路可用

- 用户注册、登录、获取当前用户
- 默认知识库自动创建
- 用户知识库管理（创建、查询、删除）
- 文档上传与本地落盘
- 文档列表查询、删除
- 文档解析、文本切分、Chunk 入库
- 文档索引任务提交、轮询、取消、重试
- 基于 Milvus 的向量索引与检索
- 基于知识库的 RAG 问答
- 图谱查看、图谱重建、图谱检索
- 记忆库视图查询、文档记忆视图、治理信息查看
- 个人画像、证据分析、成长报告、分析建议接口
- 陪伴式回复接口
- 已集成可直接使用的前端工作台

### 已有能力，但仍在持续完善

- 记忆条目自动抽取与索引链路还可以继续打磨
- 建议生成（advice）和陪伴回复（companion）仍有持续优化空间
- 聊天会话与任务记录模型虽已接入部分流程，但业务闭环还可以继续补强
- 前端当前已经覆盖主要后端能力，但交互体验和运维页仍可以继续细化

这意味着当前项目的**稳定主能力**已经不只是：

1. 认证
2. 知识库管理
3. 文档索引
4. RAG 问答

还包括：

5. 图谱与记忆视图
6. 画像与成长分析
7. 前后端一体化部署与使用

---

## 技术栈

### Web / API

- **FastAPI**：API 框架
- **Pydantic v2**：请求与响应数据校验
- **Uvicorn**：ASGI 运行服务
- **Celery**：异步任务处理

### Frontend

- **Vue 3**：前端 UI
- **TypeScript**：前端类型系统
- **Vite**：前端构建与开发工具
- **D3**：图谱可视化

### 数据层

- **PostgreSQL**：业务数据存储
- **SQLAlchemy 2.x Async**：异步 ORM
- **asyncpg**：PostgreSQL 异步驱动
- **Alembic**：数据库迁移管理
- **Redis**：Celery broker / result backend
- **Neo4j**：图投影存储与图查询后端

### RAG / AI 能力

- **LangChain**：RAG 编排与模型调用封装
- **Milvus**：向量数据库
- **langchain-milvus**：Milvus 集成
- **sentence-transformers / BAAI bge-m3**：默认 Embedding 路径
- **OpenAI-compatible LLM API**：支持 Qwen、MiMo、Kimi、GLM、DeepSeek 等 provider，默认走 DeepSeek
- **PyPDF**：PDF 文档解析

### 鉴权与安全

- **JWT Bearer Token**
- **python-jose**：JWT 编解码
- **passlib + bcrypt**：密码哈希

### 部署

- **Docker / Docker Compose**
- **Nginx**
- **Milvus Standalone 依赖组件**：etcd、MinIO

---

## 核心数据结构

项目目前围绕以下几类核心对象建模：

- **User**：用户
- **KnowledgeBase**：知识库，归属于某个用户
- **Document**：上传文档及其元信息
- **Chunk**：文档切分后的文本片段
- **MemoryEntry**：从内容中沉淀出的记忆条目
- **ChatSession**：聊天会话
- **TaskRecord**：索引与异步任务记录

可以把当前的数据流理解为：

```text
用户
-> 知识库
-> 文档
-> 文档切分 Chunk
-> 向量索引 / 检索
-> 回答、画像、成长分析、记忆视图、图谱分析
```

---

## 主要接口

### 认证

- `POST /auth/register`：注册用户并自动创建默认知识库
- `POST /auth/login`：登录，返回 JWT Token
- `GET /auth/me`：获取当前登录用户
- `GET /health/neo4j`：检查 Neo4j 图投影连通性

### 用户与知识库

- `GET /users`：用户列表
- `POST /users/{user_id}/knowledge-bases`：创建知识库
- `GET /users/{user_id}/knowledge-bases`：查询用户知识库

### 文档

- `POST /kb/documents/upload`：上传文档
- `GET /kb/documents`：查询文档列表
- `DELETE /kb/documents/{document_id}`：删除文档
- `POST /kb/documents/{document_id}/index`：为文档建立索引

### 任务

- `GET /tasks`：查看任务列表
- `POST /tasks/{task_id}/cancel`：取消任务
- `POST /tasks/{task_id}/retry`：重试任务

### RAG / 图谱 / 记忆 / 分析

- `POST /kb/chat/query`：基于知识库进行问答
- `GET /graph`：查看当前用户图谱
- `GET /graph/knowledge-bases/{knowledge_base_id}`：查看知识库图谱
- `GET /graph/documents/{document_id}`：查看文档图谱
- `POST /graph/rebuild`：重建当前用户的 Neo4j 图投影
- `POST /graph/knowledge-bases/{knowledge_base_id}/rebuild`：重建指定知识库的 Neo4j 图投影
- `GET /memory/knowledge-bases/{knowledge_base_id}/library`：查看知识库记忆库
- `GET /memory/documents/{document_id}/library`：查看文档记忆库
- `GET /profile/knowledge-bases/{knowledge_base_id}`：生成个人画像
- `GET /analysis/knowledge-bases/{knowledge_base_id}/growth`：生成成长报告
- `POST /advice/knowledge-bases/{knowledge_base_id}`：生成建议
- `POST /companion/knowledge-bases/{knowledge_base_id}/reply`：生成陪伴式回复

---

## 目录结构

```text
.
├─ app/
│  ├─ mneme/
│  │  ├─ bootstrap/                 # FastAPI 创建、路由注册、lifespan、前端托管
│  │  ├─ domains/                   # auth/users/documents/retrieval/memory/graph 等业务域
│  │  ├─ clients/                   # LLM、embedding、reranker、Neo4j、向量库等客户端
│  │  ├─ infra/                     # Celery、缓存、消息队列、限流、存储适配
│  │  ├─ models/                    # SQLAlchemy ORM
│  │  ├─ schemas/                   # Pydantic API contract
│  │  ├─ pipelines/                 # 索引、记忆、分析、建议、陪伴回复编排
│  │  └─ tasks/                     # Celery task 入口
│  └─ mneme_frontend_v0.2.1/
│     ├─ src/App.vue                # Vue workspace 外壳
│     ├─ src/composables/           # workspace 状态和业务动作
│     ├─ src/lib/                   # API client、preview API、工具函数
│     └─ src/types.ts               # 前端共享类型
├─ alembic/                         # 数据库迁移
├─ deploy/                          # 部署文档、Nginx、systemd、环境模板
├─ docker/                          # 容器启动脚本
├─ storage/                         # 本地存储目录
├─ main.py                          # 应用入口
├─ start.sh                         # 本地前后端联动启动脚本
├─ upgrade.sh                       # 服务器升级脚本
├─ docker-compose.yml
├─ Dockerfile
└─ requirements.txt
```

---

## 环境变量

项目默认从根目录 `.env` 读取配置，可以先复制示例文件：

```bash
cp .env-example .env
```

PowerShell:

```powershell
Copy-Item .env-example .env
```

常用配置项包括：

### 基础

- `DATABASE_URL`
- `JWT_SECRET`
- `RAW_FILE_DIR`
- `APP_PORT`
- `APP_HOST_PORT`
- `FORWARDED_ALLOW_IPS`
- `TRUSTED_HOSTS`

### LLM

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `DASHSCOPE_API_KEY`
- `MIMO_API_KEY`
- `KIMI_API_KEY`
- `GLM_API_KEY`
- `DEEPSEEK_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `LLM_TEMPERATURE`

`LLM_PROVIDER` 目前支持 `qwen`、`mimo`、`kimi`、`glm`、`deepseek`。默认是 `deepseek`；如果不想分别配置各家 key，也可以统一使用 `LLM_API_KEY`。`LLM_BASE_URL` 和 `LLM_MODEL_NAME` 为空时会按 provider 使用默认 OpenAI-compatible 地址和模型，也可以手动覆盖。

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=replace-with-your-provider-key
LLM_BASE_URL=
LLM_MODEL_NAME=
```

### Embedding / Vector Store

- `EMBEDDING_MODEL_NAME`
- `EMBEDDING_MODEL_PATH`
- `EMBEDDING_CACHE_DIR`
- `EMBEDDING_LOCAL_FILES_ONLY`
- `EMBEDDING_PRELOAD_ON_STARTUP`
- `RERANKER_ENABLED`
- `RERANKER_MODEL_NAME`
- `RERANKER_MODEL_PATH`
- `RERANKER_CACHE_DIR`
- `RERANKER_LOCAL_FILES_ONLY`
- `RERANKER_PRELOAD_ON_STARTUP`
- `HF_ENDPOINT`
- `HF_HUB_ETAG_TIMEOUT`
- `HF_HUB_DOWNLOAD_TIMEOUT`
- `GRAPH_BACKEND`
- `MILVUS_URI`
- `MILVUS_DB_NAME`
- `MILVUS_COLLECTION_NAME`
- `MILVUS_INDEX_TYPE`
- `MILVUS_METRIC_TYPE`
- `MILVUS_SEARCH_PARAMS`
- `RETRIEVAL_VECTOR_RECALL_K`
- `RETRIEVAL_KEYWORD_RECALL_K`
- `RETRIEVAL_MEMORY_RECALL_K`
- `RETRIEVAL_RERANK_CANDIDATE_K`
- `RETRIEVAL_CONTEXT_BUDGET_CHARS`
- `NEO4J_ENABLED`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`

### Task / Queue

- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_INDEX_QUEUE`
- `CELERY_WORKER_CONCURRENCY`
- `CELERY_LOG_LEVEL`

Embedding 模块现在会按下面的顺序选择模型来源：

1. `EMBEDDING_MODEL_PATH` 指定的本地目录
2. `EMBEDDING_MODEL_NAME` 指向的本地目录
3. `EMBEDDING_CACHE_DIR` 下已经缓存好的 Hugging Face snapshot
4. `EMBEDDING_MODEL_NAME` 对应的远端仓库

如果本地已经有缓存 snapshot，服务会直接加载本地路径，不再每次启动都去 Hugging Face 解析仓库。

如果你希望在最终候选排序上启用交叉编码器重排，可以额外配置：

```env
RERANKER_ENABLED=true
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3
RERANKER_CACHE_DIR=./storage/model_cache/reranker
RERANKER_LOCAL_FILES_ONLY=false
RERANKER_PRELOAD_ON_STARTUP=false
```

当前检索链路已经支持单独调节三路召回候选池和最终上下文预算：

```env
RETRIEVAL_VECTOR_RECALL_K=12
RETRIEVAL_KEYWORD_RECALL_K=12
RETRIEVAL_MEMORY_RECALL_K=8
RETRIEVAL_RERANK_CANDIDATE_K=20
RETRIEVAL_CONTEXT_BUDGET_CHARS=4000
```

Neo4j 是默认图后端。如果你已有历史数据，建议在首次启用后执行一次：

```bash
python scripts/rebuild_neo4j_graph.py
```

这个脚本会把已有用户、知识库、文档、memory entry 和文档关联边回填到 Neo4j。

### Docker 构建可选项

- `PYTHON_VERSION`
- `PIP_INDEX_URL`
- `PIP_EXTRA_INDEX_URL`

---

## 本地启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

前端依赖需要单独安装一次：

```bash
cd app/mneme_frontend_v0.2.1
npm install
cd ../..
```

### 2. 配置环境变量

复制 `.env-example` 为 `.env`，并补充你的真实配置。

如果你希望 embedding 只在第一次预热时联网，推荐这样配置：

```env
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_CACHE_DIR=./storage/model_cache/sentence_transformers
EMBEDDING_LOCAL_FILES_ONLY=false
EMBEDDING_PRELOAD_ON_STARTUP=false
HF_ENDPOINT=https://hf-mirror.com
HF_HUB_ETAG_TIMEOUT=60
HF_HUB_DOWNLOAD_TIMEOUT=600
```

第一次预热模型：

```bash
python scripts/preload_embedding.py
```

PowerShell 如果安装的是 Python Launcher：

```powershell
py -3 scripts/preload_embedding.py
```

预热成功后，把 `.env` 改成：

```env
EMBEDDING_LOCAL_FILES_ONLY=true
```

这样后续应用进程和 Celery worker 都会优先走本地模型，不再依赖运行时下载。

### 3. 准备基础服务

完整功能建议至少准备：

- PostgreSQL
- Redis
- Milvus
- Neo4j

如果只是在本地调试纯接口流程，也至少要确保 `DATABASE_URL` 可用。

### 4. 执行迁移

```bash
alembic upgrade head
```

### 5. 启动服务

现在推荐直接使用根目录启动脚本：

```bash
bash start.sh
```

这条命令会同时启动：

- FastAPI 后端
- Vue 前端 `npm run dev:embed`，内部执行 `vite build --watch`

前端构建结果会持续写入 `app/mneme_frontend_v0.2.1/dist`，再由后端统一托管。

默认访问地址：

- 应用首页：`http://127.0.0.1:8000/`
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

常用参数：

```bash
bash start.sh --backend-only
bash start.sh --frontend-only
bash start.sh --backend-port 8001
```

如果你想单独跑前端开发服务器，也可以：

```bash
cd app/mneme_frontend_v0.2.1
npm run dev
```

如果你只想单独起后端，也仍然可以直接执行：

```bash
uvicorn main:app --reload
```

如果你希望应用启动时就把 embedding 预热到当前进程，可以额外配置：

```env
EMBEDDING_PRELOAD_ON_STARTUP=true
```

注意：`--reload` 会启动额外进程，本地开发时可能看到 embedding 初始化日志出现多次；这不等于每次都重新下载模型。

---

## Docker 部署

如果你准备直接在云服务器上部署，当前仓库推荐用 `docker compose` 直接起整套服务：

```bash
cp .env-example .env
docker compose up -d --build
```

PowerShell:

```powershell
Copy-Item .env-example .env
docker compose up -d --build
```

这套 Compose 现在会启动：

- `app`：FastAPI 应用，内嵌 Vue 前端页面
- `migrate`：数据库迁移任务
- `worker`：Celery 文档索引 worker
- `redis`：Celery broker / result backend
- `postgres`：业务数据库
- `milvus`：向量数据库
- `neo4j`：图数据库
- `etcd / minio`：Milvus standalone 依赖

### 当前 Docker 架构

当前 `Dockerfile` 已经改成多阶段构建：

1. Node 阶段构建 Vue 前端
2. Python 阶段安装后端依赖
3. 把前端 `dist` 复制进应用镜像
4. 最终由 FastAPI 统一托管首页和静态资源

这意味着线上访问 `/` 时，会直接拿到打包后的前端页面，不再需要单独部署静态资源目录。

### 首次上线前至少要改的配置

- `LLM_PROVIDER`
- `DASHSCOPE_API_KEY` / `MIMO_API_KEY` / `KIMI_API_KEY` / `GLM_API_KEY` / `DEEPSEEK_API_KEY`
- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `NEO4J_PASSWORD`
- `MINIO_ROOT_PASSWORD`
- 如果你有本地 embedding 模型，建议配置 `EMBEDDING_MODEL_PATH`
- 如果你走 Nginx 反代，建议保留 `APP_HOST_PORT=127.0.0.1:8000`
- 如果你走 Nginx 反代，建议配置 `FORWARDED_ALLOW_IPS=127.0.0.1`
- 如果你有正式域名，建议把 `TRUSTED_HOSTS` 改成你的域名列表

### 默认端口暴露策略

当前 Compose 默认只把应用端口公开到宿主机，内部基础设施端口全部绑定到 `127.0.0.1`：

- `app`：`${APP_HOST_PORT:-127.0.0.1:8000}`
- `postgres / redis / minio / milvus / neo4j`：仅宿主机本地可访问

同时，后端现在会信任来自 `FORWARDED_ALLOW_IPS` 的代理头，并可通过 `TRUSTED_HOSTS` 限制允许访问的 Host，适合放在 Nginx 后面统一处理 HTTPS 和域名入口。

这样更适合直接上云服务器，避免把数据库、Redis、Milvus、Neo4j 直接暴露到公网。

### 常用运维命令

查看服务状态：

```bash
docker compose ps
```

查看应用日志：

```bash
docker compose logs -f app
```

查看 worker 日志：

```bash
docker compose logs -f worker
```

停止服务：

```bash
docker compose down
```

---

## 升级脚本

如果你已经把项目部署在 Linux 服务器上，现在推荐直接用根目录脚本升级：

```bash
bash upgrade.sh
```

这个脚本会自动完成：

- 拉取最新代码
- 重新构建并重启 Compose 服务
- 同步 `deploy/nginx/reminder.conf` 到系统 Nginx
- 检查并重载 Nginx
- 输出当前容器状态

如果这次更新不想动 Nginx，可以这样跳过：

```bash
ENABLE_NGINX_SYNC=0 bash upgrade.sh
```

如果你希望在代码 push 到 GitHub 后自动完成检查和远程部署，仓库现在也提供了这套文件：

- `.github/workflows/reminder-deploy.yml`
- `github-actions.deploy.sh`
- `github-actions.secrets.example`

其中真正的 GitHub Actions 工作流文件必须放在 `.github/workflows/`，根目录则保留了服务器执行脚本和 Secrets / Variables 示例，方便直接修改。

如果你不想手动去 GitHub 页面一项项填写，也可以直接在本机运行根目录脚本：

```powershell
.\setup_github_actions.ps1
```

它会自动安装 `gh`、引导你登录 GitHub，并把部署所需的 repository variables / secrets 一次性配置好。

这套 workflow 同时支持两种远程登录方式：

- 推荐：`DEPLOY_SSH_KEY`
- 兼容：`DEPLOY_PASSWORD`

如果你当前是通过 FinalShell 的用户名 + 密码登录服务器，也可以先直接配置 `DEPLOY_PASSWORD` 跑通，再在后面切换到 SSH key。

另外，`DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_PORT` 现在支持两种来源：

- `Repository variables`：推荐
- `Repository secrets`：也可以

也就是说，真正必须放进 Secrets 的通常只有：

- `DEPLOY_SSH_KEY`

或者密码模式下的：

- `DEPLOY_PASSWORD`

---

## 适用场景

Reminder 更适合这类需求：

- 想沉淀个人博客、笔记、复盘、文章
- 想基于长期材料做检索与问答
- 想在知识库基础上做画像、阶段分析与成长总结
- 想搭建一个偏“个人记忆库”方向的 RAG 系统

如果你需要的是一个简单的 FAQ Demo，这个项目会显得偏重；但如果你希望从一开始就保留“用户 - 知识库 - 记忆 - 分析”这条演进路径，它会更合适。

---

## 当前状态总结

当前仓库的真实定位可以概括为：

> 一个基于 FastAPI、Vue 3、PostgreSQL、Redis、Milvus、Neo4j、LangChain 和 OpenAI-compatible LLM provider 的个人记忆型 RAG 系统，已完成认证、知识库、文档上传索引与问答主链路，并具备图谱、记忆、画像、成长分析与前后端一体化部署能力。
