# Day 1：项目重新立项 + FastAPI 骨架落地

## 今天的总目标

- 把项目从“一个 AI 想法”收束成“15 天内能交付的后端项目”
- 在当前仓库里跑通一个更像样的 FastAPI 项目骨架
- 写出第一版 README，让项目目标、边界、接口方向都说得明明白白

## 今天结束前，你必须拿到什么

- 一个能启动的 FastAPI 服务
- 一个初步合理的目录结构
- 一个能解释项目目标的 README 初稿
- 一句你自己也能复述出来的项目定义

建议你把这句项目定义背下来：

> 这是一个基于 FastAPI 的 Agentic RAG 私有知识助手后端服务，支持文档上传、索引、检索增强问答和引用返回，重点是做成可运行、可部署、可扩展的工程项目，而不是单次问答脚本。

---

## 先用大白话把核心概念讲清楚

### 1. 这个项目到底在做什么

- 你不是在做“上传 PDF 后调一下模型”的脚本
- 你是在做一个后端系统
- 这个系统以后要负责接收文件、保存记录、建立索引、检索内容、组织答案、返回引用

白话理解：

你可以把它想成一个“会读文档、会记住文档、回答时会翻资料”的知识助手后端。

### 2. 什么叫 RAG

- `RAG` = `Retrieval-Augmented Generation`
- 中文可以简单理解成：先检索资料，再基于资料生成答案

别把它想复杂。它本质上就是两步：

1. 先去知识库里把相关内容找出来
2. 再把找到的内容喂给模型，让模型尽量“有依据地回答”

### 3. 什么叫 Agentic

- 这里的 `Agentic` 不等于“上来就多智能体大战”
- 这里更偏向“系统会按流程做事、会管理状态、会拆步骤”

白话一点：

- 普通脚本：你点一下，它答一下
- Agentic 风格系统：它知道“先上传、再索引、再检索、再回答、再记录状态”

所以你这个项目里的 “Agentic”，更多体现在流程编排和任务状态，不是 Day 1 就去做复杂 Agent。

### 4. LangChain 今天只需要懂到哪一步

- LangChain 不是大模型
- LangChain 不是向量库
- LangChain 也不是你的业务系统

它更像一个“接线工具箱”：

- 帮你接文档加载器
- 帮你接文本切分器
- 帮你接 embedding 模块
- 帮你接 retriever
- 帮你把这些部件串起来

今天你只需要记住一句话：

> LangChain 是帮你串流程的，不是替你思考业务边界的。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:40：重新定义项目，不让它失控

### 你要做的事

- 重新读一遍 [agentRAG.md](/e:/python_files/agentic_rag/agentRAG.md)
- 拿纸或者 Markdown 记下这 3 个问题：
  - 这个项目最终要交付什么
  - 这个项目明确不做什么
  - 这个项目和“普通 PDF 问答脚本”有什么区别

### 你要写下来的结论

- 必做功能清单
- 不做清单
- 简历定位

### 老师提醒

- 第一天最重要的不是写多少代码
- 第一天最重要的是：以后每一天都不跑偏

项目一旦边界不清，后面就会不停加戏：

- 想加前端
- 想加多 agent
- 想加权限
- 想加复杂工作流

这样 15 天计划会直接失控。

---

## 09:40 - 10:30：看懂当前仓库现状

### 你要做的事

- 打开 [main.py](/e:/python_files/agentic_rag/main.py)
- 确认当前只是一个 FastAPI Hello World
- 对照大纲，列出“现在缺了哪些模块”

### 你现在已经有的东西

- FastAPI 能启动
- 有最小入口文件

### 你现在明显缺的东西

- 路由分层
- 配置层
- schema 层
- 统一响应
- 文档模块
- 数据模型
- README

### 学习目标

把“项目骨架”和“业务功能”分开看：

- `main.py` 是入口，不是业务堆积场
- 路由负责接请求，不负责干重活
- 真正的处理逻辑以后会下沉到其他模块

