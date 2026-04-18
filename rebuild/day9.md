# Day 9：Context 组装治理

## 今天的总目标

- 把 `context_service` 从“检索入口”升级成“上下文治理层”
- 不再把 `top_k` 召回结果原样拼进 prompt
- 给检索结果补上去重、相邻 chunk 合并、budget 裁剪
- 让 `query_service` 只消费治理后的 context packet
- 为 Day 10 的运行时治理和 Day 13 的 Context Harness 打基础

## 今天结束前，你必须拿到什么

- 一套你自己能讲清楚的 raw retrieval 和 governed context 区分
- `services/context_service.py` 的治理入口设计
- 第一版去重、相邻合并、budget 裁剪方案
- `services/query_service.py` 的改法
- 一份你自己能讲清楚的“Day 9 为什么不是调 top_k”的认知

---

## 今天开始，RAG 不能再把召回结果直接塞进 prompt

从当前仓库看，Day 8 之后边界已经基本开始稳定：

- `services/context_service.py` 已经存在
- `services/query_service.py` 已经承接问答入口
- `routers/chat.py` 和 `routers/companion.py` 都在复用 `generate_rag_answer(...)`
- `clients/vector_store_client.py` 和 `clients/llm_client.py` 已经把依赖访问边界立起来

但现在仍然有一个很明显的问题：

```text
retrieve_documents(...)
-> format_docs(docs)
-> prompt
```

这说明当前链路里：

- 检索结果没有显式去重
- 相邻 chunk 没有合并
- 最终上下文没有预算控制
- source 列表和 prompt context 基本共用原始 docs

所以 Day 9 的核心不是继续改 prompt，  
而是：

> 先把 prompt 之前的输入治理好。

---

## 第 1 层：今天哪些地方需要写代码，哪些地方不需要

### 需要写代码的地方

这些地方不是讲概念就够了，  
应该给壳子和参考答案：

- `services/context_service.py`
- `services/query_service.py`
- 验收脚本，例如 `scripts/debug_day9.py`

原因：

- Day 9 的核心能力都落在这里
- 它们会真正改变问答主链路

### 不需要大写代码，只需要说清楚边界的地方

这些地方今天不建议大改：

- `schemas/chat.py`
- `utils/prompt_builder.py`
- `routers/chat.py`

原因：

- Day 9 的关键不是 API 契约变化
- 也不是 prompt 模板重写
- 重点是 `context_service` 的治理能力

### 今天的原则

```text
谁负责治理 context
-> 一定给代码

只涉及 API 口径和后续可选优化
-> 先说明边界，不急着展开
```

---

## 第 2 层：先把 Day 9 的两层问题分清楚

Day 9 最重要的认知，是把这两层分开。

### 第 1 层：raw retrieval

它关注的是：

- 从向量库召回什么
- `top_k` 多少
- metadata filter 怎么套
- score 怎么返回

### 第 2 层：governed context

它关注的是：

- 哪些片段要丢掉
- 哪些片段要合并
- 最终上下文保留多少
- 最终给 LLM 的文本长什么样
- 返回给前端的 sources 长什么样

如果 Day 9 不先把这两层拆开，  
你后面会很难判断：

- 是检索差
- 还是 context packing 差
- 还是 prompt 真有问题

---

## 第 3 层：结合当前项目，Day 9 的真实问题点

### 问题 1：`context_service` 现在更像检索入口

当前 `services/context_service.py` 已经做了：

- metadata filter
- Milvus expr
- retriever 构建
- `retrieve_documents(...)`
- `retrieve_documents_with_scores(...)`

但它还没做：

- 去重
- chunk 合并
- budget 裁剪
- 最终 context 组装

所以 Day 9 的第一件事，就是继续扩它的职责。

### 问题 2：`query_service` 现在还在原样拼 docs

当前路径基本是：

```text
retrieve_documents(...)
-> format_docs(docs)
-> prompt
```

这会带来非常现实的问题：

