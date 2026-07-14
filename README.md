# Reminder

面向个人长期内容沉淀的记忆型 RAG 系统。

Reminder 用来把笔记、文章、复盘和经历沉淀成可检索、可分析、可追踪的个人记忆库。它不是简单 FAQ demo，而是一套包含用户、知识库、文档、向量检索、图谱、记忆、画像和成长分析的完整应用。

## 核心能力

- 用户注册、登录和 JWT 鉴权
- 多知识库管理
- 文档上传、解析、切分和索引
- Milvus 向量检索和 RAG 问答
- Neo4j 图谱投影、查询和重建
- 记忆库、个人画像、成长报告和建议生成
- Celery 异步任务队列
- Vue 3 前端工作台，由 FastAPI 统一托管
- Docker Compose 部署 PostgreSQL、Redis、Neo4j、应用和 worker

## 技术栈

- 后端：FastAPI、Pydantic v2、SQLAlchemy Async、Alembic
- 前端：Vue 3、TypeScript、Vite、D3
- 存储与队列：PostgreSQL、Redis、Milvus、Neo4j、Celery
- AI/RAG：LangChain、OpenAI-compatible LLM、sentence-transformers、reranker
- 部署：Docker、Docker Compose、Nginx、GitHub Actions

## 项目结构

```text
.
├── app/
│   ├── mneme/                    # FastAPI 后端
│   │   ├── bootstrap/            # 应用创建、路由注册、lifespan
│   │   ├── domains/              # 业务域路由与服务
│   │   ├── clients/              # LLM、embedding、Milvus、Neo4j 等客户端
│   │   ├── infra/                # Celery、缓存、限流、重试、存储适配
│   │   ├── models/               # SQLAlchemy ORM
│   │   ├── schemas/              # Pydantic API contract
│   │   ├── pipelines/            # 索引、记忆、分析、建议等流程
│   │   └── tasks/                # Celery task 入口
│   └── mneme_frontend_v0.2.1/     # Vue 前端工作台
├── alembic/                      # 数据库迁移
├── deploy/                       # 部署配置
├── docker/                       # 镜像构建文件
├── requirements/                 # 分组依赖
├── tests/                        # 回归测试
├── main.py                       # 应用入口
├── start.sh                      # 本地联动启动脚本
└── docker-compose.yml
```

## 依赖

完整运行时依赖：

```bash
pip install -r requirements.txt
```

轻量测试依赖：

```bash
pip install -r requirements/test.txt
```

前端依赖：

```bash
cd app/mneme_frontend_v0.2.1
npm install
cd ../..
```

依赖分组：

- `requirements/base.txt`：API、数据库、任务队列、文档处理等基础依赖
- `requirements/ai.txt`：LLM、embedding、reranker 等模型依赖
- `requirements/vector.txt`：Milvus 向量库依赖
- `requirements/test.txt`：后端测试依赖
- `requirements/dev.txt`：测试和代码检查工具

## 本地启动

复制环境变量：

```bash
cp .env-example .env
```

PowerShell：

```powershell
Copy-Item .env-example .env
```

按需补充 `.env` 中的数据库、JWT、LLM、Redis、Neo4j 和 Milvus 配置。常用入口包括：

- `DATABASE_URL`
- `JWT_SECRET`
- `LLM_PROVIDER` 和对应 provider 的 API key
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `NEO4J_URI`
- `MILVUS_URI`

执行迁移并启动：

```bash
alembic upgrade head
bash start.sh
```

默认地址：

