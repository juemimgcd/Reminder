# Day 2：目标架构升级蓝图 + 分层映射

## 今天的总目标
- 把 `Mneme` 从“当前已经存在的功能仓库”映射成一张可以持续推进 20 天的目标架构蓝图。
- 把主链路从 `Document -> Chunk -> Retrieval -> Answer` 升级理解成 `Document -> Chunk -> MemoryEntry -> GraphRAG -> Profile Snapshot -> Evidence Answer`。
- 明确 `api / core / domains / workflow / infra` 这套分层不是目录好看，而是为了给 Day 3 之后的能力落位。
- 产出 Day 3 可以直接接住的输入：目标主链图、目录映射表、阶段拆分表、先做与后做的边界。

## 今天结束前，你必须拿到什么
- 一张你自己能讲顺的“当前链路 vs 目标链路”对照图。
- 一份从当前仓库真实目录映射到目标分层结构的表。
- 一份按阶段拆开的重构顺序，而不是“大重构”口号。
- 一份 Day 3 可以直接使用的 `MemoryEntry` 落位说明。
- 一份明确写清楚“今天不做什么”的边界清单。

---

## Day 2 一图总览

```mermaid
flowchart LR
    A[Day 1 真实仓库审计结果] --> B[识别当前主链]
    B --> C[画出目标主链]
    C --> D[拆出 api/core/domains/workflow/infra]
    D --> E[把真实目录映射进去]
    E --> F[得到 Day 3 以后的阶段顺序]
```

---

## 为什么这一天重要
Day 1 解决的是“方向和边界”，  
Day 2 解决的是“后面每一天到底接在哪一张总蓝图上”。

如果 Day 2 没做好，后面最容易出现 4 个问题：
- 一边说要做长期记忆，一边还是在按普通 `Chunk RAG` 的思路加功能。
- 一边说要做架构优化，一边只是机械地移动目录。
- 一边想引入 `LlamaIndex / MongoDB`，一边又不知道它们应该接管哪一层。
- 一边准备做 `MemoryEntry / GraphRAG / Eval`，一边没有统一主链，导致每天都像在另起炉灶。

所以 Day 2 的本质不是写很多代码，  
而是把“目标系统长什么样、为什么这样分层、真实仓库怎么逐步迁过去”讲清楚。

---

## Day 2 整体架构

今天你要同时抓住 3 张图。

第一张图是当前 Mneme 更接近什么：

```text
main.py
  -> routers/*
  -> services/document_service.py
  -> pipelines/document_index_pipeline.py
  -> clients/vector_store_client.py
  -> services/query_service.py
  -> answer
```

第二张图是目标业务主链应该长什么样：

```text
Document
  -> Chunk
  -> MemoryEntry
  -> CanonicalMemory / Snapshot
  -> Chunk + Memory + Graph Retrieval
  -> Evidence-based Answer
  -> Eval / Debug / Analysis
```

第三张图是目标代码结构应该长什么样：

```text
app/mneme/
  main.py
  bootstrap/
  api/
  core/
  domains/
  workflow/
  infra/
```

今天的任务，就是把这 3 张图连起来，而不是分别孤立地理解。

---

## 今天的边界要讲透
### 今天之后，各层职责应该怎么理解

从 Day 2 开始，后面的计划一律按下面这套职责理解：

```text
api
  负责路由、请求入站、schema 校验、响应结构

core
  负责配置、依赖注入、上下文、共享协议、统一异常和公共运行时规则

domains
  负责 documents / retrieval / memory / graph / profile / advice / companion / tasks 等领域

workflow
  负责长任务、阶段执行、状态机、outbox、回放、异步调度

infra
  负责 pg / vector store / neo4j / cache / retry / rate limit / celery 等底层适配
```

### 对当前仓库的处理原则

今天不要把仓库想成“错误的旧架构”，  
而要把它想成“已经有一部分正确能力，但边界还没有收干净”的过渡态。

当前这些目录今天都要被重新解释，但不是立即推翻：

