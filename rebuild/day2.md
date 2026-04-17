# Day 2：目标架构分层

## 今天的总目标

- 把 `utils/` 里已经承担业务职责的模块按层迁出去
- 明确哪些文件可以基本原样迁移，哪些文件需要小改，哪些文件暂时不动
- 先完成“职责落位”，不要把 Day 2 做成“全部重写日”
- 为 Day 3 的索引接口任务化准备稳定目录和调用边界

## 今天结束前，你必须拿到什么

- 一张清晰的迁移映射表
- 一份按优先级排序的迁移顺序
- 一份 import 改造清单
- 一份“原样迁 / 小改迁 / 暂不迁”的判断标准
- 一套 Day 3 可以直接接着改的目录结构

---

## 今天开始，Day 2 的核心就是 utils 拆分

你这个判断是对的。

对 Mneme 当前仓库来说，Day 2 的本质不是：

- 重新设计一套抽象理论
- 先建很多空目录
- 把已经能跑的逻辑重写一遍

Day 2 真正该做的是：

> 把 `utils/` 里已经长成“业务服务 / 流程编排 / 外部依赖访问 / 运行时能力”的模块，迁移到更合理的位置。

也就是说，Day 2 更像：

```text
职责拆分日
```

而不是：

```text
功能重写日
```

这点要先定死。

---

## 第 1 层：今天先用 3 种迁移类型分类

Day 2 最实用的做法不是上来就搬文件，  
而是先给每个 `utils` 模块分类型。

### 类型 1：原样迁移

适用条件：

- 文件职责已经比较清楚
- 逻辑本身没问题
- 只是目录放错了

这种文件不要重写。  
直接迁移，最多改 import。

### 类型 2：小改迁移

适用条件：

- 主体逻辑可以保留
- 但函数名、依赖路径、返回结构需要顺一下
- 或者需要把少量 HTTP 语义剥离掉

这种文件也不要推倒重写。  
只做最小改造。

### 类型 3：暂不迁移

适用条件：

- 现在还不影响 Day 3 主线
- 当前职责虽然不完美，但短期不构成阻塞
- 后面更适合和其他模块一起收敛

这类文件 Day 2 先别动。

---

## 第 2 层：当前仓库里哪些文件属于 Day 2 主战场

当前 `utils/` 里，最值得优先拆分的是这些：

- `utils/index_service.py`
- `utils/rag_service.py`
- `utils/embeddings.py`
- `utils/vector_store.py`
- `utils/llm.py`

其次是这些：

- `utils/retriever.py`
- `utils/file_loader.py`
- `utils/text_splitter.py`

暂时可以不急着动的是这些：

- `utils/exceptions.py`
- `utils/response.py`
- `utils/security.py`
- 各类 `*_prompt.py`
- 各类 `*_builder.py`

原因很简单：

- Day 3 主线是“索引接口任务化”
- 所以 Day 2 只需要先把和索引 / 检索主链路直接相关的模块拆顺

---

## 第 3 层：今天的迁移总原则

今天最重要的原则只有 4 条。

### 原则 1：先迁位置，再少量改名

不要先重写，再迁移。  
先把模块放到对的位置，再看需不需要微调。

### 原则 2：能原样保留逻辑，就不要重新实现

比如一个文件本来就在做：

- 初始化 embedding
- 初始化 Milvus
- 初始化 LLM

那它本质上就是 client。  
直接迁过去即可。

### 原则 3：只在职责变化时改代码

例如：

- 从 router 里剥离业务判断到 service
- 从 `utils/index_service.py` 改成 pipeline 入口

这种情况下才需要小改。

### 原则 4：Day 2 不追求“一次性彻底干净”

只要 Day 3 能沿着新边界继续写，  
Day 2 就算成功。

---

## 第 4 层：最重要的迁移映射表

这张表就是 Day 2 的核心。

| 当前文件 | 迁移目标 | 迁移类型 | 说明 |
|---|---|---|---|
| `utils/index_service.py` | `pipelines/document_index_pipeline.py` | 小改迁移 | 主体索引逻辑保留，但名字和调用位置要改 |
| `utils/rag_service.py` | `services/query_service.py` | 小改迁移 | 主体问答逻辑保留，但定位改成业务入口 |
| `utils/embeddings.py` | `clients/embedding_client.py` | 原样迁移 | 几乎就是 client，不用重写 |
| `utils/vector_store.py` | `clients/vector_store_client.py` | 原样迁移 | 主要是外部依赖封装，不用重写 |
| `utils/llm.py` | `clients/llm_client.py` | 原样迁移 | 只要不是混了业务规则，就直接迁 |
| `utils/retriever.py` | `services/context_service.py` | 小改迁移 | 你已经确定放到 context_service，那就和 context 入口一起收敛 |
| `utils/file_loader.py` | 先留原处，后续作为 pipeline 下游能力 | 暂不迁移 | Day 2 不阻塞主线 |
| `utils/text_splitter.py` | 先留原处，后续作为 pipeline 下游能力 | 暂不迁移 | Day 2 不阻塞主线 |
| `utils/response.py` | 保留 `utils/response.py` | 不迁移 | 通用响应包装，位置合理 |
| `utils/exceptions.py` | 保留 `utils/exceptions.py` | 不迁移 | 通用异常，位置合理 |
| `utils/security.py` | 保留 `utils/security.py` | 不迁移 | 当前可接受 |

