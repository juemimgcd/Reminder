# Day 4：文档解析与切分

## 今天的总目标

- 把上传后的原始文件真正“读成文本”
- 用 LangChain loader 把文件转成 `Document` 对象
- 用 splitter 把长文本切成可检索的 chunk
- 给 chunk 补齐来源信息、页码信息、偏移信息

## 今天结束前，你必须拿到什么

- `utils/file_loader.py`
- `utils/text_splitter.py`
- `crud/chunk.py` 的雏形
- 一组能打印出来检查的 chunk 日志
- 一套你自己能讲明白的 LangChain 文档处理认知

---

## 今天开始，LangChain 真正登场

## 第 1 层：先把 LangChain 的“包拆分”讲明白

如果你现在去搜 LangChain，最容易懵的地方就是：

- 为什么不是只装一个 `langchain`
- 为什么又有 `langchain-community`
- 为什么又有 `langchain-text-splitters`
- 为什么后面还会出现 `langchain-huggingface`、`langchain-chroma`

这是因为现在 LangChain 已经拆成了“核心 + 集成包”。

你今天先把这几层记住：

- `langchain-core`
  - 放最核心的抽象，比如 `Document`、`Embeddings`、`Runnable`
- `langchain-community`
  - 放各种社区集成，比如 loader、一些向量库、一些第三方接入
- `langchain-text-splitters`
  - 专门放文本切分器

白话理解：

- `langchain-core` 像“标准接口层”
- `langchain-community` 像“各种接头配件仓库”
- `langchain-text-splitters` 像“专门切文本的工具箱”

今天你最常用到的就是：

- `langchain_community.document_loaders`
- `langchain_text_splitters`
- `langchain_core.documents.Document`

---

## 第 2 层：今天真正的数据流是什么

今天这条链路要在你脑子里非常清楚：

```text
documents 表里的 file_path
-> loader 读取文件
-> 得到 LangChain Document 列表
-> splitter 切分
-> 得到 chunk Document 列表
-> 给 chunk 补 metadata
-> 写入 chunks 表
-> 打日志检查切分结果
```

这里最容易混淆的是两个“文档”：

- 数据库 `Document`
  - 记录文件登记信息
- LangChain `Document`
  - 记录正文内容和正文元信息

你现在要把这句话彻底背下来：

> 数据库 `Document` 解决“系统里有没有这份文件”；LangChain `Document` 解决“这份文件的文本内容是什么”。

---

## 第 3 层：Loader 到底在干什么

### 先别把 loader 想神秘

loader 的本质就是：

- 根据文件类型选一个读取器
- 把文件读出来
- 变成 LangChain `Document`

比如：

- `PyPDFLoader`
  - 负责读 PDF
- `TextLoader`
  - 负责读纯文本

### 为什么 loader 返回的不是字符串，而是 `Document`

因为 LangChain 不想只保留正文，还想顺手保留元信息。

例如一个 `Document` 里通常有两部分：

- `page_content`
  - 正文内容
- `metadata`
  - 来源信息，比如文件路径、页码、文件名

这非常重要。  
因为后面你要做引用返回、页码追踪、chunk 溯源，都离不开 metadata。

---

## 第 4 层：为什么不要偷懒直接 `load_and_split()`

这个点你要特别注意。

很多初学者会觉得：

- 既然 loader 能 `load_and_split()`
- 那我直接一步到位不就好了

但你现在这个项目不推荐这么做。

原因有 3 个：

1. 你正在学习阶段，要把“加载”和“切分”明确拆开
2. 工程里调试时，分开写更容易定位哪一步出问题
3. 官方文档里一些 loader 的 `load_and_split()` 说明已经不建议当核心主流程依赖

白话理解：

- 你要先学会把食材洗干净
- 再学会怎么切菜
- 不要上来就按“一键料理机”

---

## 第 5 层：RecursiveCharacterTextSplitter 到底在“递归”什么

这个类名字很唬人，但你把它拆开就不难了。

- `Recursive`
  - 递归尝试不同分隔符
- `Character`
  - 默认按字符长度控制 chunk 大小
- `TextSplitter`
  - 本质就是文本切分器

它的工作思路非常像：

1. 先尝试按“大块边界”切，比如空行
2. 如果还是太长，再按换行切
3. 再不行，就按句号、逗号、空格继续切
4. 还不行，就硬切

所以它不是“随机切”，而是“尽量优雅地切”。

---

## 第 6 层：`chunk_size` 和 `chunk_overlap` 到底该怎么理解

