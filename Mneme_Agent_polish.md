# Mneme Agent 优化计划

> 适用对象：当前已经完成 **FastAPI + PostgreSQL + Milvus + LangChain + Docker** 的个人记忆型 RAG 后端，目标是把项目从“能工作的 RAG Demo”升级为“能体现 Agent 能力、工程能力、评测能力的作品”。

---

## 1. 当前项目现状

根据现有简历内容，你的 Mneme 项目已经完成了这些基础能力：

- 基于 **FastAPI** 构建个人记忆型 RAG 后端
- 完成 **注册登录、默认知识库创建、文档上传、切分、索引、问答主链路**
- 使用 **PostgreSQL + SQLAlchemy 2.x Async + Alembic** 管理数据模型与迁移
- 接入 **JWT、PyPDF、Milvus、LangChain、Qwen**，实现文档解析和向量检索
- 使用 **Docker Compose** 编排 FastAPI、PostgreSQL、Milvus、etcd、MinIO 等服务
- 预留了 **画像分析、成长报告、建议生成** 等扩展接口

这说明项目已经具备：

1. 后端服务能力
2. 向量检索能力
3. 基础 RAG 能力
4. 容器化部署能力

但当前形态仍然更像 **RAG 后端**，还不够像 **Agent 系统**。

---

## 2. 项目升级目标

### 总目标

把 Mneme 升级成一个：

**可编排、可观测、可评测、可工具化、可工程化落地的个人记忆 Agent 后端。**

### 简历定位目标

升级后，这个项目最好能支撑你在简历和面试里讲出下面这些关键词：

- LangGraph / Workflow / State Machine
- Function Calling / Tool Calling / MCP
- Hybrid Retrieval / Rerank / Metadata Filter
- Trace / Eval / Dataset / Badcase 分析
- 异步处理 / 流式输出 / 限流 / 重试 / 失败治理
- 多租户隔离 / 用户画像 / 记忆写回

---

## 3. 优先级最高的优化方向

# 第一阶段：把 RAG 升级成轻 Agent

### 3.1 引入 LangGraph 重构主链路

当前链路大概率是：

`上传文档 -> 切分 -> 向量化 -> 用户提问 -> 检索 -> 回答`

建议升级成：

`用户问题 -> Query Rewrite -> Router -> Retrieve -> Rerank -> Answer -> Memory Writeback`

建议增加的节点：

- **Rewrite 节点**：将用户问题改写成更适合检索的查询
- **Router 节点**：判断本次请求该走知识库问答、记忆检索、工具调用还是报告生成
- **Retrieve 节点**：负责从 Milvus / PostgreSQL 中召回候选内容
- **Rerank 节点**：对召回结果重排序
- **Answer 节点**：带引用生成回答
- **Writeback 节点**：将对话摘要、长期偏好或新记忆写回系统

### 3.2 不要一开始就上多 Agent

当前最优路线不是堆多个 agent，而是先做：

**单 Agent + 明确状态流 + 工具节点 + 记忆写回**

这样更稳，也更容易落地到项目代码和面试表达里。

---

# 第二阶段：把检索做深

### 3.3 升级 Chunk 策略

不要只做固定长度切片。建议支持：

- 标题感知切分
- 段落保持
- overlap 可配置
- 表格 / 列表 / FAQ / 代码块特殊处理
- 不同文档类型使用不同切分策略

### 3.4 实现 Hybrid Retrieval

建议从单纯向量检索升级为：

- Dense Vector Search
- Keyword / BM25 / Sparse Search
- Hybrid Merge
- Rerank

适用场景：

- 日期
- 人名
- 专有名词
- 标题匹配
- 短文本问题

### 3.5 增加 Metadata Filter

建议把下面这些字段纳入检索过滤条件：

- user_id
- workspace_id / knowledge_base_id
- memory_type（事实 / 偏好 / 计划 / 对话）
- source_type（上传文档 / 对话写回 / 系统生成）
- created_at
- tags

