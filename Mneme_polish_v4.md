# Mneme 项目优化计划方案（不含多模态）

## 1. 项目优化目标

Mneme 当前已经具备 RAG 后端的基本形态，包括用户、知识库、文档、Chunk、向量索引、RAG 问答、图谱投影等能力。下一阶段的优化目标不应只是继续堆叠技术组件，而是将项目从“文档问答系统”升级为“个人长期记忆系统”。

本优化计划暂不纳入图片、音频、视频等多模态能力，优先强化文本记忆、结构化记忆、GraphRAG、检索质量、任务系统、工程可靠性与评测闭环。

---

## 2. 总体优化方向

### 2.1 当前定位

当前系统可以理解为：

```text
Document
  -> Chunk
  -> Embedding
  -> Vector Retrieval
  -> RAG Answer
```

这更接近传统知识库问答。

### 2.2 目标定位

优化后的系统应变成：

```text
Document
  -> Chunk
  -> MemoryEntry
  -> Entity / Event / Topic / Goal / Preference / Reflection
  -> GraphRAG
  -> Profile Snapshot
  -> Evidence-based Answer
```

核心转变是：

```text
从“文档检索”转向“长期记忆管理”
从“Chunk RAG”转向“Memory + Graph + Evidence RAG”
从“即时生成”转向“可追溯、可评测、可演化的记忆系统”
```

---

## 3. 优化优先级总览

| 阶段 | 目标 | 重点模块 | 优先级 |
|---|---|---|---|
| Phase 1 | 打通核心记忆闭环 | MemoryEntry、TaskRecord、Evidence | P0 |
| Phase 2 | 提升检索质量 | Hybrid Search、GraphRAG、Rerank | P1 |
| Phase 3 | 提升工程可靠性 | Outbox、异步任务、状态机、重试 | P1 |
| Phase 4 | 构建长期记忆能力 | 记忆合并、画像快照、时间线 | P2 |
| Phase 5 | 建立评测闭环 | RAG Eval、检索评估、回答评估 | P2 |
| Phase 7 | 分析与调试辅助层 | DuckDB、离线分析、Eval 报表、检索调试 | P2 |

---

## 3.1 DuckDB 在 Mneme 中的定位

DuckDB 不建议作为 Mneme 的主业务数据库，也不建议替代 PostgreSQL、Milvus 或 Neo4j。它更适合放在“分析与调试辅助层”，用于解决以下问题：

```text
RAG Eval 结果分析
检索日志分析
Chunk 质量分析
MemoryEntry 分布统计
用户知识库使用情况分析
embedding / rerank 实验结果分析
临时 SQL 分析
本地 Parquet / CSV 报表
```

### 3.1.1 不建议 DuckDB 承担的职责

```text
用户账号与权限
知识库主数据
文档主记录
任务状态机
事务一致性要求高的业务数据
Neo4j 图投影事实源
线上高并发 OLTP 请求
```

这些仍然应该由 PostgreSQL 承担。

### 3.1.2 适合 DuckDB 承担的职责

```text
离线分析
实验分析
Eval report
debug report
检索质量统计
数据导出分析
本地开发调试
```

推荐定位：

```text
PostgreSQL：业务事实源
Milvus：向量召回
Neo4j：图关系与 GraphRAG
DuckDB：分析、评测、调试、报表
```

### 3.1.3 推荐落地方式

短期不需要引入常驻 DuckDB 服务，只需要在后端或脚本中以 embedded 方式使用：

```text
scripts/
  export_eval_data.py
  analyze_retrieval_logs.py
  analyze_chunk_quality.py
  build_eval_report.py

data/
  exports/
    retrieval_logs.parquet
    eval_results.parquet
    chunk_stats.parquet
```

分析流程：

```text
PostgreSQL / 日志 / Eval 结果
  ↓
导出 CSV / Parquet
  ↓
DuckDB SQL 分析
  ↓
生成 Markdown / HTML / JSON 报告
```

### 3.1.4 DuckDB 可以支持的分析报表

#### 检索质量分析

```text
不同 top_k 下的 Recall
vector / keyword / graph 各自命中率
rerank 前后排名变化
无命中问题统计
低置信度回答统计
```

#### Chunk 质量分析

```text
chunk 长度分布
超长 / 过短 chunk 比例
每篇文档 chunk 数
heading_path 覆盖率
重复 chunk 检测
```

#### MemoryEntry 分析

```text
不同类型 MemoryEntry 数量
每篇文档抽取的记忆数量
低置信度记忆比例
重复记忆候选
长期主题分布
```

#### GraphRAG 分析

```text
graph expansion 平均跳数
不同关系类型使用频率
graph_context 对回答质量的提升
孤立 MemoryEntry / Document 节点比例
```

### 3.1.5 DuckDB 的价值

DuckDB 的价值不是让系统架构更复杂，而是让 Mneme 具备“自我分析能力”：

