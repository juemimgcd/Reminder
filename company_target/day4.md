# Day 4：回答证据化 + 返回结构收口

## 今天的总目标

- 把 `Mneme` 的问答结果从“有 sources 附带返回”升级成“答案本身必须绑定证据”的结构化输出。
- 基于当前真实代码，把问答主链重新讲顺：`query -> context -> evidence answer -> citations / confidence / uncertainty -> API result`。
- 在不打断现有 companion 链路的前提下，给 `chat` 返回结构增量补上 `citations / confidence / uncertainty`。
- 产出 Day 5 可以直接接住的输入：稳定 source id、证据化回答结构、后续 Hybrid Search 可继续消费的上下文契约。

## 今天结束前，你必须拿到什么

- 一份你自己能讲顺的“为什么长期记忆系统不能只返回 answer 文本”的解释。
- 一版明确的 `ChatQueryData` 目标结构，而不是只停留在 `answer + sources`。
- 一条清楚的 Day 4 主链：谁负责检索上下文，谁负责结构化回答，谁负责最终 citations 绑定。
- 一份明确写清楚“当前代码已经有什么、还缺什么”的问答链路落点说明。
- 一份 Day 5 可继续使用的交接结论：后续 Hybrid Search 应该围绕什么返回契约扩展。

---

## Day 4 一图总览

```mermaid
flowchart LR
    A[Day 3 的 MemoryEntry 资产] --> B[检索上下文]
    B --> C[给每条来源分配稳定 source_id]
    C --> D[Evidence Prompt 生成结构化回答]
    D --> E[绑定 citations / confidence / uncertainty]
    E --> F[Day 5 继续扩成 Hybrid Search]
```

---

## 为什么这一天重要

Day 3 解决的是：

> 记忆对象有没有正式进入主链。

Day 4 要解决的是：

> 主链最终吐出的回答，能不能被解释、被追溯、被质疑、被继续优化。

当前仓库里的问答链已经存在：

- `routers/chat.py`
- `services/query_service.py`
- `services/context_service.py`
- `schemas/chat.py`
- `utils/prompt_builder.py`

而且它已经能做到这些事情：

- 接收问题
- 做向量检索
- 组装上下文
- 调 LLM 生成答案
- 返回 `answer + sources`

但它还没有真正进入“证据化回答”阶段，原因至少有 4 个：

- 当前 `answer` 只是自由文本，不要求每个核心结论绑定证据。
- 当前 `sources` 更像“召回片段列表”，而不是“答案真正引用了哪些来源”。
- 当前 prompt 只要求“优先依据 context 回答”，没有要求输出结构化 citation。
- 当前返回结构没有 `confidence / uncertainty`，无法表达“有证据但仍不完全确定”的状态。

所以 Day 4 的意义不是“把 sources 再包装一下”，  
而是正式把下面这句话写进系统：

> 一个长期记忆后端不能只给结论，它必须说明结论依赖了哪些证据、证据强度如何、哪里还不确定。

---

## Day 4 整体架构

今天你要同时看清楚两条链。

第一条链是当前真实仓库已经在跑的问答链：

```text
routers/chat.py
  -> services/query_service.generate_rag_answer(...)
  -> services/context_service.build_query_context(...)
  -> utils/prompt_builder.get_rag_prompt()
  -> LLM
  -> answer + sources
```

第二条链是 Day 4 结束后你应该统一理解的证据链：

```text
Question
  -> Retrieved Sources
  -> Stable Source IDs
  -> Evidence Answer Prompt
  -> Structured Answer Draft
  -> Resolved Citations
  -> confidence / uncertainty
  -> API result
```

这里最关键的一点是：

> Day 4 不是把“召回到哪些片段”原样扔给前端，  
> 而是让系统明确说出“这次回答真正引用了哪几条来源，以及为什么引用它们”。

---

## 今天的边界要讲透

### 今天之后，各层职责应该怎么理解

从 Day 4 开始，和证据化回答最相关的职责边界建议固定成下面这样：

```text
routers/chat.py
  负责接收入参、调用 service、返回结构化响应

services/context_service.py
  负责检索、去重、合并、裁剪，并产出带稳定 source_id 的 sources

utils/prompt_builder.py
  负责定义 Evidence Answer 的提示词契约

services/query_service.py
  负责调用 prompt + parser，生成结构化 answer draft，并绑定 citations

schemas/chat.py
  负责定义最终 API 返回的最小证据化结构

services/companion_service.py
  继续消费 rag_result，但不要求 Day 4 立刻重写 companion 输出
```

### 对当前仓库的处理原则

今天不要把 Day 4 理解成“重做整个问答系统”，  
而要把它理解成“在当前问答链之上，补上证据约束层”。

当前这些事实你要明确看到：

| 真实文件 | 今天该怎么理解 |
|---|---|
| `routers/chat.py` | 当前知识库问答入口 |
| `services/query_service.py` | 当前回答编排主入口 |
| `services/context_service.py` | 当前召回后的治理层 |
| `schemas/chat.py` | 当前问答响应结构过于轻 |
| `utils/prompt_builder.py` | 当前 prompt 还没有证据化输出约束 |
| `services/companion_service.py` | 说明 rag_result 已被其他链路复用，Day 4 要增量兼容 |
| `schemas/companion.py` | 已有 `citations` 风格结构，可借鉴但不要直接硬套 |

