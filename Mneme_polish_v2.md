# Mneme 项目优化计划

**基于既定优化决策的工程化与并发能力升级方案**

- **方案基线：** Celery + Redis
- **策略原则：** 不做全盘重构，优先改执行模型、拆分 utils 中已演化为“业务服务”的模块，并逐步建立文档域 / 记忆域双流水线
- **版本：** V2 规划稿
- **适用对象：** Mneme 当前主仓库与后续 worker / embedding service 演进

## 1. 项目背景与目标

Mneme 当前已经具备认证、知识库管理、文档上传、分块索引、向量检索与 RAG 问答等主干能力，说明产品原型已跑通，数据模型也具备继续工程化的基础。

当前主要问题并不在于功能缺失，而在于执行模型仍偏向“同步 API 内串行完成重任务”，导致索引吞吐、稳定性、可扩展性和后续记忆能力接入都会受限。

本次优化不追求大规模推倒重构，而是以低风险方式完成：任务化、批处理化、模块边界清晰化、双流水线预埋，以及基础生产能力补强。

## 2. 本次优化范围（已确认采纳）

1. 索引从同步 API 改为异步任务执行
2. 同步阻塞点移出事件循环
3. 缓存 embedding / vector store / LLM 等长生命周期对象
4. 拆分 utils：把已承担业务职责的模块迁出，避免全盘重构
5. 明确“文档域”和“记忆域”两条流水线
6. 把状态管理做成幂等状态机
7. 索引链路做批处理和分段并发
8. embedding 服务后续独立化
9. 优化 context 组装，避免每次现拼超长上下文
10. 增加限流、熔断、退避重试

## 3. 优化原则

| 原则 | 说明 |
|---|---|
| 低风险优先 | 优先改“执行方式”和“模块边界”，不先动核心业务模型。 |
| 兼容现有主链路 | 保留 routers / crud / models / schemas，避免为追求架构完美引入大面积改动。 |
| 先索引后记忆 | 先把文档索引链路任务化、可并发、可恢复，再逐步接入记忆沉淀能力。 |
| 先可观测再扩容 | 在并发提升前先补上任务状态、日志、限流、重试，否则问题难以定位。 |

## 4. 目标架构（增量演进版）

在不推倒现有代码组织的前提下，建议采用如下增量结构：

```text
routers/        -> 仅负责请求校验、权限、任务提交、状态查询
crud/           -> 继续承接数据库基础读写
models/ schemas/-> 继续承接 ORM 与 DTO
services/       -> 面向业务动作的服务，如 document_service / query_service
pipelines/      -> 多步骤流程编排，如 document_index_pipeline / memory_extract_pipeline
clients/        -> 外部依赖封装，如 embedding_client / vector_store_client / llm_client
infra/          -> 运行时支撑，如 celery_app / rate_limit / retry / circuit_breaker / object_cache
utils/          -> 仅保留通用工具函数，逐步瘦身
```

## 5. 阶段计划

| 阶段 | 目标 | 预估周期 |
|---|---|---|
| Phase A：索引任务化与执行模型升级 | Celery + Redis 接入；索引接口改为任务提交；阻塞操作迁出请求线程；对象缓存；批处理与状态机落地。 | 2-3 周 |
| Phase B：检索链路与稳定性增强 | context budget、去重与合并、限流、熔断、退避重试、基础监控与压测。 | 1-2 周 |
| Phase C：双流水线与能力扩展 | 记忆域流水线异步化；embedding service 独立部署；画像/分析定时任务化。 | 2-4 周 |

## 6. Phase A 详细计划：Celery + Redis 接入

### 6.1 目标

- 把原本由 HTTP 请求直接执行的索引重任务迁移到 worker 执行。
- 使 API 层只承担提交任务、查询状态和失败重试入口。
- 为后续批量索引、横向扩容、失败恢复和 embedding 独立化打基础。

### 6.2 推荐组件

- FastAPI：接入与任务状态查询
- Celery：任务分发、重试与并发控制
- Redis：broker 与结果/轻状态缓存
- PostgreSQL：业务数据与任务状态持久化
- Milvus：向量索引

