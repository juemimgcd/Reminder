# Day 3：文档上传接口落地

## 今天的总目标

- 做出真正能接文件的后端入口
- 保存原始文件或文件元数据
- 建立文档记录表，并返回 `document_id`

## 今天结束前，你必须拿到什么

- `POST /kb/documents/upload`
- `GET /kb/documents` 的雏形
- 上传后的文档记录
- 一套清晰的上传链路认知

---

## 先把一个关键误区纠正掉

## 上传文件，不等于完成 RAG

很多初学者会把这些动作混成一件事：

- 上传文件
- 解析文件
- 切分文本
- 向量化
- 建索引
- 回答问题

实际上，这些应该拆开。

今天你只需要先把“文件进入系统”这一步做好。

白话理解：

- 上传接口像“前台收件”
- 解析和切分像“后台拆包整理”
- 向量化和建索引像“录入知识库”

今天的重点就是把“前台收件流程”做扎实。

---

## 今天和 LangChain 的关系，要这样理解

### 1. 今天的主角不是 LangChain

今天的主角是：

- FastAPI 的上传能力
- 文件保存
- 数据库记录
- 状态管理

### 2. LangChain 什么时候才真正上场

真正开始和 LangChain 强相关，是 Day 4 以后：

- 读取文件正文
- 生成文本对象
- 切分 chunk
- 进入检索链路

### 3. 为什么今天反而要“克制”

因为工程里最常见的错误就是：  
明明还在做上传接口，却提前把解析、切分、embedding 全塞进来。

这样会导致：

- 接口阻塞很久
- 错误难排查
- 分层不清晰

今天你要学会一件成熟工程师很重要的能力：

> 只做今天该做的那一层。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:40：把上传链路完整走一遍

### 今天你要记住的上传流程

```text
客户端上传文件
-> FastAPI 接收到 UploadFile
-> 校验文件类型和大小
-> 生成 document_id
-> 保存原始文件到本地目录
-> 写入 documents 表
-> 返回 document_id 和状态
```

### 你要看懂的每个节点职责

- `UploadFile`
  - 负责接住客户端传来的文件
- 文件校验
  - 防止非法类型和超大文件
- 本地存储
  - 给后面解析文件提供稳定路径
- 数据库记录
  - 给整个系统留下“这份文档存在过”的正式记录

---

## 09:40 - 10:20：理解 `UploadFile` 为什么比 `bytes` 更合适

### 结论先记住

- 小 demo 可以直接用 `bytes`
- 真做文件上传接口，更推荐 `UploadFile`

### 白话解释

`UploadFile` 更像“带文件名、类型、流式读取能力的文件对象”。  
它比直接把整个文件一次性读进内存更稳，更接近真实项目写法。

### 你今天要理解的重点

- 文件上传不是普通 JSON 请求
- 它走的是 `multipart/form-data`
- 因此项目里需要正确的依赖支持

---

## 10:20 - 11:10：设计上传目录和命名规则

### 推荐目录规则

```text
storage/raw/2026/04/03/<document_id>__原文件名.pdf
```

### 为什么不要只用原文件名

因为用户可能上传重名文件。  
如果你直接拿原文件名保存，后上传的文件很容易覆盖先上传的文件。

### 推荐命名思路

- 先生成 `document_id`
- 再拼出唯一文件名
- 文件名里保留一部分原名，方便排查

例如：

```text
doc_20260403_0001__agent_rag_intro.pdf
```

---

## 11:10 - 12:00：想清楚异常和状态

### 今天至少考虑这几类失败

- 不支持的文件类型
- 文件为空
- 文件保存失败
- 数据库写入失败

### 推荐思路

上传链路里要尽量保证“一致性”：

- 文件已经写磁盘，但数据库没写成功怎么办？
- 数据库先写成功，但磁盘保存失败怎么办？

### 简单好用的处理方式

1. 先生成 `document_id`
2. 校验文件
3. 先保存文件
4. 文件保存成功后再写数据库
5. 如果数据库写入失败，补一个清理动作，把刚保存的文件删掉

这不是最复杂的事务方案，但对 Day 3 来说足够实用。

---

## 下午编码：14:00 - 18:00

## 14:00 - 15:00：建立文档表和数据库基础

### 建议落地的文件

- `conf/database.py`
  - 建立数据库连接和会话
- `models/document.py`
  - 定义文档记录表
- `crud/document.py`
  - 封装创建文档、查询文档列表、按 ID 查询

### 这一节开始，数据库代码都按异步版来写

因为你已经明确说了自己用的是异步 SQLAlchemy 引擎，所以这里我统一改成：

