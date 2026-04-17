# Day 4：Worker 接管索引执行

## 今天的总目标

- 让 Celery worker 真正接住 Day 3 提交的索引任务
- 把文档解析、切分、入库、向量写入移到后台执行
- 打通 `task_id + document_id -> worker -> pipeline` 这条链
- 建立任务成功、失败、异常记录的最小闭环
- 为 Day 5 的批处理和 Day 6 的幂等状态机准备稳定执行入口

## 今天结束前，你必须拿到什么

- `infra/celery_app.py`
- `tasks/index_tasks.py`
- `crud/task_record.py` 的状态更新能力
- 一个 worker 可调用的 `run_document_index_pipeline(...)` 入口
- 一套任务成功 / 失败的最小状态更新逻辑
- 一份你自己能讲清楚的 “Celery task 怎么调用 async pipeline” 认知

---

## 今天开始，真正的重活要离开 API 了

Day 3 已经把索引接口改成了：

```text
提交任务
-> 返回 task_id
```

但如果 Day 4 不接住这个任务，  
那 Day 3 只是“接口长得像异步”，并没有真正变成任务化后端。

所以 Day 4 的核心不是再改 router，  
而是要回答这个问题：

> 谁来真正执行索引链路？

今天的答案是：

```text
Celery worker
```

也就是说，后面文档索引的主执行流应该变成：

```text
API 提交任务
-> Redis broker 接住消息
-> Celery worker 消费任务
-> worker 调 pipeline
-> pipeline 执行解析 / 切分 / 入库 / 向量写入
-> task_record 更新结果
```

从今天开始，Mneme 才真正开始从“同步原型”走向“后台任务化后端”。

---

## 第 1 层：今天到底比 Day 3 多了什么

Day 3 的重点是：

```text
接口返回 task_id
```

Day 4 的重点是：

```text
task_id 对应的任务真的被 worker 执行
```

你可以把两天的区别理解成：

- Day 3：建立任务提交入口
- Day 4：建立任务执行入口

### Day 3 的终点

```text
router
-> submit_document_index_task(...)
-> enqueue_index_document_task(...)
-> return task_id
```

### Day 4 的起点

```text
Celery worker
-> index_document_task(task_id, document_id)
-> run async pipeline
-> update task status
```

这两个部分必须拼在一起，  
任务化才算真的成立。

---

## 第 2 层：为什么 worker 不能只是“再包一层函数”

很多人第一次做 Celery，会把它理解成：

- 原来的函数继续保留
- 再写一个 Celery task 调这个函数

这样理解只对一半。

今天你要真正理解的是：

### worker 不是 HTTP 入口

worker 不负责：

- 解析 HTTP 参数
- 返回 HTTP 响应
- 处理用户表单
- 直接依赖 FastAPI 的 request 生命周期

worker 只负责：

- 消费任务参数
- 执行业务 pipeline
- 更新任务状态
- 记录成功或失败

### worker 也不是业务服务层

worker 不应该自己重新实现：

- 文档是否可索引的业务规则
- router 层校验逻辑
- 返回结构的 HTTP 语义

worker 更像：

> 一个后台执行壳子，它负责把任务参数转成对 pipeline 的调用。

---

## 第 3 层：今天真正的数据流是什么

Day 4 这条链路你要非常清楚：

```text
POST /kb/documents/{document_id}/index
-> 创建 task_record(status=queued)
-> enqueue task
-> Celery worker 收到 task_id + document_id
-> task_record.status = running
-> document.status = indexing
-> run_document_index_pipeline(...)
-> 成功后 task_record.status = completed
-> document.status = indexed
-> 失败后 task_record.status = failed
-> document.status = failed
```

这里最重要的两个参数是：

- `task_id`
- `document_id`

以后你看任何 worker 日志，  
优先抓这两个标识。

---

## 第 4 层：为什么今天必须讲清 async 和 Celery 的关系

当前项目的很多主链路是异步的：

- SQLAlchemy `AsyncSession`
- `load_langchain_documents(...)`
- `split_documents(...)`
- `run_document_index_pipeline(...)`