### 6.3 最小任务流

| 序号 | 步骤 | 动作 | 输出 |
|---|---|---|---|
| 1 | submit | API 接收索引请求，校验权限与幂等键，写入任务记录，投递 Celery task | task_id |
| 2 | parsing | worker 解析文档内容并落地解析结果 | raw pages / raw text |
| 3 | chunking | 按规则切分 chunk，写入 chunk 元数据 | chunk rows |
| 4 | embedding | 按 batch 生成向量 | embedding batch |
| 5 | vector_upsert | 按 batch 写入 Milvus | vector ids |
| 6 | finalize | 更新 document 与 task 状态，记录耗时与统计信息 | completed / failed |

### 6.4 建议新增目录

```text
infra/
  celery_app.py
  task_queue.py
  retry.py
  circuit_breaker.py
  rate_limit.py
  object_cache.py

tasks/
  index_tasks.py

services/
  document_service.py
  query_service.py
  context_service.py
  memory_service.py

pipelines/
  document_index_pipeline.py
  memory_extract_pipeline.py

clients/
  embedding_client.py
  vector_store_client.py
  llm_client.py
```

## 7. 幂等状态机设计

任务状态建议做成显式状态机，避免重复触发、重复写入和失败难恢复的问题。

| 状态 | 含义 | 允许迁移 |
|---|---|---|
| queued | 任务已创建，等待 worker 消费 | parsing / cancelled |
| parsing | 解析原始文档 | chunking / failed |
| chunking | 切分并写入 chunk 元数据 | embedding / failed |
| embedding | 按 batch 生成向量 | vector_upserting / failed |
| vector_upserting | 写入向量库 | completed / failed |
| completed | 索引完成 | rebuild（新版本） |
| failed | 任务失败，可人工 retry | queued（retry） |

## 8. 索引链路性能优化

- **阻塞点迁移：** 文件解析、同步 I/O、embedding、Milvus 写入等重操作从事件循环中移走；若短期无法完全拆出，则使用线程池或 worker 隔离。
- **对象缓存：** embedding model、vector store client、LLM client 做应用级单例或依赖注入缓存，避免每请求重建。
- **批处理：** chunk 生成、embedding、vector upsert 全部支持 batch size 配置，推荐先从 32~128 的批大小开始压测。
- **分段并发：** 将文档索引拆成阶段任务，在 worker 内按受控并发执行，避免单任务独占资源。

## 9. utils 拆分方案（小步重构）

不进行全量目录重构，而是把 utils 中已承担明确业务职责的模块迁出。建议按以下规则执行：

- 凡是直接承接“业务动作”的，如 rag_service、index_service、advice_builder，迁入 services/ 或 pipelines/。
- 凡是承接外部依赖访问的，如 embeddings、vector_store、llm 访问器，迁入 clients/。
- 凡是运行时能力，如重试、限流、熔断、缓存、任务队列，迁入 infra/。
- utils/ 最终仅保留纯工具函数，如格式转换、小型 helper、无业务副作用函数。

## 10. 双流水线设计

为了兼容长期记忆能力演进，建议从现在开始把“文档域”和“记忆域”视为两条独立流水线。

| 文档域流水线 | 记忆域流水线 |
|---|---|
| 上传 -> 解析 -> 切分 -> embedding -> 向量入库 | 从 chunk / 对话抽取 memory entry |
| 产出：document / chunk / vector index | 产出：memory entry / profile snapshot / analysis |
| 目标：让检索可用 | 目标：让长期归纳与人格化能力可用 |

## 11. 检索链路优化

引入 `context_service`，统一负责检索结果去重、相邻 chunk 合并、token budget 控制和 prompt 组装。

避免简单地把 top-k chunk 直接拼接为超长上下文；需要按照 token 预算做裁剪与必要压缩。

后续可在向量召回后增加 rerank 组件，提升命中质量并减少无效上下文。

## 12. 稳定性治理