- 应用首页：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`

常用启动参数：

```bash
bash start.sh --backend-only
bash start.sh --frontend-only
bash start.sh --backend-port 8001
```

## Docker

Compose 同时运行现有 Mneme 服务和独立 Memory Agent 服务。当前阶段 `MEMORY_AGENT_ENABLED=false`，因此用户请求仍只进入 Mneme；Memory Agent API 仅在 Compose 网络内通过 `memory-agent-api:8010` 提供 `/health` 和 `/health/readiness`。

服务所有权边界如下：

- Mneme 拥有 `${POSTGRES_DB:-agentic}`、Redis DB 0/1 和现有 Celery 队列。
- Memory Agent 拥有 `${MEMORY_AGENT_POSTGRES_DB:-memory_agent}`、Redis DB 2/3 和 `${MEMORY_AGENT_CELERY_QUEUE:-memory_agent}` 队列。
- `JWT_SECRET` 与 `MEMORY_AGENT_SERVICE_JWT_SECRET` 必须是不同的生产密钥。
- 服务之间只通过版本化 HTTP 契约通信；禁止直接读取对方数据库或执行跨数据库 join。

基础服务：

```bash
docker compose up -d --build
```

需要 Milvus 向量检索时启用 `vector` profile：

```bash
COMPOSE_PROFILES=vector docker compose up -d --build
```

常用命令：

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f worker
docker compose logs -f memory-agent-api
docker compose logs -f memory-agent-worker
docker compose down
```

生产环境建议把应用放在 Nginx 后面，并将 `APP_HOST_PORT` 绑定到 `127.0.0.1:8000`，避免数据库、Redis、Milvus、Neo4j 直接暴露到公网。

## 检查

后端轻量测试：

```bash
python -m pytest tests/test_text_encoding_contract.py tests/test_dependency_configuration.py -q -p no:cacheprovider
```

Python 编译检查：

```bash
python -m compileall app/mneme alembic main.py
```

## Memory Agent deletion and rebuild backfill

When Memory Agent integration is enabled, document, knowledge-base, and conversation
deletions first write a version-1 deletion event to the caller-owned Mneme transaction.
The Agent scopes every deletion by owner and nullable knowledge base. Document deletion
removes all stored projection batches/chunks and document evidence; knowledge-base
deletion removes all scoped projections, evidence, candidates, and canonical memory;
conversation deletion removes conversation evidence by session ID and explicit-request
evidence by the supplied stable message IDs. Unsupported candidates and canonical
memories are hard-deleted. Surviving confidence is deterministically capped downward.
Deletion audit results contain identifiers, counts, status, and timestamps only.

Dry-run a source rebuild without writing Outbox or Agent state:

```bash
python -m app.mneme.cli.export_agent_projection --dry-run --owner-id 42 --knowledge-base-id kb_123 --batch-size 50
```

Run the rebuild through the same version-1 online DTO builder and Outbox contract:

```bash
python -m app.mneme.cli.export_agent_projection --owner-id 42 --knowledge-base-id kb_123 --batch-size 50 --checkpoint var/memory-agent-backfill.json
```

The checkpoint is atomically replaced after each durable projection batch, accepted
legacy-memory event, or secret-filtered legacy record. It records source ID,
projection ID, batch index, event ID, and status, and is loaded automatically on the
next run. To override it, resume a document at a projection/document ID (optionally
after a batch) or resume legacy memory after a memory ID:

```bash
python -m app.mneme.cli.export_agent_projection --resume-from PROJECTION_ID --resume-batch-index 3 --batch-size 50
python -m app.mneme.cli.export_agent_projection --resume-kind legacy_memory --resume-from MEMORY_ID --batch-size 50
```

Event and Outbox idempotency makes replay duplicate-safe. Legacy memory uses stable
synthetic session/message IDs, the original first-seen timestamp, and the online
`user.memory_requested` secret filter. Limitations: legacy values are re-extracted
from their stored summaries, filtered secrets are not exported, only indexed documents
with chunks can be projected, and a deleted source cannot be rebuilt after its Mneme
content has itself been deleted.

Report Agent projection state without mutating projection or memory tables:

```bash
python -m services.memory_agent.cli.backfill --owner-id 42 --knowledge-base-id kb_123 --batch-size 100
python -m services.memory_agent.cli.backfill --resume-from PROJECTION_ID --batch-size 100 --dry-run
```

The report includes staged, active, failed, superseded, and hash-mismatch counts plus
safe projection/document identifiers; it never prints source content or failure text.

前端类型检查：

```bash
cd app/mneme_frontend_v0.2.1
npm run lint
```

## 接口入口

启动后访问 `http://127.0.0.1:8000/docs` 查看完整 API。主要业务域包括 `auth`、`users`、`documents`、`retrieval`、`memory`、`graph`、`profile`、`analysis`、`advice`、`companion` 和 `tasks`。