```text
知道检索为什么差
知道哪些文档切分不好
知道哪些记忆质量低
知道哪些关系图没有发挥作用
知道每次优化是否真的提升了效果
```

它适合在 Phase 6 的 RAG Eval 之后接入，也可以提前作为开发调试工具使用。

---



# Phase 1：打通核心记忆闭环

## 4. MemoryEntry 主链路化

### 4.1 问题

当前系统已经有文档、Chunk、RAG 问答能力，但如果 MemoryEntry 没有完全接入主索引流程，系统仍然偏向普通文档知识库。

### 4.2 目标

将 MemoryEntry 变成系统核心资产，而不是附属分析结果。

### 4.3 推荐索引流程

```text
用户上传文档
  ↓
文档解析
  ↓
文本清洗
  ↓
结构化 Chunk 切分
  ↓
Chunk 入库
  ↓
向量索引
  ↓
MemoryEntry 自动抽取
  ↓
MemoryEntry 去重 / 合并 / 置信度计算
  ↓
投影到 Neo4j
  ↓
刷新画像快照 / 主题摘要
```

### 4.4 MemoryEntry 类型设计

建议将记忆条目分为以下类型：

| 类型 | 含义 | 示例 |
|---|---|---|
| event | 事件 | “2024 年开始学习后端开发” |
| goal | 目标 | “希望转向 agent + data infra 方向” |
| preference | 偏好 | “更喜欢轻量、可独立运行的技术栈” |
| belief | 观点 | “大数据技术栈在后端视角偏冷门” |
| reflection | 反思 | “传统 RAG 只做 chunk 检索不够” |
| decision | 决策 | “暂时不把多模态纳入当前计划” |
| problem | 问题 | “长期记忆系统需要避免信息混乱” |
| skill | 技能 | “掌握 Spark、Neo4j、RAG、后端架构” |
| relationship | 人际/实体关系 | “某人/项目/组织与用户的关系” |

### 4.5 MemoryEntry 建议字段

```text
id
user_id
knowledge_base_id
document_id
chunk_id
type
title
content
summary
evidence_text
confidence
importance_score
source_start_offset
source_end_offset
first_seen_at
last_seen_at
status
created_at
updated_at
```

### 4.6 状态设计

```text
active        当前有效
merged        已合并到其他记忆
outdated      可能过时
contradicted  与新记忆冲突
archived      用户手动归档
deleted       用户删除
```

---

## 5. 回答证据化

### 5.1 问题

长期记忆系统最怕 LLM 对用户经历、偏好和目标进行过度脑补。

### 5.2 目标

所有重要回答都应能追溯到具体来源。

### 5.3 回答结构建议

```text
结论：
  系统给出的主要判断。

证据：
  1. 来源文档 / 记忆条目 / Chunk
  2. 相关原文片段
  3. 相关时间

置信度：
  高 / 中 / 低

不确定性：
  哪些地方是推断，哪些地方缺少证据。
```

### 5.4 结果对象建议

```text
answer
source_document_ids
source_chunk_ids
source_memory_entry_ids
graph_path_ids
confidence
uncertainty_notes
retrieval_debug_info
```

### 5.5 价值

- 降低幻觉
- 提高用户信任
- 方便调试 RAG 效果
- 为后续评测提供结构化依据

---

# Phase 2：提升检索质量

## 6. Hybrid Search

### 6.1 问题

纯向量检索对语义问题友好，但对以下查询不稳定：

```text
人名
项目名
日期
错误码
函数名
文档标题
具体术语
短关键词
```

### 6.2 目标

将检索层升级为：

```text
Vector Search
  + Keyword Search
  + Memory Search
  + Graph Expansion
  + Rerank
```

### 6.3 推荐检索流程

```text
用户问题
  ↓
Query Rewrite / Query Analysis
  ↓
向量召回 Chunk
  ↓
关键词召回 Chunk / Document / MemoryEntry
  ↓
MemoryEntry 召回
  ↓
Neo4j 图扩展
  ↓
结果合并去重
  ↓
Rerank
  ↓
构造最终上下文
  ↓
LLM 生成回答
```

### 6.4 ContextItem 统一结构

```text
type: chunk / document / memory / graph_path
id
text
score
source_type
source_id
metadata
why_retrieved
evidence
```

### 6.5 初期实现建议

短期不必引入复杂搜索引擎，可以先使用：

```text
PostgreSQL full-text search
Milvus vector search
Neo4j graph expansion
```

后续如果关键词检索压力变大，再考虑 Tantivy、Meilisearch 或 OpenSearch。

---

## 7. Chunk 结构化切分

### 7.1 问题

固定 chunk size 容易破坏语义结构，尤其是长文档、Markdown、PDF 转文本、复盘文档、技术笔记。

### 7.2 目标

从固定切分升级为结构感知切分。