如果只看 Day 2 主线，  
你只需要真正处理前 6 个文件，就已经够用了。

---

## 第 5 层：今天到底怎么迁，不要重写

下面直接说迁法，不再讲“先写骨架再写参考答案”。

### 1. `utils/embeddings.py` -> `clients/embedding_client.py`

这个文件本质上已经是 client。

当前逻辑：

- 读取配置
- 创建 `HuggingFaceEmbeddings`

这类逻辑不需要重写。  
直接迁移即可。

迁移方式：

1. 新建 `clients/`
2. 把文件内容直接复制到 `clients/embedding_client.py`
3. 把原调用点从：

```python
from utils.embeddings import get_embeddings
```

改成：

```python
from clients.embedding_client import get_embeddings
```

如果你想顺手改函数名，也只做很小调整，比如改成：

- `get_embedding_client`

但这个改名不是 Day 2 必须项。

### 2. `utils/vector_store.py` -> `clients/vector_store_client.py`

这个文件也基本是外部依赖封装。

里面做的主要是：

- Milvus 连接参数组装
- vector store 初始化
- add/delete/drop

这类代码 Day 2 不需要重写。  
直接迁移。

迁移方式：

1. 复制到 `clients/vector_store_client.py`
2. 把内部 import：

```python
from utils.embeddings import get_embeddings
```

改成：

```python
from clients.embedding_client import get_embeddings
```

3. 把业务层调用点改到新路径

### 3. `utils/llm.py` -> `clients/llm_client.py`

如果这个文件主要在做：

- 创建模型对象
- 读取配置
- 封装 LLM SDK

那它也不需要重写。

直接迁过去，然后把引用它的地方改 import 即可。

### 4. `utils/index_service.py` -> `pipelines/document_index_pipeline.py`

这个文件和前 3 个不一样。  
它不是纯 client，它已经在编排完整索引链路。

所以这里不是“原样改个路径就完了”，  
但也不是“全部重写”。

更合理的做法是：

1. 把文件复制到 `pipelines/document_index_pipeline.py`
2. 把函数名从：

```python
index_document
```

改成更明确的：

```python
run_document_index_pipeline
```

3. 把内部 import 改到新路径，比如：

- `utils.vector_store` -> `clients.vector_store_client`

4. 暂时保留函数主体逻辑

也就是说：

> 这是“改名 + 改 import + 改归属”，不是重写索引链路。

### 5. `utils/rag_service.py` -> `services/query_service.py`

这个文件更像业务入口层。

它现在做的事情通常是：

- 接收 question
- 调 retriever
- 组织 context
- 调 llm
- 返回 answer + sources

所以它更接近 service。

Day 2 的做法应该是：

1. 复制到 `services/query_service.py`
2. 保留主体问答逻辑
3. 只改 import 路径
4. 把检索入口直接改成从 `services/context_service.py` 引入

也就是说，Day 2 不需要马上把它拆成 3 个文件。  
先把归属放对就行。

---

## 第 6 层：今天哪些文件先别迁

有些文件虽然未来也可能要收敛，  
但 Day 2 先别动。

### `utils/file_loader.py`

原因：

- 它现在是索引 pipeline 的下游能力
- 不是 Day 3 任务化的边界阻塞点

Day 2 先不迁，避免改动面过大。

### `utils/text_splitter.py`

同理。

它目前更像 pipeline 用到的能力函数，  
不是必须马上独立成新层的模块。

### 各类 `*_prompt.py` / `*_builder.py`

现在先别碰。

原因：

- 它们属于后续可以进一步规范的层
- 但不影响 Day 3 主线

Day 2 如果把这些也一起拆，会明显扩大范围。

---

## 第 7 层：今天最实用的迁移顺序

不要按“所有 utils 从上到下扫一遍”来迁。  
按主线顺序最稳。

### 第一步：先迁 clients

先处理：

- `utils/embeddings.py`
- `utils/vector_store.py`
- `utils/llm.py`

原因：

- 这 3 个最接近“外部依赖封装”
- 逻辑最容易原样保留
- 对 Day 3 / Day 4 的后续价值最高

### 第二步：再迁 pipeline

处理：

