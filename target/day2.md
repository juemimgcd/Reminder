# Day 2：需求边界 + 数据流 + 数据模型设计

## 今天的总目标

- 把项目的数据流彻底讲清楚
- 把接口清单和数据库草案先定住
- 把 LangChain 在整条链路中的位置讲明白

## 今天结束前，你必须拿到什么

- 一张你自己能讲明白的流程图
- 一份明确的接口清单
- 一份数据库表草案
- 一套不会把“业务模型”和“LangChain 对象”混在一起的理解方式

---

## 抽丝剥茧理解 LangChain：今天最关键的学习部分

## 第 1 层：先忘掉 LangChain，只看业务

你这个系统做的事其实很朴素：

1. 用户上传文件
2. 系统把文件内容读出来
3. 系统把长文本切成小块
4. 系统把文本块变成向量
5. 系统把向量存起来
6. 用户提问
7. 系统先检索相关文本块
8. 系统把文本块连同问题一起交给模型
9. 系统返回答案和引用

这 9 步，就算完全不用 LangChain，你也能手写。

所以第一层结论是：

> LangChain 不是必须先理解的“魔法”，它只是帮你把这 9 步更方便地串起来。

## 第 2 层：LangChain 到底帮了什么

它一般会帮你处理这些环节：

- 文档加载
- 文本切分
- embedding 调用封装
- 向量库接入
- retriever 抽象
- prompt 和链路组织

白话理解：

如果你自己手写，就像自己搭水管；  
用 LangChain，就像拿到一套已经做好的管件和接头。

## 第 3 层：最容易混淆的两个 `Document`

### 业务数据库里的 `Document`

这是你项目中的“文档记录”。

它关心的是：

- 这个文件是谁上传的
- 文件名是什么
- 路径在哪
- 当前状态是什么
- 有没有完成索引

它通常会落到数据库里，比如 `documents` 表。

### LangChain 里的 `Document`

这是“处理文本时的内存对象”。

它关心的是：

- 文本正文是什么
- 来源元信息是什么

白话理解：

- 业务 `Document`：像仓库管理员手里的“入库登记表”
- LangChain `Document`：像你读文件后手里拿到的“正文卡片”

这两个名字一样，但角色完全不同。

### 记住这个铁律

> 数据库里的 `Document` 管“文件记录”，LangChain 的 `Document` 管“文本内容”。

只要这句不混，后面你会轻松很多。

## 第 4 层：今天到底要不要深学 LangChain API

今天不用急着背 API 名字。  
今天更重要的是知道它会出现在流程的哪些位置。

你今天学 LangChain，目标不是“会写炫技代码”，而是：

- 知道它为什么要出现
- 知道它跟你自己业务代码的边界
- 知道什么时候该用它，什么时候先别用它

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把完整数据流画出来

### 今天推荐你画成这条主链路

```text
用户上传文件
-> 后端保存原始文件
-> 数据库写入 document 记录
-> 解析文件正文
-> 切分 chunk
-> chunk 向量化
-> 向量入库
-> 用户发起提问
-> 检索相关 chunk
-> 模型生成答案
-> 返回答案 + sources
```

### 你今天必须能说清楚每一步的输入和输出

例如：

- 上传接口输入：文件
- 上传接口输出：`document_id`
- 解析步骤输入：原始文件路径
- 解析步骤输出：纯文本或文档对象
- 切分步骤输入：长文本
- 切分步骤输出：多个 chunk
- 检索步骤输入：问题
- 检索步骤输出：若干相关 chunk

### 老师提醒

如果你某一步说不清输入输出，那后面代码一定会写乱。

---

## 09:50 - 10:40：确定文档类型边界

### 推荐你第一阶段只支持这些类型

- `pdf`
- `txt`
- `md`

### 为什么先不急着加更多类型

- `docx` 可以加，但会增加解析分支
- `xlsx`、图片 OCR、网页抓取都会让 Day 4 以后变复杂

现在最关键的是先打通主链路，不是先把所有文件类型都支持掉。

### 今天要写下来的结论

- 支持的文档类型
- 每种类型后续准备怎么解析
- 不支持类型返回什么错误信息

---

## 10:40 - 11:30：设计数据库草案

### 你今天至少要定下这 4 张表

- `documents`
- `chunks`
- `chat_sessions`
- `task_records`

### 推荐字段草案

#### `documents`