### 先不要急着做这些

今天先不要急着做：

- 完整 Hybrid Search。
- 完整 memory 检索召回。
- GraphRAG 引用链。
- Cross-encoder rerank。
- 评测指标体系。
- 前端引用高亮全套交互。

原因很简单：

> 如果 Day 4 连“回答如何绑定来源”都没做对，  
> 后面的检索扩展只会让系统召回更多内容，但不会让回答更可信。

---

## 第 1 层：Day 4 的本质是什么

Day 4 的本质不是“给返回 JSON 多加几个字段”，而是：

```text
把问答结果
从自由文本
升级成可追溯回答
```

你今天必须能讲顺这句话：

> `Mneme` 当前已经能召回上下文，也已经能返回 sources。  
> 但如果 answer 本身不说明“用了哪些来源、为什么这些来源足够、哪里仍不确定”，那它仍然只是一个带附件的普通 RAG 返回。  
> Day 4 要做的，是把 evidence、confidence、uncertainty 正式写进回答协议。

如果这句话你讲不顺，说明 Day 4 还没做完。

---

## 第 2 层：Day 4 的主链一定要从“当前真实问答代码”出发

今天不要从未来的 GraphRAG 或 Eval 出发，  
一定要从当前真实问答链路出发。

建议你重点顺这条线去看：

```text
routers/chat.py
  -> services/query_service.generate_rag_answer(...)
  -> services/context_service.build_query_context(...)
  -> utils/prompt_builder.get_rag_prompt()
  -> schemas/chat.ChatQueryData
```

你今天要回答 4 个问题：

1. 当前 `sources` 和真正的 `citations` 差别是什么？
2. 当前 prompt 为什么还不足以支撑“证据化回答”？
3. 为什么 Day 4 应该增量保留 `sources`，而不是直接砍掉？
4. 当前 companion 链路为什么决定了 Day 4 必须走兼容式改造？

---

## 第 3 层：Day 4 必须先把“最小证据化回答对象”讲清楚

今天先不要把回答协议设计得太大，  
而是从当前 `schemas/chat.py` 出发，给它补一层最小可用结构。

当前 `schemas/chat.py` 里已有：

```text
ChatQueryRequest
ChatSourceItem
ChatQueryData
```

但当前 `ChatQueryData` 还只接近：

```text
answer
sources
```

Day 4 建议先稳定成下面这种心智：

```text
ChatQueryData
  answer
  sources
  citations
  confidence
  uncertainty
```

其中最小 `citation` 建议长成：

```text
ChatCitationItem
  source_id
  document_id
  chunk_id
  page_no
  quote
  reason
```

你今天一定要明确下面这些字段为什么重要：

| 字段 | 今天为什么必须理解 |
|---|---|
| `source_id` | 给 prompt 和 parser 一个稳定引用键，避免直接依赖自然语言描述 |
| `quote` | 让前端或调用方看见“具体引用了哪段证据” |
| `reason` | 解释“为什么这条来源支撑当前结论” |
| `confidence` | 明确回答不是只有“对/错”，还存在强弱判断 |
| `uncertainty` | 允许系统诚实地表达证据不足或结论边界 |
| `sources` | 继续保留原始召回来源，方便兼容 companion 和后续调试 |

---

## 第 4 层：Day 4 必须先把“当前不足”讲清楚

今天你要敢于明确指出，当前问答链虽然已经能返回 sources，  
但还至少有 5 个不足：

### 不足 1：当前返回的是“召回列表”，不是“引用结果”

现在 `services/context_service.py` 返回的 `sources` 代表：

```text
模型看过了哪些片段
```

但还不代表：

```text
答案最终真正引用了哪些片段
```

### 不足 2：当前 prompt 没有要求结构化 citation

当前 `utils/prompt_builder.py` 的 `get_rag_prompt()` 只要求：

- 优先依据 context 回答
- context 不足时不要编造

但还没有要求：

- 输出 citation 列表
- 给出 confidence
- 说明 uncertainty

### 不足 3：当前上下文没有稳定 source id

`services/context_service.py` 虽然会把上下文格式化成 `[片段 1]` 这种形态，  
但 API 返回的 `sources` 里没有一个明确稳定的 `source_id` 字段。

这会导致：

- prompt 引用和 API 返回难以稳定对齐
- merged chunk 的真实引用关系不够清晰
- Day 4 很难做 deterministic citation binding

### 不足 4：当前回答生成仍然是纯字符串输出

当前 `services/query_service.py` 用的是：

```text
prompt -> llm -> StrOutputParser()
```

这意味着：

- 返回格式无法被 schema 强约束
- `citation / confidence / uncertainty` 只能靠自然语言猜
- 下游没法稳定消费

### 不足 5：当前 companion 链路决定 Day 4 不能粗暴替换结构

`services/companion_service.py` 会直接把 `rag_result` 打包进输入，  
这意味着 Day 4 应该：

