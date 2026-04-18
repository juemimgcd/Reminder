# Day 8：utils 轻量拆分

## 今天的总目标

- 把 `utils/` 里残留的业务动作继续迁到 `services/`
- 把多步骤组合逻辑从 router 收进 `pipelines/`
- 把依赖 LangChain 的文件加载和切分能力收进 `clients/`
- 让 router 不再直接拼 analysis / advice / companion 这类长链路
- 让 Day 9 的 context 治理有稳定落点，而不是继续散在多个模块里

## 今天结束前，你必须拿到什么

- 一张清晰的 Day 8 迁移表
- 一份“哪些地方需要写代码，哪些地方只做边界说明”的判断
- `clients/document_loader_client.py` 和 `clients/text_splitter_client.py` 的落地方案
- `pipelines/analysis_pipeline.py` / `pipelines/advice_pipeline.py` / `pipelines/companion_pipeline.py` 的第一版设计
- 一份你自己能讲清楚的“Day 8 为什么不是纯搬文件”的认知

---

## 今天开始，Day 8 不是“目录整理”，而是“职责归位”

Day 7 之后，你已经开始有这些边界：

- `clients/embedding_client.py`
- `clients/vector_store_client.py`
- `clients/llm_client.py`
- `infra/object_cache.py`
- `services/document_service.py`
- `services/query_service.py`
- `services/context_service.py`
- `pipelines/document_index_pipeline.py`

这意味着系统已经不再是一个纯 `utils` 大仓库。  
Day 8 的任务不是“看起来更整齐”，  
而是继续把剩余职责归位。

### 为什么 Day 8 不是纯搬文件

如果你只是把：

- `utils/advice_builder.py`

挪成：

- `services/advice_service.py`

但下面这些没变：

- router 还是直接拼整条链路
- 多步骤组合还是散在接口里
- import 方向还是到处绕老路径

那 Day 8 实际上没有完成。

所以 Day 8 真正要做的是：

```text
旧 utils 业务函数
-> service 业务动作
-> pipeline 组合流程
-> router 只做入口和参数校验
```

---

## 第 1 层：今天哪些地方需要写代码，哪些地方不需要

这是 Day 8 最重要的判断。

### 需要写代码的地方

这些地方不是“解释一下就行”，  
而是应该实际给壳子和参考答案：

- `clients/document_loader_client.py`
- `clients/text_splitter_client.py`
- `pipelines/analysis_pipeline.py`
- `pipelines/advice_pipeline.py`
- `pipelines/companion_pipeline.py`
- 对应 router 的调用链改法

原因很直接：

- 这些地方会新增文件
- 会改变依赖方向
- 会改变调用链

### 不需要大写代码，只需要说清楚边界的地方

这些地方今天不应该展开成大改造：

- `utils/prompt_builder.py`
- `utils/profile_prompt.py`
- `utils/growth_prompt.py`
- `utils/advice_prompt.py`
- `utils/companion_prompt.py`
- `utils/entry_prompt.py`

原因：

- 它们仍然属于 prompt 模板层
- Day 8 的重点不是 prompt 重构
- 今天先处理“谁来执行动作”和“谁来组合流程”

### 今天的原则

```text
涉及调用链变化
-> 给代码壳子和答案

只涉及边界认知
-> 说清楚为什么今天先不改
```

---

## 第 2 层：Day 8 的真实迁移表

结合当前项目，Day 8 最实用的迁移表应该是：

| 当前文件 | 当前问题 | Day 8 目标位置 |
|---|---|---|
| `utils/file_loader.py` | 外部依赖能力混在 utils | `clients/document_loader_client.py` |
| `utils/text_splitter.py` | 外部依赖能力混在 utils | `clients/text_splitter_client.py` |
| `utils/memory_organizer.py` | 业务动作混在 utils | `services/memory_service.py` |
| `utils/profile_builder.py` | 业务动作混在 utils | `services/profile_service.py` |
| `utils/growth_analyzer.py` | 业务动作混在 utils | `services/growth_service.py` |
| `utils/advice_builder.py` | 业务动作混在 utils | `services/advice_service.py` |
| `utils/companion_builder.py` | 业务动作混在 utils | `services/companion_service.py` |
| router 里的组合逻辑 | 多步骤链路散在接口层 | `pipelines/*.py` |

### 这张表真正要表达什么

不是“文件去哪儿”。  
而是：