| 字段 | 作用 | 白话解释 |
| --- | --- | --- |
| `id` | 文档主键 | 这份文档在系统里的唯一身份证 |
| `knowledge_base_id` | 所属知识库 | 先留字段，后面支持多知识库时会用上 |
| `file_name` | 原始文件名 | 给用户看，方便识别 |
| `file_path` | 存储路径 | 程序后续靠它去读文件 |
| `file_type` | 文件类型 | 比如 `pdf`、`md` |
| `file_size` | 文件大小 | 做校验和排查都好用 |
| `status` | 当前状态 | 如 `uploaded`、`indexing`、`indexed`、`failed` |
| `created_at` | 创建时间 | 记录什么时候上传 |
| `updated_at` | 更新时间 | 排查状态变化用 |

#### `chunks`

| 字段 | 作用 | 白话解释 |
| --- | --- | --- |
| `id` | chunk 主键 | 每个文本块自己的身份证 |
| `document_id` | 所属文档 | 表示它是从哪份文档切出来的 |
| `chunk_index` | 顺序号 | 方便追踪切分位置 |
| `content` | 文本内容 | 真正会被检索的文本 |
| `page_no` | 页码 | PDF 场景下方便引用 |
| `start_offset` | 起始位置 | 后续做定位更方便 |
| `end_offset` | 结束位置 | 和起始位置配套 |
| `created_at` | 创建时间 | 保持记录完整 |

#### `chat_sessions`

| 字段 | 作用 | 白话解释 |
| --- | --- | --- |
| `id` | 会话主键 | 一轮或多轮问答的归属 ID |
| `knowledge_base_id` | 所属知识库 | 这轮会话是基于哪个知识库问的 |
| `title` | 会话标题 | 可以先留空，后面自动生成也行 |
| `created_at` | 创建时间 | 方便查历史 |

#### `task_records`

| 字段 | 作用 | 白话解释 |
| --- | --- | --- |
| `id` | 任务主键 | 后续异步索引会用 |
| `task_type` | 任务类型 | 比如 `index_document` |
| `target_id` | 任务对象 ID | 表示这条任务是给谁干活 |
| `status` | 任务状态 | `pending`、`running`、`success`、`failed` |
| `error_message` | 错误信息 | 失败时排查用 |
| `created_at` | 创建时间 | 保持可追踪 |
| `updated_at` | 更新时间 | 记录状态变更 |

---

## 11:30 - 12:00：把接口清单定死

### 你今天要确认的接口

- `POST /kb/documents/upload`
- `POST /kb/documents/{document_id}/index`
- `GET /kb/documents`
- `GET /kb/documents/{document_id}`
- `DELETE /kb/documents/{document_id}`
- `POST /kb/chat/query`
- `GET /kb/chat/history/{session_id}`
- `GET /health`

### 今天先别做的接口

- 批量上传
- 批量删除
- 多用户权限接口
- 前端页面接口

这些东西现在都不是主线。

---

## 下午编码：14:00 - 18:00

## 14:00 - 15:00：把 Day 2 的“设计结果”固化到文件里

### 建议新增或补充的文件

- `models/base.py`
  - 放通用 `Base`，顺手把公共时间字段抽出来
- `alembic/`
  - 放数据库迁移脚本
- `alembic.ini`
  - Alembic 配置文件
- `schemas/document.py`
  - 写上传响应、文档列表项、文档详情响应
- `schemas/chat.py`
  - 先把问答请求和响应结构占好位置
- `models/document.py`
  - 写 `Document` ORM 草稿
- `models/chunk.py`
  - 写 `Chunk` ORM 草稿
- `models/chat_session.py`
  - 写 `ChatSession` ORM 草稿
- `models/task_record.py`
  - 写 `TaskRecord` ORM 草稿
- `conf/database.py`
  - 初始化异步数据库连接和依赖

### 今天不要只“想结构”，要把代码骨架真写出来

下面这组代码不是最终成品，但非常适合 Day 2。  
它的作用是：先把数据库连接、ORM 模型、Pydantic 模型占好坑。

这一版我按你 [news.py](/e:/python_files/review_backend/models/news.py) 的风格来写，也就是：

- 用 `Mapped[...]`
- 用 `mapped_column(...)`
- 用 `DeclarativeBase`
- 需要索引时用 `__table_args__`
- 查询层按异步 `AsyncSession` 来设计

你要先记住一个很重要的结论：

> 模型类的“写法风格”和“是否异步”不是一回事。

也就是说：

- `Mapped + mapped_column` 是 SQLAlchemy 2.0 的现代模型写法
- `AsyncSession + create_async_engine` 是数据库连接和查询执行方式

这两套东西经常一起出现，但它们管的不是同一个层面。

### 这次我们直接走正式路线：不用 `create_all()`，改用 Alembic

这个决定是对的，而且很像真实项目。

你可以把两者区别先记成一句大白话：

