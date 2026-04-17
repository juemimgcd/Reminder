# Day 3：索引接口任务化

## 今天的总目标

- 把索引接口从“同步执行完整索引链路”改成“提交索引任务”
- 让 API 层只负责校验、创建任务、投递任务、返回 `task_id`
- 明确任务记录和文档状态之间的关系
- 为 Day 4 的 Celery worker 接管索引执行预留入口
- 保证现有 `routers / services / tasks / pipelines / crud / schemas` 的调用边界不乱

## 今天结束前，你必须拿到什么

- 一个新的索引任务提交返回结构
- 一个 `crud/task_record.py` 的最小设计
- 一个基于现有 `services/document_service.py` 继续扩展的任务提交入口设计
- 一个 `tasks/index_tasks.py` 的占位任务设计
- 一版变薄后的 `routers/documents.py` 索引接口思路
- 一套你自己能讲清楚的 “API 返回 `task_id`，worker 后台执行” 心智模型

---

## 今天开始，索引接口不再直接干重活

Day 3 是本轮优化第一次真正改变系统执行模型的一天。

Day 1 讲清楚了：

- 当前问题不是功能缺失
- 当前问题是同步重任务压在 API 链路里
- 本轮优化主线是 `Celery + Redis`

Day 2 讲清楚了：

- router 只做入口
- service 承接业务动作
- pipeline 承接多步骤索引链路
- client 和 infra 承接外部依赖与运行时能力

今天要开始把这个原则落到索引接口上。

当前接口大概率更像这样：

```text
POST /kb/documents/{document_id}/index
-> 查 document
-> 判断状态
-> 调 index_document(...)
-> 解析文件
-> 切分文本
-> 写 chunks
-> 写向量库
-> 更新状态
-> 返回 indexed
```

Day 3 以后应该变成：

```text
POST /kb/documents/{document_id}/index
-> 查 document 并校验是否可索引
-> 创建 task_record
-> 投递后台任务
-> 返回 task_id
```

注意这句话：

> Day 3 不是让 worker 真正跑完整索引；Day 3 是先让 API 不再同步跑完整索引。

真正的 worker 执行细节放到 Day 4。

---

## 第 1 层：今天的核心变化是什么

今天最核心的变化只有一个：

```text
同步索引接口
-> 任务提交接口
```

也就是说，接口返回的含义变了。

### 以前返回什么

以前接口大概率返回：

- `document_id`
- `knowledge_base_id`
- `chunk_count`
- `status=indexed`

这代表：

> 请求结束时，索引已经做完。

### 以后返回什么

任务化以后，接口应该先返回：

- `task_id`
- `document_id`
- `knowledge_base_id`
- `status=queued`
- `message=任务已提交`

这代表：

> 请求结束时，索引任务已经提交，但索引不一定完成。

这是一个非常重要的语义变化。

---

## 第 2 层：为什么 Day 3 不直接做完整 Celery worker

很多人一做到任务化，就想今天一次性做完：

- 安装 Celery
- 配 Redis
- 写 worker
- 改接口
- 跑完整索引
- 做状态查询
- 做失败重试

这个节奏太急。

Day 3 先只解决：

> API 层从同步执行改为提交任务。

原因有 3 个：

1. 先改接口语义，明确用户拿到的是 `task_id`
2. 先建立任务记录，后续状态机才有落点
3. 先把 worker 调用点留出来，Day 4 再接真实执行

这样做风险更低。

---

## 第 3 层：今天的数据流是什么

今天这条链路要在脑子里非常清楚：

```text
用户调用索引接口
-> router 接收 document_id
-> service 校验 document 是否可索引
-> service 创建 task_record
-> service 更新 document.status 为 queued 或 indexing_pending
-> task queue 投递 index task
-> router 返回 task_id
```

注意，这里还没有真正执行：

- 文件解析
- 文本切分
- embedding
- Milvus 写入

这些要交给 Day 4 的 worker。

---

## 第 4 层：任务记录和文档状态怎么分工

当前仓库已经有：

- `models/task_record.py`
- `models/document.py`

这说明你不需要从零发明任务概念。