- 依赖访问放进 `clients`
- 单动作业务放进 `services`
- 多步骤编排放进 `pipelines`

这才是 Day 8 的核心。

---

## 第 3 层：今天要改哪些文件

Day 8 主要围绕这些文件展开：

- `clients/document_loader_client.py`
- `clients/text_splitter_client.py`
- `services/memory_service.py`
- `services/profile_service.py`
- `services/growth_service.py`
- `services/advice_service.py`
- `services/companion_service.py`
- `pipelines/analysis_pipeline.py`
- `pipelines/advice_pipeline.py`
- `pipelines/companion_pipeline.py`
- `routers/analysis.py`
- `routers/advice.py`
- `routers/companion.py`
- `routers/profile.py`
- `routers/memory.py`

### 每个位置今天负责什么

| 文件 | 今天负责什么 |
|---|---|
| `clients/document_loader_client.py` | 文件加载能力归位 |
| `clients/text_splitter_client.py` | 文本切分能力归位 |
| `services/*_service.py` | 单动作业务承接 |
| `pipelines/*.py` | 多步骤业务编排 |
| `routers/*.py` | 清理旧拼装逻辑，只保留入口职责 |

---

## 第 4 层：今天不要做什么

Day 8 不建议做：

- 不做 prompt 目录全面重构
- 不做 `services` class 化大改造
- 不做 memory pipeline 全落地
- 不做 Day 9 的 context packing 提前实现
- 不做 Day 10 的限流、熔断、重试

今天只做：

> 把“谁负责动作，谁负责流程，谁负责依赖访问”这三件事放回正确位置。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 8 的主问题讲顺

### 今天你要能顺着说出来

```text
Day 2 先定义 services / pipelines / clients / infra 的目标层次
-> Day 7 开始把运行时边界做稳
-> Day 8 继续把旧 utils 里的职责按真实边界迁出去
```

### 你必须能回答这两个问题

1. 为什么 Day 8 不是纯搬文件？
2. 为什么 analysis / advice / companion 这类链路更像 pipeline，而不是继续塞在 router？

---

## 09:50 - 10:40：先把 router 应该怎么变讲清楚

### Day 8 之后最理想的依赖方向

```text
router -> pipeline / service
pipeline -> service / client
service -> client / prompt / schema
client -> 第三方依赖
infra -> 运行时底座
utils -> 通用支持
```

### 为什么 router 不应该继续拼业务

因为现在这些链路都已经明显超过“入口层”范围：

- analysis
- advice
- companion

它们都不是“一次 service 调用”。  
它们是：

- 先读 memory entries
- 再组织 memory library
- 再做 profile
- 再做 growth report
- 最后可能再做 advice 或 companion response

这就是 pipeline。

---

## 10:40 - 11:30：先决定今天哪些文件真的需要新建

Day 8 最值得新建的文件是：

- `clients/document_loader_client.py`
- `clients/text_splitter_client.py`
- `pipelines/analysis_pipeline.py`
- `pipelines/advice_pipeline.py`
- `pipelines/companion_pipeline.py`

### 为什么这几个最值得新建

因为：

- 它们是新边界的明确落点
- 一旦这些文件存在，router 就有地方把逻辑交出去
- 后面 Day 9 的 context 治理也更容易接进 `services/context_service.py`

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 8 最直接的验收方式

今天最少要能回答：

1. 哪些迁移是纯位置迁移？
2. 哪些迁移一定会带来调用链变化？
3. 哪些地方今天必须写代码？
4. 哪些地方今天只要先讲清楚为什么不改？
5. Day 8 做完以后，Day 9 的 context 治理应该落在哪？

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:40：把文件加载能力迁进 `clients/document_loader_client.py`

### 这一段属于新增能力

因为它不是普通 import 替换，  
而是明确把“文件加载”从 `utils` 迁进 `clients`。

### `clients/document_loader_client.py` 练手骨架版

```python
from langchain_core.documents import Document as LCDocument


async def load_langchain_documents(
    *,
    file_path: str,
    file_type: str,
    user_id: int,
    knowledge_base_id: str,
    knowledge_base_pk: int,
    document_id: str,
    document_pk: int,
    file_name: str,
) -> list[LCDocument]:
    # 你要做的事：
    # 1. 校验文件是否存在
    # 2. 根据 file_type 选择 loader
    # 3. 把 loader.load() 放到线程执行
    # 4. 给每个 doc 补齐 metadata
    raise NotImplementedError("先自己实现 document_loader_client")
```

