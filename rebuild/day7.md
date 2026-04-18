# Day 7：阻塞点迁移与对象缓存

## 今天的总目标

- 找出当前索引和问答链路里真正会阻塞的同步调用
- 把文件解析、向量写入这类同步重操作移到线程执行
- 让 `embedding`、`vector store`、`llm` 这几个长生命周期对象在进程内复用
- 避免每次请求或每次任务重复初始化重对象
- 让 Day 3 到 Day 6 建起来的任务化链路真正开始适合生产化运行

## 今天结束前，你必须拿到什么

- 一张当前阻塞点清单
- 一个新的 `infra/object_cache.py`
- 一套 `clients/embedding_client.py` / `clients/vector_store_client.py` / `clients/llm_client.py` 的缓存接入方案
- 一套 `utils/file_loader.py` 和 `clients/vector_store_client.py` 的阻塞迁移方案
- 一份你自己能讲清楚的“为什么 worker 有了还要继续迁移阻塞点”的认知

---

## 结合当前项目现状，Day 7 为什么更重要

你现在的项目状态和最初规划时相比，已经有几个非常关键的现实背景：

- embedding 模型已经切到 `BAAI/bge-m3`
- Milvus 不再考虑走本地 `milvus-lite`，而是走远程服务端 Milvus
- 之前的旧向量缓存 / 旧索引数据已经清理过

这 3 个变化会直接放大 Day 7 的必要性。

### 1. `BAAI/bge-m3` 比之前的轻量模型更值得缓存

`bge-m3` 更通用，也更适合你后面中英混合和通用检索场景。  
但代价也很直接：

- 模型对象更重
- 初始化成本更高
- 每次重建 client 的开销更明显

所以 Day 7 的对象缓存，不再只是“锦上添花”，  
而是对当前模型选择的必要配套。

### 2. 远程 Milvus 服务让 `vector_store` 更像真正的基础设施 client

现在 `MILVUS_URI` 已经不是本地文件路径的思路了，  
而是远程服务地址。

这意味着：

- `get_vector_store()` 更应该被视为长生命周期 client
- 每次重新创建连接对象更没有必要
- 运行时边界会比本地 lite 模式更清晰

### 3. 旧缓存清理后，Day 7 更适合按“冷启动”口径验收

既然之前的旧索引 / 旧缓存已经清掉了，  
那 Day 7 的验收就更应该看：

- 冷启动时对象是否只初始化一次
- 第一次重建索引时阻塞点是否已经迁出 async 主链
- 后续重复跑任务时是否真的在复用对象

也就是说，Day 7 的目标不是“理论上支持缓存”，  
而是：

> 在一个干净环境里，确认缓存和阻塞迁移在真实链路里能成立。

---

## 今天开始，worker 有了不代表系统就轻了

到 Day 6 为止，Mneme 已经完成了这些关键变化：

```text
API 提交任务
-> worker 后台执行
-> pipeline 跑索引链路
-> batch 写向量
-> task 有显式阶段状态
```

这已经让系统从“同步 API 原型”走到了“可任务化运行后端”。

但这里还有两个很现实的问题：

### 问题 1：阻塞点还在 async 链路里

当前项目里仍然有明显同步调用，比如：

- `loader.load()`
- `vector_store.add_documents(...)`

这些调用虽然现在已经不在 HTTP 请求线程里，  
但它们仍然会阻塞 worker 里的事件循环。

### 问题 2：重对象还在重复初始化

当前这些函数每次调用都会重新 new 一次对象：

- `get_embeddings()`
- `get_vector_store()`
- `get_llm()`

这会带来：

- 初始化成本重复支付
- 内存和连接资源抖动
- worker 稍微并发一点就更不稳定

所以 Day 7 的核心不是再改接口，  
而是：

> 把真正重的同步点移出去，把真正重的对象复用起来。

---

## 第 1 层：今天到底在优化什么

Day 7 优化的是两类问题：

```text
阻塞点
对象生命周期
```

### 阻塞点问题

当前典型阻塞点有：