### `chunk_size`

意思是：

- 每个 chunk 尽量控制在多大

你可以先把它理解成：

- 每个知识片段不要太长
- 太长会影响 embedding 和检索精度

### `chunk_overlap`

意思是：

- 相邻 chunk 之间保留一部分重复内容

为什么要重叠？

因为如果你切得太硬，句子可能会在边界断开。  
一旦断得太狠，后面检索就容易丢上下文。

白话理解：

- `chunk_size`：一刀切多大
- `chunk_overlap`：相邻两刀之间留多少“重叠缓冲”

### 初学阶段推荐值

- `chunk_size=500`
- `chunk_overlap=100`

先别急着做复杂调参。  
Day 4 的目标是先切得合理、能追踪来源，不是先做最优评测。

---

## 第 7 层：今天 metadata 要补到什么程度

今天你最少要让 chunk 具备这些信息：

- `document_id`
- `file_name`
- `file_type`
- `source`
- `chunk_id`
- `chunk_index`
- `page_no`
- `start_offset`

其中你要特别理解 3 个字段：

### `chunk_id`

- 这是每个 chunk 自己的唯一身份标识
- 后面写数据库、写向量库、返回引用都会用到

### `chunk_index`

- 这是顺序号
- 方便你知道它在原文中排第几个

### `start_offset`

- 表示这个 chunk 在原文中的起始位置
- 如果 splitter 支持记录起始索引，这个字段很有用

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 4 的主链路讲顺

### 今天你要能顺着说出来

```text
先查 documents 表
-> 拿到 file_path 和 file_type
-> 调 loader 读文件
-> 得到 LangChain Document
-> 调 splitter 切 chunk
-> 给 chunk 补 metadata
-> 写入 chunks 表
```

### 你必须能回答这两个问题

1. 为什么上传成功不等于已经完成文本解析？
2. 为什么 LangChain `Document` 比直接用 `str` 更适合后续 RAG？

---

## 09:50 - 10:40：理解不同文件类型应该怎么读

### 第一阶段先这样定

- `pdf`
  - 用 `PyPDFLoader`
- `txt`
  - 用 `TextLoader`
- `md`
  - 先也用 `TextLoader`

### 为什么 Markdown 第一阶段先按纯文本读

因为你现在最重要的是把 ingestion 主链路跑通。  
如果一上来就追求 Markdown 标题级别解析，会把复杂度拉高。

后面如果你想做更细的 Markdown 结构化处理，再考虑 `UnstructuredMarkdownLoader` 也不迟。

---

## 10:40 - 11:30：把 splitter 参数和 chunk 设计想清楚

### 今天你先统一定一个基础切分方案

```python
chunk_size = 500
chunk_overlap = 100
separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
```

### 为什么中文项目要手动加中文分隔符

因为默认英文分隔规则不一定适合中文语料。  
你手动把中文句号、问号、逗号加进去，切分通常会更自然。

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 4 最直接的验收方式

不是先做 API，而是先打印 chunk 调试信息。

你今天至少要能打印：

- chunk 总数
- 每个 chunk 的前 100 个字符
- 每个 chunk 的 `document_id`
- 每个 chunk 的 `page_no`
- 每个 chunk 的 `chunk_index`

如果这些信息都能打出来，你今天就不是“写了代码”，而是真正“看到了结果”。

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:30：先补依赖

### 推荐安装

```powershell
pip install -U langchain-community langchain-text-splitters pypdf
```

### 为什么 Day 4 先不装太多包

因为今天只做两件事：

- 读取文件
- 切分文本

embedding、向量库是 Day 5 的事。

---

## 14:30 - 15:20：实现 `utils/file_loader.py`

### 今天建议落地的文件

- `utils/file_loader.py`
- `utils/text_splitter.py`
- `crud/chunk.py`

### `utils/file_loader.py` 练手骨架版

```python
from pathlib import Path

from langchain_core.documents import Document as LCDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from utils.exceptions import BusinessException


def load_langchain_documents(
    *,
    file_path: str,
    file_type: str,
    document_id: str,
    file_name: str,
) -> list[LCDocument]:
    # 你要做的事：
    # 1. 把 file_path 转成 Path，并检查文件是否存在
    # 2. 根据 file_type 选择 loader
    #    - pdf -> PyPDFLoader
    #    - txt / md -> TextLoader
    # 3. 调 loader.load() 得到 LangChain Document 列表
    # 4. 给每个 Document 的 metadata 补充：
    #    document_id / file_name / file_type / source
    # 5. 返回处理后的文档列表
    raise NotImplementedError("先自己实现 load_langchain_documents")
```