- 保留 `answer`
- 保留 `sources`
- 增量新增 `citations / confidence / uncertainty`

而不是直接把旧结构砍掉重来。

---

## 第 5 层：Day 4 的最小证据链应该长什么样

今天建议你把 Day 4 的最小证据链固定成下面这条：

```text
Question
  -> build_query_context(...)
  -> sources with source_id
  -> get_evidence_rag_prompt(...)
  -> EvidenceAnswerDraft
  -> resolve_citations(...)
  -> ChatQueryData
```

这条链一定要表达两个原则：

### 原则 1：引用必须绑定到稳定 source_id

今天不要让模型随口说“根据上面第二段内容”。  
要让它明确引用：

```text
S1
S2
S3
```

然后由服务层把这些 `source_id` 解析回真实 `document_id / chunk_id / page_no`。

### 原则 2：最终返回必须区分“召回源”和“真正引用”

今天不要把 `sources` 和 `citations` 混成一个概念。

```text
sources
  = 召回后进入上下文的候选来源

citations
  = 最终回答真正使用到的证据来源
```

只有这样，Day 5 以后做 Hybrid Search 才不会把“召回质量”和“回答证据质量”混在一起。

---

## 第 6 层：结合当前仓库，Day 4 最小落点应该放在哪

今天最值得反复看的真实文件是这些：

| 文件 | 今天为什么要看 |
|---|---|
| `schemas/chat.py` | 定义 Day 4 最小证据化响应结构 |
| `services/context_service.py` | 给 sources 分配稳定 `source_id`，并格式化 Evidence 上下文 |
| `utils/prompt_builder.py` | 明确 Evidence Answer 的 prompt 契约 |
| `services/query_service.py` | 从纯文本回答升级到结构化回答 |
| `routers/chat.py` | 保持入口简单，只接结构化结果 |
| `routers/companion.py` | 确认 Day 4 的结果结构仍能被 companion 链路消费 |
| `services/companion_service.py` | 验证 rag_result 走兼容式扩展不会出问题 |
| `schemas/companion.py` | 借鉴 `citations` 的产品化表达方式 |

今天不需要扫全仓，  
只要围绕这几处把“证据化回答”讲清楚就够了。

---

## 第 7 层：Day 4 最小接口建议长什么样

今天你不一定要一次定完所有最终接口，  
但建议先把 Day 4 的最小结构化结果统一成下面这种心智：

```text
ChatQueryData
  answer
  sources
  citations
  confidence
  uncertainty
```

以及：

```text
EvidenceAnswerDraft
  answer
  citations[source_id, quote, reason]
  confidence
  uncertainty
```

这里推荐一个最小 API 形态：

```text
ChatQueryData
  answer: str
  sources: list[ChatSourceItem]
  citations: list[ChatCitationItem]
  confidence: str
  uncertainty: str | None
```

其中 `confidence` 今天先建议收口成：

```text
high
medium
low
```

这样做的意义是：

- 让 Day 4 的回答能被前端或调用方稳定消费
- 让 Day 5 以后检索质量提升可以直接反映到 confidence
- 让 Day 15 以后调试和 Eval 可以直接观察 citation 质量

---

## 第 8 层：Day 4 不建议做什么

今天不建议做：

- 直接把 `sources` 整个替换掉。
- 直接在 Day 4 引入 memory 检索。
- 直接做复杂多跳引用图。
- 直接做前端高亮联动。
- 直接把 query_service 拆成很多新模块。
- 直接把 companion 结果也全部改成新协议。

今天真正要避免的坑只有一句话：

> 用“把所有问答能力一次性重做”的冲动，替代“先把回答证据化协议立住”的工作。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 3 的 memory 资产翻译成 Day 4 的证据语言

今天第一段不要急着改代码，  
先把 Day 3 的结论翻译成一句话：

> 既然 `MemoryEntry` 和 chunk 都已经是系统资产，那么 Day 4 的回答就必须诚实说明：它到底用了哪些资产作为证据。

### 你至少要能回答这两个问题

1. 为什么“有 sources”还不等于“回答可追溯”？
2. 为什么 Day 4 不应该直接跳去做 Hybrid Search？

---

## 09:50 - 10:40：沿真实问答链路看当前 answer 是怎么出来的

建议你顺着这条链去读：

```text
routers/chat.py
-> services/query_service.py
-> services/context_service.py
-> utils/prompt_builder.py
-> schemas/chat.py
```

### 今天你要特别记住 4 个事实

- 当前 answer 是字符串，不是结构化对象。
- 当前 sources 是召回结果，不是 citation 结果。
- 当前 prompt 没有要求引用和置信度。
- 当前 companion 已经复用 rag_result，所以 Day 4 必须兼容旧字段。

---

## 10:40 - 11:30：把 Day 4 的最小协议和非目标钉死

### 今天必须明确要做

- 给每条 source 增加稳定 `source_id`。
- 给问答返回结构补上 `citations / confidence / uncertainty`。
- 把问答 prompt 从自由文本约束成结构化 evidence answer。
- 保留 `sources`，避免打断 companion 链路。