- `utils/file_loader.py` 里的 `loader.load()`
- `clients/vector_store_client.py` 里的 `vector_store.add_documents(...)`
- 未来 query 里可能出现的同步 SDK 调用

### 对象生命周期问题

当前典型重对象有：

- `HuggingFaceEmbeddings`
- `Milvus`
- `ChatOpenAI`

这些对象如果每次调用都重建，  
哪怕功能上“能跑”，工程上也不够稳。

---

## 第 2 层：为什么 Day 7 不只是“性能优化”

很多人会把 Day 7 理解成：

- 晚点再做也行
- 只是让速度快一点

这理解太轻了。

Day 7 真正解决的是：

> 执行模型虽然已经任务化了，但运行时行为还不够稳定。

如果你不做 Day 7，系统很容易出现这些现象：

- worker 一次索引时 CPU 或 I/O 卡很久
- 重对象反复初始化，日志里每次都像新启动一样
- embedding / vector store / llm 每次请求都“从头来”
- 稍微上并发后，资源抖动明显

所以 Day 7 不是“可做可不做”的美化。  
它是在把 Day 3 到 Day 6 搭起来的链路，往真正可运行的方向推进。

---

## 第 3 层：今天先把真实阻塞点列出来

结合当前仓库，Day 7 先盯这两个最明显的点就够了。

### 阻塞点 1：文件解析

当前 `utils/file_loader.py` 里有：

```python
docs = loader.load()
```

无论是：

- `PyPDFLoader`
- `TextLoader`

这一层本质上都是同步 I/O / 同步解析。

它不应该继续直接跑在 async pipeline 里。

### 阻塞点 2：向量写入

当前 `clients/vector_store_client.py` 里有：

```python
vector_store.add_documents(...)
```

这个调用通常会连着做：

- embedding
- 向量写入

它本质上也是重同步调用。

### 为什么 Day 7 先只抓这两个

因为这两个点：

- 都在主索引链路上
- 都足够重
- 都已经有真实代码落点

先把它们迁出去，收益最大。

---

## 第 4 层：今天先把真实重对象列出来

结合当前仓库，最典型的重对象就是这 3 个。

### 1. `clients/embedding_client.py`

当前：

```python
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(...)
```

这意味着每次调用都 new 一个模型包装对象。

在你现在已经切到 `BAAI/bge-m3` 的前提下，  
这一点的成本会比之前更明显。

### 2. `clients/vector_store_client.py`

当前：

```python
def get_vector_store() -> Milvus:
    return Milvus(...)
```

这意味着每次调用都重新构建 vector store client。

而你现在走的是远程 Milvus 服务端模式，  
这类对象更适合在进程内复用，而不是每次重新构建。

### 3. `clients/llm_client.py`

当前：

```python
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(...)
```

这意味着每次 query、每次 builder 都会重新初始化模型 client。

虽然 LLM client 不像 embedding 模型那么重，  
但它仍然属于典型长生命周期对象，Day 7 一起收进缓存边界最顺。

### Day 7 的目标

不是把这些对象做成“全局神秘单例”，  
而是先做到：

> 同一个 worker 进程内尽量复用。

这已经能解决大量重复初始化问题。

---

## 第 5 层：今天的最稳边界

Day 7 最稳的边界是：

- `infra/object_cache.py`
  - 负责缓存对象
- `clients/*.py`
  - 负责定义“怎么构建对象”
- `utils/file_loader.py` / `clients/vector_store_client.py`
  - 负责把阻塞同步调用搬到线程执行

不要把缓存和阻塞迁移逻辑塞到：

- router
- service
- pipeline 主体规则层

这些层不应该承担运行时底座能力。

### 结合你当前项目，Day 7 的真实落地顺序

今天最建议的执行顺序是：

1. 先补 `infra/object_cache.py`
2. 再给 `embedding / vector_store / llm` 接进程内缓存
3. 再把 `loader.load()` 和 `vector_store.add_documents(...)` 搬到线程执行
4. 最后用“清理过旧缓存后的冷启动重建”来做验收

这个顺序的好处是：

- 先解决对象反复初始化
- 再解决 async 链路里的同步阻塞
- 最后在真实链路里一起验证