但你要先讲清楚两者分工。

### `documents.status` 表达什么

`documents.status` 更适合表达：

> 这份文档当前对业务来说处在什么状态？

例如：

- `uploaded`
- `queued`
- `indexing`
- `indexed`
- `failed`

它是文档维度的状态。

### `task_records.status` 表达什么

`task_records.status` 更适合表达：

> 某一次后台任务执行到什么状态？

例如：

- `queued`
- `running`
- `completed`
- `failed`

它是任务维度的状态。

### 为什么两个状态都需要

因为一份文档可能经历多次任务：

- 第一次索引
- 失败后重试
- 未来重建索引

如果只用 `documents.status`，你很难追踪每一次任务。  
如果只用 `task_records.status`，你又很难快速知道文档当前是否可用。

你要记住这句话：

> document 记录业务对象状态，task_record 记录一次执行过程状态。

---

## 第 5 层：今天先定哪些状态

Day 6 会专门做幂等状态机。  
所以 Day 3 不要一上来把状态体系做得太复杂。

今天先用最小状态即可。

### 文档状态

建议先用：

- `uploaded`
- `queued`
- `indexing`
- `indexed`
- `failed`

### 任务状态

建议先用：

- `queued`
- `running`
- `completed`
- `failed`

### 为什么 Day 3 先不用完整阶段状态

Day 6 才会把任务拆成：

- `parsing`
- `chunking`
- `embedding`
- `vector_upserting`
- `completed`
- `failed`

今天先把提交任务链路跑通。  
不要把状态机复杂度提前塞进 Day 3。

---

## 第 6 层：router、service、task、pipeline 怎么配合

今天最关键的是调用顺序。

你要把这条链记住：

```text
router
-> document_service.submit_index_task(...)
-> crud.task_record.create_task_record(...)
-> infra.task_queue.enqueue_index_task(...)
-> tasks.index_tasks.index_document_task(...)
-> pipelines.document_index_pipeline.run_document_index_pipeline(...)
```

Day 3 重点在前半段：

```text
router
-> service
-> task record
-> enqueue
-> return task_id
```

Day 4 才重点处理后半段：

```text
task
-> pipeline
-> parsing/chunking/embedding/upsert
-> update result
```

---

## 第 7 层：今天不要做什么

Day 3 不建议做：

- 不把完整索引逻辑搬进 Celery task
- 不做完整状态机
- 不做 batch embedding
- 不做 worker 并发调优
- 不做 retry / rate limit / circuit breaker
- 不做 MCP
- 不做 memory pipeline

今天只做一件事：

> 索引接口从“同步执行”变成“提交任务”。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 3 的主链路讲顺

### 今天你要能顺着说出来

```text
用户提交索引请求
-> API 校验 document 是否存在、是否可索引
-> 创建 task_record
-> 投递 index task
-> 返回 task_id
-> worker 后续异步执行索引
```

### 你必须能回答这两个问题

1. 为什么任务化以后不能再返回 `chunk_count` 作为同步结果？
2. 为什么 Day 3 只提交任务，不急着把 worker 完整跑通？

---

## 09:50 - 10:40：理解 `task_id` 的意义

### `task_id` 不是随便生成的字符串

`task_id` 是后续所有任务治理能力的入口。

后面你会围绕它做：

- 状态查询
- 失败重试
- 错误定位
- 任务耗时统计
- 任务恢复
- 幂等控制

所以 Day 3 返回 `task_id`，不是为了“接口看起来异步”，  
而是为了让后续所有运行时治理都有抓手。

### 一个推荐 ID 形态

可以先用：

```text
task_index_20260417123000_ab12cd
```

这个 ID 至少表达：

- 它是任务
- 它和 index 有关
- 它大概什么时候创建
- 它有短随机串避免冲突

---

## 10:40 - 11:30：确定 Day 3 的最小文件边界

### 今天建议思考这些文件

- `schemas/document.py`
- `crud/task_record.py`
- `services/document_service.py`
- `infra/task_queue.py`
- `tasks/index_tasks.py`
- `routers/documents.py`