### 今天明确不做

- 不做 Hybrid Search。
- 不做 memory recall。
- 不做 graph citations。
- 不做完整前端展示方案。

### 这一段最重要的结论

你要得到一句稳定的话：

> Day 4 先解决“回答如何绑定证据”，不是先解决“所有召回源如何变得最强”。

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 4 最直接的验收方式

- 你能自己画出 `question -> sources -> citations -> answer` 链路。
- 你能指出当前 `sources` 和 `citations` 的职责差别。
- 你能说出当前 prompt 为什么必须升级成结构化输出。
- 你能说出 Day 5 为什么要继续围绕这份回答协议扩检索。

如果你说不清楚，说明今天还没完成。

---

## 下午编码：14:00 - 18:00

## 14:00 - 15:00：先把 `schemas/chat.py` 和 `services/context_service.py` 变成 Evidence-ready

这一段的目标不是直接调 LLM 生成结构化答案，  
而是先让上下文和返回结构具备“能被证据化”的条件。

### 文件 1：`schemas/chat.py`

这个文件今天只解决一件事：

> 把问答返回结构从 `answer + sources` 扩成 Evidence-ready 的 schema。

#### `schemas/chat.py` 练手骨架版

```python
from pydantic import BaseModel, Field


class ChatCitationItem(BaseModel):
    source_id: str = Field(..., description="稳定来源 ID，例如 S1")
    document_id: str = Field(..., description="来源文档 ID")
    chunk_id: str = Field(..., description="来源片段 ID")
    page_no: int | None = Field(default=None, description="来源页码")
    quote: str = Field(..., description="本次回答实际引用的证据片段")
    reason: str = Field(..., description="为什么它支撑当前回答")


class EvidenceCitationDraft(BaseModel):
    source_id: str = Field(..., description="模型引用的来源 ID")
    quote: str = Field(..., description="模型提取的证据片段")
    reason: str = Field(..., description="引用理由")


class EvidenceAnswerDraft(BaseModel):
    answer: str = Field(..., description="基于证据的最终回答")
    citations: list[EvidenceCitationDraft] = Field(default_factory=list)
    confidence: str = Field(..., description="high / medium / low")
    uncertainty: str | None = Field(default=None, description="仍不确定的部分")
```

#### `schemas/chat.py` 参考答案

```python
from pydantic import BaseModel, Field


class ChatCitationItem(BaseModel):
    source_id: str = Field(..., description="稳定来源 ID，例如 S1")
    document_id: str = Field(..., description="来源文档 ID")
    chunk_id: str = Field(..., description="来源片段 ID")
    page_no: int | None = Field(default=None, description="来源页码")
    quote: str = Field(..., description="本次回答实际引用的证据片段")
    reason: str = Field(..., description="为什么它支撑当前回答")


class EvidenceCitationDraft(BaseModel):
    source_id: str = Field(..., description="模型引用的来源 ID")
    quote: str = Field(..., description="模型提取的证据片段")
    reason: str = Field(..., description="引用理由")


class EvidenceAnswerDraft(BaseModel):
    answer: str = Field(..., description="基于证据的最终回答")
    citations: list[EvidenceCitationDraft] = Field(default_factory=list)
    confidence: str = Field(..., description="high / medium / low")
    uncertainty: str | None = Field(default=None, description="仍不确定的部分")
```

#### `schemas/chat.py` 按原文件具体怎么改

文件位置：

- `schemas/chat.py`

你当前文件里已经有：

```python
class ChatSourceItem(BaseModel):
    knowledge_base_id: str | None = None
    document_id: str
    chunk_id: str
    page_no: int | None = None
    text: str


class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
```

这里建议改成增量兼容的结构：

```python
class ChatSourceItem(BaseModel):
    source_id: str
    knowledge_base_id: str | None = None
    document_id: str
    chunk_id: str
    page_no: int | None = None
    text: str


class ChatCitationItem(BaseModel):
    source_id: str
    document_id: str
    chunk_id: str
    page_no: int | None = None
    quote: str
    reason: str


class EvidenceCitationDraft(BaseModel):
    source_id: str
    quote: str
    reason: str


class EvidenceAnswerDraft(BaseModel):
    answer: str
    citations: list[EvidenceCitationDraft]
    confidence: str
    uncertainty: str | None = None


class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
    citations: list[ChatCitationItem]
    confidence: str
    uncertainty: str | None = None
```

也就是说：

- 在 `ChatSourceItem` 里新增 `source_id`
- 在 `ChatQueryData` 里新增 `citations / confidence / uncertainty`
- 额外补两个 parser 专用 schema：`EvidenceCitationDraft`、`EvidenceAnswerDraft`

### 文件 2：`services/context_service.py`

这个文件今天只解决一件事：

> 给每条召回 source 分配稳定 `source_id`，并让 prompt 上下文与 API sources 共用同一套编号。

#### `services/context_service.py` 练手骨架版