| 当前目录 / 文件 | 今天要怎么理解 |
|---|---|
| `main.py` | 当前总入口，后面要变薄 |
| `routers/` | 当前 `api` 雏形 |
| `schemas/` | 当前请求响应和 DTO 雏形 |
| `services/` | 当前业务入口和领域服务混合层 |
| `pipelines/` | 当前主链编排雏形 |
| `clients/` | 当前外部依赖适配层 |
| `infra/` | 当前运行时能力层 |
| `tasks/` | 当前异步执行入口 |
| `models/` | 当前主数据模型 |
| `crud/` | 当前持久化访问层雏形 |

### 先不要急着做这些

今天先不要急着做：
- 全量目录迁移。
- 大面积改 import。
- 正式引入 `LlamaIndex`。
- 正式引入 `MongoDB`。
- 先做完整 `workflow` 实现。
- 先把所有 `services` 拆成几十个子包。

原因很简单：

> Day 2 还在回答“蓝图是什么”，不是在回答“全部代码今天怎么一次性搬完”。

---

## 第 1 层：Day 2 的本质是什么

Day 2 的本质不是“画一张漂亮架构图”，而是：

```text
把 Day 1 得到的真实事实
变成 Day 3 - Day 20 都能沿用的目标系统蓝图
```

你今天必须能讲顺这句话：

> Mneme 当前已经有上传、切分、索引、检索、问答、任务、图存储这些基础能力。  
> 现在要做的不是推翻它，而是把这些能力重新收口到长期记忆系统的主链、分层和阶段路线里。  
> Day 2 的作用，就是把“看清楚现状”升级成“知道后面每一步应该落在哪一层”。

如果这句话你讲不顺，说明 Day 2 还没做完。

---

## 第 2 层：Day 2 的主链一定要从当前真实仓库出发

今天仍然不能从想象中的新项目出发，  
一定要从当前真实仓库出发。

建议你继续围绕这条真实链路去看：

```text
main.py
  -> routers/documents.py
  -> services/document_service.py
  -> pipelines/document_index_pipeline.py
  -> services/memory_service.py
  -> services/context_service.py
  -> services/query_service.py
  -> clients/vector_store_client.py
  -> clients/neo4j_client.py
  -> tasks/index_tasks.py
  -> infra/task_queue.py
```

今天你要从这条链路里回答 4 个问题：
- 现在真正的“主链”走到哪里了？
- 哪些能力已经有雏形，只是没有正式纳入目标结构？
- 哪些能力看起来很多，但其实没有统一编排？
- 哪些文件后面会成为 Day 3 之后的主要落点？

---

## 第 3 层：Day 2 必须先把“目标主链”讲清楚

今天最重要的一件事，是把目标主链写成统一口径。

推荐你把目标主链固定成下面这条：

```text
Document
  -> Chunk
  -> MemoryEntry
  -> CanonicalMemory / Profile Snapshot
  -> Hybrid Retrieval
  -> Graph Expansion
  -> Evidence-based Answer
  -> Debug / Eval / Analysis
```

这里每一段都代表后面几天的核心抓手：

| 主链节点 | 后面会接哪几天 |
|---|---|
| `Document -> Chunk` | Day 3 以前的已有基础，后面继续优化 |
| `Chunk -> MemoryEntry` | Day 3 |
| `MemoryEntry -> Evidence Answer` | Day 4 |
| `Hybrid Retrieval` | Day 5 - Day 7 |
| `Graph Expansion` | Day 8 - Day 11 |
| `CanonicalMemory / Snapshot` | Day 12 - Day 14 |
| `Debug / Eval / Analysis` | Day 15 - Day 17 |
| `薄入口 + 分层收口 + 技术减重` | Day 18 - Day 20 |

只要这张表清楚了，后面每一天都不会飘。

---

## 第 4 层：Day 2 必须先把“目标分层”讲清楚

今天一定要明确，后面说的分层不是抽象概念，而是为了减少当前仓库的混层问题。

你可以先把目标结构理解成：

```text
app/mneme/
  main.py
  bootstrap/
    app_factory.py
    wiring.py
  api/
    routes/
    deps.py
    schemas/
  core/
    config.py
    container.py
    context.py
    exceptions.py
  domains/
    documents/
    retrieval/
    memory/
    graph/
    profile/
    tasks/
  workflow/
    jobs/
    outbox/
    state_machine/
  infra/
    db/
    vector/
    graph/
    cache/
    queue/
```