### 7.3 推荐层级

```text
Document
  -> Section
  -> Chunk
  -> EvidenceSpan
```

### 7.4 Chunk 字段建议

```text
id
document_id
section_id
heading_path
section_title
content
content_hash
start_char
end_char
token_count
page_number
paragraph_index
created_at
```

### 7.5 检索时上下文扩展

不要只返回单个 Chunk。建议支持：

```text
命中 Chunk
  + 前一个 Chunk
  + 后一个 Chunk
  + 所属 Section 摘要
  + 关联 MemoryEntry
```

这样可以减少“上下文断裂”。

---

## 8. Rerank 层

### 8.1 问题

多路召回后，结果质量参差不齐。如果直接拼接给 LLM，容易造成上下文污染。

### 8.2 目标

增加统一 rerank 阶段。

### 8.3 Rerank 输入

```text
query
candidate_context_items
user_id
knowledge_base_id
conversation_context
```

### 8.4 Rerank 输出

```text
ranked_context_items
final_score
reason
dedup_group
```

### 8.5 实现路径

短期：

```text
规则分数融合：
  vector_score
  keyword_score
  memory_importance_score
  graph_distance_score
  recency_score
```

中期：

```text
使用 cross-encoder / LLM rerank
```

---

# Phase 3：GraphRAG 优化

## 9. Neo4j 从图展示升级为检索层

### 9.1 问题

如果 Neo4j 只用于展示图谱，价值有限。它应该参与上下文扩展和多跳推理。

### 9.2 目标

Neo4j 用于回答：

```text
这条记忆和哪些文档有关？
这个主题反复出现在哪些时间？
哪些目标和哪些问题相关？
哪些观点发生了变化？
哪些文档共享相同记忆？
```

### 9.3 推荐图模型

```text
(:User)-[:OWNS]->(:KnowledgeBase)
(:KnowledgeBase)-[:CONTAINS]->(:Document)
(:Document)-[:HAS_CHUNK]->(:Chunk)
(:Document)-[:EXTRACTS]->(:MemoryEntry)
(:Chunk)-[:EVIDENCE_FOR]->(:MemoryEntry)

(:MemoryEntry)-[:MENTIONS]->(:Entity)
(:MemoryEntry)-[:ABOUT_TOPIC]->(:Topic)
(:MemoryEntry)-[:OCCURRED_AT]->(:Time)
(:MemoryEntry)-[:SUPPORTS]->(:MemoryEntry)
(:MemoryEntry)-[:CONTRADICTS]->(:MemoryEntry)
(:MemoryEntry)-[:REFINES]->(:MemoryEntry)
(:MemoryEntry)-[:REPEATED_IN]->(:Document)
```                                                                                                                                                                                   

### 9.4 GraphRAG 流程

```text
向量 / 关键词召回 seed nodes
  ↓
定位 Document / Chunk / MemoryEntry
  ↓
Neo4j 进行 1~2 跳扩展
  ↓
过滤用户权限和知识库边界
  ↓
提取 graph paths
  ↓
转换成 structured context
  ↓
交给 LLM
```

### 9.5 Graph Context 示例

```text
主题：职业方向
相关记忆：
  - 学习后端
  - 关注大数据技术栈
  - 关注 agent 工程化
  - 偏好轻量独立运行组件

关系：
  - “大数据技术栈冷门” SUPPORTS “agent 工程中数据基础设施有壁垒”
  - “Flink 太重” REFINES “偏好轻量技术栈”
```

---

## 10. 关系类型细化

### 10.1 当前问题

单一 `RELATED` 关系表达力有限。

### 10.2 建议增加关系类型

```text
SIMILAR_TOPIC
SAME_PERIOD
SHARES_MEMORY
SUPPORTS
CONTRADICTS
REFINES
CAUSES
LEADS_TO
REPEATED_IN
EVIDENCE_FOR
ABOUT_TOPIC
MENTIONS
```

### 10.3 价值

- 支持更细粒度推理
- 支持时间演化分析
- 支持矛盾检测
- 支持反复主题发现
- 支持更可信的画像生成

---

# Phase 4：工程可靠性优化

## 11. Graph Projection Outbox

### 11.1 问题

业务流程中直接写 Neo4j，一旦 Neo4j 不可用，容易出现投影缺失。

### 11.2 目标

PostgreSQL 作为事实源，Neo4j 作为可重放投影。

### 11.3 Outbox 表设计

```text
graph_projection_outbox
  id
  event_type
  aggregate_type
  aggregate_id
  user_id
  knowledge_base_id
  payload
  status
  retry_count
  last_error
  created_at
  updated_at
  processed_at
```

### 11.4 事件类型

```text
UserCreated
KnowledgeBaseCreated
DocumentCreated
DocumentIndexed
ChunkCreated
MemoryExtracted
MemoryMerged
DocumentDeleted
KnowledgeBaseDeleted
```

