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

前端类型检查：

```bash
cd app/mneme_frontend_v0.2.1
npm run lint
```

## 接口入口

启动后访问 `http://127.0.0.1:8000/docs` 查看完整 API。主要业务域包括 `auth`、`users`、`documents`、`retrieval`、`memory`、`graph`、`profile`、`analysis`、`advice`、`companion` 和 `tasks`。