注意，这不是要求你今天创建这套目录，  
而是要求你今天明确每一类现有代码以后该落到哪一层。

---

## 第 5 层：Day 2 必须把“当前目录 -> 目标分层”映射清楚

这张映射表就是今天最重要的中间产物之一。

| 当前目录 / 文件 | 目标落位 | 原因 |
|---|---|---|
| `routers/*.py` | `api/routes/` | 明确路由层只保留入站职责 |
| `schemas/*.py` | `api/schemas/` 或 `domains/*/schemas.py` | 按请求响应和领域 DTO 逐步收口 |
| `services/document_service.py` | `domains/documents/service.py` | 文档领域入口 |
| `services/query_service.py` | `domains/retrieval/service.py` | 检索与问答统一入口 |
| `services/context_service.py` | `domains/retrieval/context_service.py` | 统一上下文组装 |
| `services/memory_service.py` | `domains/memory/service.py` | `MemoryEntry` 和长期记忆主链 |
| `services/graph_*` | `domains/graph/` | 图存储、图查询、图投影收口 |
| `pipelines/document_index_pipeline.py` | `domains/documents/index_pipeline.py` 或 `workflow/jobs/` | 先保留主链编排，后续再决定下沉 |
| `pipelines/analysis_pipeline.py` | `domains/profile/` 或 `workflow/jobs/` | 看是领域逻辑还是长任务逻辑 |
| `clients/*.py` | `infra/*` 对应子层 | 外部依赖适配天然属于基础设施 |
| `infra/task_queue.py` / `infra/celery_app.py` | `workflow/queue/` 或 `infra/queue/` | 运行时执行层 |
| `tasks/index_tasks.py` | `workflow/jobs/index_job.py` | 异步任务外壳 |
| `models/*.py` | `domains/*/models.py` 或共享主模型层 | 按领域逐步回收 |
| `crud/` | `domains/*/repository.py` | 用领域仓储接口收口 |

你今天不要求一次把答案定死，  
但必须先有一版足够能指导后面 5 天的映射草案。

---

## 第 6 层：Day 2 必须把“阶段顺序”拆出来

今天不能只说“以后要优化架构”，  
必须把顺序拆出来。

推荐你把后续顺序固定成下面这条：

```text
Phase A
  先稳定主链定义
  Day 3 - Day 7
  重点是 MemoryEntry、Evidence、Hybrid Retrieval

Phase B
  再把图层真正接入主链
  Day 8 - Day 11
  重点是 GraphRAG、Graph Projection、Outbox

Phase C
  再做长期记忆收敛
  Day 12 - Day 14
  重点是 CanonicalMemory、Snapshot、Timeline

Phase D
  再做 Debug / Eval / Analysis
  Day 15 - Day 17
  重点是可解释、可评测、可分析

Phase E
  最后收入口、分层和技术减重
  Day 18 - Day 20
  重点是 thin entry、领域分层、LlamaIndex / MongoDB 裁剪式接管
```

这条顺序有一个核心原则：

> 先把业务主链做对，再把工程结构收好，最后再引成熟框架减重。

---

## 第 7 层：结合当前仓库，Day 2 最小落点应该放在哪

今天最值得你反复看的真实文件是这些：

| 文件 | 今天为什么要看 |
|---|---|
| `main.py` | 明确为什么 Day 18 要做薄入口 |
| `routers/documents.py` | 看文档入口和业务边界 |
| `routers/chat.py` | 看问答入口如何连到检索主链 |
| `services/document_service.py` | 看文档侧业务入口 |
| `services/query_service.py` | 看检索问答逻辑入口 |
| `services/context_service.py` | 看多源上下文是如何组织的 |
| `services/memory_service.py` | 看 `MemoryEntry` 当前已经做到哪里 |
| `services/graph_projection_service.py` | 看图投影如何切入后面几天 |
| `pipelines/document_index_pipeline.py` | 看主链编排已经具备哪些雏形 |
| `clients/vector_store_client.py` | 看向量层是否适合后续交给 LlamaIndex |
| `clients/neo4j_client.py` | 看图层目前是存取层还是已具备更高层语义 |
| `tasks/index_tasks.py` | 看异步执行层未来怎么变成 `workflow/jobs` |
| `Mneme_polish_v4.md` | 看完整路线和减重策略 |
| `company_target/day1-day20-summary.md` | 确保 Day 2 不跑偏 |

