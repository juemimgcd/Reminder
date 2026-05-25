# Day 10：Retrieval Debug，建立调优观测面

## 今天的总目标

今天不是继续改召回公式，  
也不是继续增加新的检索源，  
而是在 Day 7 到 Day 9 已经形成的链路上，  
补上一份**可读、可返回、可日志观测的 Retrieval Debug packet**。

Day 10 要解决的问题是：

> 当 RAG 回答不好时，系统到底是 router 分错了、召回没召到、fusion 排错了、context 组装错了，还是生成阶段没有正确引用证据？

所以今天的优化目标是：

```text
router decision
-> recall candidates
-> fusion / rerank scores
-> final context
-> answer / citation debug
```

---

## 今天结束前已经拿到什么

今天完成了这 6 件事：

1. 在 `schemas/chat.py` 新增 `RetrievalDebugData`，并把它挂到 `ChatQueryData.debug`。
2. 新增 `services/retrieval_debug_service.py`，专门负责把内部对象序列化成 debug packet。
3. `services/context_service.py` 会返回 `debug`，包含 query terms、lexical backend、各路候选、fusion/rerank 后候选和 final context。
4. `services/query_service.py` 会把 route 和 answer/citation debug 合并进最终返回。
5. 非 RAG 分支也会返回 debug，说明为什么 bypass retrieval。
6. 新增 `scripts/debug_day10.py`，可在无数据库、无 ES、无 LLM key 的环境下验证 debug packet 结构。

---

## Day 10 一图总览

```text
Question
-> Query Router
-> Retrieval
   - vector candidates
   - lexical candidates
   - memory candidates
-> Fusion / Rerank
-> Final Context
-> Evidence Answer
-> Debug Packet
```

```mermaid
flowchart LR
    A[Query] --> B[Router Debug]
    B --> C[Recall Debug]
    C --> D[Fusion / Rerank Debug]
    D --> E[Context Debug]
    E --> F[Answer / Citation Debug]
```

---

## 这一天为什么重要

RAG 失败并不只有一种原因。

常见失败路径至少有这些：

```text
router 把问题分错了
vector 没召回关键 chunk
BM25 / keyword 没命中精确词
memory recall 噪声太大
fusion 把正确候选排低了
rerank bonus 给错了
final context 被 budget 截掉了
模型没有引用已经给出的证据
```

如果没有 Retrieval Debug，  
这些问题都会被模糊地归因成：

```text
RAG 效果不好
```

Day 10 的核心是让系统开始能回答：

> 坏在链路的哪一段。

---

## 本次代码落点

### 文件 1：`schemas/chat.py`

新增：

```python
class RetrievalDebugData(BaseModel):
    route: dict | None = None
    query_terms: list[str]
    lexical_backend: str | None
    counts: dict[str, int]
    vector_candidates: list[dict]
    lexical_candidates: list[dict]
    memory_candidates: list[dict]
    fused_candidates: list[dict]
    final_context: list[dict]
    answer_debug: dict | None
```

并在 `ChatQueryData` 中新增：

```python
debug: RetrievalDebugData | None = None
```

这不会破坏现有 answer/sources/citations 结构，  
但会让调试工具可以直接看到完整链路。

---

### 文件 2：`services/retrieval_debug_service.py`

新增 4 个核心函数：

```python
serialize_context_item(...)
serialize_context_items(...)
build_retrieval_debug_packet(...)
build_answer_debug(...)
```

其中 `serialize_context_item(...)` 会保留：

```text
rank
recall_type
document_id
chunk_id
memory_entry_id
section_title
section_path
matched_terms
vector_score
bm25_score
keyword_score
memory_score
fusion_score
rerank_score
exact_match_count
recall_ranks
rerank_reasons
text_preview
```

注意这里输出的是 `text_preview`，不是完整 chunk 文本，避免 debug packet 过大。

---

### 文件 3：`services/context_service.py`

`build_query_context(...)` 现在返回：

```python
"debug": build_retrieval_debug_packet(...)
```

debug packet 包含：

```text
query_terms
lexical_backend
counts
vector_candidates
lexical_candidates
memory_candidates
fused_candidates
final_context
```

其中 `counts` 包含：

```text
raw_count
dedup_count
vector_count
lexical_count
memory_count
candidate_count
fusion_count
rerank_count
final_count
```

这让“没召回”和“召回了但没进 final context”可以被区分。

---

### 文件 4：`services/query_service.py`

`generate_rag_answer(...)` 现在会把 route 和 answer debug 合并进去：