```python
from langchain_core.documents import Document as LCDocument


def build_source_item(doc: LCDocument, *, source_id: str) -> dict:
    # 你要做的事情：
    # 1. 继续复用当前 metadata 清洗逻辑
    # 2. 给每条 source 增加稳定 source_id
    # 3. 保留 document_id / chunk_id / page_no / text 等字段
    # 4. 不要在这里写 LLM 逻辑
    raise NotImplementedError


def format_context_docs(docs: list[LCDocument]) -> str:
    # 你要做的事情：
    # 1. 用和 sources 相同的顺序枚举片段
    # 2. 给每段上下文显式写出 source_id
    # 3. 让后续 prompt 可以稳定引用 source_id
    # 4. 不要在这里裁剪业务字段
    raise NotImplementedError
```

#### `services/context_service.py` 参考答案

```python
from langchain_core.documents import Document as LCDocument


def build_source_item(doc: LCDocument, *, source_id: str) -> dict:
    ensure_source_metadata(doc)
    source_chunk_ids = doc.metadata["source_chunk_ids"]
    source_page_nos = doc.metadata["source_page_nos"]
    if len(source_chunk_ids) <= 1:
        chunk_ref = source_chunk_ids[0] if source_chunk_ids else doc.metadata.get("chunk_id")
    else:
        chunk_ref = f"{source_chunk_ids[0]}..{source_chunk_ids[-1]}"

    return {
        "source_id": source_id,
        "knowledge_base_id": doc.metadata.get("knowledge_base_id"),
        "document_id": doc.metadata.get("document_id"),
        "chunk_id": chunk_ref,
        "page_no": source_page_nos[0] if len(source_page_nos) == 1 else None,
        "text": doc.page_content,
        "source_chunk_ids": source_chunk_ids,
        "source_page_nos": source_page_nos,
        "merged_chunk_count": doc.metadata.get("merged_chunk_count", 1),
    }


def format_context_docs(docs: list[LCDocument]) -> str:
    sections: list[str] = []
    for index, doc in enumerate(docs, start=1):
        source_id = f"S{index}"
        ensure_source_metadata(doc)
        sections.append(
            "\n".join(
                [
                    f"[来源 {source_id}]",
                    f"source_id={source_id}",
                    f"knowledge_base_id={doc.metadata.get('knowledge_base_id')}",
                    f"document_id={doc.metadata.get('document_id')}",
                    f"chunk_id={doc.metadata.get('chunk_id')}",
                    f"source_chunk_ids={doc.metadata.get('source_chunk_ids')}",
                    f"page_no={doc.metadata.get('page_no')}",
                    f"text={doc.page_content}",
                ]
            )
        )
    return "\n\n".join(sections)
```

#### `services/context_service.py` 按原文件具体怎么改

文件位置：

- `services/context_service.py`

#### 1. 改 `build_source_item(...)` 的函数签名和返回值

你当前大致是：

```python
def build_source_item(doc: LCDocument) -> dict:
    ...
    return {
        "knowledge_base_id": ...,
        "document_id": ...,
        "chunk_id": ...,
        "page_no": ...,
        "text": doc.page_content,
    }
```

这里建议改成：

```python
def build_source_item(doc: LCDocument, *, source_id: str) -> dict:
    ...
    return {
        "source_id": source_id,
        "knowledge_base_id": ...,
        "document_id": ...,
        "chunk_id": ...,
        "page_no": ...,
        "text": doc.page_content,
        "source_chunk_ids": ...,
        "source_page_nos": ...,
        "merged_chunk_count": ...,
    }
```

#### 2. 改 `build_query_context(...)` 里 sources 的构造方式

你当前文件末尾大致是：

```python
    return {
        "context_text": format_context_docs(final_docs),
        "sources": [build_source_item(doc) for doc in final_docs],
        "raw_count": len(raw_items),
        ...
    }
```

这里建议改成：

```python
    source_items = [
        build_source_item(doc, source_id=f"S{index}")
        for index, doc in enumerate(final_docs, start=1)
    ]

    return {
        "context_text": format_context_docs(final_docs),
        "sources": source_items,
        "raw_count": len(raw_items),
        ...
    }
```

#### 3. 改 `format_context_docs(...)`，让 prompt 里的上下文和 sources 共用同一套 source id

你当前大致是：

```python
for index, doc in enumerate(docs, start=1):
    sections.append(
        "\n".join(
            [
                f"[片段 {index}]",
                f"knowledge_base_id=...",
                f"document_id=...",
                f"chunk_id=...",
                f"text=...",
            ]
        )
    )
```

这里建议改成：

```python
for index, doc in enumerate(docs, start=1):
    source_id = f"S{index}"
    sections.append(
        "\n".join(
            [
                f"[来源 {source_id}]",
                f"source_id={source_id}",
                f"knowledge_base_id=...",
                f"document_id=...",
                f"chunk_id=...",
                f"source_chunk_ids=...",
                f"page_no=...",
                f"text=...",
            ]
        )
    )
```

这样后面 query service 就能稳定让模型输出：

```text
S1
S3
```

然后再映射回真实 source item。

### 这一步真正要得到什么

不是今天就把 answer 生成重写完，  
而是让 Day 4 的上下文输入和返回结构，先具备“可证据化”的前提。

---