- `create_all()`：像“程序启动时顺手把表拍出来”
- Alembic：像“数据库结构变化有正式记录、有版本号、有回滚能力”

为什么你这个项目更适合 Alembic：

- 后面字段一定会改
- 索引一定可能会补
- 异步任务表、chunk 表以后大概率会继续演化
- 你需要的是“可追踪的数据库变更”，不是“能跑就行”

### 先把目录补齐

```powershell
New-Item -ItemType Directory models,crud,docs -Force
New-Item -ItemType File models/__init__.py,models/base.py,models/document.py,models/chunk.py,models/chat_session.py,models/task_record.py -Force
New-Item -ItemType File schemas/document.py,schemas/chat.py,conf/database.py,docs/flow.md -Force
```

Alembic 目录不要手搓，直接用命令初始化：

```powershell
pip install alembic
alembic init -t async alembic
```

这里的 `-t async` 很关键。  
因为你项目运行时本来就是异步 SQLAlchemy，Alembic 也应该按异步模板来生成。

### 先在 `conf/config.py` 里补数据库地址

如果你想本地先轻量跑通，异步 SQLite 就够了：

```python
DATABASE_URL = "sqlite+aiosqlite:///./agentic_rag.db"
```

如果你已经在用 PostgreSQL，那就换成：

```python
DATABASE_URL = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/agentic_rag"
```

### `conf/database.py`

这里改成异步版，风格尽量贴近你自己的项目。

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from conf.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

这段代码你要看懂 4 个名字：

- `engine`：数据库引擎，像是“数据库连接总开关”
- `AsyncSessionLocal`：异步数据库会话工厂
- `get_database()`：FastAPI 里常见的依赖注入写法，后面接口会用它拿异步数据库会话

### `alembic/env.py`

这一段是 Alembic 的关键接线位。  
它的作用只有一句话：

> 告诉 Alembic：数据库地址在哪里，模型元数据在哪里。

你可以先按下面这个版本改：

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from conf.config import settings
from models.base import Base
import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 这里把项目里的数据库地址塞给 Alembic。
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# autogenerate 会根据这里的 metadata 去比对模型和数据库差异。
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 为什么 `import models` 在 Alembic 里也很重要

因为 Alembic 的 `autogenerate` 只能识别“已经被 Python 导入进来的模型”。  
如果你只写了模型文件，但 `env.py` 里根本没导入它们，Alembic 很可能看不到你的表。

### Alembic 的工作顺序，你现在就要记牢

1. 先写模型
2. 再生成迁移脚本
3. 再执行迁移
4. 不要反过来让应用启动时偷偷建表

### 第一次迁移，你可以直接这样做

```powershell
alembic revision --autogenerate -m "init agentic rag tables"
alembic upgrade head
```

这两条命令的意思非常朴素：

- `revision --autogenerate`：根据模型变化自动生成一版迁移脚本
- `upgrade head`：把数据库升级到最新版本

### `models/base.py`

这一步很像你自己的项目做法。  
把公共时间字段抽到基类里，后面每个模型都不用重复写。

```python
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
```

这里你会发现，它和你 [base.py](/e:/python_files/review_backend/models/base.py) 的思路是一样的：

- 所有表共用的字段，往 `Base` 里提
- 各业务模型只写自己的业务字段
- 这样代码更整洁，也更不容易漏字段

### `models/document.py`

```python
from typing import Optional

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_knowledge_base_id", "knowledge_base_id"),
        Index("idx_documents_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="文档ID")
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="所属知识库ID",
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="文件类型")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="文件大小，单位字节")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        comment="文档状态",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, file_name='{self.file_name}', status='{self.status}')>"
```

这里最关键的是理解：

- 这张表保存的是“文档登记信息”
- 它不是用来保存正文全文的
- 正文切分后的内容，以后会去 `chunks` 表和向量库

### `models/chunk.py`

```python
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="Chunk ID")
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id"),
        nullable=False,
        comment="所属文档ID",
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="Chunk 顺序号")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="文本块内容")
    page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页码")
    start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="起始偏移量")
    end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="结束偏移量")

    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
```

### `models/chat_session.py`

```python
from typing import Optional

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_knowledge_base_id", "knowledge_base_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="会话ID")
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="所属知识库ID",
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="会话标题")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, knowledge_base_id={self.knowledge_base_id})>"
```

### `models/task_record.py`

```python
from typing import Optional

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class TaskRecord(Base):
    __tablename__ = "task_records"
    __table_args__ = (
        Index("idx_task_records_target_id", "target_id"),
        Index("idx_task_records_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="任务ID")
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务类型")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="目标对象ID")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="任务状态",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    def __repr__(self) -> str:
        return f"<TaskRecord(id={self.id}, task_type='{self.task_type}', status='{self.status}')>"
```