### `clients/document_loader_client.py` 参考答案

```python
import asyncio
from pathlib import Path

from langchain_core.documents import Document as LCDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from utils.exceptions import BusinessException


async def load_langchain_documents(
    *,
    file_path: str,
    file_type: str,
    user_id: int,
    knowledge_base_id: str,
    knowledge_base_pk: int,
    document_id: str,
    document_pk: int,
    file_name: str,
) -> list[LCDocument]:
    path = Path(file_path)
    if not path.exists():
        raise BusinessException(message="file not found", status_code=404)

    if file_type == "pdf":
        loader = PyPDFLoader(str(file_path))
    elif file_type in ["txt", "md"]:
        loader = TextLoader(file_path, autodetect_encoding=True)
    else:
        raise BusinessException(message="Incorrect file type")

    docs = await asyncio.to_thread(loader.load)

    for doc in docs:
        doc.metadata["user_id"] = user_id
        doc.metadata["knowledge_base_id"] = knowledge_base_id
        doc.metadata["knowledge_base_pk"] = knowledge_base_pk
        doc.metadata["document_id"] = document_id
        doc.metadata["document_pk"] = document_pk
        doc.metadata["file_name"] = file_name
        doc.metadata["file_type"] = file_type
        doc.metadata["source"] = str(file_path)

    return docs
```

### 这里要特别注意

Day 8 这里不是“发明新逻辑”，  
而是把 Day 7 已经做过的阻塞迁移能力放到更合理的位置。

---

## 14:40 - 15:10：把切分能力迁进 `clients/text_splitter_client.py`

### 这一段也属于新增能力

因为它会改变 `document_index_pipeline` 的依赖方向。

### `clients/text_splitter_client.py` 练手骨架版

```python
from langchain_core.documents import Document as LCDocument


async def build_text_splitter():
    # 你要做的事：
    # 1. 返回 RecursiveCharacterTextSplitter
    # 2. 保持现有 chunk_size / chunk_overlap / separators
    raise NotImplementedError("先自己实现 build_text_splitter")


async def split_documents(
    *,
    document_id: str,
    documents: list[LCDocument],
) -> list[LCDocument]:
    # 你要做的事：
    # 1. 调 build_text_splitter()
    # 2. split_documents(...)
    # 3. 给每个 chunk 补 chunk_id / chunk_index / page_no / start_offset
    raise NotImplementedError("先自己实现 split_documents")
```

### `clients/text_splitter_client.py` 参考答案

```python
import uuid

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


async def build_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        add_start_index=True,
    )


async def split_documents(
    *,
    document_id: str,
    documents: list[LCDocument],
) -> list[LCDocument]:
    splitter = await build_text_splitter()
    chunks = splitter.split_documents(documents=documents)

    for index, chunk in enumerate(chunks):
        raw_page = chunk.metadata.get("page")
        page_no = raw_page + 1 if isinstance(raw_page, int) else None
        start_offset = chunk.metadata.get("start_index")

        chunk.metadata["chunk_id"] = f"{document_id}_chunk_{index}_{uuid.uuid4().hex[:6]}"
        chunk.metadata["chunk_index"] = index
        chunk.metadata["page_no"] = page_no
        chunk.metadata["start_offset"] = start_offset

    return chunks
```

### 为什么 Day 8 这里值得写代码

因为 Day 9 的相邻 chunk 合并要依赖：

- `chunk_index`
- `page_no`
- `start_offset`

如果 Day 8 不把这层边界收稳，  
Day 9 会很难做。

---

## 15:10 - 15:50：把 analysis 组合逻辑收进 `pipelines/analysis_pipeline.py`

### 这一段属于新增能力

analysis 不是一个单动作。  
它天然是：

```text
memory entries
-> memory library
-> profile
-> growth report
```

### `pipelines/analysis_pipeline.py` 练手骨架版

```python
from sqlalchemy.ext.asyncio import AsyncSession


async def run_analysis_pipeline(
    db: AsyncSession,
    *,
    user_id: int,
    knowledge_base_id: str,
    recent_days: int = 30,
) -> dict:
    # 你要做的事：
    # 1. 读取 memory entries
    # 2. 组织 memory_library
    # 3. 生成 profile
    # 4. 生成 growth_report
    # 5. 返回最终 report
    raise NotImplementedError("先自己实现 run_analysis_pipeline")
```