## 15:00 - 16:20：让 `utils/prompt_builder.py` 和 `services/query_service.py` 正式承认 Evidence Answer

这一段的目标是让问答生成从“纯文本回答”升级成“结构化证据回答”。

### 文件 3：`utils/prompt_builder.py`

这个文件今天只解决一件事：

> 把 prompt 从“尽量依据 context 回答”升级成“必须按 source_id 输出结构化证据答案”。

#### `utils/prompt_builder.py` 练手骨架版

```python
from langchain_core.prompts import ChatPromptTemplate


def get_evidence_rag_prompt(format_instructions: str):
    # 你要做的事情：
    # 1. 明确告诉模型必须依据 context 回答
    # 2. 明确告诉模型 citations 只能引用 source_id
    # 3. 要求输出 answer / citations / confidence / uncertainty
    # 4. 不要让模型输出自然语言解释包装层
    raise NotImplementedError
```

#### `utils/prompt_builder.py` 参考答案

```python
from langchain_core.prompts import ChatPromptTemplate


def get_evidence_rag_prompt(format_instructions: str):
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个基于知识库证据回答问题的助手。"
                "你必须只依据给定 context 回答。"
                "每条 citation 只能引用 context 中提供的 source_id。"
                "如果证据不足，请在 uncertainty 中明确说明。"
                f"请严格按下面格式输出：\n{format_instructions}",
            ),
            (
                "human",
                "已检索内容如下：\n{context}\n\n用户问题：\n{question}",
            ),
        ]
    )
```

#### `utils/prompt_builder.py` 按原文件具体怎么改

文件位置：

- `utils/prompt_builder.py`

你当前已经有：

```python
def get_rag_prompt() -> ChatPromptTemplate:
    ...
```

Day 4 最简单的增量做法不是直接删掉它，  
而是新增一个专用函数：

```python
def get_evidence_rag_prompt(format_instructions: str) -> ChatPromptTemplate:
    ...
```

也就是说：

- 保留 `get_rag_prompt()`，避免旧逻辑和其他分支立即失效
- 新增 `get_evidence_rag_prompt(...)`
- 在 system prompt 里明确：
  - 只能依据 context 回答
  - citation 只能引用 `source_id`
  - 要输出 `answer / citations / confidence / uncertainty`

### 文件 4：`services/query_service.py`

这个文件今天只解决一件事：

> 把当前 `StrOutputParser()` 的纯文本回答链，升级成 parser 约束下的结构化 Evidence Answer。

#### `services/query_service.py` 练手骨架版

```python
from langchain_core.output_parsers import PydanticOutputParser

from clients.llm_client import get_llm
from schemas.chat import EvidenceAnswerDraft, EvidenceCitationDraft
from utils.prompt_builder import get_evidence_rag_prompt


def resolve_citations(
    citation_drafts: list[EvidenceCitationDraft],
    sources: list[dict],
) -> list[dict]:
    # 你要做的事情：
    # 1. 先按 source_id 建 lookup
    # 2. 只保留能在 sources 中找到的 citation
    # 3. 组装最终 ChatCitationItem 需要的字段
    # 4. 不要在这里生成 answer 文本
    raise NotImplementedError


async def invoke_evidence_answer(
    *,
    question: str,
    context_text: str,
    sources: list[dict],
    knowledge_base_id: str | None = None,
    user_id: int | None = None,
) -> dict:
    # 你要做的事情：
    # 1. 用 Pydantic parser 约束输出结构
    # 2. 调 evidence prompt 拿到 EvidenceAnswerDraft
    # 3. 把 draft citations 解析成最终 citations
    # 4. 返回 answer / citations / confidence / uncertainty
    raise NotImplementedError
```

#### `services/query_service.py` 参考答案

```python
from langchain_core.output_parsers import PydanticOutputParser

from clients.llm_client import get_llm
from schemas.chat import EvidenceAnswerDraft, EvidenceCitationDraft
from utils.prompt_builder import get_evidence_rag_prompt


def resolve_citations(
    citation_drafts: list[EvidenceCitationDraft],
    sources: list[dict],
) -> list[dict]:
    source_lookup = {
        item["source_id"]: item
        for item in sources
        if item.get("source_id")
    }
    citations: list[dict] = []
    for item in citation_drafts:
        source = source_lookup.get(item.source_id)
        if not source:
            continue
        citations.append(
            {
                "source_id": item.source_id,
                "document_id": source["document_id"],
                "chunk_id": source["chunk_id"],
                "page_no": source.get("page_no"),
                "quote": item.quote,
                "reason": item.reason,
            }
        )
    return citations


async def invoke_evidence_answer(
    *,
    question: str,
    context_text: str,
    sources: list[dict],
    knowledge_base_id: str | None = None,
    user_id: int | None = None,
) -> dict:
    parser = PydanticOutputParser(pydantic_object=EvidenceAnswerDraft)
    prompt = get_evidence_rag_prompt(parser.get_format_instructions())
    llm = get_llm()
    chain = prompt | llm | parser
    result = await chain.ainvoke(
        {
            "context": context_text,
            "question": question,
        }
    )
    citations = resolve_citations(result.citations, sources)
    return {
        "answer": result.answer,
        "citations": citations,
        "confidence": result.confidence,
        "uncertainty": result.uncertainty,
    }
```