- `AsyncSession`
- `async def`
- `await db.execute(...)`
- `select(...)` 风格查询

你会发现，这和你自己项目里的 CRUD 写法是同一路数。

这里再补一句很关键的话：

> Day 3 默认你已经在 Day 2 跑过 Alembic 迁移了，所以接口开发是在“已有表结构”的前提下进行。

也就是说，今天不再讨论 `create_all()`，只讨论“如何正确使用已经迁移好的数据库”。

### 今天你可以先自己练手的数据库与 CRUD 骨架

#### `crud/document.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document


async def create_document(
    db: AsyncSession,
    *,
    document_id: str,
    knowledge_base_id: str | None,
    file_name: str,
    file_path: str,
    file_type: str,
    file_size: int,
    status: str = "uploaded",
) -> Document:
    # 你要做的事：
    # 1. 用传进来的参数创建一个 Document 对象
    # 2. 把对象加入当前数据库会话
    # 3. 调用 flush，让 SQLAlchemy 先把改动同步到数据库
    # 4. 调用 refresh，拿到数据库中的最新对象状态
    # 5. 返回这个 document 对象
    raise NotImplementedError("先自己实现 create_document")


async def list_documents(db: AsyncSession) -> list[Document]:
    # 你要做的事：
    # 1. 写一个 select(Document) 查询
    # 2. 按 created_at 倒序排列，让最新上传的文档排前面
    # 3. 用 await db.execute(sql) 执行查询
    # 4. 把结果转成 Document 列表返回
    raise NotImplementedError("先自己实现 list_documents")


async def get_document_by_id(db: AsyncSession, document_id: str) -> Document | None:
    # 你要做的事：
    # 1. 查询 id 等于 document_id 的那条记录
    # 2. 执行 SQL
    # 3. 如果找到就返回 Document，如果找不到就返回 None
    raise NotImplementedError("先自己实现 get_document_by_id")
```

### `crud/document.py` 参考答案

你先自己写完，再往下对照。

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document


async def create_document(
    db: AsyncSession,
    *,
    document_id: str,
    knowledge_base_id: str | None,
    file_name: str,
    file_path: str,
    file_type: str,
    file_size: int,
    status: str = "uploaded",
) -> Document:
    document = Document(
        id=document_id,
        knowledge_base_id=knowledge_base_id,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        status=status,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession) -> list[Document]:
    sql = select(Document).order_by(Document.created_at.desc())
    result = await db.execute(sql)
    return result.scalars().all()


async def get_document_by_id(db: AsyncSession, document_id: str) -> Document | None:
    sql = select(Document).where(Document.id == document_id)
    result = await db.execute(sql)
    return result.scalar_one_or_none()
```

这段 CRUD 代码你要学会看 3 个动作：

- `add()`：把对象放进本次数据库会话
- `flush()`：把改动先推送到数据库，让对象拿到最新数据库状态
- `refresh()`：把数据库最新状态重新刷回 Python 对象

### 为什么这里没有手写 `await db.commit()`

因为我们在 Day 2 的 `get_database()` 里，已经统一做了：

- 成功时自动提交
- 出错时自动回滚

这样路由和 CRUD 层会更清爽。  
当然，如果你更喜欢“在 CRUD 内部显式提交”，也可以保留那个风格，但整项目要统一。

### 如果今天你又改了模型，正确动作是什么

不是重启服务，不是删库重来，而是：

```powershell
alembic revision --autogenerate -m "update document table"
alembic upgrade head
```

这就是 Alembic 的核心价值：  
数据库结构变化，靠迁移版本推进，不靠程序启动时“顺手补表”。

### `schemas/document.py` 今天建议扩展成下面这样

如果你昨天已经写了基础版本，今天把它补完整：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadData(BaseModel):
    document_id: str = Field(..., description="上传成功后的文档 ID")
    file_name: str
    file_type: str
    file_size: int
    status: str


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime


class DocumentListData(BaseModel):
    items: list[DocumentListItem]
    total: int
```

### 如果你怕一开始接 PostgreSQL 太重

可以先在本地用异步 SQLite 跑通 Day 3。  
重点不是数据库有多“高级”，而是先把接口、ORM、状态流跑通。

只要你表结构设计合理，后面切到 PostgreSQL 并不难。

异步 SQLite 连接串写法你要记住：

```python
sqlite+aiosqlite:///./agentic_rag.db
```

### `models/document.py` 今天建议至少有这些字段

- `id`
- `knowledge_base_id`
- `file_name`
- `file_path`
- `file_type`
- `file_size`
- `status`
- `created_at`
- `updated_at`

### 建议写的白话注释

```python
# 这张表记录的是“文件在系统中的登记信息”，不是文件正文本身。
# 真正的正文解析和 chunk 切分，会在后续步骤里处理。
```

---

## 15:00 - 16:00：实现上传接口

### 建议落地的文件

- `routers/documents.py`
  - 实现 `POST /kb/documents/upload`
- `schemas/document.py`
  - 定义上传响应模型
- `utils/exceptions.py`
  - 定义文件类型或上传失败异常
- `conf/config.py`
  - 增加上传目录配置

### 先补一个简单但很好用的异常模块

#### `utils/exceptions.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse


class BusinessException(Exception):
    def __init__(self, message: str, code: int = 4000, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code


async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
        },
    )
```

这段代码的意义很简单：  
以后你想报“文件类型不支持”“文件为空”这种业务错误时，不用每个地方手写一坨返回格式。

### `conf/config.py` 记得补两个上传相关配置

```python
from pathlib import Path


class Settings:
    BASE_DIR = Path(__file__).resolve().parent.parent

    PROJECT_NAME = "Agentic RAG Assistant"
    VERSION = "0.1.0"
    DESCRIPTION = "一个基于 FastAPI 的 Agentic RAG 私有知识助手后端项目"
    API_PREFIX = "/api/v1"

    STORAGE_DIR = BASE_DIR / "storage"
    RAW_FILE_DIR = STORAGE_DIR / "raw"

    # 这里先把允许的上传类型和大小写死，后面再改成环境变量也不迟。
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
    MAX_FILE_SIZE = 10 * 1024 * 1024


settings = Settings()
```

### `routers/documents.py`

这是 Day 3 最关键的文件。  
这次我改成更适合你练习的写法：

- 前面是“练手骨架版”
- 后面是“完整参考答案”

你最好先自己写一遍，再看答案。

```python
from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from conf.database import get_database
from crud.document import create_document, list_documents
from schemas.document import DocumentListData, DocumentListItem, DocumentUploadData
from utils.exceptions import BusinessException
from utils.response import success_response

router = APIRouter(prefix="/kb/documents", tags=["documents"])


def build_document_id() -> str:
    # 你要做的事：
    # 1. 取当前时间，格式可以是 年月日时分秒
    # 2. 再拼一个 uuid 的前几位，避免重复
    # 3. 返回类似 doc_20260403112233_ab12cd 这样的字符串
    raise NotImplementedError("先自己实现 build_document_id")


def ensure_storage_dir() -> Path:
    # 你要做的事：
    # 1. 取出 settings 里配置的原始文件目录
    # 2. 如果目录不存在，就自动创建
    # 3. 返回这个目录 Path 对象
    raise NotImplementedError("先自己实现 ensure_storage_dir")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_database),
):
    # 你要做的事可以按下面顺序一点点写：
    #
    # 第 1 步：先校验文件名是否为空
    # 如果 file.filename 没有值，直接抛 BusinessException
    #
    # 第 2 步：提取安全文件名和后缀
    # 可以用 Path(file.filename).name 和 suffix.lower()
    #
    # 第 3 步：校验后缀是否合法
    # 如果不在 settings.ALLOWED_EXTENSIONS 里，就报不支持的文件类型
    #
    # 第 4 步：计算文件大小
    # 先把游标挪到文件末尾，取 tell()，再挪回开头
    #
    # 第 5 步：校验文件大小
    # 既要拦截空文件，也要拦截超过 MAX_FILE_SIZE 的文件
    #
    # 第 6 步：生成 document_id，准备存储目录和最终保存路径
    #
    # 第 7 步：把上传的文件写到磁盘
    # 可以用 with save_path.open("wb") 配合 shutil.copyfileobj(...)
    #
    # 第 8 步：调用 create_document，把文档记录写入数据库
    #
    # 第 9 步：如果过程出错，记得清理已经落盘的文件，避免脏数据
    #
    # 第 10 步：返回统一响应 success_response(...)
    raise NotImplementedError("先自己实现 upload_document")


@router.get("")
async def get_document_list(db: AsyncSession = Depends(get_database)):
    # 你要做的事：
    # 1. 调用 list_documents(db) 查出所有文档
    # 2. 把每条 ORM 对象转成 DocumentListItem
    # 3. 用 DocumentListData 组装 items 和 total
    # 4. 返回 success_response(...)
    raise NotImplementedError("先自己实现 get_document_list")
```

### `routers/documents.py` 参考答案

你先自己敲，再对照这一版。

```python
from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from conf.config import settings
from conf.database import get_database
from crud.document import create_document, list_documents
from schemas.document import DocumentListData, DocumentListItem, DocumentUploadData
from utils.exceptions import BusinessException
from utils.response import success_response