今天不需要再去“扫全仓”，  
而是要从这些文件提炼出可被蓝图吸收的结构事实。

---

## 第 8 层：Day 2 最小输出文件应该有哪些

今天结束前，推荐你至少拿到下面这些输出：

```text
company_target/
  day2.md
  day2_target_blueprint.md
  day2_layer_mapping.md
  day2_phase_plan.md
  day2_memoryentry_handoff.md
```

它们分别回答的问题是：

| 输出文件 | 回答什么问题 |
|---|---|
| `day2_target_blueprint.md` | 目标主链到底长什么样 |
| `day2_layer_mapping.md` | 当前目录以后应该落到哪一层 |
| `day2_phase_plan.md` | 后面 18 天为什么按这个顺序推进 |
| `day2_memoryentry_handoff.md` | Day 3 为什么应该先做 `MemoryEntry` |

---

## 第 9 层：Day 2 不建议做什么

今天不建议做这些：
- 不要新建一整套最终目录。
- 不要大规模移动文件。
- 不要先改全仓 import。
- 不要把 `LlamaIndex` 当成今天的主题。
- 不要把 `MongoDB` 当成今天的主题。
- 不要把 Day 2 写成“技术选型对比文”。

今天真正的目标是：

> 用最少的动作，把后面 18 天的主线和代码落位彻底讲顺。

---

## 上午学习：9:00 - 12:00

## 09:00 - 09:50：把 Day 1 的审计结果收口成目标主链

今天第一段不要碰实现，  
先把 Day 1 的“现状描述”翻译成 Day 2 的“目标链路描述”。

### 你要输出的最小结论
- 当前 Mneme 已经不是空项目，而是一个有文档、检索、任务、图存储雏形的后端。
- 当前主链仍然偏 `Chunk RAG`，还没有真正统一到 `MemoryEntry`。
- 后续蓝图要围绕 `MemoryEntry -> Evidence -> GraphRAG -> Snapshot -> Eval` 展开。

### 推荐你写成这张对照表

| 当前 | 目标 |
|---|---|
| `Document -> Chunk -> Retrieval -> Answer` | `Document -> Chunk -> MemoryEntry -> Hybrid Retrieval -> GraphRAG -> Evidence Answer` |
| `services` 平铺 | 按 `domains/*` 收口 |
| `main.py` 入口渐重 | `bootstrap + thin main` |
| 图层已有基础 | 图层正式进入主链 |
| 评测和分析分散 | Debug / Eval / Analysis 独立成闭环 |

---

## 09:50 - 10:40：把分层职责固定成统一口径

这一段的关键不是写更多术语，  
而是保证你后面每天说的“这一层”都是同一种意思。

### 今天必须固定住的分层解释

```text
api = 入站和响应
core = 配置、容器、上下文、共享协议
domains = 业务领域
workflow = 长任务、状态和回放
infra = 外部依赖和运行时适配
```

### 今天要避免的误区
- 误区：把 `services` 整体直接等同于未来的 `domains`。
  规避建议：先承认它是“业务入口和领域逻辑混层”的过渡层。
- 误区：把 `clients` 视为“工具目录”。
  规避建议：把它当作未来 `infra` 的雏形。

---

## 10:40 - 11:30：做当前目录到目标分层的第一版映射

这一段你最需要的是“先可用”，不是“先完美”。

### 今天至少要映射这些目录
- `routers`
- `schemas`
- `services`
- `pipelines`
- `clients`
- `infra`
- `tasks`
- `models`
- `crud`

### 今天的合格标准
- 每个目录至少知道以后大致落哪一层。
- 每个目录至少知道为什么这样落。
- 至少指出 3 个最混层的地方。

---

## 11:30 - 12:00：写出 Day 3 之前的阶段顺序

这一段不要泛泛说“后面再做”，  
要明确 Day 3 为什么先做 `MemoryEntry`。

### 推荐你固定成下面这句话

> 因为没有 `MemoryEntry` 正式进入主链，后面的 Evidence、Hybrid Retrieval、GraphRAG、Snapshot、Eval 都只能漂在外面，无法形成长期记忆系统的统一核心对象。