---

---

## 第 6 层：今天不要做什么

Day 7 不建议做：

- 不做分布式缓存
- 不做 Redis 对象缓存
- 不做跨 worker 共享对象
- 不做线程池参数深度调优
- 不做完整熔断与限流
- 不做 embedding service 独立化

今天只做：

> 进程内对象复用 + 关键同步阻塞点迁移到线程执行。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 7 的主问题讲顺

### 今天你要能顺着说出来

```text
Day 3 建立任务提交入口
-> Day 4 worker 接管执行
-> Day 5 批处理降低单次压力
-> Day 6 状态机让执行阶段可见
-> Day 7 继续处理真实阻塞点和重对象生命周期
```

### 你必须能回答这两个问题

1. 为什么 worker 有了以后，async 链路里仍然可能有阻塞问题？
2. 为什么 `get_embeddings()` / `get_vector_store()` / `get_llm()` 重复 new 会成为实际工程问题？

---

## 09:50 - 10:40：先把阻塞点和重对象分开看

### 阻塞点关注什么

阻塞点关注的是：

- 当前调用是不是同步重操作
- 它是不是跑在 async 链路里
- 它会不会卡住事件循环

### 重对象关注什么

重对象关注的是：

- 是否每次调用都重新初始化
- 是否适合进程内复用
- 是否应该有统一缓存入口

这两个问题经常一起出现，  
但它们不是同一个问题。

---

## 10:40 - 11:30：先决定今天改哪些文件

### Day 7 最值得先动的文件

- `infra/object_cache.py`
- `clients/embedding_client.py`
- `clients/vector_store_client.py`
- `clients/llm_client.py`
- `utils/file_loader.py`

### 为什么 Day 7 先动这些

因为这几处已经覆盖了：

- 文件解析阻塞
- embedding 对象重复构建
- vector store 对象重复构建
- llm 对象重复构建
- batch 写入中的同步阻塞

先把这些点稳住，  
Day 7 就已经达标。

并且它们都已经和你当前真实配置绑定：

- `BAAI/bge-m3`
- 远程 Milvus
- 任务化索引主链

所以这一天做完，收益会非常直接。

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 7 最直接的验收方式

今天最少要能回答：

1. 哪两个真实阻塞点已经迁到线程执行
2. 哪三个重对象已经进入进程内缓存
3. 为什么 `object_cache` 放在 `infra/` 最合理
4. 为什么 Day 7 还不需要做 Redis 级对象缓存
5. 在旧缓存已经清理后的冷启动环境里，第一次重建是否仍然能稳定完成

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:30：新增 `infra/object_cache.py`

### 这一段属于新增能力

所以这里保留壳子和参考实现。

### `infra/object_cache.py` 练手骨架版

```python
_CACHE: dict[str, object] = {}


def get_cached_object(key: str) -> object | None:
    # 你要做的事：
    # 1. 按 key 取缓存对象
    raise NotImplementedError("先自己实现 get_cached_object")


def set_cached_object(key: str, value: object) -> object:
    # 你要做的事：
    # 1. 按 key 写缓存对象
    # 2. 返回 value
    raise NotImplementedError("先自己实现 set_cached_object")
```

### `infra/object_cache.py` 参考答案

```python
_CACHE: dict[str, object] = {}


def get_cached_object(key: str) -> object | None:
    return _CACHE.get(key)


def set_cached_object(key: str, value: object) -> object:
    _CACHE[key] = value
    return value
```

### 这里要先理解的点

Day 7 的这个缓存是：

- 进程内缓存
- worker 级缓存
- API 进程和 worker 进程各自拥有自己的缓存

它不是：

- Redis 缓存
- 跨进程共享缓存
- 分布式对象池

今天做到进程内复用就够了。

尤其对你现在的 `bge-m3`，  
先把这个级别的缓存做稳，收益就已经很大。

---

## 14:30 - 15:20：给 `clients/*.py` 接入对象缓存

### 这是普通增量修改，不是重写

这里不需要“壳子 + 答案”去重写整文件。  
更合理的是直接说明怎么改。

### 1. `clients/embedding_client.py`