#### `services/query_service.py` 按原文件具体怎么改

文件位置：

- `services/query_service.py`

#### 1. 在 import 区补 parser 和新 schema

你当前已有：

```python
from langchain_core.output_parsers import StrOutputParser
```

这里建议改成：

```python
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
```

并补上：

```python
from clients.llm_client import get_llm
from schemas.chat import EvidenceAnswerDraft, EvidenceCitationDraft
from utils.prompt_builder import get_evidence_rag_prompt, get_general_chat_prompt, get_rag_prompt
```

如果你后面确定 `get_rag_prompt()` 不再使用，  
可以再做第二步清理；  
但 Day 4 计划里先按增量兼容写最稳。

这里几个 import 分别是：

- `PydanticOutputParser`：来自 `langchain_core.output_parsers`
- `get_llm`：来自 `clients.llm_client`
- `EvidenceAnswerDraft`、`EvidenceCitationDraft`：来自 `schemas.chat`
- `get_evidence_rag_prompt`：来自 `utils.prompt_builder`

#### 2. 在 `invoke_llm_answer(...)` 旁边新增 `resolve_citations(...)` 和 `invoke_evidence_answer(...)`

你当前文件里已经有：

```python
async def invoke_llm_answer(... ) -> str:
    ...
```

建议就在这个函数后面插入：

```python
def resolve_citations(
    citation_drafts: list[EvidenceCitationDraft],
    sources: list[dict],
) -> list[dict]:
    ...


async def invoke_evidence_answer(
    *,
    question: str,
    context_text: str,
    sources: list[dict],
    knowledge_base_id: str | None = None,
    user_id: int | None = None,
) -> dict:
    ...
```

这样文件结构最自然：

```text
general llm invoke
-> evidence parser helpers
-> generate_rag_answer
```

#### 3. 改 `generate_rag_answer(...)` 的三个返回分支

你当前大致有 3 个分支：

- general chat bypass
- empty sources
- normal rag answer

当前 general chat bypass 返回大致是：

```python
        return {
            "answer": answer,
            "sources": [],
        }
```

这里 Day 4 建议改成：

```python
        return {
            "answer": answer,
            "sources": [],
            "citations": [],
            "confidence": "low",
            "uncertainty": "这是通用回答，未绑定知识库证据。",
        }
```

当前 empty sources 分支大致是：

```python
        return {
            "answer": "我无法从已检索内容中找到相关答案。请先确认文档已经完成索引。",
            "sources": [],
        }
```

这里 Day 4 建议改成：

```python
        return {
            "answer": "我无法从已检索内容中找到相关答案。请先确认文档已经完成索引。",
            "sources": [],
            "citations": [],
            "confidence": "low",
            "uncertainty": "当前没有可用证据来源。",
        }
```

当前正常分支大致是：

```python
    answer = await invoke_llm_answer(
        prompt=get_rag_prompt(),
        question=question,
        context_text=context_packet["context_text"],
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
    )

    return {
        "answer": answer,
        "sources": context_packet["sources"],
    }
```

这里建议改成：

```python
    evidence_result = await invoke_evidence_answer(
        question=question,
        context_text=context_packet["context_text"],
        sources=context_packet["sources"],
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
    )

    return {
        "answer": evidence_result["answer"],
        "sources": context_packet["sources"],
        "citations": evidence_result["citations"],
        "confidence": evidence_result["confidence"],
        "uncertainty": evidence_result["uncertainty"],
    }
```

也就是说：

- `sources` 继续保留
- `citations / confidence / uncertainty` 新增
- 结构化证据答案只进入 normal rag path，不影响 general prompt 逻辑

### 这一步真正要得到什么

不是让模型“看起来更会解释”，  
而是让回答协议第一次正式变成可结构化验证的对象。

---

## 16:20 - 17:10：把 `routers/chat.py` 和兼容性收口讲清楚

这一段的目标不是再造一层 router 逻辑，  
而是确保 Day 4 的结构升级不会打断现有使用方。

### 文件 5：`routers/chat.py`

这个文件今天只解决一件事：

> 保持入口简单，只接住 Day 4 升级后的结构化结果，并把日志补完整。

#### `routers/chat.py` 练手骨架版

```python
async def query_chat(payload, current_user, db):
    # 你要做的事情：
    # 1. 保持现有鉴权和限流逻辑不变
    # 2. 调用升级后的 generate_rag_answer(...)
    # 3. 记录 citation_count / confidence
    # 4. 返回新的 ChatQueryData
    raise NotImplementedError
```

#### `routers/chat.py` 参考答案

```python
async def query_chat(payload, current_user, db):
    result = await generate_rag_answer(
        question=payload.question,
        knowledge_base_id=payload.knowledge_base_id,
        user_id=current_user.id,
        top_k=payload.top_k,
    )
    app_logger.bind(module="chat_router").info(
        f"chat query success user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"source_count={len(result['sources'])} citation_count={len(result['citations'])} "
        f"confidence={result['confidence']}"
    )
    data = ChatQueryData(**result)
    return success_response(data=data)
```