- 重复 chunk 直接浪费上下文
- 碎片 chunk 不利于 LLM 理解
- 长短不一的片段让 `top_k` 失去预算意义

### 问题 3：`top_k` 被误当成上下文预算

当前 `schemas/chat.py` 只有：

- `top_k`

但 Day 9 必须明确：

> `top_k` 只是召回控制，不是最终 context 大小控制。

真正应该控制最终输入大小的，  
是：

- `context_budget`
- 或第一版更务实的字符预算

### 问题 4：Day 9 不只影响 chat

因为 `routers/companion.py` 也会复用：

- `generate_rag_answer(...)`

这意味着 Day 9 的改动不是只优化一个接口。  
它会直接影响：

- chat answer
- companion 的 RAG 部分
- 后续任何复用 query service 的链路

---

## 第 4 层：今天要改哪些文件

Day 9 主要围绕这些文件展开：

- `services/context_service.py`
- `services/query_service.py`
- `scripts/debug_day9.py`

### 每个文件今天负责什么

| 文件 | 今天负责什么 |
|---|---|
| `services/context_service.py` | 召回后治理、组装 context packet |
| `services/query_service.py` | 改成只消费治理后的 context |
| `scripts/debug_day9.py` | 打印治理前后统计，做最小验收 |

---

## 第 5 层：今天不要做什么

Day 9 不建议做：

- 不做复杂 rerank
- 不做 query rewrite
- 不做 cross-encoder
- 不做复杂语义压缩
- 不做精确 tokenizer 工程化
- 不做 API schema 全面改造

今天只做：

> 让召回结果进入 prompt 之前，先经过最基本的上下文治理。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 9 的主问题讲顺

### 今天你要能顺着说出来

```text
Day 8 先把 query / companion 这类链路的模块边界立起来
-> Day 9 再把 retrieval 和 context packing 分层
-> 让 query_service 不再直接吃原始召回结果
```

### 你必须能回答这两个问题

1. 为什么 `top_k` 不能等价于最终 context 大小？
2. 为什么 Day 9 的主逻辑应该收在 `context_service`，而不是塞回 `query_service`？

---

## 09:50 - 10:40：先把 Day 9 的目标输入输出讲清楚

### Day 9 之后 `context_service` 的理想输入

- `query`
- `user_id`
- `knowledge_base_id`
- `top_k`
- `context_budget`

### Day 9 之后 `context_service` 的理想输出

- `context_text`
- `sources`
- `raw_count`
- `dedup_count`
- `merged_count`
- `final_count`

### 为什么先定这个结构

因为一旦这个结构清楚，  
后面 helper 函数怎么拆就很自然了。

---

## 10:40 - 11:30：先决定去重和合并的第一版口径

### 去重第一版最稳的规则

1. 先按 `chunk_id` 去重
2. 再按 `document_id + page_no + text` 做弱去重

### 相邻合并第一版最稳的规则

- 同 `document_id`
- `chunk_index` 连续
- `page_no` 一致或相邻
- 合并后长度不超过上限

### 为什么 Day 9 第一版先这样做

因为：

- 规则简单
- 可解释
- 风险低
- 足够解决第一批脏上下文问题

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 9 最直接的验收方式

今天最少要能回答：

1. raw retrieval 和 governed context 的区别是什么？
2. 为什么当前 metadata 已经足够支持第一版相邻 chunk 合并？
3. Day 9 的 budget 第一版为什么可以先用字符数近似？
4. `query_service` 在 Day 9 之后为什么应该变薄？
5. Day 9 做完以后，Day 10 为什么更容易落地？

---

## 下午编码：14:00 - 18:00

## 14:00 - 15:00：先把 `context_service` 扩成治理入口

### 这一段属于新增能力

Day 9 第一件事不是改 prompt。  
而是先在 `services/context_service.py` 里补一个统一入口，例如：

- `build_query_context(...)`

它负责：

```text
retrieve_with_scores
-> deduplicate
-> merge_adjacent
-> trim_by_budget
-> build context_text
-> build sources
```