但 Celery 默认的 task 函数通常是同步函数。

这意味着 Day 4 会遇到一个非常关键的问题：

> 同步 Celery task，怎么调用 async pipeline？

### 最简单可落地的方式

先用：

```python
asyncio.run(...)
```

也就是：

```text
Celery 同步任务
-> asyncio.run(run_index_document_task_async(...))
-> 在 async 函数里拿 AsyncSession
-> 调 pipeline
```

### 为什么 Day 4 先用这个方案

因为当前仓库已经是 async ORM + async pipeline。

如果 Day 4 一上来就为了 Celery 改成全同步，  
改动会非常大。

所以今天最务实的做法是：

- Celery task 保持同步入口
- 真实索引逻辑继续放在 async runner 里

---

## 第 5 层：今天先把 Celery 的职责讲明白

Celery 今天只需要承担这些职责：

- 从 Redis broker 消费任务
- 把 `task_id`、`document_id` 交给 task 函数
- 把任务路由到 worker
- 作为后台执行入口

它今天还不需要承担完整高级功能：

- 不急着做复杂 queue 路由
- 不急着做 task chain
- 不急着做 chord / group
- 不急着做 retry policy 细化
- 不急着做 result backend 深度治理

Day 4 的目标只有一个：

> 让 worker 接住索引任务，并把 pipeline 跑起来。

---

## 第 6 层：今天最小需要哪些文件

今天建议围绕这几个文件展开：

- `requirements.txt`
- `conf/config.py`
- `infra/celery_app.py`
- `infra/task_queue.py`
- `tasks/index_tasks.py`
- `crud/task_record.py`
- `pipelines/document_index_pipeline.py`
- `docker-compose.yml`

### 每个文件今天的职责

| 文件 | 今天负责什么 |
|---|---|
| `requirements.txt` | 加入 Celery / Redis 依赖 |
| `conf/config.py` | 提供 broker / backend 配置 |
| `infra/celery_app.py` | 创建 Celery app |
| `infra/task_queue.py` | 真正调用 Celery task.delay(...) |
| `tasks/index_tasks.py` | worker 任务入口 |
| `crud/task_record.py` | 更新任务状态和错误信息 |
| `pipelines/document_index_pipeline.py` | 被 worker 调用的索引主流程 |
| `docker-compose.yml` | 加 Redis 和 worker 服务 |

---

## 第 7 层：今天不要做什么

Day 4 不建议做：

- 不细化到 `parsing / chunking / embedding / vector_upserting`
- 不做 batch embedding
- 不做对象缓存
- 不做 retry / rate limit / circuit breaker
- 不做 context 治理
- 不做 memory pipeline
- 不做 MCP

今天只做：

> worker 真正执行索引链路，并能正确写成功 / 失败状态。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 4 的主链路讲顺

### 今天你要能顺着说出来

```text
Day 3 把索引接口改成提交任务
-> Day 4 引入 Celery worker
-> worker 根据 task_id 和 document_id 执行索引
-> pipeline 完成解析 / 切分 / 入库 / 向量写入
-> task_record 和 document 状态被更新
```

### 你必须能回答这两个问题

1. 为什么 Day 4 的主角不是 router，而是 worker？
2. 为什么 Celery task 不应该直接把业务逻辑重新写一遍？

---

## 09:50 - 10:40：理解 Celery 同步 task 和 async pipeline 的桥接

### 今天你先记住这个结构

```text
index_document_task(...)
-> asyncio.run(run_index_document_task_async(...))
-> AsyncSessionLocal()
-> run_document_index_pipeline(...)
```

### 为什么这个结构适合当前项目

因为当前项目的数据库和索引链路已经明显是 async 风格。

如果你今天强行把它们改造成同步：

- 改动面会很大
- 很多现有函数都要重写
- Day 4 的重点就会跑偏

所以今天最合理的策略是：

- 保持 Celery task 作为同步外壳
- 让真实执行逻辑继续运行在 async runner 里

---

## 10:40 - 11:30：把成功和失败的状态流讲明白

### 成功路径