当前是：

```python
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(...)
```

Day 7 直接改成：

1. 先查 `get_cached_object("embedding_client")`
2. 有缓存就直接返回
3. 没缓存再创建对象
4. 用 `set_cached_object(...)` 写回缓存

### 2. `clients/vector_store_client.py`

当前是：

```python
def get_vector_store() -> Milvus:
    return Milvus(...)
```

Day 7 同样改成：

1. 先查 `get_cached_object("vector_store_client")`
2. 没有才创建 `Milvus(...)`
3. 写回缓存

### 3. `clients/llm_client.py`

当前是：

```python
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(...)
```

Day 7 同样接缓存。

### 一个最实用的缓存键建议

- `embedding_client`
- `vector_store_client`
- `llm_client`

今天先不要把 key 设计搞复杂。  
一类对象一个固定 key 就够了。

---

## 15:20 - 16:10：迁移文件解析阻塞点

### 这一段属于新增能力

因为它不只是“改路径”，  
而是把同步解析逻辑搬到线程执行。

### 当前问题

`utils/file_loader.py` 里现在是：

```python
docs = loader.load()
```

这行虽然写在 async 函数里，  
但它本质上还是同步阻塞调用。

### 最稳的第一版做法

直接用：

```python
await asyncio.to_thread(loader.load)
```

### `utils/file_loader.py` 练手骨架版

```python
import asyncio


async def load_langchain_documents(...):
    # 你要做的事：
    # 1. 保留原来的 loader 选择逻辑
    # 2. 把 loader.load() 搬到 to_thread
    # 3. 保留后面的 metadata 补齐逻辑
    raise NotImplementedError("先自己实现 Day 7 阻塞迁移版 file_loader")
```

### `utils/file_loader.py` 参考改法

```python
import asyncio


async def load_langchain_documents(...):
    ...
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

### 为什么这里不需要重写 loader 逻辑

因为 Day 7 的重点不是换 loader，  
而是：

> 保留原逻辑，把同步阻塞调用迁出去。

---

## 16:10 - 17:00：迁移向量写入阻塞点

### 这一段也属于新增能力

当前 `clients/vector_store_client.py` 里无论是：

- `add_documents_to_vector_store(...)`
- `add_documents_to_vector_store_in_batches(...)`

最终都在直接调用：

```python
vector_store.add_documents(...)
```

这也是同步重操作。

### 最稳的第一版做法

同样先用：

```python
await asyncio.to_thread(...)
```

把真正的写入动作放到线程执行。

### `clients/vector_store_client.py` 练手骨架版

```python
import asyncio


async def add_documents_to_vector_store_in_batches(
    *,
    chunk_docs: list[LCDocument],
    batch_size: int,
) -> dict:
    # 你要做的事：
    # 1. 保留原来的 batch 切片逻辑
    # 2. 每个 batch 的 add_documents(...) 改成 to_thread
    # 3. 保留 batch_count / total_count 汇总
    raise NotImplementedError("先自己实现 Day 7 阻塞迁移版 vector upsert")
```

### `clients/vector_store_client.py` 参考改法

```python
import asyncio


async def add_documents_to_vector_store_in_batches(
    *,
    chunk_docs: list[LCDocument],
    batch_size: int,
) -> dict:
    vector_store = get_vector_store()
    batches = build_document_batches(
        chunk_docs,
        batch_size=batch_size,
    )

    total_count = 0
    for batch_docs in batches:
        ids = [str(chunk.metadata["chunk_id"]) for chunk in batch_docs]
        await asyncio.to_thread(
            vector_store.add_documents,
            batch_docs,
            ids,
        )
        total_count += len(batch_docs)

    return {
        "batch_count": len(batches),
        "total_count": total_count,
        "batch_size": batch_size,
    }