### 11.5 状态

```text
pending
processing
done
failed
dead_letter
```

### 11.6 消费流程

```text
业务写 PostgreSQL
  ↓
同事务写 outbox
  ↓
worker 扫描 pending 事件
  ↓
写 Neo4j
  ↓
成功标记 done
  ↓
失败重试
  ↓
超过阈值进入 dead_letter
```

---

## 12. TaskRecord 状态机

### 12.1 问题

文档索引、记忆抽取、图谱重建、画像刷新都不是简单同步请求。

### 12.2 目标

将长任务统一纳入 TaskRecord 管理。

### 12.3 任务类型

```text
document_parse
document_index
embedding_build
memory_extract
memory_merge
graph_projection
graph_rebuild
profile_refresh
rag_eval_run
```

### 12.4 状态设计

```text
pending
running
succeeded
failed
cancelled
retrying
```

### 12.5 字段建议

```text
id
task_type
user_id
knowledge_base_id
document_id
status
progress
current_step
input_payload
result_payload
error_message
retry_count
created_at
started_at
finished_at
```

### 12.6 前端体验

支持展示：

```text
文档解析中 20%
正在生成向量 45%
正在抽取记忆 70%
正在写入图谱 90%
完成
```

---

# Phase 5：长期记忆能力

## 13. 记忆合并与演化

### 13.1 问题

长期系统会不断产生重复、相似、过时甚至冲突的记忆。

### 13.2 目标

建立记忆合并、冲突检测和演化追踪机制。

### 13.3 合并流程

```text
新 MemoryEntry
  ↓
检索相似历史 MemoryEntry
  ↓
判断关系：
    duplicate
    supplement
    contradict
    refine
    temporal_update
  ↓
合并或建立图关系
  ↓
更新 canonical memory
```

### 13.4 CanonicalMemory 设计

```text
id
user_id
type
title
summary
current_state
evidence_count
confidence
importance_score
first_seen_at
last_seen_at
status
created_at
updated_at
```

### 13.5 MemoryEntry 与 CanonicalMemory

```text
(:MemoryEntry)-[:INSTANCE_OF]->(:CanonicalMemory)
(:MemoryEntry)-[:REFINES]->(:MemoryEntry)
(:MemoryEntry)-[:CONTRADICTS]->(:MemoryEntry)
```

### 13.6 价值

- 降低记忆噪声
- 发现长期趋势
- 支持成长时间线
- 支持画像更新
- 支持“我以前是不是改变过想法？”这类问题

---

## 14. 个人画像快照

### 14.1 问题

如果每次生成画像都临时扫描全部资料，成本高且结果不稳定。

### 14.2 目标

建立周期性或事件驱动的画像快照。

### 14.3 快照类型

```text
stable_profile      长期稳定画像
recent_profile      最近 30 天画像
topic_profile       某个主题画像
growth_snapshot     阶段性成长分析
preference_snapshot 偏好摘要
goal_snapshot       目标摘要
```

### 14.4 ProfileSnapshot 字段

```text
id
user_id
knowledge_base_id
snapshot_type
time_range_start
time_range_end
summary
traits
goals
preferences
risks
evidence_memory_ids
confidence
created_at
```

### 14.5 刷新策略

```text
文档索引完成后局部刷新
MemoryEntry 合并后局部刷新
每天/每周定时全量刷新
用户手动触发刷新
```

---

## 15. 时间线与反复主题发现

### 15.1 目标

让系统能回答：

```text
我最近反复关注什么？
我的长期目标怎么变化？
哪些问题一直没有解决？
哪些观点前后发生过变化？
```

### 15.2 推荐能力

```text
Topic Frequency Timeline
Memory Recurrence Detection
Goal Evolution Detection
Contradiction Detection
Period Summary
```

### 15.3 示例输出

```text
过去 6 个月反复出现的主题：
1. Agent 工程化
2. 后端与数据基础设施结合
3. 轻量数据处理技术
4. GraphRAG 与长期记忆
```

---

# Phase 6：评测闭环

## 16. RAG Eval

### 16.1 问题

没有评测闭环时，RAG 优化容易靠感觉。

### 16.2 目标

建立检索、回答、引用、图扩展的评测体系。

### 16.3 Eval 数据结构

```text
eval_dataset
eval_case
eval_run
eval_result
```

### 16.4 EvalCase 字段

```text
id
dataset_id
question
expected_answer
expected_document_ids
expected_chunk_ids
expected_memory_entry_ids
expected_topics
rubric
created_at
```

### 16.5 指标

```text
Recall@K
MRR
Context Precision
Answer Faithfulness
Citation Accuracy
Graph Expansion Usefulness
Hallucination Rate
```

### 16.6 评测触发时机

```text
修改 chunk 策略后
修改 embedding 模型后
修改 rerank 逻辑后
修改 GraphRAG 后
发布新版本前
```