```text
queued
-> running
-> completed
```

对应文档状态：

```text
queued
-> indexing
-> indexed
```

### 失败路径

```text
queued
-> running
-> failed
```

对应文档状态：

```text
queued
-> indexing
-> failed
```

### 今天先做到什么程度

Day 4 先做到：

- 任务开始时设 `running`
- 任务成功时设 `completed`
- 任务失败时设 `failed`
- 失败时落 `error_message`

这已经足够支撑后续 Day 5 和 Day 6。

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 4 最直接的验收方式

今天最少要验证这几件事：

1. worker 能启动
2. 任务能被投递到 Celery
3. task 收到 `task_id` 和 `document_id`
4. task 能把 `task_record.status` 改成 `running`
5. pipeline 成功后能改成 `completed`
6. 抛异常时能改成 `failed`

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:30：先补依赖和配置

### 推荐补充依赖

当前 `requirements.txt` 里还没有 Celery / Redis 相关依赖。

今天建议补：

- `celery`
- `redis`

### `requirements.txt` 建议新增

```text
celery==5.5.3
redis==6.2.0
```

### `conf/config.py` 建议新增

```python
CELERY_BROKER_URL: str = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
CELERY_INDEX_QUEUE: str = "document_index"
```

### 为什么 Day 4 先只加这 3 个配置

因为今天最重要的是：

- broker 能连上
- backend 可选可用
- 队列名稳定

不要一上来把 Celery 所有配置都塞进 settings。

---

## 14:30 - 15:20：实现 `infra/celery_app.py`

### 建议新建

- `infra/celery_app.py`

### `infra/celery_app.py` 练手骨架版

```python
from celery import Celery


def build_celery_app() -> Celery:
    # 你要做的事：
    # 1. 读取 broker / backend
    # 2. 创建 Celery app
    # 3. 配置默认队列
    # 4. 自动发现 tasks
    raise NotImplementedError("先自己实现 build_celery_app")


celery_app = build_celery_app()
```

### `infra/celery_app.py` 参考答案

```python
from celery import Celery

from conf.config import settings


def build_celery_app() -> Celery:
    app = Celery(
        "mneme",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    app.conf.update(
        task_default_queue=settings.CELERY_INDEX_QUEUE,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Shanghai",
        enable_utc=False,
    )
    app.autodiscover_tasks(["tasks"])
    return app


celery_app = build_celery_app()
```

### 这一段你一定要看懂

`celery_app.py` 的职责不是执行业务逻辑，  
它只是把 worker 运行时所需的 Celery app 建起来。

---

## 15:20 - 16:10：把 `infra/task_queue.py` 从占位版改成真实投递

### 当前 Day 3 的占位思路

Day 3 里 `enqueue_index_document_task(...)` 只是记一条日志。

Day 4 开始，它应该真的投递 Celery 任务。

### `infra/task_queue.py` 练手骨架版

```python
def enqueue_index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    # 你要做的事：
    # 1. 导入 Celery task
    # 2. 调用 delay 或 apply_async
    # 3. 传入 task_id 和 document_id
    raise NotImplementedError("先自己实现 enqueue_index_document_task")
```

### `infra/task_queue.py` 参考答案

```python
from tasks.index_tasks import index_document_task


def enqueue_index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    index_document_task.apply_async(
        kwargs={
            "task_id": task_id,
            "document_id": document_id,
        }
    )
```

### 为什么这里推荐 `apply_async`

因为后面你更容易扩展：

- 指定 queue
- 指定 countdown
- 指定 retry policy
- 指定 headers

Day 4 虽然不一定马上用到，  
但 `apply_async(...)` 比单纯 `delay(...)` 更像工程化入口。

---

## 16:10 - 17:00：实现 `tasks/index_tasks.py`

### 建议新建

- `tasks/index_tasks.py`

### 今天建议拆成两层

第一层：Celery task，同步入口  
第二层：async runner，真正执行业务

### `tasks/index_tasks.py` 练手骨架版