### `services/context_service.py` 练手骨架版

```python
from langchain_core.documents import Document as LCDocument


def build_source_item(doc: LCDocument) -> dict:
    # 你要做的事：
    # 1. 从 metadata 提取 knowledge_base_id / document_id / chunk_id / page_no
    # 2. 带上 text
    raise NotImplementedError("先自己实现 build_source_item")


def deduplicate_retrieved_documents(
    items: list[tuple[LCDocument, float]],
) -> list[tuple[LCDocument, float]]:
    # 你要做的事：
    # 1. 先按 chunk_id 去重
    # 2. 再按 document_id + page_no + text 去重
    raise NotImplementedError("先自己实现 deduplicate_retrieved_documents")


def merge_adjacent_scored_documents(
    items: list[tuple[LCDocument, float]],
    *,
    max_merged_length: int = 1200,
) -> list[tuple[LCDocument, float]]:
    # 你要做的事：
    # 1. 同 document_id 内按 chunk_index 排序
    # 2. chunk_index 连续时尝试合并
    # 3. 合并后保留较优 score
    raise NotImplementedError("先自己实现 merge_adjacent_scored_documents")


def trim_scored_documents_by_budget(
    items: list[tuple[LCDocument, float]],
    *,
    max_chars: int,
) -> list[tuple[LCDocument, float]]:
    # 你要做的事：
    # 1. 顺序保留片段
    # 2. 累积字符数
    # 3. 超预算就停止
    raise NotImplementedError("先自己实现 trim_scored_documents_by_budget")


def format_context_docs(docs: list[LCDocument]) -> str:
    # 你要做的事：
    # 1. 把治理后的 docs 格式化成 prompt context
    raise NotImplementedError("先自己实现 format_context_docs")


async def build_query_context(
    query: str,
    *,
    top_k: int = 4,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
    context_budget: int = 4000,
) -> dict:
    # 你要做的事：
    # 1. 先召回 with scores
    # 2. 去重
    # 3. 合并
    # 4. 裁剪
    # 5. 生成 context_text / sources / 统计信息
    raise NotImplementedError("先自己实现 build_query_context")
```

### `services/context_service.py` 参考答案