---

## 17. Retrieval Debug

### 17.1 目标

每次问答都能看到系统为什么召回这些上下文。

### 17.2 Debug 信息

```text
query_rewrite
vector_results
keyword_results
memory_results
graph_expansion_paths
rerank_scores
final_context_items
excluded_items
```

### 17.3 价值

- 方便排查召回失败
- 方便调参
- 方便做 eval
- 方便解释回答来源

---

# Phase 7：模块化与工程结构

## 18. 领域模块拆分

### 18.1 问题

随着项目复杂度上升，全局 `routers/ services/ models/ schemas/ crud/ utils/` 结构容易变得难维护。

### 18.2 推荐结构

```text
mneme/
  auth/
  users/
  knowledge_base/
  documents/
  chunks/
  retrieval/
  memory/
  graph/
  profile/
  analysis/
  companion/
  tasks/
  eval/
  storage/
  common/
```

### 18.3 每个模块内部

```text
models.py
schemas.py
repository.py
service.py
router.py
events.py
```

### 18.4 价值

- 降低模块耦合
- 更容易测试
- 更容易替换实现
- 更适合长期维护

---

## 19. Service 边界建议

### 19.1 RetrievalService

负责：

```text
query analysis
vector search
keyword search
memory search
graph expansion
rerank
context assembly
```

### 19.2 MemoryService

负责：

```text
memory extraction
memory merge
memory status update
canonical memory
memory confidence
```

### 19.3 GraphService

负责：

```text
Neo4j projection
graph query
graph expansion
graph rebuild
graph relationship calculation
```

### 19.4 TaskService

负责：

```text
task lifecycle
progress update
retry
failure logging
```

### 19.5 ProfileService

负责：

```text
profile snapshot
growth summary
preference summary
goal summary
```

### 19.6 EvalService

负责：

```text
eval dataset
eval run
retrieval eval
answer eval
report generation
```

---

# 20. 推荐实施路线图

## 20.1 第 1 周：记忆闭环

目标：

```text
MemoryEntry 接入文档索引流程
MemoryEntry 与 Chunk / Document 建立关系
RAG 回答支持 source_memory_entry_ids
```

任务：

```text
1. 设计 MemoryEntry 类型与字段
2. 在文档索引 pipeline 中加入 memory extraction
3. 将 MemoryEntry 写入 PostgreSQL
4. 同步 MemoryEntry 到 Neo4j
5. RAG 回答返回引用证据
```

验收标准：

```text
上传一篇文档后，系统能自动生成 MemoryEntry
用户提问时，回答能引用相关 MemoryEntry
Neo4j 中能看到 Document -> MemoryEntry 关系
```

---

## 20.2 第 2 周：Hybrid Search

目标：

```text
将纯向量检索升级为 vector + keyword + memory 检索
```

任务：

```text
1. 为 Document / Chunk / MemoryEntry 增加全文检索能力
2. 设计 ContextItem 统一返回结构
3. 实现多路召回合并
4. 增加基础 rerank 规则
5. 输出 retrieval_debug_info
```

验收标准：

```text
关键词型问题能准确命中文档
语义型问题仍能通过向量召回
回答结果能展示每个上下文来源的召回原因
```

---

## 20.3 第 3 周：GraphRAG

目标：

```text
让 Neo4j 参与检索上下文扩展
```

任务：

```text
1. 增加 MemoryEntry 相关图关系
2. 增加 graph expansion 查询接口
3. 将 graph paths 转换为 structured context
4. 在 RetrievalService 中接入 GraphRAG
5. 给回答结果增加 graph_context
```

验收标准：

```text
用户问题能触发图谱扩展
回答能利用相关记忆、主题、文档关系
debug 信息中能看到 graph path
```

---

## 20.4 第 4 周：任务状态机与 Outbox

目标：

```text
提升异步任务和图投影可靠性
```

任务：

```text
1. 完善 TaskRecord 状态机
2. 文档索引流程异步化
3. 增加 graph_projection_outbox
4. 增加 outbox worker
5. 增加失败重试和 dead_letter
```

验收标准：

```text
长任务有明确进度
Neo4j 短暂不可用不会导致图谱投影永久丢失
失败任务可以重试
```

---

## 20.5 第 5 周：记忆合并与画像快照

目标：

```text
从记忆条目堆积升级为长期记忆管理
```

任务：

```text
1. 设计 CanonicalMemory
2. 实现相似记忆检测
3. 实现 duplicate / supplement / contradict / refine 分类
4. 建立 ProfileSnapshot
5. 文档更新后局部刷新画像
```

验收标准：

```text
重复记忆能被合并
冲突记忆能被标记
用户画像可以从快照读取，而不是每次全量生成
```

---

## 20.6 第 6 周：评测闭环

目标：

```text
建立可持续优化 RAG 的评测体系
```

任务：