- **限流：** 对上传、索引提交、问答请求按用户或知识库维度限流，防止热点流量打爆 worker 或外部依赖。
- **熔断：** 对 embedding、LLM、Milvus 等外部依赖建立熔断策略，避免故障扩散。
- **退避重试：** 对可恢复错误采用指数退避重试；对不可恢复错误快速失败并落库。
- **任务恢复：** 失败任务保留错误信息与最后步骤，支持 retry 和后续问题定位。

## 13. 里程碑与验收标准

- **M1：索引 API 任务化** —— 索引请求平均响应显著缩短；接口返回 `task_id`；支持状态查询。
- **M2：worker 稳定运行** —— 文档可由 Celery worker 完成解析、切分、embedding、向量写入。
- **M3：状态机与重试可用** —— 失败任务可重试；重复提交不产生重复索引。
- **M4：检索链路优化** —— 上下文组装稳定；长文档问答延迟与 token 开销得到控制。
- **M5：双流水线预埋** —— 文档域与记忆域模块边界清晰，可为后续记忆能力接入预留位置。

## 14. 风险与应对

| 风险 | 应对措施 |
|---|---|
| Celery 接入初期复杂度上升 | 先只接入单一索引任务，避免过早引入复杂 task chain。 |
| worker 与 API 的状态一致性问题 | 通过 task 表 + document 状态字段双重校验，所有状态迁移走统一服务层。 |
| 批处理参数不合理 | 通过压测和线上观测逐步调 batch size，避免一次性调大导致内存抖动。 |
| utils 拆分过程中回归风险 | 每迁出一个模块就补一轮接口回归，采用小步提交而不是一次性迁移。 |

## 15. 结论

本次优化的核心不是继续增加接口能力，而是把 Mneme 从“同步式可运行原型”提升为“可扩展的任务化后端”。在既有仓库基础上，建议优先完成 Celery + Redis 接入、索引任务化、批处理与状态机建设，并以轻量方式拆分 utils，为双流水线和后续 embedding service 独立化奠定基础。


---

## 16. V1 / V2 路线图：从基础 Harness 到进阶 Harness

为了避免把“第一版工程化优化”和“完整的 Harness Engineering”混为一谈，建议将 Mneme 的后续演进明确拆分为 **V1（基础 Harness）** 与 **V2（进阶 Harness）** 两个阶段。

### 16.1 总体判断

当前 Mneme 更适合先完成 **基础运行时能力建设**，再继续引入更完整的 Harness Engineering 设计。原因是：

- 当前系统的主要问题仍然是索引链路偏同步、阻塞点较多、上下文管理粗放、状态恢复不足。
- 这些问题不解决，后续即使引入更复杂的 agent harness，也会因为底层执行模型不稳定而放大系统复杂度。
- 因此，第一阶段的重点应是先把系统从“可运行原型”升级为“任务化、可恢复、可观测的基础 harness 后端”。

换句话说：

> 第一版 polish 本身就已经是在建设 Harness Engineering 的基础层，只是不需要一开始就引入过于复杂的 Harness 体系。

### 16.2 V1：基础 Harness（建议优先完成）

V1 对应当前已经确认采纳的优化项，目标是先把 Mneme 建成一个具备基本运行时控制能力的 Agent / RAG 后端。

#### V1 的核心建设项

1. **Runtime Harness（运行时基础设施）**
   - 使用 `Celery + Redis` 完成索引任务异步化
   - 将阻塞操作移出请求链路
   - 建立幂等状态机
   - 支持失败重试、限流、熔断、退避重试
   - 建立基础任务状态查询机制

2. **Context Harness（上下文治理）**
   - 引入 `context_service`
   - 控制 token budget
   - 对检索结果做去重、相邻 chunk 合并、裁剪与必要压缩
   - 避免每次简单拼接超长上下文

3. **Module Boundary Harness（轻量模块边界治理）**
   - 拆分 `utils` 中已经承担业务职责的模块
   - 新增 `services / pipelines / clients / infra`
   - 保留当前 `routers / crud / models / schemas` 主体结构，避免大重构