```python
import asyncio

from infra.celery_app import celery_app


@celery_app.task(name="tasks.index_document_task")
def index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    # 你要做的事：
    # 1. 用 asyncio.run(...) 调 async runner
    # 2. 把 task_id / document_id 传进去
    raise NotImplementedError("先自己实现 index_document_task")


async def run_index_document_task_async(
    *,
    task_id: str,
    document_id: str,
) -> None:
    # 你要做的事：
    # 1. 创建 AsyncSession
    # 2. 把 task_record.status 改成 running
    # 3. 把 document.status 改成 indexing
    # 4. 查询 document
    # 5. 调 run_document_index_pipeline(...)
    # 6. 成功时标记 completed
    # 7. 失败时标记 failed 和 error_message
    raise NotImplementedError("先自己实现 run_index_document_task_async")
```

### `tasks/index_tasks.py` 参考答案

```python
import asyncio

from conf.database import AsyncSessionLocal
from crud.document import get_document_by_id, update_document_status
from crud.task_record import update_task_record_status
from infra.celery_app import celery_app
from pipelines.document_index_pipeline import run_document_index_pipeline


@celery_app.task(name="tasks.index_document_task")
def index_document_task(
    *,
    task_id: str,
    document_id: str,
) -> None:
    asyncio.run(
        run_index_document_task_async(
            task_id=task_id,
            document_id=document_id,
        )
    )


async def run_index_document_task_async(
    *,
    task_id: str,
    document_id: str,
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await update_task_record_status(
                db,
                task_id=task_id,
                status="running",
            )
            await update_document_status(
                db,
                document_id=document_id,
                status="indexing",
            )

            document = await get_document_by_id(db, document_id=document_id)
            if not document:
                raise ValueError(f"document not found: {document_id}")

            await run_document_index_pipeline(
                db,
                document=document,
            )

            await update_task_record_status(
                db,
                task_id=task_id,
                status="completed",
            )
            await db.commit()
        except Exception as exc:
            await update_task_record_status(
                db,
                task_id=task_id,
                status="failed",
                error_message=str(exc),
            )
            await update_document_status(
                db,
                document_id=document_id,
                status="failed",
            )
            await db.commit()
            raise
```

### 这里有 4 个特别容易忽略的点

#### 点 1：worker 自己要管理数据库会话

FastAPI 的 `Depends(get_database)` 只在 HTTP 请求里生效。  
Celery worker 没有这个依赖注入环境。

所以 task 里要自己拿：

```python
AsyncSessionLocal()
```

#### 点 2：task 入口和 async runner 要分开

这样做的好处是：

- Celery 层更薄
- async 逻辑更集中
- 以后测试 async runner 更方便

#### 点 3：异常时别忘了写回数据库

如果只 `raise`，  
数据库里可能看不到失败状态和错误信息。

worker 任务最怕这种“实际失败了，但数据库还像没事一样”。

#### 点 4：pipeline 不负责 task_record

pipeline 负责索引链路本身。

task_record 的更新更适合放在 worker task 层，  
因为这是“任务执行语义”，不是“业务流程语义”。

---

## 17:00 - 17:30：补 `crud/task_record.py` 的状态更新能力

### 今天建议补这个函数

```python
async def update_task_record_status(
    db: AsyncSession,
    *,
    task_id: str,
    status: str,
    error_message: str | None = None,
) -> TaskRecord | None:
    ...
```

### `crud/task_record.py` 参考答案

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.task_record import TaskRecord


async def update_task_record_status(
    db: AsyncSession,
    *,
    task_id: str,
    status: str,
    error_message: str | None = None,
) -> TaskRecord | None:
    result = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.status = status
    if error_message is not None:
        task.error_message = error_message

    await db.flush()
    await db.refresh(task)
    return task
```

### 为什么 Day 4 一定要补这个

因为 Day 3 只有任务创建，  
Day 4 开始任务真的会动起来。

只会创建，不会更新，  
那 `task_records` 这个表就还是摆设。

---

## 17:30 - 18:00：补运行环境

### `docker-compose.yml` 建议新增 `redis`

```yaml
redis:
  image: redis:7
  container_name: mneme-redis
  restart: unless-stopped
  ports:
    - "6379:6379"