### `models/__init__.py`

这个文件的作用，是把模型统一导入，后面初始化数据库时会方便很多。

```python
from models.base import Base
from models.chat_session import ChatSession
from models.chunk import Chunk
from models.document import Document
from models.task_record import TaskRecord

__all__ = ["Base", "Document", "Chunk", "ChatSession", "TaskRecord"]
```

### `schemas/document.py`

这里开始出现 Pydantic 模型。  
它和数据库 ORM 模型的区别要记牢：

- ORM 模型给数据库用
- Pydantic 模型给接口收参与返回用

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadData(BaseModel):
    document_id: str = Field(..., description="上传成功后返回的文档 ID")
    file_name: str
    status: str


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_type: str
    status: str
    created_at: datetime


class DocumentDetailItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str | None = None
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime
```

### `schemas/chat.py`

虽然 Day 2 还不做聊天接口，但 schema 先占住位置，后面会轻松很多。

```python
from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    question: str = Field(..., description="用户输入的问题")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    top_k: int = Field(default=4, ge=1, le=10, description="检索返回的片段数量")
    session_id: str | None = Field(default=None, description="可选，会话 ID")


class ChatSourceItem(BaseModel):
    document_id: str
    chunk_id: str
    text: str


class ChatQueryData(BaseModel):
    answer: str
    sources: list[ChatSourceItem]
```

### Day 2 结束前，`main.py` 临时补成这样

你今天还不做完整业务接口，但不要在应用启动时建表。  
建表这件事，交给 Alembic。

```python
from fastapi import FastAPI

from conf.config import settings
from routers.health import router as health_router
from utils.response import success_response

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)


