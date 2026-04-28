# Mneme

> 面向个人长期内容沉淀的记忆型 RAG 后端

`Mneme` 不是单纯的“上传文档 + 问答”示例项目，而是一个围绕 **用户、知识库、文档、记忆条目、画像分析** 设计的后端服务。它的目标是把个人长期写作、笔记、复盘和经历，逐步沉淀为可检索、可分析、可追踪的个人记忆库。

当前仓库已经完成一条可用主链路：

```text
注册 / 登录
-> 创建默认知识库
-> 上传文档
-> 文档切分与索引
-> 向量检索
-> 基于知识库的 RAG 问答
```

在此基础上，项目还提供了记忆库组织、个人画像、成长分析、建议生成、陪伴回复等能力的代码框架。

---

## 项目定位

Mneme 的核心不是一次性回答问题，而是让系统随着内容积累，逐步形成对用户的长期理解。

与普通问答型 RAG 相比，这个项目更强调：

- **用户域与知识库域隔离**：不同用户、不同知识库的数据边界明确
- **检索优先**：先索引、再召回、后生成，避免把长文本直接塞进上下文
- **长期沉淀**：不仅保留原文，还尝试组织出记忆条目、画像和成长线索
- **工程化后端结构**：具备数据库模型、鉴权、迁移、容器化与向量库接入

---

## 当前能力概览

### 已实现且主链路可用

- 用户注册、登录、获取当前用户
- 默认知识库自动创建
- 用户知识库管理
- 文档上传与本地落盘
- 文档解析、文本切分、Chunk 入库
- 基于 Milvus 的向量索引与检索
- 基于知识库的 RAG 问答
- 记忆库视图查询
- 个人画像 / 成长报告的生成接口

### 已有代码框架，但仍在完善

- 记忆条目自动抽取尚未完全接入主索引流程
- 建议生成（advice）接口仍需进一步打磨
- 陪伴式回复（companion）接口仍需进一步打磨
- 聊天会话与任务记录模型已预留，但尚未形成完整业务闭环

这意味着当前项目的**稳定主能力**是：

1. 认证
2. 知识库管理
3. 文档索引
4. RAG 问答

而画像、成长、建议、陪伴等属于**已进入实现阶段的增强能力**。

---

## 技术栈

### Web / API

- **FastAPI**：API 框架
- **Pydantic v2**：请求与响应数据校验
- **Uvicorn**：ASGI 运行服务

### 数据层

- **PostgreSQL**：业务数据存储
- **SQLAlchemy 2.x Async**：异步 ORM
- **asyncpg**：PostgreSQL 异步驱动
- **Alembic**：数据库迁移管理
- **Neo4j（可选）**：图投影存储与图查询后端

### RAG / AI 能力

- **LangChain**：RAG 编排与模型调用封装
- **Milvus**：向量数据库
- **langchain-milvus**：Milvus 集成
- **sentence-transformers/all-mpnet-base-v2**：默认 Embedding 模型
- **DashScope Compatible API / Qwen**：默认大模型接入
- **PyPDF**：PDF 文档解析

### 鉴权与安全

- **JWT Bearer Token**
- **python-jose**：JWT 编解码
- **passlib + bcrypt**：密码哈希

### 部署

- **Docker / Docker Compose**
- **Milvus Standalone 依赖组件**：etcd、MinIO

---

## 核心数据结构

项目目前围绕以下几类核心对象建模：

- **User**：用户
- **KnowledgeBase**：知识库，归属于某个用户
- **Document**：上传文档及其元信息
- **Chunk**：文档切分后的文本片段
- **MemoryEntry**：从内容中沉淀出的记忆条目
- **ChatSession**：聊天会话预留模型
- **TaskRecord**：任务记录预留模型

可以把当前的数据流理解为：

```text
用户
-> 知识库
-> 文档
-> 文档切分 Chunk
-> 向量索引 / 检索
-> 回答、画像、成长分析
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
- `POST /kb/documents/{document_id}/index`：为文档建立索引

### RAG / 记忆 / 分析

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

### 开发中接口

- `POST /advice/knowledge-bases/{knowledge_base_id}`
- `POST /companion/knowledge-bases/{knowledge_base_id}/reply`

接口定义已存在，但建议视为开发中能力。

---

## 目录结构

```text
.
├─ conf/          # 配置、数据库连接
├─ crud/          # 数据访问层
├─ models/        # SQLAlchemy 模型
├─ routers/       # FastAPI 路由
├─ schemas/       # Pydantic 请求/响应模型
├─ utils/         # RAG、鉴权、画像、分析等核心逻辑
├─ alembic/       # 数据库迁移
├─ storage/       # 本地存储目录
├─ main.py        # 应用入口
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