### 3.6 增加 Rerank

建议流程：

1. 先召回 topK 候选
2. 使用 reranker 重排
3. 只把重排后的前几条交给模型

这样可以明显提高上下文质量，减少无关内容进入 prompt。

### 3.7 做“证据是否充足”的判断

不要默认检索到内容就回答。应该加一层判断：

- 证据足够：正常带引用回答
- 证据不足：拒答或转工具调用
- 证据冲突：提示用户可能存在矛盾记忆

---

# 第三阶段：加入工具能力，让它真正像 Agent

### 3.8 先做 Function Calling / Tool Calling

建议先封装 3~5 个工具：

- `search_memory(query, filters)`
- `add_memory(content, type, tags)`
- `get_user_profile(user_id)`
- `generate_growth_report(user_id, date_range)`
- `search_documents(query, kb_id)`

### 3.9 再往上做 MCP

在有了工具抽象后，再把项目扩展成 MCP server。

建议暴露：

#### Tools
- `search_memory`
- `add_memory`
- `summarize_history`
- `generate_report`

#### Resources
- 最近对话摘要
- 用户画像快照
- 某时间段成长轨迹

这样外部 Agent 或客户端就能按标准接入 Mneme。

---

# 第四阶段：加入评测与可观测能力

### 3.10 接入 Langfuse 或等价 tracing 系统

最少记录：

- 原始 query
- rewrite 后 query
- 检索结果
- rerank 后结果
- 最终 prompt
- 模型回答
- token 消耗
- latency
- trace_id

### 3.11 自建一个小型评测集

先不要贪大，做 30~50 条就够了，分成：

- 事实型问题
- 偏好型问题
- 时间线问题
- 多跳问题
- 无答案问题
- 易混淆问题

### 3.12 建立升级前后的对比指标

建议至少统计：

- Recall@K
- TopK 命中率
- 引用覆盖率
- Faithfulness
- 无答案识别率
- 平均响应耗时

你后面最值钱的简历表达，不是“实现了某功能”，而是：

- 将 Top5 命中率从 X 提升到 Y
- 将平均响应时间从 Xms 降低到 Yms
- 将无答案误答率从 X% 降低到 Y%

---

# 第五阶段：把工程能力做出来

### 3.13 文档入库异步化

当前如果上传文档后同步执行解析、切片、embedding、入库，用户体验和系统稳定性都不够好。

建议改为：

- 上传成功后立即返回 `task_id`
- 后台异步执行解析、切片、embedding、索引
- 前端轮询或 SSE 获取任务状态
- 支持失败重试和幂等

### 3.14 支持流式输出

在问答接口里增加 SSE：

- 流式输出回答 token
- 最后返回 citation / trace_id / tool_calls

### 3.15 增加限流与缓存

建议加：

- 用户级限流
- 上传任务并发控制
- embedding 缓存
- 热点问题缓存
- 检索结果缓存

### 3.16 增加失败治理

至少补上：

- LLM 调用超时
- 重试机制
- fallback model
- 向量库故障降级
- 工具调用异常兜底

### 3.17 多租户隔离

如果你想把项目讲得更工程化，必须体现：

- 不同用户的知识库隔离
- 不同用户的记忆隔离
- 检索阶段严格过滤 user_id / tenant_id
- 任务、文档、索引、会话全链路绑定用户

---

## 4. 最推荐的 V2 版本结构

### 核心模块

```text
app/
  api/
    auth.py
    chat.py
    upload.py
    memory.py
    reports.py
  agent/
    graph.py
    state.py
    router.py
    tools.py
    prompts.py
  retrieval/
    chunker.py
    embedder.py
    retriever.py
    reranker.py
    filters.py
  memory/
    models.py
    service.py
    writeback.py
    profile.py
  tasks/
    document_tasks.py
    embedding_tasks.py
  observability/
    tracing.py
    metrics.py
    eval.py
  infra/
    cache.py
    rate_limit.py
    settings.py
```