```text
1. 建立 eval_dataset / eval_case / eval_run / eval_result
2. 增加检索评测
3. 增加回答忠实度评测
4. 增加引用准确性评测
5. 生成 eval report
```

验收标准：

```text
修改检索策略后，可以量化比较效果
每次评测能看到 Recall@K、Faithfulness、Citation Accuracy
```

---

## 20.7 第 7 周：DuckDB 分析与调试辅助层

目标：

```text
用 DuckDB 建立本地分析、Eval 报表和检索调试能力
```

任务：

```text
1. 将 retrieval logs / eval results / chunk stats 导出为 Parquet
2. 增加 DuckDB 分析脚本
3. 生成 chunk 质量报告
4. 生成 retrieval debug 报告
5. 生成 eval 对比报告
```

验收标准：

```text
可以用 SQL 分析一次 RAG Eval 的结果
可以对比不同检索策略的效果
可以定位低质量 chunk、低置信度 memory、低命中 query
```

---

# 21. P0 任务清单

以下是最建议优先完成的任务：

```text
1. MemoryEntry 接入主索引流程
2. RAG 回答绑定证据来源
3. ContextItem 统一抽象
4. Hybrid Search 初版
5. Neo4j GraphRAG 扩展查询
6. TaskRecord 状态机
7. graph_projection_outbox
8. Retrieval Debug 信息
```

---

# 22. 不建议近期做的事情

当前阶段不建议优先做：

```text
1. 多模态图片/音频/视频能力
2. 引入过重的数据平台，如 Flink、Kafka、Spark 集群
3. 过早做复杂前端可视化
4. 过早接入多个向量数据库
5. 过早做大规模权限系统
6. 过早做复杂 agent 多角色协作
```

原因：

```text
当前项目的核心差异化还没有完全落在“长期记忆系统”上。
在记忆抽取、合并、GraphRAG、证据化回答和评测闭环完成前，继续加外围能力会稀释重点。
```

---

# 23. 最终目标形态

优化完成后的 Mneme 应该具备以下能力：

```text
1. 用户上传文档后，系统自动抽取长期记忆
2. 每条记忆都有证据来源
3. 系统能识别重复、补充、冲突和演化的记忆
4. 用户提问时，不只是检索 Chunk，而是检索 Chunk + Memory + Graph
5. Neo4j 不只是展示图谱，而是参与 GraphRAG
6. 回答能解释依据、置信度和不确定性
7. 长任务可追踪、可重试、可恢复
8. RAG 效果可以通过 eval 持续评估
9. 用户画像来自稳定快照，而不是每次临时生成
10. 整体系统具备向“个人记忆操作系统”演进的基础
```

---

# 24. 一句话总结

Mneme 下一阶段最值得优化的方向是：

```text
把 MemoryEntry 从辅助功能变成核心资产，
把 Neo4j 从图展示变成 GraphRAG 检索层，
把 RAG 从一次性生成变成证据驱动、可评测、可演化的长期记忆系统。
```

---

# 25. 参考 AtlasClaw 的架构借鉴清单

这里不照搬 `D:\python_files\atlasclaw` 的平台能力，只提炼对 `Mneme` 真正有用的架构做法。

Mneme 当前的主要问题是：

```text
main.py 入口偏重
routers / services / models / schemas / crud 平铺
documents 等路由直接编排 storage / graph sync / task queue
pipeline 已承载主链路，但副作用边界还不够清楚
```

## 25.1 值得直接参考的部分

### A. 薄入口 + bootstrap 分层

参考 AtlasClaw，把应用拆成：

```text
main.py
  -> create_app()
  -> lifespan()

bootstrap/
  -> app_factory.py
  -> startup.py
  -> shutdown.py
  -> router_registry.py
```

目的：

```text
让 main.py 只负责装配
把日志、数据库、Milvus、Neo4j、Celery、资源检查从入口下沉
```

### B. 请求级依赖收口

当前很多接口直接依赖：

```text
Depends(get_current_user)
Depends(get_database)
```

后面引入更多能力后，建议统一成一个轻量上下文对象：

```text
RequestContext
  user
  db
  request_id
  knowledge_base_scope
  trace metadata
  feature flags
```

目的是减少路由层重复代码，不是做复杂 IoC。

### C. `api/` 装配层

建议增加轻量的 API 收口层：

```text
api/
  router.py
  deps.py
  errors.py
  response.py
```

职责：

```text
router.py 统一 include_router
deps.py 统一 DB / user / request scope
errors.py 统一异常映射
response.py 统一响应结构
```

### D. 领域优先目录

相比继续扩大：

```text
routers/
services/
schemas/
models/
crud/
clients/
pipelines/
```

更适合逐步转成：

```text
app/
  mneme/
    api/
    core/
    infra/
    domains/
      auth/
      users/
      documents/
      retrieval/
      memory/
      graph/
      profile/
      tasks/
      analysis/
```