### 每个文件的职责

| 文件 | 职责 |
|---|---|
| `schemas/document.py` | 定义索引任务提交返回结构 |
| `crud/task_record.py` | 创建和查询任务记录 |
| `services/document_service.py` | 校验文档并提交索引任务 |
| `infra/task_queue.py` | 隔离任务投递方式 |
| `tasks/index_tasks.py` | 放 Celery task 入口，占位给 Day 4 |
| `routers/documents.py` | 调 service 并返回响应 |

### 这里最重要的边界

router 不直接知道 Celery 怎么投递。  
它只知道：

```text
submit_index_task(...) 返回一个任务提交结果
```

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 3 最直接的验收方式

今天至少要能回答：

1. 索引接口现在返回的是任务提交结果，不是索引完成结果
2. `task_record` 里能查到新建任务
3. document 状态能从 `uploaded` 进入 `queued`
4. 任务投递入口存在，即使 Day 4 才接真实 worker 执行

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:40：先补索引任务返回 Schema

### 建议修改

- `schemas/document.py`

### `schemas/document.py` 练手骨架版

```python
from pydantic import BaseModel


class DocumentIndexTaskData(BaseModel):
    # 你要做的事：
    # 1. 返回 task_id
    # 2. 返回 document_id
    # 3. 返回 knowledge_base_id
    # 4. 返回任务状态
    # 5. 可选返回提示信息
    raise NotImplementedError
```

### `schemas/document.py` 参考答案

```python
from pydantic import BaseModel, Field


class DocumentIndexTaskData(BaseModel):
    task_id: str = Field(..., description="索引任务 ID")
    document_id: str = Field(..., description="文档 ID")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    status: str = Field(..., description="任务当前状态")
    message: str = Field(default="index task submitted", description="任务提交说明")
```

### 这一段你一定要看懂

旧的 `DocumentIndexData` 表达的是：

```text
索引完成后的结果
```

新的 `DocumentIndexTaskData` 表达的是：

```text
索引任务已经被提交
```

这两个语义不要混用。

---

## 14:40 - 15:30：实现 `crud/task_record.py`

### 建议新建

- `crud/task_record.py`

### `crud/task_record.py` 练手骨架版

```python
from sqlalchemy.ext.asyncio import AsyncSession

from models.task_record import TaskRecord


async def create_task_record(
    db: AsyncSession,
    *,
    task_id: str,
    task_type: str,
    target_id: str,
    status: str = "queued",
) -> TaskRecord:
    # 你要做的事：
    # 1. 构造 TaskRecord
    # 2. add 到 session
    # 3. flush
    # 4. refresh
    # 5. 返回 task
    raise NotImplementedError("先自己实现 create_task_record")
```

### `crud/task_record.py` 参考答案

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.task_record import TaskRecord