router = APIRouter(prefix="/kb/documents", tags=["documents"])


def build_document_id() -> str:
    # 时间戳 + 随机串，够你现在这个学习项目稳定使用了。
    return f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


def ensure_storage_dir() -> Path:
    raw_dir = settings.RAW_FILE_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_database),
):
    if not file.filename:
        raise BusinessException("上传失败，文件名不能为空", code=4001)

    file_name = Path(file.filename).name
    file_ext = Path(file_name).suffix.lower()

    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise BusinessException(
            f"暂不支持该文件类型：{file_ext}",
            code=4002,
        )

    # 先把游标移动到文件末尾，拿到文件大小，再移回开头。
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size == 0:
        raise BusinessException("上传失败，文件不能为空", code=4003)

    if file_size > settings.MAX_FILE_SIZE:
        raise BusinessException("上传失败，文件大小超过限制", code=4004)

    document_id = build_document_id()
    raw_dir = ensure_storage_dir()
    safe_name = file_name.replace(" ", "_")
    save_path = raw_dir / f"{document_id}__{safe_name}"

    try:
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        document = await create_document(
            db,
            document_id=document_id,
            knowledge_base_id=None,
            file_name=file_name,
            file_path=str(save_path),
            file_type=file_ext.lstrip("."),
            file_size=file_size,
            status="uploaded",
        )
    except Exception as exc:
        # 如果数据库写入失败，最好把刚刚保存到磁盘的文件也清掉，避免脏数据。
        if save_path.exists():
            save_path.unlink()
        raise BusinessException(f"上传失败：{exc}", code=5001, status_code=500)

    return success_response(
        data=DocumentUploadData(
            document_id=document.id,
            file_name=document.file_name,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
        ),
        message="upload success",
    )


@router.get("")
async def get_document_list(db: AsyncSession = Depends(get_database)):
    documents = await list_documents(db)
    items = [DocumentListItem.model_validate(doc) for doc in documents]

    return success_response(
        data=DocumentListData(items=items, total=len(items)),
        message="get document list success",
    )
```

### 这段上传代码，你一定要逐段理解

#### 第 1 段：为什么先校验 `file.filename`

因为如果连文件名都没有，后面的后缀判断、落盘命名都会出问题。

#### 第 2 段：为什么要自己判断后缀

因为不能指望前端永远传对。  
后端必须自己兜底。

#### 第 3 段：为什么要先算 `file_size`

因为文件太大时，你需要尽早拒绝，避免白白写磁盘。

#### 第 4 段：为什么先生成 `document_id`

因为你落盘文件名和数据库主键都需要一个稳定 ID。  
先生成，后面路径和数据库记录就能统一。

#### 第 5 段：为什么出错时要删文件

因为你要尽量避免这种情况：

- 磁盘里有文件
- 数据库里却没这条记录

这就叫“脏数据”。

#### 第 6 段：为什么路由也要改成 `async def`

因为你整套数据库访问已经是异步模式了。  
这时候路由层如果还是同步函数，风格就不统一，也没法直接 `await create_document(...)`。

### 推荐接口行为

- 接收文件
- 校验后缀
- 生成 `document_id`
- 保存文件
- 写入 `documents` 表
- 返回结果

### 推荐响应示例

```json
{
  "code": 0,
  "message": "upload success",
  "data": {
    "document_id": "doc_20260403_0001",
    "file_name": "agent_rag_intro.pdf",
    "status": "uploaded"
  }
}
```

### 建议写的白话注释

```python
# 上传接口只负责“接住并登记文件”，不在这里直接做解析和向量化。
# 这样可以让接口更快，也方便后面把索引流程独立出去。
```

### `main.py` 今天要再补两件事

1. 注册 `documents` 路由
2. 注册业务异常处理器

```python
from fastapi import FastAPI

from conf.config import settings
from routers.documents import router as documents_router
from routers.health import router as health_router
from utils.exceptions import BusinessException, business_exception_handler
from utils.response import success_response

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
)