---

## 下午编码：14:00 - 18:00

## 14:00 - 15:00：生成 Day 2 目标蓝图文档

这一段的目标不是做应用代码，  
而是做一个能帮助你自动整理 Day 2 蓝图的最小脚本。

### 练手骨架版

```python
from pathlib import Path


class TargetArchitectureBlueprintBuilder:
    def __init__(self, project_root: Path) -> None:
        # 你要做的事：
        # 1. 保存项目根目录
        # 2. 预留输出目录 company_target
        # 3. 不要在初始化里做重 IO
        raise NotImplementedError

    def current_chain(self) -> list[str]:
        # 你要做的事：
        # 1. 返回当前 Mneme 的主链节点列表
        # 2. 节点必须基于真实仓库，不要写想象中的模块
        raise NotImplementedError

    def target_chain(self) -> list[str]:
        # 你要做的事：
        # 1. 返回目标长期记忆系统的主链节点列表
        # 2. 要包含 MemoryEntry、GraphRAG、Evidence 等关键节点
        raise NotImplementedError

    def stage_plan(self) -> list[tuple[str, str]]:
        # 你要做的事：
        # 1. 返回阶段名称和重点说明
        # 2. 阶段顺序要和 day1-day20-summary 保持一致
        raise NotImplementedError

    def build_markdown(self) -> str:
        # 你要做的事：
        # 1. 组装 current chain、target chain、stage plan
        # 2. 输出成一个自解释的 Markdown 文本
        # 3. 文本里要让 Day 3 能直接看懂该接什么
        raise NotImplementedError

    def output_path(self) -> Path:
        # 你要做的事：
        # 1. 返回 day2_target_blueprint.md 的路径
        raise NotImplementedError

    def write(self) -> Path:
        # 你要做的事：
        # 1. 调用 build_markdown
        # 2. 确保父目录存在
        # 3. 以 UTF-8 写入目标文件
        raise NotImplementedError


def main() -> None:
    # 你要做的事：
    # 1. 以当前仓库根目录初始化 builder
    # 2. 执行写入
    # 3. 打印输出路径
    raise NotImplementedError
```

### 参考答案版

```python
from pathlib import Path


class TargetArchitectureBlueprintBuilder:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.target_dir = project_root / "company_target"

    def current_chain(self) -> list[str]:
        return [
            "main.py",
            "routers/documents.py",
            "services/document_service.py",
            "pipelines/document_index_pipeline.py",
            "services/query_service.py",
            "clients/vector_store_client.py",
            "answer",
        ]

    def target_chain(self) -> list[str]:
        return [
            "Document",
            "Chunk",
            "MemoryEntry",
            "CanonicalMemory / Profile Snapshot",
            "Hybrid Retrieval",
            "GraphRAG Expansion",
            "Evidence-based Answer",
            "Debug / Eval / Analysis",
        ]

    def stage_plan(self) -> list[tuple[str, str]]:
        return [
            ("Phase A", "Day 3 - Day 7：MemoryEntry、Evidence、Hybrid Retrieval"),
            ("Phase B", "Day 8 - Day 11：GraphRAG、Graph Projection、Outbox"),
            ("Phase C", "Day 12 - Day 14：CanonicalMemory、Snapshot、Timeline"),
            ("Phase D", "Day 15 - Day 17：Debug、Eval、DuckDB Analysis"),
            ("Phase E", "Day 18 - Day 20：thin entry、分层收口、LlamaIndex / MongoDB 减重"),
        ]

    def build_markdown(self) -> str:
        current = "\n".join(f"- {item}" for item in self.current_chain())
        target = "\n".join(f"- {item}" for item in self.target_chain())
        stages = "\n".join(f"- `{name}`：{desc}" for name, desc in self.stage_plan())
        return "\n".join(
            [
                "# Day 2 目标架构蓝图",
                "",
                "## 当前主链",
                current,
                "",
                "## 目标主链",
                target,
                "",
                "## 阶段顺序",
                stages,
                "",
                "## Day 3 要接住的事情",
                "- 把 `MemoryEntry` 正式拉进主链。",
                "- 不再让它只是附属分析结果。",
                "- 为后续 Evidence 和 GraphRAG 提供统一核心对象。",
            ]
        )

    def output_path(self) -> Path:
        return self.target_dir / "day2_target_blueprint.md"

    def write(self) -> Path:
        self.target_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_path()
        path.write_text(self.build_markdown(), encoding="utf-8")
        return path


def main() -> None:
    builder = TargetArchitectureBlueprintBuilder(Path.cwd())
    path = builder.write()
    print(path)
```