每个领域内部再放：

```text
router.py
schemas.py
service.py
repository.py
models.py
events.py
```

### E. 全局资源容器

可引入轻量版 `AppContainer`：

```text
AppContainer
  settings
  db_engine
  vector_client
  graph_client
  task_dispatcher
  retrieval_service
  graph_projection_service
```

目的：

```text
减少全局 import 穿透
方便测试替换依赖
方便启动期统一校验资源
```

### F. 更清楚的运行时边界

目标边界应收敛为：

```text
router
  -> application service
application service
  -> repository / domain service / dispatcher
pipeline
  -> 只负责阶段执行
projection / outbox / async task
  -> 独立处理副作用
```

这比继续让 `documents` 路由直接操作多个基础设施更可维护。

## 25.2 适合中期借鉴的部分

```text
1. Retrieval Orchestrator
   统一 query analysis / recall / rerank / context assembly / debug payload

2. Runtime 目录治理
   明确 storage/raw、parsed、debug、eval、reports 等目录边界

3. 测试分层
   至少建立 api / services / pipelines / retrieval / graph / tasks

4. docs/architecture.md
   把系统上下文、索引链路、检索链路、异步任务链路写成事实文档
```

## 25.3 当前不建议照搬的部分

下面这些不是当前 Mneme 的第一优先级：

```text
多渠道接入
Provider Registry / 插件化外部系统
复杂 RBAC 与租户隔离
Hook Runtime / Heartbeat Runtime
TokenPool / 多模型多令牌调度
平台型后台能力
```

当前资源更应该优先投入：

```text
长期记忆闭环
Hybrid Search
GraphRAG
Evidence 回答
任务可靠性
评测闭环
模块边界稳定
```

## 25.4 引入 LlamaIndex / MongoDB 的裁剪式策略

这两个方向都可以帮助 Mneme 减重，但职责不同：

```text
LlamaIndex 适合减少 RAG 编排代码量
MongoDB 适合承接半结构化数据与可选的检索统一层
```

### A. LlamaIndex 建议引入

优先让 LlamaIndex 接管这些能力：

```text
1. ingestion pipeline
   文档加载、切分、节点化、metadata 处理、去重

2. retrieval pipeline
   retriever、rerank、query engine、context assembly

3. GraphRAG PoC
   优先尝试 PropertyGraphIndex + Neo4j
```

这意味着可以逐步减薄当前这些自研层：

```text
clients/document_loader_client.py
clients/text_splitter_client.py
部分 vector retrieval 编排
部分 memory / graph 检索编排
```

### B. LlamaIndex 暂不接管

下面这些暂时不要交给 LlamaIndex：

```text
FastAPI 路由层
鉴权与用户体系
TaskRecord 状态机
Celery 分发与任务治理
Document / User / KnowledgeBase 主数据事务
```

原因：

```text
这些是系统骨架，不是 RAG 框架最擅长的部分
```

### C. MongoDB 建议引入的方式

MongoDB 目前更适合先做两类角色：

```text
1. 半结构化副存储
   ProfileSnapshot
   RetrievalDebugInfo
   EvalResult
   Memory 主题归档
   实验与分析报告

2. 检索统一层候选
   如果后面希望把 metadata filter + vector search + text search 尽量收敛到一处，
   可以评估 MongoDB Atlas Vector Search 作为 Milvus 的替代候选
```

### D. MongoDB 当前不建议直接替换

暂时不建议直接用 MongoDB 替掉这些主事务对象：

```text
users
documents
knowledge_bases
task_records
核心业务事实表
```

原因：

```text
当前项目已经基于 SQLAlchemy + Alembic + PostgreSQL 建好主数据层
TaskRecord / Document / User 这类对象仍然更适合关系型事务边界
如果现在直接替主库，复杂度会明显高于收益
```

### E. 推荐引入顺序

推荐顺序如下：

```text
Phase A
  保留 PostgreSQL + Milvus + Neo4j
  引入 LlamaIndex，只替换 ingestion / retrieval / GraphRAG 编排

Phase B
  引入 MongoDB 作为 snapshot / debug / eval / retrieval logs 的副存储

Phase C
  如果 MongoDB Atlas Vector Search 实测足够稳定，再评估是否替换 Milvus

Phase D
  最后才讨论 MongoDB 是否进入主业务数据层
```

### F. 对 Mneme 的直接意义

如果按这个方式引入，收益是：

```text
减少自研 RAG 编排代码
减少未来维护 loader / splitter / retriever / query engine 的成本
保留 PostgreSQL 事务主干稳定性
给后续 Hybrid Search / GraphRAG / Eval 留出更快的实验空间
```

---

# 26. 参考 AtlasClaw 的架构改造步骤

这里保留最终效果不变，只压缩为更短的执行路线。

## 26.1 阶段 0：先定边界

目标：