- `utils/index_service.py`

原因：

- Day 3 以后它就是任务执行链路的核心承接点

### 第三步：再迁 service

处理：

- `utils/rag_service.py`
- `utils/retriever.py`

原因：

- 这两个文件都已经进入 query/context 主链路
- 你已经明确 `retriever` 放到 `services/context_service.py`
- 这样后面 context 治理就有稳定落点

### 第四步：暂缓其余模块

包括：

- loader
- splitter
- prompt / builder

先不要扩大范围。

---

## 第 8 层：今天最关键的 import 改造清单

Day 2 真正会花时间的，不是写新功能，  
而是改 import。

最关键的改造会集中在这些地方：

### `utils/vector_store.py` 迁移后

原来：

```python
from utils.embeddings import get_embeddings
```

改成：

```python
from clients.embedding_client import get_embeddings
```

### `utils/index_service.py` 迁移后

原来：

```python
from utils.vector_store import add_documents_to_vector_store
```

改成：

```python
from clients.vector_store_client import add_documents_to_vector_store
```

### `utils/rag_service.py` 迁移后

原来：

```python
from utils.llm import get_llm
from utils.retriever import retrieve_documents
```

Day 2 先最小化改成：

```python
from clients.llm_client import get_llm
from services.context_service import retrieve_documents
```

### `routers/documents.py`

原来：

```python
from utils.index_service import index_document
```

后面会走向：

```python
from pipelines.document_index_pipeline import run_document_index_pipeline
```

但 Day 3 会进一步把它从 router 中拿掉，  
所以 Day 2 这里只要知道迁移方向即可。

---

## 第 9 层：今天最小目录目标

Day 2 不需要一下子把所有文件都塞满。  
最小目录目标就够了：

```text
services/
  context_service.py
  query_service.py

pipelines/
  document_index_pipeline.py

clients/
  embedding_client.py
  vector_store_client.py
  llm_client.py
```

如果今天只先把这几个文件落出来，  
Day 3 就已经有稳定落点了。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：先把 Day 2 的主问题讲顺

### 今天你要能顺着说出来

```text
Day 1 确定主线和边界
-> Day 2 不重写功能
-> Day 2 先拆 utils 的职责归属
-> 外部依赖先迁到 clients
-> 索引主链路迁到 pipelines
-> 问答入口迁到 services
-> Day 3 再继续做索引接口任务化
```

### 你必须能回答这两个问题

1. 为什么 Day 2 的重点是迁移，不是重写？
2. 为什么 clients 应该先迁，而不是先动所有 prompt / builder？

---

## 09:50 - 10:40：先做模块分类

### 今天先按这三类分类

- 原样迁移
- 小改迁移
- 暂不迁移

### 你至少要把这些文件分完

- `utils/index_service.py`
- `utils/rag_service.py`
- `utils/embeddings.py`
- `utils/vector_store.py`
- `utils/llm.py`
- `utils/retriever.py`
- `utils/file_loader.py`
- `utils/text_splitter.py`

只要这一步做清楚，  
后面迁移动作就会快很多。

---

## 10:40 - 11:30：优先处理最容易原样迁移的模块

### 今天最先动这 3 个

- `embeddings.py`
- `vector_store.py`
- `llm.py`

原因：

- 它们最接近 client
- 最少需要改业务逻辑
- 改完就能立即给 Day 3 / Day 4 使用

### 今天不要先碰什么

- 不先拆 prompt
- 不先拆 builder
- 不先重构 retriever
- 不先改 loader / splitter

先抓主线。

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 2 最直接的验收方式

今天最少要能回答：

1. 哪些文件是原样迁移？
2. 哪些文件只是小改迁移？
3. 为什么 `index_service.py` 迁到 pipeline 不是“重写一遍”？
4. Day 3 接下来应该基于哪个新路径继续改？

---

## 下午迁移：14:00 - 18:00

## 14:00 - 14:40：先迁 `clients/`

### 今天建议直接迁过去的文件

- `utils/embeddings.py` -> `clients/embedding_client.py`
- `utils/vector_store.py` -> `clients/vector_store_client.py`
- `utils/llm.py` -> `clients/llm_client.py`

### 这一段的执行原则

- 文件主体逻辑原样保留
- 只改模块路径和内部 import
- 不顺手做缓存
- 不顺手做熔断
- 不顺手做重试

这些属于后面几天的事。

---

## 14:40 - 15:30：再迁 `pipelines/`

### 今天建议处理

- `utils/index_service.py` -> `pipelines/document_index_pipeline.py`

### 这里怎么迁最合理

不是重写。  
而是这样做：

1. 复制文件
2. 改文件名和函数名
3. 改向量库 import
4. 保留索引链路主体逻辑

### 今天改完后你脑子里要变成什么