app.add_exception_handler(BusinessException, business_exception_handler)


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
app.include_router(documents_router)
```

你会发现，这个 `main.py` 比之前更干净。  
原因很简单：

- 应用负责启动服务和注册路由
- Alembic 负责管理数据库结构

这才是职责分离。

---

## 16:00 - 17:00：补文档列表接口雏形

### 为什么 Day 3 就建议顺手补 `GET /kb/documents`

因为你上传完文件以后，需要一个最直接的方式验证：

- 数据库里是否真的有记录
- 状态是否正确
- 文件元数据是否保存完整

### 建议落地的文件

- `routers/documents.py`
  - 再补 `GET /kb/documents`
- `schemas/document.py`
  - 定义列表返回项
- `crud/document.py`
  - 实现查询列表方法

### 列表接口先做到什么程度就够了

- 能查出 `id`
- 能查出 `file_name`
- 能查出 `file_type`
- 能查出 `status`
- 能查出 `created_at`

先别急着分页、筛选、排序一大堆功能。

### 现在你已经有两条可验证链路了

- `POST /kb/documents/upload`
- `GET /kb/documents`

这两个接口组合起来，刚好可以构成 Day 3 的最小闭环：

1. 上传文件
2. 看数据库有没有记录
3. 看返回结构是不是你想要的样子

---

## 17:00 - 18:00：做联调和手工验证

### 今天推荐你至少测这几组情况

- 上传一个合法 `pdf`
- 上传一个合法 `txt`
- 上传一个不支持的后缀
- 上传一个空文件
- 上传成功后，立刻调列表接口

### 你要观察的点

- 返回里有没有 `document_id`
- 文件有没有真的落盘
- 数据库有没有记录
- 错误提示是不是人能看懂

### 可以直接复制的测试方式

先启动服务：

```powershell
uvicorn main:app --reload
```

如果你用的是 PostgreSQL 异步连接，记得先确认数据库本身已经启动。  
如果你用的是 `sqlite+aiosqlite`，本地通常会更省心一些。

如果你刚改过模型，测试上传接口前先别忘了：

```powershell
alembic revision --autogenerate -m "update upload related tables"
alembic upgrade head
```

然后优先用 Swagger 测：

- 打开 `http://127.0.0.1:8000/docs`
- 找到 `POST /kb/documents/upload`
- 选择一个本地文件上传
- 再调 `GET /kb/documents`

如果你更想用命令行，也可以这样发请求：

```powershell
curl.exe -X POST "http://127.0.0.1:8000/kb/documents/upload" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@test.txt"
```

### 手工测试通过后，你今天的主任务就算完成了

不要因为“还没做解析和切分”而焦虑。  
今天的目标是上传入口，不是整条 RAG 主链路。

---

## 晚上复盘：20:00 - 21:00

### 今晚你要能自己讲出来的 7 个点

1. 为什么上传接口不应该直接做索引？
2. 为什么上传接口推荐用 `UploadFile`？
3. 为什么要先生成 `document_id` 再保存文件？
4. 为什么文件名不能只用原始文件名？
5. `documents` 表里为什么要有 `status`？
6. 为什么今天要顺手做文档列表接口？
7. 今天和 LangChain 的边界到底在哪？

### 复盘结论要写成一句话

建议你写成这样：

> Day 3 的目标不是让系统“会回答问题”，而是先让系统“规范地收进文档，并留下可追踪记录”。

---

## 今日验收标准

- `POST /kb/documents/upload` 可用
- 上传成功后能返回 `document_id`
- 原始文件能落到指定目录
- 文档记录成功写入数据库
- `GET /kb/documents` 能查到刚上传的记录
- Swagger 可以直接调试上传接口

---

## 今天最容易踩的坑

### 坑 1：忘记处理 `multipart/form-data` 相关依赖

问题：

- 接口看着写对了
- 实际一传文件就报错

规避建议：

- 提前确认上传依赖齐全
- 先用 Swagger 手动传一遍文件

### 坑 2：把文件路径直接写死在业务代码里

问题：

- 以后改目录很麻烦

规避建议：

- 上传目录放进 `conf/config.py`

### 坑 3：数据库记录和磁盘文件不一致

问题：

- 文件有了，数据库没有
- 或者数据库有了，文件没了

规避建议：

- 按固定顺序处理
- 失败时补清理动作

### 坑 4：上传成功后没有做列表验证

问题：

- 你以为成功了
- 实际数据库字段可能存错了

规避建议：

- 当天就把列表接口雏形补出来

### 坑 5：今天就急着接 LangChain

问题：

- 分层会立刻变乱

规避建议：

- 记住今天的主线是文件入口，不是 RAG 编排

---

## 给明天的交接提示

明天你会正式进入 ingestion 的下一层：

- 读取文件正文
- 统一抽成文本
- 切分 chunk
- 给 chunk 补来源信息

到那时，LangChain 才会真正开始变得“具体”。  
你会看到它最实用的一面：

- 它不负责替你做产品决策
- 它负责把“读文本、切文本”这些重复劳动标准化

等你走到 Day 4，再回头看 Day 3，你会发现今天做的上传接口，其实是在给后面的 RAG 主链路铺路。