### `pipelines/analysis_pipeline.py` 参考答案

```python
from crud.memory_entry import list_memory_entries_by_user_id
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile


async def run_analysis_pipeline(
    db,
    *,
    user_id: int,
    knowledge_base_id: str,
    recent_days: int = 30,
) -> dict:
    entries = await list_memory_entries_by_user_id(db, user_id=user_id)
    entry_dicts = [item.__dict__ for item in entries]

    memory_library = build_memory_library(entry_dicts)

    profile = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
    )

    report = await build_growth_report(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
        profile=profile,
        recent_days=recent_days,
    )

    return report
```

### 这里的重点

Day 8 的 pipeline 第一版不用复杂。  
它最重要的价值是：

- 收组合流程
- 让 router 变薄

---

## 15:50 - 16:30：把 advice 链路收进 `pipelines/advice_pipeline.py`

### 这一段属于新增能力

因为 advice 不是单步 LLM 调用，  
它是在 analysis 结果上再走一步：

```text
memory library
-> profile
-> growth report
-> growth advice
```

### `pipelines/advice_pipeline.py` 练手骨架版

```python
from sqlalchemy.ext.asyncio import AsyncSession


async def run_advice_pipeline(
    db: AsyncSession,
    *,
    user_id: int,
    knowledge_base_id: str,
    focus_goal: str | None = None,
) -> dict:
    # 你要做的事：
    # 1. 读 memory entries
    # 2. 组 memory_library
    # 3. 产出 profile
    # 4. 产出 growth_report
    # 5. 产出 growth_advice
    raise NotImplementedError("先自己实现 run_advice_pipeline")
```

### `pipelines/advice_pipeline.py` 参考答案

```python
from crud.memory_entry import list_memory_entries_by_user_id
from services.advice_service import build_growth_advice
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile


async def run_advice_pipeline(
    db,
    *,
    user_id: int,
    knowledge_base_id: str,
    focus_goal: str | None = None,
) -> dict:
    entries = await list_memory_entries_by_user_id(db, user_id=user_id)
    entry_dicts = [item.__dict__ for item in entries]

    memory_library = build_memory_library(entry_dicts)

    profile = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
    )

    growth_report = await build_growth_report(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
        profile=profile,
    )

    advice = await build_growth_advice(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        profile=profile,
        growth_report=growth_report,
        focus_goal=focus_goal,
    )

    return advice
```

### 这里为什么要把 `advice_service` 单独拆出来

因为：

- `growth_service` 更偏“分析输出”
- `advice_service` 更偏“建议生成”

把这两者强行塞一个文件，  
后面只会越来越长。

---

## 16:30 - 17:00：把 companion 链路收进 `pipelines/companion_pipeline.py`

### 这一段属于新增能力

因为 companion 已经明显不是一个简单的：

```text
question -> llm
```

它更像：

```text
question
-> RAG answer
-> memory library
-> profile
-> growth report
-> companion response
```

### `pipelines/companion_pipeline.py` 练手骨架版

```python
from sqlalchemy.ext.asyncio import AsyncSession


async def run_companion_pipeline(
    db: AsyncSession,
    *,
    user_id: int,
    knowledge_base_id: str,
    question: str,
    top_k: int = 4,
) -> dict:
    # 你要做的事：
    # 1. 调 generate_rag_answer(...)
    # 2. 读 memory entries
    # 3. 组 memory_library
    # 4. 产出 profile 和 growth_report
    # 5. 调 build_companion_response(...)
    raise NotImplementedError("先自己实现 run_companion_pipeline")
```

### `pipelines/companion_pipeline.py` 参考答案

```python
from crud.memory_entry import list_memory_entries_by_user_id
from services.companion_service import build_companion_response
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile
from services.query_service import generate_rag_answer


async def run_companion_pipeline(
    db,
    *,
    user_id: int,
    knowledge_base_id: str,
    question: str,
    top_k: int = 4,
) -> dict:
    rag_result = await generate_rag_answer(
        question=question,
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        top_k=top_k,
    )

    entries = await list_memory_entries_by_user_id(db, user_id=user_id)
    entry_dicts = [item.__dict__ for item in entries]
    memory_library = build_memory_library(entry_dicts)

    profile = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
    )

    growth_report = await build_growth_report(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
        profile=profile,
    )

    return await build_companion_response(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        question=question,
        rag_result=rag_result,
        profile=profile,
        growth_report=growth_report,
    )
```