---

## 15:00 - 16:10：生成目录分层映射表

这一段的目标是把“未来落哪一层”固定成文档，而不是只留在脑子里。

### 练手骨架版

```python
from pathlib import Path


class LayerMappingBuilder:
    def __init__(self, project_root: Path) -> None:
        # 你要做的事：
        # 1. 保存项目根目录
        # 2. 预设需要映射的目录列表
        raise NotImplementedError

    def source_directories(self) -> list[str]:
        # 你要做的事：
        # 1. 返回当前仓库最关键的源目录
        # 2. 至少包括 routers、services、pipelines、clients、infra、tasks
        raise NotImplementedError

    def target_layer_for(self, name: str) -> str:
        # 你要做的事：
        # 1. 把当前目录名映射到目标层
        # 2. 返回值要足够稳定，方便后续写 Markdown 表
        raise NotImplementedError

    def reason_for(self, name: str) -> str:
        # 你要做的事：
        # 1. 给每个目录写一句映射原因
        # 2. 原因要贴近 Mneme 真实现状
        raise NotImplementedError

    def build_markdown(self) -> str:
        # 你要做的事：
        # 1. 产出一个 Markdown 表格
        # 2. 让 Day 3 之后能直接按这张表继续演进
        raise NotImplementedError

    def output_path(self) -> Path:
        # 你要做的事：
        # 1. 返回 day2_layer_mapping.md 的路径
        raise NotImplementedError

    def write(self) -> Path:
        # 你要做的事：
        # 1. 写出 Markdown 文件
        raise NotImplementedError


def main() -> None:
    # 你要做的事：
    # 1. 初始化 builder
    # 2. 生成映射文档
    raise NotImplementedError
```

### 参考答案版

```python
from pathlib import Path


class LayerMappingBuilder:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.target_dir = project_root / "company_target"

    def source_directories(self) -> list[str]:
        return [
            "routers",
            "schemas",
            "services",
            "pipelines",
            "clients",
            "infra",
            "tasks",
            "models",
            "crud",
        ]

    def target_layer_for(self, name: str) -> str:
        mapping = {
            "routers": "api/routes",
            "schemas": "api/schemas 或 domains/*/schemas.py",
            "services": "domains/*/service.py",
            "pipelines": "domains/*/pipeline.py 或 workflow/jobs",
            "clients": "infra/*",
            "infra": "core/* 或 infra/*",
            "tasks": "workflow/jobs",
            "models": "domains/*/models.py",
            "crud": "domains/*/repository.py",
        }
        return mapping.get(name, "待定")

    def reason_for(self, name: str) -> str:
        reasons = {
            "routers": "当前已经是入站层雏形，应继续收口为 API 层。",
            "schemas": "当前承担请求响应和 DTO 角色，后续按用途分流。",
            "services": "当前是业务入口与领域逻辑混层，后续要按领域回收。",
            "pipelines": "当前是主链编排雏形，后续再决定保留在领域侧还是下沉到 workflow。",
            "clients": "当前本质上是外部依赖适配层。",
            "infra": "当前是运行时能力集合，后续需要更清晰地区分核心规则和底层适配。",
            "tasks": "当前是异步任务入口，适合演进成 workflow jobs。",
            "models": "当前是主数据模型层，后续按领域收口更清晰。",
            "crud": "当前是数据访问层，后续适合演进成 repository 语义。",
        }
        return reasons.get(name, "待补充")

    def build_markdown(self) -> str:
        lines = [
            "# Day 2 分层映射表",
            "",
            "| 当前目录 | 目标落位 | 原因 |",
            "|---|---|---|",
        ]
        for name in self.source_directories():
            lines.append(
                f"| `{name}` | `{self.target_layer_for(name)}` | {self.reason_for(name)} |"
            )
        return "\n".join(lines)

    def output_path(self) -> Path:
        return self.target_dir / "day2_layer_mapping.md"

    def write(self) -> Path:
        self.target_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_path()
        path.write_text(self.build_markdown(), encoding="utf-8")
        return path


def main() -> None:
    builder = LayerMappingBuilder(Path.cwd())
    path = builder.write()
    print(path)
```