---

## 10:30 - 11:20：先设计骨架，不急着填肉

### 推荐你今天先创建的目录

```text
agentic_rag/
├─ routers/
├─ schemas/
├─ conf/
├─ utils/
├─ target/
├─ README.md
└─ main.py
```

### 为什么 Day 1 不把所有目录一次建满

因为你现在最需要的是“能启动、能继续拆、不会乱”，不是“看起来很完整”。

今天先把最关键的几层搭出来：

- 入口层：`main.py`
- 路由层：`routers/`
- 配置层：`conf/`
- 通用结构层：`schemas/`、`utils/`

剩下的 `crud/`、`models/`、`cache/` 等目录，Day 2 和 Day 3 再按需求补，会更自然。

---

## 11:20 - 12:00：写 README 第一版

### README 第一版至少要写什么

- 项目名称
- 项目定位
- 当前阶段目标
- 计划支持的核心能力
- 本地启动方式
- API 预览

### 先不要追求完美

今天的 README 不是最终版本，它的作用是：

- 给未来的自己看
- 给你后面第 14 天继续补内容打地基
- 防止你写着写着忘了项目要做什么

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:40：整理基础项目结构

### 今天建议落地的文件级任务

- `main.py`
  - 保留应用入口
  - 配置应用标题、版本、文档说明
  - 注册路由
- `routers/health.py`
  - 新建健康检查接口
- `routers/__init__.py`
  - 标记包目录
- `schemas/common.py`
  - 放统一响应结构
- `utils/response.py`
  - 放成功响应的辅助函数
- `conf/config.py`
  - 放项目名、版本、上传目录等基础配置
- `README.md`
  - 写项目说明第一版

### 先把依赖装上，不然后面代码会跑不起来

如果你还没有 `requirements.txt`，今天先最小化安装这些：

```powershell
pip install fastapi uvicorn sqlalchemy python-multipart
```

如果你想顺手记到依赖文件里，可以先写成：

```txt
fastapi
uvicorn[standard]
sqlalchemy
python-multipart
```

### 先把目录和空文件建出来

你可以用 PowerShell 直接敲：

```powershell
New-Item -ItemType Directory routers,schemas,conf,utils -Force
New-Item -ItemType File routers/__init__.py,schemas/__init__.py,conf/__init__.py,utils/__init__.py -Force
New-Item -ItemType File routers/health.py,schemas/common.py,utils/response.py,conf/config.py,README.md -Force
```

### 今天你可以直接照着写的最小可运行代码

下面这一组代码的目标只有一个：  
让项目从“只有一个 hello world 文件”，变成“已经有分层雏形的 FastAPI 项目”。

#### `conf/config.py`

```python
from pathlib import Path


class Settings:
    # `__file__` 是当前这个文件自己的路径。
    # `parent.parent` 往上退两层，就能拿到项目根目录。
    BASE_DIR = Path(__file__).resolve().parent.parent

    PROJECT_NAME = "Agentic RAG Assistant"
    VERSION = "0.1.0"
    DESCRIPTION = "一个基于 FastAPI 的 Agentic RAG 私有知识助手后端项目"

    API_PREFIX = "/api/v1"

    # 先把存储目录约定好，后面 Day 3 上传文件时直接复用。
    STORAGE_DIR = BASE_DIR / "storage"
    RAW_FILE_DIR = STORAGE_DIR / "raw"


settings = Settings()
```

这段代码你要看懂 3 件事：

- 为什么要有 `settings`
- 为什么路径最好集中管理
- 为什么 Day 1 就先把 `RAW_FILE_DIR` 留出来

白话解释：

- `settings` 就像项目的“公共配置本”
- 以后别的文件要拿项目名、版本号、上传目录，直接从这里拿
- 这样后面你改目录，不需要全项目到处搜字符串

#### `schemas/common.py`