```python
from copy import deepcopy
from typing import Any

from langchain_core.documents import Document as LCDocument

from clients.vector_store_client import get_vector_store


MetadataFilter = dict[str, int | str]


def build_metadata_filter(
    *,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
) -> MetadataFilter:
    metadata_filter: MetadataFilter = {}
    if user_id:
        metadata_filter["user_id"] = user_id
    if knowledge_base_id:
        metadata_filter["knowledge_base_id"] = knowledge_base_id
    return metadata_filter


def build_milvus_expr(metadata_filter: MetadataFilter) -> str | None:
    if not metadata_filter:
        return None

    expr_parts: list[str] = []
    for key, value in metadata_filter.items():
        if isinstance(value, str):
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            expr_parts.append(f'{key} == "{escaped_value}"')
        else:
            expr_parts.append(f"{key} == {value}")
    return " and ".join(expr_parts)


async def retrieve_documents_with_scores(
    query: str,
    top_k: int = 4,
    *,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
):
    vector_store = get_vector_store()
    metadata_filter = build_metadata_filter(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )
    expr = build_milvus_expr(metadata_filter)
    search_kwargs: dict[str, Any] = {
        "query": query,
        "k": top_k,
    }
    if expr:
        search_kwargs["expr"] = expr
    return vector_store.similarity_search_with_score(**search_kwargs)


def build_source_item(doc: LCDocument) -> dict:
    return {
        "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
        "document_id": doc.metadata.get("document_id"),
        "chunk_id": doc.metadata.get("chunk_id"),
        "page_no": doc.metadata.get("page_no"),
        "text": doc.page_content,
    }


def deduplicate_retrieved_documents(
    items: list[tuple[LCDocument, float]],
) -> list[tuple[LCDocument, float]]:
    deduped: list[tuple[LCDocument, float]] = []
    seen_chunk_ids: set[str] = set()
    seen_fallback_keys: set[tuple] = set()

    for doc, score in items:
        chunk_id = str(doc.metadata.get("chunk_id") or "")
        if chunk_id and chunk_id in seen_chunk_ids:
            continue

        fallback_key = (
            doc.metadata.get("document_id"),
            doc.metadata.get("page_no"),
            doc.page_content,
        )
        if fallback_key in seen_fallback_keys:
            continue

        if chunk_id:
            seen_chunk_ids.add(chunk_id)
        seen_fallback_keys.add(fallback_key)
        deduped.append((doc, score))

    return deduped


def merge_adjacent_scored_documents(
    items: list[tuple[LCDocument, float]],
    *,
    max_merged_length: int = 1200,
) -> list[tuple[LCDocument, float]]:
    if not items:
        return []

    sorted_items = sorted(
        items,
        key=lambda item: (
            str(item[0].metadata.get("document_id") or ""),
            int(item[0].metadata.get("chunk_index") or 0),
        ),
    )

    merged: list[tuple[LCDocument, float]] = []

    for doc, score in sorted_items:
        if not merged:
            merged.append((deepcopy(doc), score))
            continue

        last_doc, last_score = merged[-1]
        same_document = last_doc.metadata.get("document_id") == doc.metadata.get("document_id")
        last_index = last_doc.metadata.get("chunk_index")
        current_index = doc.metadata.get("chunk_index")
        consecutive = (
            isinstance(last_index, int)
            and isinstance(current_index, int)
            and current_index == last_index + 1
        )
        merged_length = len(last_doc.page_content) + len(doc.page_content)

        if same_document and consecutive and merged_length <= max_merged_length:
            last_doc.page_content = f"{last_doc.page_content}\n{doc.page_content}"
            last_doc.metadata["chunk_index"] = current_index
            if doc.metadata.get("page_no") is not None:
                last_doc.metadata["page_no"] = doc.metadata.get("page_no")
            merged[-1] = (last_doc, min(last_score, score))
        else:
            merged.append((deepcopy(doc), score))

    return merged


def trim_scored_documents_by_budget(
    items: list[tuple[LCDocument, float]],
    *,
    max_chars: int,
) -> list[tuple[LCDocument, float]]:
    kept: list[tuple[LCDocument, float]] = []
    total_chars = 0

    for doc, score in items:
        current_length = len(doc.page_content)
        if kept and total_chars + current_length > max_chars:
            break
        if not kept and current_length > max_chars:
            kept.append((doc, score))
            break

        kept.append((doc, score))
        total_chars += current_length

    return kept


def format_context_docs(docs: list[LCDocument]) -> str:
    sections: list[str] = []
    for index, doc in enumerate(docs, start=1):
        sections.append(
            "\n".join(
                [
                    f"[片段 {index}]",
                    f"knowledge_base_id={doc.metadata.get('knowledge_base_id')}",
                    f"document_id={doc.metadata.get('document_id')}",
                    f"chunk_id={doc.metadata.get('chunk_id')}",
                    f"page_no={doc.metadata.get('page_no')}",
                    f"text={doc.page_content}",
                ]
            )
        )
    return "\n\n".join(sections)


async def build_query_context(
    query: str,
    *,
    top_k: int = 4,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
    context_budget: int = 4000,
) -> dict:
    raw_items = await retrieve_documents_with_scores(
        query=query,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )

    deduped_items = deduplicate_retrieved_documents(raw_items)
    merged_items = merge_adjacent_scored_documents(deduped_items)
    final_items = trim_scored_documents_by_budget(
        merged_items,
        max_chars=context_budget,
    )

    final_docs = [doc for doc, _ in final_items]

    return {
        "context_text": format_context_docs(final_docs),
        "sources": [build_source_item(doc) for doc in final_docs],
        "raw_count": len(raw_items),
        "dedup_count": len(deduped_items),
        "merged_count": len(merged_items),
        "final_count": len(final_items),
    }
```