```text
debug["route"] = route
debug["answer_debug"] = build_answer_debug(...)
```

`answer_debug` 包含：

```text
answer_length
source_count
citation_count
available_source_ids
cited_source_ids
confidence
uncertainty
```

这样可以初步判断：

```text
有 source 但没有 citation
citation 引用的是哪些 source
answer 是否低 confidence
```

---

### 文件 5：非 RAG 分支 Debug

Day 7 引入了这些分支：

```text
general_chat
profile_query
analysis_query
action_request
```

Day 10 给它们也补了 debug：

```text
route
counts 全为 0
answer_debug.path
answer_debug.reason
```

这样调试时不会误以为“没有 retrieval debug 是系统漏记录”，  
而是能明确看到：

```text
这次本来就没有走检索
```

---

### 文件 6：`scripts/debug_day10.py`

新增本地脚本：

```text
.\.venv\Scripts\python.exe scripts\debug_day10.py
```

它构造一组模拟候选：

```text
vector: chunk_debug_1
bm25: chunk_debug_1
memory: chunk_debug_1
```

然后验证 debug packet 能看到：

```text
query_type
lexical_backend
counts
vector candidate count
lexical candidate count
memory candidate count
fused top recall type
final context count
answer_debug
```

---

## 当前 Debug Packet 结构

一个 RAG 问答的 debug 大致长这样：

```text
debug
├── route
├── query_terms
├── lexical_backend
├── counts
├── vector_candidates
├── lexical_candidates
├── memory_candidates
├── fused_candidates
├── final_context
└── answer_debug
```

这对应 Day 10 的 5 段问题定位：

```text
router debug
recall debug
fusion / rerank debug
context debug
answer / citation debug
```

---

## 本地验证结果

已运行语法检查：

```text
.\.venv\Scripts\python.exe -m compileall schemas\chat.py services\retrieval_debug_service.py services\context_service.py services\query_service.py scripts\debug_day10.py
```

已运行 Day 10 调试脚本：

```text
.\.venv\Scripts\python.exe scripts\debug_day10.py
```

关键输出：

```text
query_type=kb_qa
lexical_backend=elasticsearch_bm25
counts={'raw_count': 1, 'dedup_count': 1, 'vector_count': 1, 'lexical_count': 1, 'memory_count': 1, 'candidate_count': 3, 'fusion_count': 1, 'rerank_count': 1, 'final_count': 1}
vector_candidate_count=1
lexical_candidate_count=1
memory_candidate_count=1
fused_top_recall_type=vector+bm25+memory
final_context_count=1
answer_debug={'answer_length': 52, 'source_count': 1, 'citation_count': 1, ...}
```

这说明 Day 10 的最小验收成立：

```text
router 决策可见
recall 候选可见
fusion/rerank 后的排序可见
final context 可见
answer/citation 统计可见
```

---

## 今天没有做什么

### 1. 没有新建 debug 数据库表

今天先把 debug packet 做成响应对象和日志可消费结构。  
真正落库可以和 Day 11 的 eval run / eval result 一起设计，避免提前建一张字段不稳定的表。

### 2. 没有改变 fusion/rerank 公式

Day 10 只做观测面，不继续改排序策略。  
排序策略仍然沿用 Day 9 的 RRF + lightweight rerank。

### 3. 没有做 citation 严格校验

当前只记录 citation 统计。  
quote 是否真的存在于 source text、claim 是否被支撑，留给 Day 12。

---

## 今日验收标准

今天结束时，至少要能回答这 6 个问题：

1. 一次问答没有 source 时，是 router 没让它检索，还是 retrieval 没召回？
2. vector、lexical、memory 三路分别召回了多少候选？
3. 被多路召回命中的 chunk 在 fusion 后有没有排上去？
4. final context 是哪些候选，和 fused candidates 是否一致？
5. 模型最终引用了哪些 source_id？
6. 当前 debug packet 哪些字段能直接服务 Day 11 eval？

---

## 给 Day 11 的交接提示

Day 11 可以接住 Day 10 的这个前提：

> 每次问答已经能产出一份结构化 debug packet，里面有 query、router、recall、fusion、rerank、context 和 answer/citation 的关键字段。

所以 Day 11 不需要靠人工观察日志来判断效果，  
而可以开始设计：

```text
eval case
expected source ids
retrieval result
Recall@K
MRR
nDCG
source hit
answer relevance
citation accuracy
```

Day 10 最终交给 Day 11 的输入是：

```text
RetrievalDebugData
counts
candidate ranks
final context
answer_debug
```

这就是 Day 10 最终要交给 Day 11 的东西。