```python
from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = Field(default=0, description="0 表示成功，非 0 表示失败")
    message: str = Field(default="ok", description="给前端或调用方看的提示信息")
    data: Any | None = Field(default=None, description="真正的业务数据")
```

你现在先别纠结泛型、复杂封装。  
对初学阶段来说，先把统一格式立住最重要。

#### `utils/response.py`

```python
from typing import Any

from schemas.common import ApiResponse


def success_response(data: Any = None, message: str = "ok") -> ApiResponse:
    # 这里统一返回 ApiResponse，好处是后面所有成功接口都长得一样。
    return ApiResponse(code=0, message=message, data=data)
```

#### `routers/health.py`

```python
from fastapi import APIRouter

from utils.response import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    # 健康检查接口一般不做复杂逻辑，它的主要任务是告诉你：
    # 服务是否启动了，路由是否注册成功了。
    return success_response(
        data={"service": "agentic-rag", "status": "running"},
        message="service is healthy",
    )
```

#### `main.py`

把你现在的 [main.py](/e:/python_files/agentic_rag/main.py) 先改造成下面这样：

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
    # 根路由通常用来返回欢迎信息、版本信息，方便你确认服务已经起来了。
    return success_response(
        data={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
        message="welcome to agentic rag assistant",
    )


# 这里先只做应用初始化和路由挂载，不在 main.py 里堆业务逻辑。
# 这样后面文档上传、聊天、索引接口都能继续拆分，不会把入口文件写成大杂烩。
app.include_router(health_router)
```

#### `README.md`

第一版不用追求华丽，先把骨架写出来：

````md
# Agentic RAG Assistant

## 项目简介

这是一个基于 FastAPI 的 Agentic RAG 私有知识助手后端项目。
目标是在 15 天内完成一个可运行、可演示、可部署的 AI 应用后端。

## 当前阶段

- Day 1：搭项目骨架
- Day 2：明确数据流和数据模型
- Day 3：实现文档上传接口

## 计划功能

- 文档上传
- 文档解析与切分
- 向量化索引
- 检索增强问答
- 引用返回
- Docker 化部署

## 本地启动

```bash
uvicorn main:app --reload
```
````

### 你今天改完以后，项目最小目录应该长这样

```text
agentic_rag/
├─ conf/
│  ├─ __init__.py
│  └─ config.py
├─ routers/
│  ├─ __init__.py
│  └─ health.py
├─ schemas/
│  ├─ __init__.py
│  └─ common.py
├─ utils/
│  ├─ __init__.py
│  └─ response.py
├─ target/
├─ README.md
└─ main.py
```

### 为什么先做健康检查接口

因为它特别适合用来验证“项目骨架是不是通了”。

白话说：

- 如果 `/health` 能返回正确结果
- Swagger 能打开
- 路由注册也正常

那说明你的第一层骨架搭对了。

---

## 14:40 - 15:30：改造 `main.py`

### 目标

把现在单文件小 demo，改成“入口负责挂载，业务往外拆”的结构。

### 你要完成的事

- 给 FastAPI 应用补上标题和描述
- 把根路由保留为欢迎页或版本页
- 把 `/health` 路由单独拆到 `routers/health.py`

### 建议写的白话注释

```python
# 这里先只做应用初始化和路由挂载，不在 main.py 里堆业务逻辑。
# 这样后面文档上传、聊天、索引接口都能继续拆分，不会把入口文件写成大杂烩。
```

这类注释很好，因为它解释的是“为什么这样设计”，不是废话式注释。

---

## 15:30 - 16:20：补 `schemas/common.py` 和 `utils/response.py`

### 目标

提前建立统一响应习惯，避免后面每个接口返回格式都不一样。

### 推荐思路

- `schemas/common.py`
  - 定义统一响应模型，比如 `code`、`message`、`data`
- `utils/response.py`
  - 封装 `success_response(data, message="ok")`

### 为什么第一天就要做这个

很多人会觉得统一响应可以以后再补。

但实际上，接口一多之后再回头改，成本会很高。  
第一天先把骨架立住，后面你所有 API 都可以沿用这套返回结构。

### 建议写的白话注释

```python
# 统一响应格式的目的，不是为了“好看”，而是为了让前端、测试和日志都更容易处理。
```

---

## 16:20 - 17:10：补 `conf/config.py`

### 目标

把一些会反复使用的项目配置集中起来。

### 今天先放哪些配置就够了

- 项目名称
- 项目版本
- API 前缀
- 上传目录

### 为什么不要把配置散落在各个文件里

因为以后你会遇到这些情况：

- 上传目录要改
- 项目名要改
- 环境变量要接入

如果每个文件自己写一份，后面会很难维护。

### 建议写的白话注释

```python
# 配置集中管理的好处是：后面无论切换本地、测试还是生产环境，都只需要从这里统一调整。
```

---

## 17:10 - 18:00：写 README 初稿

### 你至少要写出下面这些小节

- 项目介绍
- 为什么这个项目不是普通 PDF 问答脚本
- 技术栈
- 当前进度
- 本地运行方式
- 计划中的 API

### README 里可以直接写的句子

- 当前阶段先聚焦后端 API，不引入复杂前端工程。
- 当前阶段先完成上传、索引、检索问答主链路，再逐步补缓存、异步任务和 Docker 化。
- 当前阶段不做多智能体编排，优先把基础工程链路跑通。

### 今天最后一定要自己跑一遍

启动命令：

```powershell
uvicorn main:app --reload
```

打开浏览器确认两个地址：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

如果 `/docs` 能打开，并且你能看到 `/health`，说明 Day 1 的骨架已经立起来了。

---

## 晚上复盘：20:00 - 21:00

### 复盘问题

你要能不用看稿，自己回答这几个问题：

1. 这个项目和普通问答脚本的区别是什么？
2. 为什么 `main.py` 不能一直堆业务？
3. 为什么今天要先做 `/health`？
4. 为什么第一天就建议建立统一响应格式？
5. LangChain 在这个项目里扮演什么角色？

### 如果你答不出来，重点回看哪里

- 答不出项目边界：回看 [agentRAG.md](/e:/python_files/agentic_rag/agentRAG.md)
- 答不出骨架设计：回看你今天拆出来的目录
- 答不出 LangChain 定位：记住一句话，“它是流程接线工具箱，不是业务边界设计者”

---

## 今日验收标准

- 本地 `uvicorn` 能正常启动
- Swagger 页面能打开
- `/health` 可以访问
- 项目目录不再只有一个 `main.py`
- README 初稿已经写出来
- 你能用 1 分钟讲清楚项目定位

---

## 今天最容易踩的坑

### 坑 1：一上来把目录建得特别全

问题：

- 看起来很完整
- 实际上很多目录今天根本用不到

规避建议：

- 先建核心目录
- 等 Day 2、Day 3 真的需要时再补模块

### 坑 2：把业务逻辑继续写在 `main.py`

问题：

- 刚开始很快
- 后面非常难拆

规避建议：

- 从第一天开始就坚持“入口归入口，路由归路由”

### 坑 3：觉得 README 可以最后再写

问题：

- 到第 10 天以后，你可能已经忘了最初的边界

规避建议：

- 第一版不求华丽
- 先把项目定位和路线写清楚

### 坑 4：把 LangChain 想成“万能魔法库”

问题：

- 容易产生“只要学会 LangChain，项目自然就出来了”的错觉

规避建议：

- 先把系统拆成若干普通后端步骤
- 再看哪些步骤适合用 LangChain 接起来

---

## 给明天的交接提示

明天不是继续堆代码，而是要把“数据怎么流动”彻底说清楚。  
你会开始接触两个特别重要的概念：

- 业务里的 `Document`
- LangChain 里的 `Document`

它们名字一样，但不是一回事。  
只要你把这个区别搞懂，后面很多概念都会顺下来。