### `utils/file_loader.py` 参考答案

```python
from pathlib import Path

from langchain_core.documents import Document as LCDocument
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from utils.exceptions import BusinessException


def load_langchain_documents(
    *,
    file_path: str,
    file_type: str,
    document_id: str,
    file_name: str,
) -> list[LCDocument]:
    path = Path(file_path)

    if not path.exists():
        raise BusinessException(message=f"文件不存在：{file_path}", code=4041, status_code=404)

    if file_type == "pdf":
        loader = PyPDFLoader(str(path))
    elif file_type in {"txt", "md"}:
        loader = TextLoader(path, autodetect_encoding=True)
    else:
        raise BusinessException(message=f"暂不支持该文件类型：{file_type}", code=4002)

    docs = loader.load()

    for doc in docs:
        doc.metadata["document_id"] = document_id
        doc.metadata["file_name"] = file_name
        doc.metadata["file_type"] = file_type
        doc.metadata["source"] = str(path)

    return docs
```

### 这一段你一定要看懂

- `PyPDFLoader` 和 `TextLoader` 的职责只是“把文件读出来”
- 它们不会替你设计业务 `metadata`
- 所以 `document_id`、`file_name` 这些业务字段，必须你自己补进去

---

## 15:20 - 16:20：实现 `utils/text_splitter.py`

### `utils/text_splitter.py` 练手骨架版

```python
import uuid

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_text_splitter() -> RecursiveCharacterTextSplitter:
    # 你要做的事：
    # 1. 返回一个 RecursiveCharacterTextSplitter
    # 2. 设置 chunk_size、chunk_overlap
    # 3. 给中文文本补一套适合的 separators
    # 4. 打开 add_start_index，方便记录 chunk 起始位置
    raise NotImplementedError("先自己实现 build_text_splitter")


def split_documents(
    *,
    document_id: str,
    documents: list[LCDocument],
) -> list[LCDocument]:
    # 你要做的事：
    # 1. 调 build_text_splitter()
    # 2. 用 splitter.split_documents(documents) 切分
    # 3. 遍历每个 chunk，补 metadata：
    #    chunk_id / chunk_index / page_no / start_offset
    # 4. 返回切分后的 chunk 列表
    raise NotImplementedError("先自己实现 split_documents")
```

### `utils/text_splitter.py` 参考答案

```python
import uuid

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        add_start_index=True,
    )


def split_documents(
    *,
    document_id: str,
    documents: list[LCDocument],
) -> list[LCDocument]:
    splitter = build_text_splitter()
    chunks = splitter.split_documents(documents)

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

### 这里有 4 个特别容易忽略的点

#### 点 1：为什么 `separators` 要自己写

因为中文和英文断句方式不同。  
你不手动加中文标点，切出来的边界可能很生硬。

#### 点 2：为什么要 `add_start_index=True`

因为后面你如果想知道：

- 这个 chunk 在原文什么位置开始
- 引用时怎么更精确定位

这个信息会很好用。

#### 点 3：为什么 `chunk_id` 不能只靠顺序号

因为后面写数据库、写向量库时，最好让 ID 更稳一些。  
顺序号加随机串，会比单纯 `0,1,2,3` 更保险。

#### 点 4：为什么 `page_no` 要自己整理

loader 给你的 metadata 不一定长得刚好适合数据库字段。  
你现在要学会一件很重要的工程习惯：

> 第三方工具给你的数据，先整理成你项目自己的标准格式，再继续往下流。

---

## 16:20 - 17:10：实现 `crud/chunk.py`

### `crud/chunk.py` 练手骨架版

```python
from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import Chunk


async def create_chunks(
    db: AsyncSession,
    *,
    document_id: str,
    chunk_docs: list[LCDocument],
) -> list[Chunk]:
    # 你要做的事：
    # 1. 遍历 chunk_docs
    # 2. 从 metadata 里取出 chunk_id / chunk_index / page_no / start_offset
    # 3. 用这些数据构造 Chunk ORM 对象
    # 4. 文本内容放到 content 字段
    # 5. end_offset 可以用 start_offset + len(page_content) 简单计算
    # 6. 批量 add_all 后 flush
    # 7. 返回创建好的 chunk 列表
    raise NotImplementedError("先自己实现 create_chunks")
