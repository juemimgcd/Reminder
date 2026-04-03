# Agentic RAG 私有知识助手

> 时间范围：Day 1 - Day 15  
> 目标定位：用 FastAPI 做一个可部署的 **Agentic RAG 私有知识助手**，替换掉原来的基础 RAG 项目。  
> 参考方向：Quivr 这类“面向产品集成的 RAG 平台”思路，而不是只做一个 notebook 问答 demo。  
> 适用人群：已经有 Python 后端、FastAPI、Redis、Docker 基础，想转向 Agent / AI 应用开发的人。  

---

## 一、项目目标

在 15 天内完成一个最小可演示、可部署、可写进简历的 Agentic RAG 后端项目。  
最终效果不是“脚本能回答问题”，而是：

- 能上传文档
- 能建立索引
- 能进行带引用的问答
- 能管理会话或知识库
- 能通过 FastAPI API 调用
- 能本地 Docker 跑通
- 至少预留异步索引 / 任务状态能力

---

## 二、项目最终形态

### 必做功能
- 文档上传
- 文档解析与切分
- 向量化索引
- 检索增强问答
- 返回引用片段
- FastAPI API
- Swagger 可调试
- Docker 化
- 基础日志
- 基础异常处理

### 可选增强
- Redis 缓存热点问答
- Celery / 后台任务异步索引
- 多知识库支持
- metadata filter
- 简单会话历史

### 坚决不做
- 完整前端平台
- 多租户权限系统
- 太复杂的向量库评测
- 各种 RAG 高级技巧全塞进去
- 一上来做多 agent
- 为了“像产品”而引入大量无关工程复杂度

---

## 三、推荐技术栈

- **API 框架**：FastAPI
- **Agent / RAG 编排**：LangChain 或原生封装（保持轻量）
- **工作流**：可先不用 LangGraph，必要时只做简单状态流
- **向量库**：先选最容易跑起来的方案
- **缓存 / 任务状态**：Redis
- **异步任务**：Celery 或 FastAPI BackgroundTasks
- **数据库**：PostgreSQL / MySQL（至少存文档元数据、任务状态）
- **部署**：Docker / Docker Compose
- **日志**：结构化日志或至少标准 logging

---

## 四、目录结构建议（按你的习惯版）

```text
agentic_rag_assistant/
├─ routers/        # 路由层，按业务模块拆分接口
│  ├─ documents.py
│  ├─ chat.py
│  └─ health.py
├─ crud/           # 数据访问层，封装数据库查询与写入逻辑
│  ├─ document.py
│  ├─ chunk.py
│  ├─ chat_session.py
│  └─ task_record.py
├─ models/         # SQLAlchemy ORM 模型
│  ├─ document.py
│  ├─ chunk.py
│  ├─ chat_session.py
│  └─ task_record.py
├─ schemas/        # Pydantic 请求/响应模型
│  ├─ document.py
│  ├─ chat.py
│  └─ common.py
├─ conf/           # 数据库、Redis、环境配置
│  ├─ config.py
│  ├─ database.py
│  ├─ redis.py
│  └─ logger.py
├─ cache/          # 缓存读写封装
│  └─ qa_cache.py
├─ utils/          # 鉴权、密码加密、统一响应等通用工具 + 项目核心能力
│  ├─ response.py
│  ├─ exceptions.py
│  ├─ file_loader.py
│  ├─ text_splitter.py
│  ├─ embeddings.py
│  ├─ vector_store.py
│  ├─ retriever.py
│  ├─ rag_pipeline.py
│  └─ citation_builder.py
├─ alembic/        # 数据库迁移脚本
├─ main.py         # 应用入口
├─ Dockerfile
├─ docker-compose.yml
└─ requirements.txt
```