```text
先确定 api / application / domain / infra 四层职责，再做迁移
```

要点：

```text
pipeline 只做阶段执行
router 不直接做 graph sync / queue dispatch / storage orchestration
repository 管 DB 读写
service 管业务编排
clients 只封装外部调用
```

产出：

```text
docs/architecture.md 初稿
模块职责表
迁移优先级列表
```

## 26.2 阶段 1：把 `main.py` 变薄

目标结构：

```text
app/mneme/
  main.py
  bootstrap/
    app_factory.py
    startup.py
    shutdown.py
    router_registry.py
```

动作：

```text
提取 create_app()
提取 lifespan()
提取 routers / middlewares / exception handlers 注册
提取 startup resource checks
```

验收：

```text
路由与中间件行为不变
应用仍可正常启动
main.py 只保留薄装配
```

## 26.3 阶段 2：引入 `core` 和 `api`

目标结构：

```text
app/mneme/
  core/
    config.py
    deps.py
    container.py
    logging.py
  api/
    router.py
    deps.py
    response.py
    errors.py
```

动作：

```text
把配置和 DB 依赖收口
定义 RequestContext
定义 AppContainer
把 success_response / exception handler 收口到 api 层
```

验收：

```text
DB / user / request scope 获取方式统一
异常与响应有单一入口
```

## 26.4 阶段 3：先重构 `documents`

之所以先做它，是因为它同时牵涉：

```text
上传
文件存储
文档记录
task_record
pipeline
memory rebuild
graph projection
vector upsert
```

目标结构：

```text
domains/documents/
  router.py
  schemas.py
  repository.py
  service.py
  storage.py
  events.py
```

动作：

```text
router 只做参数解析、鉴权、响应
文件保存下沉到 storage service
文档 CRUD 下沉到 repository
索引提交放到 documents service
graph projection 改成事件或 dispatcher 触发
```

验收：

```text
documents/router.py 不再直接编排多个副作用
上传、索引、删除链路行为保持一致
```

## 26.5 阶段 4：抽 `retrieval`

目标结构：

```text
domains/retrieval/
  service.py
  schemas.py
  rerank.py
  context_builder.py
  debug.py
```

动作：

```text
定义 ContextItem
抽 RetrievalService
抽 QueryAnalysis / RecallMerger / RetrievalDebugPayload
让 chat / analysis / advice / companion 共享 retrieval service
```

验收：

```text
召回逻辑不再重复
retrieval_debug_info 结构统一
GraphRAG 接入点唯一
```

## 26.6 阶段 5：抽 `memory` 与 `graph`

目标结构：

```text
domains/memory/
  service.py
  extractor.py
  merger.py
  repository.py

domains/graph/
  service.py
  projection.py
  queries.py
  repository.py
```

动作：

```text
Memory 提供 extract / merge / query
Graph 提供 project / expand / rebuild
pipeline 只调用领域接口
Neo4j 写入逐步改成 outbox 驱动
```

## 26.7 阶段 6：独立 `workflow / jobs`

目标结构：

```text
workflow/
  jobs/
    document_index.py
  dispatcher.py
  task_state.py
  events.py
```

动作：

```text
`infra/task_queue.py` 只做 dispatch
`tasks/index_tasks.py` 迁到 workflow/jobs
`services/task_state_service.py` 迁到 workflow/task_state.py
统一任务状态枚举与 progress / result / error payload
```

验收：

```text
任务执行层与 HTTP 路由解耦
状态机集中维护
```

## 26.8 阶段 7：整体目录收口到包内

推荐目标：

```text
app/
  mneme/
    main.py
    bootstrap/
    api/
    core/
    infra/
    workflow/
    domains/
      auth/
      users/
      documents/
      retrieval/
      memory/
      graph/
      profile/
      tasks/
      analysis/
      companion/
    tests/
```

说明：

```text
这一步放在前面阶段完成后再做
否则只是搬目录，不是真正降耦合
```

## 26.9 阶段 8：补测试与文档闭环

动作：

```text
为 documents / retrieval / memory / graph / workflow 建最小测试集
为 startup / config / deps 建基础测试
新增 docs/architecture.md / docs/runtime-flows.md / docs/module-boundaries.md
```

验收：

```text
核心主链路重构后可回归验证
文档可支持后续持续演进
```

---

# 27. 简化结论

Mneme 最值得学习 AtlasClaw 的，不是平台化功能，而是：

```text
把启动、依赖、领域、运行时副作用分层收口
```

最建议的顺序仍然不变：

```text
1. main.py 变薄
2. 引入 api / core / container
3. 先重构 documents
4. 抽 retrieval orchestrator
5. 抽 memory / graph 边界
6. 独立 workflow / jobs
7. 最后再做整体目录迁移
```

这样做既能减小重构风险，也能真正托住后面的 MemoryEntry、GraphRAG 和 Eval 演进。