async def create_task_record(
    db: AsyncSession,
    *,
    task_id: str,
    task_type: str,
    target_id: str,
    status: str = "queued",
) -> TaskRecord:
    task = TaskRecord(
        id=task_id,
        task_type=task_type,
        target_id=target_id,
        status=status,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_task_record_by_id(
    db: AsyncSession,
    *,
    task_id: str,
) -> TaskRecord | None:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    return result.scalar_one_or_none()
```

### 为什么 Day 3 要先建任务记录

因为 API 一旦返回 `task_id`，  
这个 `task_id` 就必须能被系统解释。

如果只把任务丢给 Celery，但数据库没有任务记录，  
后面状态查询、失败定位、重试入口都会很别扭。

---

## 15:30 - 16:20：实现 `infra/task_queue.py`

### 建议新建

- `infra/task_queue.py`

### 为什么要有这一层

router 和 service 不应该直接写：

```python
index_document_task.delay(...)
```

更稳的方式是包一层：

```text
enqueue_index_document_task(...)
```

这样以后你要替换 Celery、加日志、加幂等检查、加降级策略，  
不会到处改业务代码。

### `infra/task_queue.py` 练手骨架版

```python
def enqueue_index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    # 你要做的事：
    # 1. 调用 tasks.index_tasks.index_document_task
    # 2. 把 task_id 和 document_id 传进去
    # 3. Day 3 可以先做占位，Day 4 再接 Celery
    raise NotImplementedError("先自己实现 enqueue_index_document_task")
```

### `infra/task_queue.py` 参考答案：Day 3 占位版

```python
from conf.logging import app_logger


def enqueue_index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    app_logger.bind(module="task_queue").info(
        "index task queued",
        task_id=task_id,
        document_id=document_id,
    )
```

### Day 4 后可以替换成什么

Day 4 接 Celery 后，这里可以变成：

```python
from tasks.index_tasks import index_document_task


def enqueue_index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    index_document_task.delay(task_id=task_id, document_id=document_id)
```

今天先不强行要求 Celery 跑起来。

---

## 16:20 - 17:10：在现有 `services/document_service.py` 上继续加任务提交入口

### 建议修改，不建议重写整文件

- `services/document_service.py`

如果上一版 `document_service.py` 里已经有：

- `ensure_document_can_index(...)`
- 或其他文档状态判断函数

那这些函数应该直接保留。  
Day 3 要做的是在这个基础上新增：

- `build_index_task_id(...)`
- `submit_document_index_task(...)`

不要把已经合理的文档校验函数又重写一遍。

### `services/document_service.py` 最小增量改法

如果你上一版已经有：

```python
async def ensure_document_can_index(...): ...
```

那 Day 3 最合理的方式是保留它，  
再在同一个文件里继续加任务提交函数。

```python
from sqlalchemy.ext.asyncio import AsyncSession


async def submit_document_index_task(
    db: AsyncSession,
    *,
    document_id: str,
) -> dict:
    # 你要做的事：
    # 1. 校验 document 是否存在、是否可索引
    # 2. 生成 task_id
    # 3. 创建 task_record
    # 4. 更新 document.status 为 queued
    # 5. 投递任务
    # 6. 返回任务提交结果
    raise NotImplementedError("先自己实现 submit_document_index_task")
```

### `services/document_service.py` 参考改法

```python
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from crud.document import update_document_status
from crud.task_record import create_task_record
from infra.task_queue import enqueue_index_document_task


async def ensure_document_can_index(
    db: AsyncSession,
    *,
    document_id: str,
):
    ...


def build_index_task_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"task_index_{timestamp}_{uuid.uuid4().hex[:6]}"


async def submit_document_index_task(
    db: AsyncSession,
    *,
    document_id: str,
) -> dict:
    document = await ensure_document_can_index(
        db,
        document_id=document_id,
    )

    task_id = build_index_task_id()

    await create_task_record(
        db,
        task_id=task_id,
        task_type="document_index",
        target_id=document.id,
        status="queued",
    )
    await update_document_status(db, document_id=document.id, status="queued")
    enqueue_index_document_task(task_id=task_id, document_id=document.id)

    return {
        "task_id": task_id,
        "document_id": document.id,
        "knowledge_base_id": document.knowledge_base_id,
        "status": "queued",
        "message": "index task submitted",
    }
```

### 这里有 3 个特别容易忽略的点

#### 点 1：先落库，再投递任务

如果先投递任务、后写数据库，worker 可能先跑起来，  
结果发现数据库里还没有 task_record。

#### 点 2：投递失败要考虑事务

Day 3 可以先不展开补偿逻辑，  
但你要知道这里未来需要处理：

- 任务记录创建成功
- document 状态已变更
- 但 Celery 投递失败

这会在后续稳定性治理里继续处理。

#### 点 3：不要在 service 里执行索引

service 今天只提交任务。  
真正执行索引的地方应该是 Day 4 的 worker + pipeline。

---

## 17:10 - 18:00：改造 `routers/documents.py` 的索引接口

### 当前接口的问题

当前 `index_document_api(...)` 大致是：

```text
router
-> 查 document
-> 判断状态
-> await index_document(db, doc)
-> 同步返回索引结果
```

这个接口的问题不是“写错了”，  
而是它属于同步原型阶段的写法。

Day 3 以后应该变成：

```text
router
-> submit_document_index_task(...)
-> commit
-> 返回 task_id
```

### `routers/documents.py` 练手骨架版

```python
@router.post("/{document_id}/index")
async def index_document_api(
    document_id: str,
    db: AsyncSession = Depends(get_database),
):
    # 你要做的事：
    # 1. 调 service 提交索引任务
    # 2. commit
    # 3. 用 DocumentIndexTaskData 包装返回
    raise NotImplementedError("先自己实现任务化索引接口")
```

### `routers/documents.py` 参考答案

```python
from schemas.document import DocumentIndexTaskData
from services.document_service import submit_document_index_task


@router.post("/{document_id}/index")
async def index_document_api(
    document_id: str,
    db: AsyncSession = Depends(get_database),
):
    result = await submit_document_index_task(
        db,
        document_id=document_id,
    )
    await db.commit()

    return success_response(
        data=DocumentIndexTaskData(**result),
        message="index task submitted",
    )
```

### 为什么这里要明显变薄

router 一旦继续保留：

- 查 document
- 判断状态
- 创建任务
- 投递任务
- 处理状态

那 Day 2 的分层就白做了。

router 的目标不是“什么都不做”，  
而是只做入口层该做的事。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. 同步索引接口和任务提交接口的语义差异是什么？
2. 为什么任务化以后接口不能立即返回 `chunk_count`？
3. `documents.status` 和 `task_records.status` 分别表达什么？
4. 为什么 Day 3 先用最小状态，不直接做完整状态机？
5. 为什么 router 不应该直接调用 Celery task？
6. 为什么要先创建 task_record，再投递任务？
7. 为什么 `infra/task_queue.py` 可以先做占位？
8. Day 4 worker 接管执行时，需要从 Day 3 接住什么？

---

## 今日验收标准

- 索引接口语义已经从“同步索引完成”改为“索引任务已提交”
- 返回结构中包含 `task_id`
- 有最小 `crud/task_record.py` 设计
- 有最小 `DocumentIndexTaskData` 设计
- 有 `submit_document_index_task(...)` 的 service 入口设计
- 有 `enqueue_index_document_task(...)` 的任务投递入口设计
- `routers/documents.py` 的索引接口思路已经明显变薄
- 能讲清楚 Day 4 worker 要接住的参数是 `task_id` 和 `document_id`

---

## 今天最容易踩的坑

### 坑 1：接口仍然同步等待索引完成

问题：

- 表面上加了任务概念
- 实际请求还是等完整索引结束

规避建议：

- Day 3 的接口只返回任务提交结果

### 坑 2：返回结构还沿用 `DocumentIndexData`

问题：

- `chunk_count` 等字段代表索引完成结果
- 任务提交时这些信息还不存在

规避建议：

- 新增 `DocumentIndexTaskData`
- 不混用“提交结果”和“完成结果”

### 坑 3：只有 Celery 任务，没有数据库任务记录

问题：

- 后续状态查询、重试、排查都缺抓手

规避建议：

- 先写 `task_record`
- 再投递后台任务

### 坑 4：service 里偷偷执行完整索引

问题：

- 重任务只是从 router 搬到了 service
- 执行模型没有真正改变

规避建议：

- service 只负责提交任务
- pipeline 和 worker 才负责执行

### 坑 5：Day 3 就把状态机做得过细

问题：

- 提前引入 parsing/chunking/embedding 等复杂状态
- 任务提交链路还没稳定就开始膨胀

规避建议：

- Day 3 先用 `queued / running / completed / failed`
- Day 6 再细化幂等状态机

---

## 给明天的交接提示

明天会进入 Day 4：Worker 接管索引执行。

Day 4 要接住今天留下的两个核心参数：

- `task_id`
- `document_id`

明天真正要做的是：

```text
Celery worker 获取任务
-> 根据 document_id 查文档
-> 更新 task_record.status
-> 调 document_index_pipeline
-> 成功后标记 completed
-> 失败后标记 failed 并记录 error_message
```

只要 Day 3 的任务提交入口清楚，  
Day 4 就可以专注解决“后台任务到底怎么执行索引链路”。