@app.get("/")
def root():
    return success_response(
        data={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
        message="welcome to agentic rag assistant",
    )


app.include_router(health_router)
```

### 为什么 `main.py` 里这次反而不要出现数据库建表逻辑

因为数据库结构属于“迁移职责”，不是“应用启动职责”。

你后面应该形成这样的习惯：

- 改模型
- 生成 migration
- 执行 migration
- 启动服务

而不是：

- 改模型
- 启动服务
- 指望 `create_all()` 帮你偷偷补结构

前者像工程项目，后者更像学习 demo。

### 为什么 Day 2 就建议写模型草稿

因为很多设计问题，只有落成字段后你才会发现：

- 这个状态值放哪里
- 这个接口到底返回什么
- 这个字段是不是缺了

不要把“设计”理解成纯画图。  
好的设计应该能快速落到代码骨架上。

---

## 15:00 - 16:00：把流程图写到仓库里

### 推荐做法

在项目里加一个文档文件，例如：

- `docs/flow.md`
- 或者直接补到 `README.md`

### 推荐用 Mermaid 画图

```mermaid
flowchart TD
    A[上传文件] --> B[保存原始文件]
    B --> C[写入 documents 表]
    C --> D[解析文件]
    D --> E[切分 chunks]
    E --> F[向量化]
    F --> G[写入向量库]
    H[用户提问] --> I[Retriever 检索]
    I --> J[拼接上下文]
    J --> K[LLM 生成答案]
    K --> L[返回 answer 和 sources]
```

### `docs/flow.md` 你可以直接这样写

````md
# Agentic RAG 数据流

```mermaid
flowchart TD
    A[上传文件] --> B[保存原始文件]
    B --> C[写入 documents 表]
    C --> D[解析文件]
    D --> E[切分 chunks]
    E --> F[向量化]
    F --> G[写入向量库]
    H[用户提问] --> I[Retriever 检索]
    I --> J[拼接上下文]
    J --> K[LLM 生成答案]
    K --> L[返回 answer 和 sources]
```
````

### 为什么要把图写到仓库里

不是为了好看，是为了后面你自己、面试官、协作者都能快速理解系统结构。

---

## 16:00 - 17:00：把业务模型和 LangChain 模型彻底隔开

### 今天最值得你写在笔记里的结论

- `models/document.py` 是数据库实体
- LangChain `Document` 是文本处理中间对象

### 建议你在将来相关代码里写这样的注释

```python
# 这里的 Document 指数据库里的文档记录，负责保存文件元数据和状态。
# 后续解析文件正文时，还会出现 LangChain 的 Document 对象，两者不是一个东西。
```

### 抽丝剥茧地看一眼 LangChain 的 `Document`

你还没学过 LangChain，所以这里我只给你看“样子”和“用途”，不要求你今天就全会。

```python
from langchain_core.documents import Document as LCDocument


lc_doc = LCDocument(
    page_content="这是一段从 pdf 里抽出来的正文内容",
    metadata={
        "document_id": "doc_001",
        "source": "rag_intro.pdf",
        "page": 1,
    },
)
```

现在你只要看懂两件事：

- `page_content`：正文内容本身
- `metadata`：和正文绑定的辅助信息

把它和数据库里的 `Document` 对比一下：

- 数据库 `Document`：管文件记录
- LangChain `LCDocument`：管文本内容

### 再往前走半步，看看 LangChain 未来会怎么切分文本

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)

chunks = splitter.split_documents([lc_doc])
```

现在先别怕这 3 行。

你可以这样理解：

- `chunk_size=500`：每块尽量 500 个字符左右
- `chunk_overlap=100`：相邻块之间重叠 100 个字符，防止上下文断掉
- `split_documents([lc_doc])`：把一个长文本对象切成多个小文本对象

这就是 LangChain 最朴素、最实用的一面。  
它不是魔法，它是在帮你做“重复而标准化的文本处理”。

这句注释非常有价值，因为它能帮未来的你避免“同名概念打架”。

### 你现在就该形成的编码习惯

- 数据库模型叫“文档记录”
- 文本处理中间对象叫“文本对象”或“LC Document”

哪怕只是你自己在心里这样区分，后面也会清爽很多。

---

## 17:00 - 18:00：给 Day 3 的上传接口打地基

### 你今天要提前想清楚的事

- 上传接口返回什么
- 文档状态初始值是什么
- 文件路径准备怎么命名
- 允许上传哪些后缀
- 文件过大时怎么报错

### 推荐的上传后状态

- 文件刚保存成功：`uploaded`
- 文件开始索引：`indexing`
- 索引完成：`indexed`
- 索引失败：`failed`

### 为什么状态字段这么重要

因为后面你一定会遇到这种情况：

- 用户上传了，但还没索引完
- 用户重复点了建立索引
- 某个文档解析失败了

如果你没有状态字段，很多行为就会变得说不清。

### 今天结束前，你可以顺手做一次小验证

先生成并执行迁移：

```powershell
alembic revision --autogenerate -m "init agentic rag tables"
alembic upgrade head
```

然后确认两件事：

- Alembic 没有报 `target_metadata is None` 之类的错误
- 如果你用的是 `sqlite+aiosqlite`，项目根目录下会出现 `agentic_rag.db`

再启动服务：

```powershell
uvicorn main:app --reload
```

这说明 Day 2 的数据库骨架已经真正落地了，而且走的是正式迁移流程。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己说顺的 6 句话

1. 上传接口和索引接口为什么要分开？
2. 为什么先只支持 `pdf`、`txt`、`md`？
3. `documents` 表和 `chunks` 表各自负责什么？
4. 为什么需要 `task_records`？
5. 业务 `Document` 和 LangChain `Document` 的区别是什么？
6. LangChain 在这条链路里帮的是哪几类工作？

### 如果你能把这 6 句话说明白

那 Day 2 就真的学进去了，不是“看过了”。

---

## 今日验收标准

- 你能画出完整数据流
- 你能讲清每一步输入和输出
- 接口清单已经确定
- 数据表草案已经写下
- 你已经区分清楚业务 `Document` 和 LangChain `Document`

---

## 今天最容易踩的坑

### 坑 1：文档类型一开始支持太多

问题：

- 解析分支变多
- 调试成本暴增

规避建议：

- 第一阶段只做 `pdf`、`txt`、`md`

### 坑 2：把“上传”和“索引”绑死在一个接口里

问题：

- 接口会变慢
- 错误处理复杂
- 后面做异步任务很难拆

规避建议：

- 上传负责接文件和存记录
- 索引负责重处理任务

### 坑 3：把数据库模型和 LangChain 概念混在一起

问题：

- 命名混乱
- 代码职责混乱

规避建议：

- 先从脑子里区分清楚“文件记录”和“文本对象”

### 坑 4：今天只画图，不落字段

问题：

- 设计看起来很顺
- 一写代码才发现大量细节没想过

规避建议：

- 今天一定要把核心表字段写出来

---

## 给明天的交接提示

明天会进入真正的后端入口：文档上传。  
你会第一次遇到一个很重要的工程分层问题：

- FastAPI 的 `UploadFile` 负责“接住文件”
- 你的业务代码负责“保存文件、写数据库记录”
- LangChain 相关处理要等到“解析正文”阶段再出场

换句话说，明天你会开始明白：

> 上传文件，不等于已经进入 RAG。