### LLM

- `DASHSCOPE_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `LLM_TEMPERATURE`

### Embedding / Vector Store

- `EMBEDDING_MODEL_NAME`
- `EMBEDDING_MODEL_PATH`
- `EMBEDDING_CACHE_DIR`
- `EMBEDDING_LOCAL_FILES_ONLY`
- `EMBEDDING_PRELOAD_ON_STARTUP`
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
- `NEO4J_ENABLED`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`

Embedding 模块现在会按下面的顺序选择模型来源：

1. `EMBEDDING_MODEL_PATH` 指定的本地目录
2. `EMBEDDING_MODEL_NAME` 指向的本地目录
3. `EMBEDDING_CACHE_DIR` 下已经缓存好的 Hugging Face snapshot
4. `EMBEDDING_MODEL_NAME` 对应的远端仓库

如果本地已经有缓存 snapshot，服务会直接加载本地路径，不再每次启动都去 Hugging Face 解析仓库。

如果你准备把 `/graph` 接口切到 Neo4j，建议先把 `.env` 里的 `GRAPH_BACKEND=neo4j`、`NEO4J_ENABLED=true` 配好，然后执行一次：

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

### 2. 配置环境变量

复制 `.env-example` 为 `.env`，并补充你的真实配置。

如果你希望 embedding 只在第一次预热时联网，推荐这样配置：

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

- `app`：FastAPI API 服务
- `worker`：Celery 文档索引 worker
- `redis`：Celery broker / result backend
- `postgres`：业务数据库
- `milvus`：向量数据库
- `etcd / minio`：Milvus standalone 依赖

### 首次上线前至少要改的配置

- `DASHSCOPE_API_KEY`
- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- 如果你有本地 embedding 模型，建议配置 `EMBEDDING_MODEL_PATH`

### 默认端口暴露策略

当前 Compose 默认只把应用端口公开到宿主机，内部基础设施端口全部绑定到 `127.0.0.1`：

- `app`：`${APP_HOST_PORT:-8000}`
- `postgres / redis / minio / milvus`：仅宿主机本地可访问

这样更适合直接上云服务器，避免把数据库、Redis、Milvus 直接暴露到公网。

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

### 3. 准备 PostgreSQL

确保数据库已启动，并且 `DATABASE_URL` 可用。

### 4. 执行迁移

```bash
alembic upgrade head
```

### 5. 启动服务

```bash
uvicorn main:app --reload
```

如果你希望应用启动时就把 embedding 预热到当前进程，可以额外配置：

```env
EMBEDDING_PRELOAD_ON_STARTUP=true
```

注意：`--reload` 会启动额外进程，本地开发时可能看到 embedding 初始化日志出现多次；这不等于每次都重新下载模型。

默认访问地址：

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

---

## Docker 部署

项目提供了完整的容器化部署文件：

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

启动：

```bash
docker compose up --build
```

默认会启动以下服务：

- `mneme-app`：FastAPI 应用
- `mneme-postgres`：PostgreSQL
- `mneme-milvus`：Milvus
- `mneme-etcd`：Milvus 依赖组件
- `mneme-minio`：Milvus 依赖组件

容器启动时会先执行：

```bash
alembic upgrade head
```

随后启动应用服务。

如果拉取 Python 依赖较慢，可以在 `.env` 中配置镜像源，例如：

```env
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 适用场景

Mneme 更适合这类需求：

- 想沉淀个人博客、笔记、复盘、文章
- 想基于长期材料做检索与问答
- 想在知识库基础上做画像、阶段分析与成长总结
- 想搭建一个偏“个人记忆库”方向的 RAG 后端

如果你需要的是一个简单的 FAQ Demo，这个项目会显得偏重；但如果你希望从一开始就保留“用户 - 知识库 - 记忆 - 分析”这条演进路径，它会更合适。

---

## 当前状态总结

当前仓库的真实定位可以概括为：

> 一个基于 FastAPI、PostgreSQL、Milvus、LangChain 和 Qwen 的个人记忆型 RAG 后端，已完成认证、知识库、文档上传索引与问答主链路，并具备画像、成长分析与陪伴能力的扩展框架。