```

### `crud/chunk.py` 参考答案

```python
from langchain_core.documents import Document as LCDocument
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import Chunk


async def create_chunks(
    db: AsyncSession,
    *,
    document_id: str,
    chunk_docs: list[LCDocument],
) -> list[Chunk]:
    chunk_entities: list[Chunk] = []

    for chunk_doc in chunk_docs:
        content = chunk_doc.page_content.strip()
        if not content:
            continue

        start_offset = chunk_doc.metadata.get("start_offset")
        end_offset = (
            start_offset + len(content)
            if isinstance(start_offset, int)
            else None
        )

        chunk = Chunk(
            id=chunk_doc.metadata["chunk_id"],
            document_id=document_id,
            chunk_index=chunk_doc.metadata["chunk_index"],
            content=content,
            page_no=chunk_doc.metadata.get("page_no"),
            start_offset=start_offset,
            end_offset=end_offset,
        )
        chunk_entities.append(chunk)

    db.add_all(chunk_entities)
    await db.flush()
    return chunk_entities
```

### 为什么 Day 4 就建议把 chunk 写数据库

因为你后面会需要：

- 做引用返回
- 做问题定位
- 做 debug
- 检查切分是否合理

如果 chunk 只存在内存里，你后面排查会很痛苦。

---

## 17:10 - 18:00：做一个最小调试脚本

### 建议新建

- `docs/debug_day4.md`
- 或者临时写一个 `scripts/debug_day4.py`

### 你今天最少要验证这件事

给一份测试文档跑完下面流程：

1. 查到 `document.file_path`
2. `load_langchain_documents(...)`
3. `split_documents(...)`
4. 打印前 3 个 chunk

### 调试输出建议长这样

```python
print(f"chunk_count={len(chunk_docs)}")
for chunk in chunk_docs[:3]:
    print("=" * 50)
    print(chunk.metadata)
    print(chunk.page_content[:120])
```

只要你能看到：

- chunk 数量合理
- metadata 在
- 文本不是空的

那 Day 4 主链路就算基本打通了。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己讲顺的 8 个点

1. LangChain `Document` 和数据库 `Document` 有什么区别？
2. loader 为什么返回 `Document` 而不是直接返回字符串？
3. 为什么 Day 4 不推荐偷懒用 `load_and_split()`？
4. `RecursiveCharacterTextSplitter` 的“递归”是什么意思？
5. `chunk_size` 和 `chunk_overlap` 分别解决什么问题？
6. 为什么中文文本要手动加分隔符？
7. 为什么 chunk 一定要补 metadata？
8. 为什么 Day 4 就建议把 chunk 写进数据库？

---

## 今日验收标准

- 任意一份测试文档能成功读成 LangChain `Document`
- 能切成多条合理 chunk
- 每条 chunk 都有 `document_id`
- PDF chunk 能带页码或页码原始信息
- 每条 chunk 都有 `chunk_id` 和 `chunk_index`
- 可以把 chunk 结果打印出来检查

---

## 今天最容易踩的坑

### 坑 1：把 Markdown 一开始就做太复杂

问题：

- 容易掉进格式解析细节
- 主链路迟迟跑不通

规避建议：

- 第一阶段先把 `md` 当普通文本处理

### 坑 2：直接用 `load_and_split()`

问题：

- 学不会链路拆分
- 调试困难

规避建议：

- `load()`
- 然后 `split_documents()`
- 分两步写清楚

### 坑 3：切完 chunk 但不补 metadata

问题：

- 后面完全不知道 chunk 从哪来

规避建议：

- 当天就把 `document_id`、`chunk_id`、`page_no`、`start_offset` 补齐

### 坑 4：只看 chunk 数量，不看 chunk 内容

问题：

- 你以为切好了
- 实际可能切得很碎、很乱、很空

规避建议：

- 至少打印前 3 条 chunk 看实际文本

### 坑 5：以为 loader 会帮你处理所有业务 metadata

问题：

- 后面数据库字段和 LangChain metadata 对不上

规避建议：

- 第三方数据先归一化成你项目自己的 metadata 标准

---

## 给明天的交接提示

明天会进入 RAG 最核心的一层之一：

- embedding
- vector store
- index API

你会开始真正理解 3 个特别容易混淆的概念：

- 谁负责“把文本变向量”
- 谁负责“把向量存起来”
- 谁负责“按问题把相似文本查出来”

只要这 3 个角色你分清了，后面的 RAG 主链路会顺很多。