### 这里的意义

Day 8 不是要把 companion 变得更复杂，  
而是把复杂性从 router 里拿出来。

---

## 17:00 - 17:30：把 router 改成只调 pipeline 或 service

### 这一段需要改代码，但不需要重写整文件

你今天真正要做的是：

- 改 import
- 改调用目标
- 保留参数校验和权限校验

### 典型迁移改法

把 router 里原来这种：

```python
entries = await list_memory_entries_by_user_id(...)
memory_library = build_memory_library(...)
profile = await build_personal_profile(...)
report = await build_growth_report(...)
advice = await build_growth_advice(...)
```

改成：

```python
advice = await run_advice_pipeline(
    db,
    user_id=current_user.id,
    knowledge_base_id=knowledge_base_id,
    focus_goal=payload.focus_goal,
)
```

### 为什么这里不给整文件答案

因为 router 里的权限校验、参数来源和 response schema 细节不完全一样。  
Day 8 这里更重要的是理解：

> router 要交出组合权，只保留入口职责。

---

## 17:30 - 18:00：哪些地方今天先不写代码，只要说清楚

### prompt 文件今天先不动

今天先不新增：

- `prompts/` 目录
- `builders/` 目录
- 更复杂的 prompt 分层

原因：

- 今天的收益不在这里
- 现在最大问题是执行职责没完全归位
- prompt 重构放到后面做更稳

### memory pipeline 今天也先不完整落地

虽然 `memory_service.py` 已经在形成，  
但 Day 8 先不要把它扩成完整 `memory_extract_pipeline`。

那是 Day 12 的重点。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. Day 8 为什么不是纯文件迁移？
2. 为什么 `document_loader` 和 `text_splitter` 更适合放进 `clients/`？
3. 为什么 `analysis`、`advice`、`companion` 更像 pipeline？
4. 为什么 `advice_service` 应该和 `growth_service` 分开？
5. 为什么 router 不应该继续拼多步骤业务？
6. 哪些地方今天必须给代码壳子和答案？
7. 哪些地方今天只需要说清楚为什么先不改？
8. Day 8 做完以后，Day 9 的 context 治理为什么会更容易落地？

---

## 今日验收标准

- 已明确 Day 8 里哪些地方必须写代码
- 已给出 `document_loader_client.py` 的壳子和参考答案
- 已给出 `text_splitter_client.py` 的壳子和参考答案
- 已给出 `analysis / advice / companion` 三条 pipeline 的壳子和参考答案
- 已说明 router 应该怎么迁移，而不是继续拼业务
- 已说明 prompt 层今天为什么先不展开重构

---

## 今天最容易踩的坑

### 坑 1：只搬文件，不改调用链

问题：

- 看起来已经分层
- 实际逻辑还是老结构

规避建议：

- 迁完以后一定改 router 的调用方向

### 坑 2：把所有业务动作都塞进一个 service

问题：

- 单文件会越来越长
- 语义边界会越来越模糊

规避建议：

- analysis / growth / advice / companion 分开承接

### 坑 3：今天顺手重构 prompt 体系

问题：

- 范围会迅速失控
- Day 8 的主目标会跑偏

规避建议：

- 先把执行职责归位
- prompt 后面再治理

### 坑 4：pipeline 写成“超级 service”

问题：

- pipeline 里把所有细节都揉成一团

规避建议：

- pipeline 只做流程组合
- 单动作继续留在 service

### 坑 5：以为 Day 8 不需要写代码

问题：

- 会把 Day 8 误解成“目录整理日”

规避建议：

- 记住 Day 8 的关键成果是依赖方向变化，不只是文件位置变化

---

## 给明天的交接提示

明天会进入 Day 9：`Context 组装治理`。

Day 9 的前提不是“已有 query 接口”这么简单，  
而是：

> 当 router、pipeline、service、client 的边界开始清楚后，  
> context 去重、相邻 chunk 合并、budget 裁剪这些能力才知道应该放在哪一层。

所以 Day 8 最关键的交接只有一句话：

```text
旧 utils 的职责已经开始按 service / pipeline / client 重新落位，接下来做 context 治理时，不需要再一边查逻辑一边猜模块边界。
```