### 模块落位说明
- **routers/**：承接 `/kb/documents/*`、`/kb/chat/*`、`/health` 等接口。
- **crud/**：负责文档、分块、会话、索引任务状态的读写封装。
- **models/**：至少包括 `Document`、`Chunk`、`ChatSession`、`TaskRecord`。
- **schemas/**：定义上传文档、建立索引、发起问答、返回引用等请求/响应模型。
- **conf/**：放数据库连接、Redis 连接、环境变量、日志初始化。
- **cache/**：后续可以先做热点问答缓存；没有时间可以先留空。
- **utils/**：为了贴合你的目录习惯，把项目特有的 RAG 能力先放这里；后续如果项目做大，再把 `rag_pipeline`、`retriever`、`vector_store` 单独拆出去也不迟。

---

## 五、推荐 API 设计

```text
POST   /kb/documents/upload
POST   /kb/documents/{document_id}/index
GET    /kb/documents
GET    /kb/documents/{document_id}
DELETE /kb/documents/{document_id}

POST   /kb/chat/query
GET    /kb/chat/history/{session_id}

GET    /health
```

### `POST /kb/chat/query` 请求示例
```json
{
  "question": "总结这份文档的核心内容",
  "knowledge_base_id": "kb_001",
  "top_k": 4,
  "session_id": "session_001"
}
```

### 响应示例
```json
{
  "answer": "文档主要介绍了……",
  "sources": [
    {
      "document_id": "doc_001",
      "chunk_id": "chunk_014",
      "text": "原文片段……"
    }
  ]
}
```

---

## 六、15 天执行计划

## Day 1：项目重新立项
### 当天目标
- 明确这是“Agentic RAG 私有知识助手”，不是普通 PDF 问答脚本
- 明确最终交付物
- 创建项目仓库

### 必做任务
- 写项目简介
- 建立 Git 仓库
- 初始化 FastAPI 项目结构
- 写出 README 第一版

### 当日产出
- 可运行的 FastAPI hello world
- 项目目录骨架
- README 初稿

### 验收标准
- 本地 `uvicorn` 能启动
- Swagger 能打开

---

## Day 2：需求边界和数据流
### 当天目标
把项目边界定死，防止失控。

### 必做任务
- 画数据流：上传文档 -> 切分 -> 向量化 -> 检索 -> 生成答案 -> 返回引用
- 确定只支持的文档类型
- 确定数据库表和元数据字段

### 当日产出
- 一张流程图
- 一份接口清单
- 一份数据表草案

### 验收标准
- 你能清楚讲出每一步输入输出

---

## Day 3：文档上传接口
### 当天目标
做出真正的后端入口。

### 必做任务
- 实现文档上传 API
- 保存原始文件或文件元数据
- 建立文档记录表

### 当日产出
- `POST /kb/documents/upload`
- 文档列表接口雏形

### 验收标准
- 可以上传文件并拿到 document_id

---

## Day 4：文档解析与切分
### 当天目标
先把 ingestion 跑通，不管回答质量。

### 必做任务
- 实现 document loader
- 实现 text splitter
- 给 chunk 加 source / page / offset 信息

### 当日产出
- 解析服务模块
- chunk 结果日志

### 验收标准
- 任意一份测试文档都能切成合理 chunk
- chunk 可追踪来源

---

## Day 5：embedding 和向量入库
### 当天目标
打通索引建立链路。

### 必做任务
- 接 embedding 模块
- 建立向量存储
- 完成索引 API 的最小实现

### 当日产出
- `POST /kb/documents/{document_id}/index`
- 向量入库成功日志

### 验收标准
- 一个文档完成索引后，系统能确认 chunk 数量和索引状态

---

## Day 6：retriever 检索能力
### 当天目标
优先检查“查得到”，不要先纠结“答得美不美”。

### 必做任务
- 实现 retriever
- 支持 top-k
- 打印检索片段

### 当日产出
- retriever service
- 检索调试脚本

### 验收标准
- 对文档中明确存在的信息，能召回相关片段

---

## Day 7：最小问答链路
### 当天目标
完成基础 RAG 回答。

### 必做任务
- 把检索结果拼进 prompt
- 调模型生成回答
- 返回答案

### 当日产出
- `rag_service.py`
- 最小问答 demo

### 验收标准
- 可以针对已索引文档发起问题并得到回答

---

## Day 8：引用返回与答案结构化
### 当天目标
让结果更像产品能力，而不是黑盒输出。

### 必做任务
- 返回 source chunks
- 设计统一响应结构
- 记录 answer + source 绑定关系

### 当日产出
- citation service
- 标准 response schema

### 验收标准
- 每次回答至少附带 1 组来源片段

---

## Day 9：接入 FastAPI 聊天接口
### 当天目标
把问答能力正式服务化。

### 必做任务
- 实现 `POST /kb/chat/query`
- 参数校验
- 错误处理

### 当日产出
- chat route
- 请求/响应 schema

### 验收标准
- Swagger 能直接测试问答接口

---

## Day 10：Redis / 缓存 / 会话
### 当天目标
增加工程味和系统稳定性。

### 必做任务
- 接 Redis
- 做热点问题缓存，或做简单 session 保存
- 记录会话 id

### 当日产出
- Redis 连接模块
- session / cache 逻辑

### 验收标准
- 第二次相同请求能体现缓存命中，或 session 能查询到历史

---

## Day 11：异步索引
### 当天目标
把“重任务”从主请求线程中拆出来。

### 必做任务
- 用 Celery 或 BackgroundTasks 做异步索引
- 提供任务状态接口或状态字段
- 记录 indexing status

### 当日产出
- index task module
- 文档状态更新逻辑

### 验收标准
- 上传文档后可以异步触发索引，而不是一直阻塞请求

---

## Day 12：日志和异常处理
### 当天目标
把项目从“能跑”提升到“像个后端系统”。

### 必做任务
- 增加请求日志
- 增加错误日志
- 统一异常格式
- 加 request id

### 当日产出
- logger.py
- 自定义异常类

### 验收标准
- 错误发生时日志可追踪
- API 返回统一错误格式

---

## Day 13：Docker 化
### 当天目标
让项目具备可迁移和可部署性。

### 必做任务
- 写 Dockerfile
- 写 docker-compose.yml
- 配置 `.env.example`

### 当日产出
- Docker 一键启动能力

### 验收标准
- `docker compose up` 后服务能正常启动

---

## Day 14：README、架构图、项目说明
### 当天目标
准备简历和展示材料。

### 必做任务
- 完善 README
- 画系统架构图
- 补接口示例
- 补运行说明

### 当日产出
- 完整 README
- 一张架构图

### 验收标准
- 别人拿到仓库后知道它做什么、怎么启动、怎么调用

---

## Day 15：验收与简历提炼
### 当天目标
完成第一阶段收尾，确保能写进简历。

### 必做任务
- 自测全部接口
- 补 bug
- 写 3 条简历项目描述
- 准备 1 分钟项目讲解稿

### 最终验收标准
- 文档上传可用
- 索引建立可用
- 带引用问答可用
- FastAPI API 可用
- Docker 可用
- README 基本完整
- 你能讲清楚为什么这不是普通 PDF 问答脚本

---

## 七、简历写法参考

- 基于 FastAPI 构建 Agentic RAG 私有知识助手，完成文档上传、切分、向量化索引、检索增强问答与引用返回等核心能力。
- 设计文档索引与问答 API，结合 Redis / 异步任务实现索引状态管理与热点请求优化，提升后端服务可用性与扩展性。
- 使用 Docker 完成服务容器化部署，并通过统一日志与异常处理机制增强系统排障与维护效率。

---

## 八、交给 Codex 的细化要求

你可以把下面这段直接丢给 Codex：

```text
请基于这份《Agentic RAG 私有知识助手》15天计划，继续细化为“每天的详细实施清单”。
要求：
1. 每天拆成：上午学习、下午编码、晚上复盘。
2. 每天给出明确文件级任务，例如修改哪些模块、增加哪些接口、写哪些 schema。
3. 每天给出验收标准。
4. 每天给出可能踩坑点和规避建议。
5. 以 FastAPI 后端落地为主，不要写成 notebook 学习路线。
6. 控制范围，不要引入前端大工程。
7. 输出格式仍然是 Markdown。
```

---

## 九、这个项目是否和 FastAPI 强相关

是，强相关。  
这个项目的“智能能力”来自 RAG / LLM / 检索，  
但它的“工程形态”应该是：

- FastAPI 作为 API 服务框架
- Redis 作为缓存或状态层
- 数据库作为文档元数据层
- Docker 作为部署层

你做出来以后，它在简历上的定位应该是：

**AI 应用后端 / Agentic RAG 服务开发项目**