#### `routers/chat.py` 按原文件具体怎么改

文件位置：

- `routers/chat.py`

当前主逻辑本身不用重写，  
只建议补成功日志。

你当前大致是：

```python
    app_logger.bind(module="chat_router").info(
        f"chat query success user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"source_count={len(result['sources'])}"
    )
```

建议改成：

```python
    app_logger.bind(module="chat_router").info(
        f"chat query success user_id={current_user.id} knowledge_base_id={payload.knowledge_base_id} "
        f"source_count={len(result['sources'])} citation_count={len(result['citations'])} "
        f"confidence={result['confidence']}"
    )
```

其他逻辑：

- 鉴权不改
- 限流不改
- `generate_rag_answer(...)` 的调用方式不改
- `ChatQueryData(**result)` 继续保留

### 兼容性确认：`routers/companion.py` / `services/companion_service.py`

你当前 `services/companion_service.py` 只是把 `rag_result` 打包成 JSON 继续喂给 prompt。  
这意味着：

- Day 4 新增字段不会破坏它
- 反而会让 companion 以后更容易消费 citation / confidence

所以今天的原则是：

```text
先兼容
先增量
先让主问答协议立住
```

而不是：

```text
今天把所有依赖 rag_result 的链路一起重写
```

---

## 17:10 - 18:00：给 Day 5 留一份最小交付说明

今天结束前，建议你至少整理出下面这张交付链：

```text
稳定 source_id
-> sources / citations 职责分离
-> answer / confidence / uncertainty 协议
-> companion 兼容式扩展
-> Day 5 可继续扩检索质量
```

Day 5 最需要接住的一句话是：

> 现在回答协议已经能表达“引用了什么、为什么引用、哪里不确定”，所以下一步要优化的就不再是“返回结构”，而是“召回质量本身”。

---

## 晚上复盘：20:00 - 21:00

今晚不要泛泛复述今天做了什么，  
而要回答下面这些问题：

1. 当前 `sources` 和 `citations` 到底差在哪？
2. 为什么 Day 4 必须先给 source 分配稳定 `source_id`？
3. 为什么 `StrOutputParser()` 不足以支撑 Evidence Answer？
4. 为什么 Day 4 应该保留 `sources` 而不是直接替换？
5. Day 5 为什么应该去优化检索，而不是继续堆回答字段？

如果其中有两题答不顺，说明今天还没真正收口。

---

## 今日验收标准

- 你能清楚讲出 Day 4 的核心不是“返回更多字段”，而是“让回答可追溯”。
- 你能指出 `schemas/chat.py`、`services/context_service.py`、`utils/prompt_builder.py`、`services/query_service.py` 之间的关系。
- 你能说出当前为什么需要 `source_id`，而不是只靠 chunk_id 或片段序号口头描述。
- 你能给出一版最小响应结构，让问答正式包含 `citations / confidence / uncertainty`。
- 你能给 Day 5 留下一份清楚的检索质量交接输入。

---

## 今天最容易踩的坑

### 坑 1：把 Day 4 理解成“已有 sources，所以天然已经证据化”

问题：

看到接口已经返回 `sources`，  
就误以为回答已经可以追溯。

规避建议：

区分清楚：

```text
sources = 检索候选
citations = 回答真正引用
```

### 坑 2：今天就急着做 Hybrid Search

问题：

一看到回答质量问题，就想立刻引入 keyword / memory / graph recall。

规避建议：

先把回答协议立住。  
没有稳定 citation 协议，后面多路召回只会让分析更乱。

### 坑 3：让模型直接输出 chunk_id，结果和最终 source 对不上

问题：

merged chunk、相邻片段合并、range chunk id 都会让直接引用原始 chunk_id 变得不稳定。

规避建议：

先在 context 和 API 里统一出 `source_id`，  
再让模型只引用 `source_id`。

### 坑 4：Day 4 直接砍掉 `sources`

问题：

因为想突出 citations，就把 `sources` 删掉。

规避建议：

今天先保留：

- `sources` 供兼容和调试
- `citations` 供最终回答引用

### 坑 5：今天把 companion 也一起大改

问题：

看到 companion 已经复用 rag_result，就想趁机全部升级。

规避建议：

Day 4 先让主问答协议稳定，  
companion 只做兼容确认，不做大面积改造。

---

## 给明天的交接提示

Day 5 要接住的不是“继续讨论回答协议”，  
而是基于 Day 4 已经稳定下来的证据化返回，开始优化检索质量本身。

明天开始之前，你应该已经具备这 5 份输入：

```text
带 source_id 的 sources
-> 最小 citations 结构
-> confidence / uncertainty 协议
-> 兼容 companion 的 rag_result 结构
-> 可继续扩召回的上下文契约
```

到了 Day 5，就不要再反复讨论“回答要不要带证据”，  
而是直接进入：

```text
Question
-> Vector Recall
-> Keyword Recall
-> Memory Recall
-> Candidate Merge
-> Evidence Answer
```

这就是 Day 4 最终要交给 Day 5 的东西。