```

### `docker-compose.yml` 建议新增 `worker`

```yaml
worker:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: mneme-worker
  restart: unless-stopped
  depends_on:
    - postgres
    - redis
    - milvus
  env_file:
    - .env
  environment:
    DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-123456}@postgres:5432/${POSTGRES_DB:-agentic}
    MILVUS_URI: ${MILVUS_URI:-http://milvus:19530}
    CELERY_BROKER_URL: redis://redis:6379/0
    CELERY_RESULT_BACKEND: redis://redis:6379/1
    PYTHONPATH: /app
  volumes:
    - ./storage:/app/storage
  command: ["celery", "-A", "infra.celery_app:celery_app", "worker", "--loglevel=INFO"]
```

### 为什么 Day 4 就建议把 worker 服务独立出来

因为 worker 和 API 的生命周期不一样：

- API 负责接请求
- worker 负责跑后台任务

这两个进程后面一定会分开。  
Day 4 就先按这个方向设计，会省很多返工。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. Day 3 的任务提交和 Day 4 的任务执行分别解决什么问题？
2. 为什么 worker 不是 HTTP 层，也不是业务服务层？
3. 为什么 Celery task 可以先用 `asyncio.run(...)` 去桥接 async pipeline？
4. 为什么 task 层要自己创建数据库会话？
5. 为什么 task 开始时要把 `task_record.status` 改成 `running`？
6. 为什么失败时要同时更新 `task_record` 和 `document`？
7. 为什么 pipeline 不应该自己负责 `task_record` 状态更新？
8. 为什么 Day 4 先不做复杂状态机和批处理？

---

## 今日验收标准

- 已补 Celery / Redis 依赖和最小配置
- `infra/celery_app.py` 存在且职责清晰
- `infra/task_queue.py` 已从占位投递升级为真实 Celery 投递
- `tasks/index_tasks.py` 能接住 `task_id` 和 `document_id`
- worker 能通过 async runner 调 `run_document_index_pipeline(...)`
- `task_record` 能从 `queued` 更新到 `running / completed / failed`
- `document.status` 能从 `queued` 更新到 `indexing / indexed / failed`
- worker 异常时能把错误信息落回数据库

---

## 今天最容易踩的坑

### 坑 1：Celery task 里直接复制整段索引逻辑

问题：

- task 变成另一个大杂烩
- 和 pipeline 职责冲突

规避建议：

- task 只负责任务执行壳子
- 真正业务流程继续放 pipeline

### 坑 2：直接在 task 里用 `Depends(get_database)`

问题：

- Celery 不是 FastAPI 请求上下文
- 依赖注入不会自动生效

规避建议：

- worker 自己创建 `AsyncSessionLocal()`

### 坑 3：成功路径能跑，失败路径没写数据库

问题：

- worker 实际失败了
- 但数据库还是 `queued` 或 `running`

规避建议：

- `except` 里先更新 `task_record` 和 `document`
- 再 `commit`
- 最后再抛异常

### 坑 4：把 document 状态和 task 状态混成一个概念

问题：

- 一个表达业务对象
- 一个表达任务执行
- 混在一起后面会很乱

规避建议：

- document 看文档可用性
- task_record 看任务执行进度

### 坑 5：Day 4 就急着做复杂 Celery 编排

问题：

- worker 才刚接起来
- 复杂度会过早上升

规避建议：

- 先把单一索引任务跑通
- 后面再做 chain、batch、retry 和并发优化

---

## 给明天的交接提示

明天会进入 Day 5：索引链路批处理。

Day 5 不是再讲怎么让 worker 跑起来，  
而是要开始解决：

```text
一个 worker 跑索引时
-> embedding 和 vector upsert 怎么别一条一条做
-> 怎么开始按 batch 处理
-> 怎么为吞吐和资源利用率做准备
```

所以 Day 4 最关键的交接只有一句话：

```text
worker 已经能接住任务并调用索引 pipeline，接下来要优化的是执行效率，而不是再重新设计执行入口。
```