### 推荐接口

#### 文档与知识库
- `POST /documents/upload`
- `GET /tasks/{task_id}`
- `GET /knowledge-bases/{id}/documents`

#### Agent 与问答
- `POST /chat/ask`
- `POST /chat/stream`
- `GET /traces/{trace_id}`

#### 记忆管理
- `POST /memory`
- `GET /memory/search`
- `PATCH /memory/{id}`
- `DELETE /memory/{id}`

#### 报告与画像
- `GET /profile`
- `POST /reports/growth`
- `GET /reports/{report_id}`

#### MCP
- `mcp.tools.search_memory`
- `mcp.tools.add_memory`
- `mcp.tools.generate_report`
- `mcp.resources.profile_snapshot`

---

## 5. 三周落地路线

## 第 1 周：把主链路升级成 Agent Workflow

目标：

- 接入 LangGraph
- 增加 Rewrite / Router / Retrieve / Answer / Writeback 节点
- 完成基础状态流

交付物：

- 可运行的 LangGraph 主链路
- 带 trace_id 的问答接口
- 问答响应中返回 citation

## 第 2 周：把检索质量做深

目标：

- 支持 metadata filter
- 引入 hybrid retrieval
- 增加 rerank
- 整理 30 条评测数据

交付物：

- 升级前后对比表
- 简单 badcase 集
- TopK 命中率统计脚本

## 第 3 周：把工具化与工程化补齐

目标：

- 接入 3 个工具
- 完成异步文档处理
- 增加 SSE 流式输出
- 补限流与错误处理

交付物：

- 可演示的 Agent Demo
- 工具调用日志
- 项目 README 的架构图与时序图

---

## 6. 最值得写进 README 的内容

建议把 README 从“技术栈罗列”升级成：

1. 项目简介
2. 系统架构图
3. 主链路时序图
4. 检索链路说明
5. Agent 工作流说明
6. 工具调用示例
7. 评测方式与指标
8. 部署方式
9. 后续规划

README 里最好直接放：

- 架构图
- 一次完整请求的 trace 图
- 检索结果示意图
- 升级前后指标对比

---

## 7. 升级后可直接写进简历的表述

你现在的描述偏“做了什么”，升级后建议改成“做了什么 + 为什么更强 + 带来什么结果”。

### 示例写法

- 基于 LangGraph 重构个人记忆 Agent 工作流，实现 query rewrite、检索路由、工具调用与记忆写回
- 基于 Milvus 实现 dense+sparse hybrid retrieval 与 rerank，提升测试集 Top-K 命中率与回答相关性
- 接入 tracing 与离线评测链路，支持 badcase 定位、版本对比与回答质量回归验证
- 基于 MCP 暴露记忆检索、写入与报告生成工具，支持外部 Agent/客户端标准化调用
- 通过异步文档处理、SSE 流式输出、限流与失败治理，将系统升级为可持续迭代的 AI 应用后端

---

## 8. 最终建议：不要乱加功能，按价值排序

如果时间有限，优先级一定要这样排：

### 必做
1. LangGraph 编排
2. Hybrid Retrieval + Rerank
3. Trace + Eval
4. Tool Calling

### 强烈建议做
5. 异步文档处理
6. SSE 流式输出
7. Metadata Filter
8. 多租户隔离

### 有余力再做
9. MCP server
10. 用户画像
11. 成长报告
12. 多 Agent

---

## 9. 一句话总结

Mneme 现在已经有一个不错的 RAG 后端底座。

下一步最正确的方向，不是继续堆模型和接口，而是把它升级成：

**有工作流编排、有检索优化、有工具能力、有评测闭环、有工程化能力的 Agent 项目。**

做到这一步，它就不再只是一个学生项目，而会更像一个能支撑你去投国内 Agent 开发岗的作品。