以后提到文档索引主链路，你想到的应该是：

```text
pipelines/document_index_pipeline.py
```

而不是：

```text
utils/index_service.py
```

---

## 15:30 - 16:20：再迁 `services/`

### 今天建议处理

- `utils/rag_service.py` -> `services/query_service.py`
- `utils/retriever.py` -> `services/context_service.py`

### 这里怎么迁

也不是重写。

直接迁过去，然后：

- 改 `llm` import
- 把 `retriever` 调用改成 `services.context_service`
- 暂时保留 `format_docs(...)`、`build_sources(...)`

同时把 `utils/retriever.py` 迁到：

- `services/context_service.py`

先保留主体检索逻辑，后面再继续往这个文件里加：

- 去重
- chunk 合并
- token budget 控制

也就是说，Day 2 先把 context 入口放对，  
Day 9 再把 context 治理做深。

---

## 16:20 - 17:10：统一改 import，不急着删旧文件

### 今天最稳的方式

先迁新文件，再逐步改调用点，  
不要一迁完就立即删旧文件。

建议顺序：

1. 新路径文件落好
2. 改调用方 import
3. 确认没有路径错误
4. 再考虑删旧文件或保留过渡别名

### 为什么不建议立刻删旧文件

因为 Day 2 的目标是把边界先理顺，  
不是制造大面积 import 断裂。

如果项目里还有多个地方引用旧路径，  
那就先过渡，再收尾。

---

## 17:10 - 18:00：整理 Day 3 的入口

### 到 Day 2 结束时，Day 3 最重要的输入应该是

- 索引主链路已经有新归属：
  - `pipelines/document_index_pipeline.py`
- 外部依赖已经有新归属：
  - `clients/embedding_client.py`
  - `clients/vector_store_client.py`
  - `clients/llm_client.py`
- 问答主入口已经有新归属：
  - `services/context_service.py`
  - `services/query_service.py`

### 这时候 Day 3 才能顺着改什么

Day 3 就可以自然地做：

```text
router
-> document_service.submit_index_task(...)
-> task queue
-> worker
-> pipeline
```

如果 Day 2 没先把归属理顺，  
Day 3 很容易继续把任务逻辑堆回 `utils/`。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. Day 2 的核心为什么是 `utils` 拆分，而不是功能重写？
2. 什么叫“原样迁移”？
3. 什么叫“小改迁移”？
4. 为什么 `embeddings.py`、`vector_store.py`、`llm.py` 基本可以直接迁？
5. 为什么 `index_service.py` 要迁到 `pipelines/`，但不用重写整条索引链？
6. 为什么 `retriever.py` 放到 `services/context_service.py` 是合理的？
7. 为什么 Day 2 不急着处理 prompt / builder？
8. Day 3 最需要接住 Day 2 的哪些新路径？

---

## 今日验收标准

- 已经明确哪些文件原样迁移
- 已经明确哪些文件小改迁移
- 已经明确哪些文件暂不迁移
- `clients/`、`pipelines/`、`services/` 的最小落点已经清楚
- `utils/index_service.py` 的迁移方式是“改归属 + 改 import”，不是重写
- `utils/rag_service.py` 的迁移方式是“改归属 + 保留主体逻辑”
- `utils/retriever.py` 已明确迁到 `services/context_service.py`
- Day 3 后续会基于新路径继续做任务化，而不是继续扩张 `utils/`

---

## 今天最容易踩的坑

### 坑 1：把迁移理解成重写

问题：

- 明明逻辑没问题
- 却花大量时间重新实现

规避建议：

- 能原样迁就原样迁
- 只在职责变化明显时小改

### 坑 2：Day 2 就想把整个 utils 全拆完

问题：

- 范围迅速失控
- 影响 Day 3 主线推进

规避建议：

- 先抓索引和问答主链路相关模块

### 坑 3：先删旧文件，再改 import

问题：

- 很容易造成路径断裂

规避建议：

- 先迁新路径
- 再逐步改调用点
- 最后再收尾

### 坑 4：把 prompt / builder 也一起纳入 Day 2

问题：

- 这些模块不是当前任务化主线的阻塞点

规避建议：

- Day 2 先不扩大范围

### 坑 5：目录分了，但职责没变

问题：

- 文件路径变了
- 但还是老问题

规避建议：

- 迁移时先判断职责，再决定落点

---

## 给明天的交接提示

明天会进入 Day 3：索引接口任务化。

Day 3 不是再讨论“这个文件该放哪”，  
而是要基于 Day 2 已经拆好的归属，开始真正把索引接口改成：

```text
提交任务
-> 返回 task_id
```

所以 Day 2 最关键的交接只有一句话：

```text
先把 utils 里已经成熟的职责迁到正确层级，后面的任务化才不会继续堆回 utils。
```