4. **Dual Pipeline Foundation（双流水线基础）**
   - 明确文档域流水线
   - 预埋记忆域流水线
   - 为后续 memory entry、profile snapshot、analysis 异步化做边界准备

#### V1 完成后的系统形态

当 V1 完成后，Mneme 应具备以下特征：

- API 层不再直接承担长链路重任务
- 索引链路可异步执行、可重试、可查询状态
- 检索链路具备基础上下文预算与组装控制
- 运行时治理能力初步建立
- 文档域与记忆域不再混在一个同步执行模型里

此时系统可以认为已经具备 **基础 Harness**，也就是能够支撑后续更复杂 agent 能力建设的底座。

### 16.3 V2：进阶 Harness（建议在 V1 稳定后推进）

V2 不再只是“把任务跑起来”，而是进一步补齐更完整的 Harness Engineering 层，使 Mneme 更接近现代 Agent Infrastructure。

#### V2 的重点方向

1. **Verification Harness（验证闸门）**
   - 索引后自动校验 chunk 数、向量数、状态一致性
   - 检索前后校验知识库范围、越权访问、空上下文问题
   - memory entry 抽取后的 schema 校验、去重校验与质量闸门
   - 将关键链路上的“自动检查”系统化，而不是依赖人工排查

2. **Policy Externalization（策略外置）**
   - 将 chunk 规则、batch 策略、retry 策略、context packing 规则、memory extraction policy 外置配置化
   - 避免每次微调都修改核心代码
   - 为不同知识库、不同租户或不同任务模式预留策略差异化空间

3. **Runtime Governance（更强运行时治理）**
   - 更细粒度的工具/服务访问权限控制
   - 用户级、知识库级、任务级配额体系
   - 更完善的失败恢复和任务补偿机制
   - 更强的可观测性与告警

4. **Evaluation / Observability Harness（评估与观测）**
   - 建立索引质量、检索质量、问答质量的自动化评估
   - 追踪任务耗时、失败原因、上下文长度、token 消耗
   - 为后续迭代提供量化依据

5. **Portable Harness（可移植控制层，后续可选）**
   - 将部分高层控制逻辑从代码中抽象出来
   - 逐步形成可移植的 harness 配置与策略描述
   - 为更长时、更复杂的 agent 运行模式打基础

### 16.4 为什么不建议现在直接跳到 V2

如果在 V1 尚未完成时就直接引入完整的进阶 Harness，会有几个明显问题：

- 底层执行模型尚不稳定，复杂度会被过早拉高
- 当前性能和并发问题尚未解决，进阶 Harness 难以发挥真实价值
- 验证层、治理层、评估层会依赖稳定的任务执行与状态管理，否则很难落地
- 工程投入会从“可控增量优化”变成“多方向同时推进”，风险明显上升

因此，更合理的顺序是：

> **先完成基础 Harness（V1），再进入进阶 Harness（V2）。**

### 16.5 建议执行顺序

#### 第一阶段：完成 V1
优先顺序建议如下：

1. `Celery + Redis` 接入  
2. 索引任务化  
3. 阻塞点迁移  
4. 对象缓存  
5. 批处理与幂等状态机  
6. `utils` 轻量拆分  
7. `context_service` 建立  
8. 限流、熔断、退避重试  
9. 文档域 / 记忆域双流水线边界预埋

#### 第二阶段：进入 V2
在 V1 稳定运行后，再逐步推进：

1. verification gate  
2. policy externalization  
3. 更细粒度 runtime governance  
4. evaluation / observability harness  
5. embedding service 独立化  
6. 记忆域异步抽取与周期性归纳任务

### 16.6 结论

Mneme 可以采用 Harness Engineering，而且很适合走这条路线；但最合理的方式不是在当前阶段直接引入一整套复杂 Harness 体系，而是：

- 先把第一版 polish 做完，把它视为 **基础 Harness 建设**
- 再在稳定的执行模型和模块边界之上，逐步演进到 **进阶 Harness 层**

也就是说：

> **V1 不是和 Harness Engineering 分开的事情，而是 Harness Engineering 的落地起点。**