---

## 16:10 - 17:00：整理 Day 3 的 `MemoryEntry` 交接输入

这一段的目标是让明天不是“随便挑一块开始改”，  
而是明确为什么应该先从 `MemoryEntry` 开始。

### Day 3 最需要接住的一句话

> Day 3 不是先做图，也不是先做评测，而是先把 `MemoryEntry` 正式变成长期记忆系统里的核心对象。只有主对象稳定了，后面的 Evidence、Hybrid Retrieval、GraphRAG 才会真正有统一中心。

### 你今天至少要写下这 4 点
- `MemoryEntry` 当前在哪些文件里已经出现。
- 它现在为什么还没有成为真正主链对象。
- 它进入主链后最先影响哪几条流程。
- Day 3 最合理的第一落点在哪些文件。

---

## 17:00 - 18:00：补齐 Day 2 的阶段计划文档

这一段要把后面 18 天的顺序写成能直接复用的文档。

### 推荐最小内容
- 为什么先做 `MemoryEntry / Evidence / Retrieval`。
- 为什么图层不应该早于核心对象入链。
- 为什么 `Eval / Debug / Analysis` 必须建立在前面主链稳定之后。
- 为什么 `LlamaIndex / MongoDB` 应该最后作为减重策略切入。

---

## 晚上复盘：20:00 - 21:00

晚上复盘不要复述一天做了什么，  
而要回答下面这些问题：

1. 你能不能不看仓库，直接讲出“当前链路”和“目标链路”的差异？
2. 你能不能说清楚为什么 `MemoryEntry` 是 Day 3，而不是图层或评测先上？
3. 你能不能说清楚 `services / pipelines / clients / tasks` 分别以后要落哪？
4. 你能不能解释为什么 Day 2 还不能急着引入 `LlamaIndex / MongoDB`？
5. 你今天产出的文档，明天能不能直接拿来开工？

如果其中有两题回答不顺，说明今天还没有真正收口。

---

## 今日验收标准

- 你能清楚讲出 `Mneme` 当前主链和目标主链。
- 你能清楚讲出目标分层不是为了好看，而是为了给后续能力落位。
- 你至少产出一份目标蓝图文档和一份目录映射文档。
- 你能把 Day 3 的 `MemoryEntry` 交接说明写清楚。
- 你没有把 Day 2 写成全量重构计划，也没有提前冲进实现细节。

---

## 今天最容易踩的坑

- 问题：把 Day 2 做成“概念很多，但跟仓库没关系”。
  规避建议：所有蓝图都要回指真实文件，比如 `main.py`、`services/memory_service.py`、`tasks/index_tasks.py`。

- 问题：把 Day 2 做成“已经开始大迁移目录”。
  规避建议：今天只做蓝图、映射和阶段顺序，不做大面积迁移。

- 问题：把 Day 2 做成“技术选型讨论会”。
  规避建议：`LlamaIndex / MongoDB` 只点到后面 Day 20 的减重阶段，不抢今天主题。

- 问题：把 Day 2 写成“纯架构图”，没有 Day 3 可用输入。
  规避建议：必须补一份 `MemoryEntry` 交接说明。

---

## 给明天的交接提示

Day 3 要接住的不是“继续谈架构”，  
而是基于今天的蓝图，正式把 `MemoryEntry` 拉进主链。

明天开始之前，你应该已经具备这 4 份输入：

```text
当前链路 vs 目标链路对照
-> 目录到目标分层的映射表
-> 阶段推进顺序
-> MemoryEntry 进入主链的理由和落点
```

到了 Day 3，就不要再反复讨论“整体方向对不对”，  
而是直接进入：

```text
Document
-> Chunk
-> MemoryEntry
-> 去重 / 合并 / 置信度
-> 图投影准备
```

这就是 Day 2 最终要交给 Day 3 的东西。