```

### 这里要特别注意

Day 7 的目标不是让它“变成纯异步 SDK”，  
而是把同步重调用从当前 async 链路里隔离出去。

这是非常现实、也非常实用的一步。

对当前项目来说，这一步的现实价值非常高，因为：

- 远程 Milvus 写入本身就带网络往返
- `bge-m3` 的 embedding 计算也不轻
- 这两者叠在一起时，更不应该继续直接压在 async 执行流里

---

## 17:00 - 18:00：整理 Day 7 之后的运行时认知

### 到 Day 7 为止，Mneme 多了什么

从今天开始，Mneme 的索引和问答底座不只是：

- 有任务
- 有 worker
- 有 batch
- 有状态机

还开始有：

- 重对象复用
- 阻塞点隔离

### 这意味着什么

这意味着后面系统在这些方面会更稳：

- worker 重复跑任务时不会每次都重建大对象
- 文件解析不会直接堵住当前 async 执行流
- 向量写入不会直接占住 async 链路
- 后面再加限流、熔断、重试时位置会更清楚

Day 7 本质上是在做：

> 运行时基础设施的第一轮加固。

如果再结合你现在已经完成的环境切换来看，  
Day 7 还有一个很现实的成果：

> 模型层和向量库层都已经开始按“真实线上基础设施”的方式来对待，而不是临时脚本式使用。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. 为什么 worker 有了，async 链路里仍然可能有阻塞点？
2. 当前项目里最典型的两个阻塞点分别是什么？
3. 为什么 `get_embeddings()` / `get_vector_store()` / `get_llm()` 适合做进程内缓存？
4. 为什么 `object_cache.py` 应该放在 `infra/`？
5. 为什么 `await asyncio.to_thread(loader.load)` 比直接保留 `loader.load()` 更合理？
6. 为什么 Day 7 的目标不是把所有 SDK 变成原生 async？
7. Day 7 做的缓存为什么不是 Redis 缓存？
8. Day 8 继续做 `utils` 轻量拆分时，为什么边界会更清楚？

---

## 今日验收标准

- 已识别并说明当前两个真实阻塞点
- 已新增 `infra/object_cache.py`
- `embedding / vector store / llm` 已有进程内缓存接入方案
- `utils/file_loader.py` 已有阻塞迁移方案
- `clients/vector_store_client.py` 已有阻塞迁移方案
- 能清楚区分“对象缓存”和“阻塞迁移”是两类不同优化
- 能说明 Day 7 解决的是运行时稳定性问题，而不只是单纯提速
- 能说明 `BAAI/bge-m3 + 远程 Milvus` 为什么会放大 Day 7 的价值
- 在旧缓存已清理的前提下，能用冷启动链路做一次完整验收

---

## 今天最容易踩的坑

### 坑 1：以为 worker 已经足够，不需要再迁移阻塞点

问题：

- worker 只是把重活移出 HTTP
- 但 async 链路里仍然可能被同步调用卡住

规避建议：

- 把真正重的同步调用迁到线程执行

### 坑 2：把对象缓存理解成分布式缓存

问题：

- Day 7 只是进程内复用
- 不是 Redis 共享对象

规避建议：

- 先把进程内缓存做稳
- 后面再谈更复杂缓存层

### 坑 3：把 AsyncSession 也塞进 object_cache

问题：

- 数据库会话不是长生命周期可复用重对象
- 它和请求/任务上下文强绑定

规避建议：

- 只缓存 embedding / vector store / llm 这类稳定对象

### 坑 4：看到 `async def` 就以为里面不会阻塞

问题：

- async 函数里一样可以写同步重操作

规避建议：

- 看实际调用是不是同步 I/O 或重 CPU/SDK 调用

### 坑 5：Day 7 就顺手做完整熔断、限流、重试

问题：

- 范围迅速膨胀
- Day 7 的重点会跑偏

规避建议：

- 先做对象复用和阻塞迁移
- 运行时治理能力后面继续接

---

## 给明天的交接提示

明天会进入 Day 8：`utils` 轻量拆分。

Day 8 不是回头重新讲抽象，  
而是要在 Day 2 的迁移计划、Day 7 的运行时加固基础上，继续把剩余职责边界收紧。

所以 Day 7 最关键的交接只有一句话：

```text
运行时重对象和阻塞点已经开始有稳定落点，接下来继续拆 utils 时，不再只是“文件挪位置”，而是带着更清楚的运行时边界去拆。
```