### 这里有 4 个特别容易忽略的点

#### 点 1：Day 9 第一版就该用 with scores

因为后面你要做：

- 排序
- 裁剪
- 评估

这时候保留 score 视角更稳。

#### 点 2：第一版去重一定先做确定性规则

不要一上来做复杂语义去重。  
先把：

- `chunk_id`
- `document_id + page_no + text`

这种确定性去重做稳。

#### 点 3：第一版 budget 可以先用字符数近似

Day 9 的重点不是 tokenizer 工程化。  
而是让“最终输入有预算”这件事先成立。

#### 点 4：context service 应该返回结构化 packet

不要只返回字符串。  
保留：

- `context_text`
- `sources`
- 过程统计

后面做观测时会轻松很多。

---

## 15:00 - 15:40：让 `query_service` 只消费治理后的 context

### 这一段属于增量修改

这里不需要重写整条问答链。  
只需要把：

```text
retrieve_documents(...)
-> format_docs(...)
```

改成：

```text
build_query_context(...)
-> 直接拿 context_text
```

### `services/query_service.py` 练手骨架版

```python
async def generate_rag_answer(
    question: str,
    *,
    knowledge_base_id: str,
    user_id: int | None = None,
    top_k: int = 4,
) -> dict:
    # 你要做的事：
    # 1. 调 build_query_context(...)
    # 2. 没有 sources 时直接返回兜底答案
    # 3. 用 context_text 进 prompt
    # 4. 返回 answer + sources
    raise NotImplementedError("先自己实现 Day 9 版 generate_rag_answer")
```

### `services/query_service.py` 参考答案

```python
from langchain_core.output_parsers import StrOutputParser

from clients.llm_client import get_llm
from services.context_service import build_query_context
from utils.prompt_builder import get_rag_prompt


async def generate_rag_answer(
    question: str,
    *,
    knowledge_base_id: str,
    user_id: int | None = None,
    top_k: int = 4,
) -> dict:
    context_packet = await build_query_context(
        query=question,
        top_k=top_k,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not context_packet["sources"]:
        return {
            "answer": "我无法从已检索内容中找到相关答案。请先确认文档已经完成索引。",
            "sources": [],
        }

    prompt = get_rag_prompt()
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    answer = await chain.ainvoke(
        {
            "context": context_packet["context_text"],
            "question": question,
        }
    )

    return {
        "answer": answer,
        "sources": context_packet["sources"],
    }
```

### 这里为什么要让 `query_service` 变薄

因为后面你再加：

- rerank
- 压缩
- 评估
- 观测

时，最理想的状态是：

> 继续只改 `context_service`，不要重新拆问答主流程。

---

## 15:40 - 16:10：哪些地方今天先不写代码，只说清楚

### `schemas/chat.py` 今天先不急着改

当前返回结构还是：

- `answer`
- `sources`

这对 Day 9 第一版完全够用。

### 为什么今天不急着把 meta 暴露到 API

因为 Day 9 当前最重要的是：

- 先让内部治理链成立

至于：

- `raw_count`
- `dedup_count`
- `merged_count`
- `final_count`

这些先保留在内部 packet 里就够了。  
后面要不要暴露给 API，再单独决定。

### prompt 模板今天也先不重写

Day 9 先不碰：

- system prompt 内容
- 多轮会话 prompt 设计

因为今天真正的问题不在 prompt，  
而在输入上下文还太脏。

---

## 16:10 - 17:00：写一个最小验收脚本

### 这一段建议写代码

因为 Day 9 最需要的不是“代码看起来对”，  
而是你能看到：

- 原始召回多少条
- 去重后多少条
- 合并后多少条
- 最终保留多少条

### `scripts/debug_day9.py` 练手骨架版

```python
import asyncio


async def main():
    # 你要做的事：
    # 1. 调 build_query_context(...)
    # 2. 打印 raw_count / dedup_count / merged_count / final_count
    # 3. 打印最终 sources
    raise NotImplementedError("先自己实现 debug_day9")


if __name__ == "__main__":
    asyncio.run(main())
```

### `scripts/debug_day9.py` 参考答案

```python
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.context_service import build_query_context


async def main():
    packet = await build_query_context(
        query="请总结这个知识库里关于 FastAPI 后端经验的内容",
        top_k=6,
        user_id=1,
        knowledge_base_id="kb_demo_001",
        context_budget=3000,
    )

    print(f"raw_count={packet['raw_count']}")
    print(f"dedup_count={packet['dedup_count']}")
    print(f"merged_count={packet['merged_count']}")
    print(f"final_count={packet['final_count']}")
    print("=" * 60)
    print(packet["context_text"])
    print("=" * 60)
    for item in packet["sources"]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())
```

### 为什么 Day 9 值得写这个脚本

因为如果没有这类最小验收脚本，  
你很难确认：

- 去重到底有没有发生
- 合并到底有没有起效
- budget 到底有没有真正限制住最终输入

---

## 17:00 - 18:00：整理 Day 9 之后的边界认知

### 到 Day 9 为止，问答链路应该开始变成这样

```text
router
-> query_service
-> context_service
   -> retrieve
   -> deduplicate
   -> merge
   -> trim
   -> build context_text
-> llm
```

### 这意味着什么

这意味着：

- 检索和 context packing 已经分层
- query service 不再直接管理原始 docs
- 后面做限流、熔断、重试、观测时位置会更清楚

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. 为什么 `top_k` 不等于最终 context 大小？
2. 为什么 Day 9 需要 `context_service` 统一承接治理逻辑？
3. 去重第一版为什么先按确定性规则做？
4. 为什么当前 metadata 已经足够支持第一版相邻 chunk 合并？
5. 为什么 budget 第一版可以先用字符数近似？
6. 为什么 `query_service` 应该只消费治理后的 context packet？
7. 哪些地方今天必须给代码壳子和答案？
8. 哪些地方今天只需要说清楚为什么先不改？

---

## 今日验收标准

- 已明确 Day 9 里哪些地方必须写代码
- 已给出 `context_service.py` 的治理入口壳子和参考答案
- 已给出去重、相邻合并、budget 裁剪的第一版实现
- 已给出 `query_service.py` 的增量改法和参考答案
- 已说明 `schemas/chat.py` 今天为什么可以先不改
- 已给出 `debug_day9.py` 的最小验收脚本壳子和参考答案

---

## 今天最容易踩的坑

### 坑 1：把 Day 9 理解成调 prompt

问题：

- prompt 可能更复杂了
- 但输入上下文还是脏的

规避建议：

- 先治 context，再谈 prompt

### 坑 2：把 `top_k` 当成最终预算

问题：

- 检索数量和最终输入长度不是一回事

规避建议：

- 单独建立 `context_budget` 概念

### 坑 3：一上来就做复杂 rerank

问题：

- 范围会立刻膨胀
- Day 9 第一版难以收敛

规避建议：

- 先做确定性去重和相邻合并

### 坑 4：只返回 `context_text`，不保留治理统计

问题：

- 后面很难评估和观测

规避建议：

- 第一版就保留 `raw_count / dedup_count / merged_count / final_count`

### 坑 5：把治理逻辑又塞回 `query_service`

问题：

- 问答服务会重新变厚
- 后面扩展更难

规避建议：

- 让 `query_service` 只消费 context packet

---

## 给明天的交接提示

明天会进入 Day 10：`限流、熔断与退避重试`。

Day 10 的前提不是“外部依赖已经很多”这么简单，  
而是：

> 当 retrieval 和 context packing 已经有了清晰边界后，  
> 你才能更准确地判断哪一层在慢、哪一层该限流、哪一层失败后适合重试。

所以 Day 9 最关键的交接只有一句话：

```text
上下文不再是原始召回结果的直接拼接物，context_service 已经开始承接检索后的治理逻辑，接下来做运行时治理时，边界会更清楚，定位也会更准。
```
