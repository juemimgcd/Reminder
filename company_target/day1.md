# Day 1：明确长期记忆系统方向 + 架构优化边界

## 今天的总目标

- 把 Mneme 从“已经能跑的 Chunk RAG 后端”重新定义成“要演进成长期记忆系统的后端”
- 把本轮优化的重点从“继续堆功能”切换成“先讲清楚主链、边界、分层和减重顺序”
- 基于当前真实仓库做一次架构审计，明确哪些位置已经适合保留，哪些位置必须后续收口
- 产出 Day 2 可以直接接住的输入：目标链路图、边界清单、目录分层草案、阶段优先级

## 今天结束前，你必须拿到什么

- 一份你自己能讲清楚的优化边界认知
- 一张当前 Mneme 的“现状主链路图”
- 一张目标 Mneme 的“长期记忆系统主链路图”
- 一份“这轮先不做什么”的清单
- 一份“当前仓库文件应该怎么看”的结构审计记录
- 一份能交给 Day 2 继续使用的架构分层草案

---

## Day 1 一图总览

```mermaid
flowchart LR
    A[当前 Mneme 仓库] --> B[识别当前主链路]
    B --> C[识别当前结构问题]
    C --> D[明确目标系统不是文档问答而是长期记忆]
    D --> E[明确本轮边界与非目标]
    E --> F[得到 Day 2 的架构分层输入]
```

---

## 为什么这一天重要

Day 1 不解决“怎么实现所有能力”，  
而是先解决“接下来 20 天到底在优化什么”。

如果这一天讲不清楚，后面很容易发生 4 件事：

- 一边想做长期记忆，一边还是按普通 RAG 的心智写代码
- 一边说要做架构优化，一边只是机械搬目录
- 一边觉得 LlamaIndex / MongoDB 很好，一边又不知道该接管哪一层
- 一边想靠近公司项目，一边把当前仓库直接带进大重构失控区

所以 Day 1 的任务不是写重代码，  
而是把“方向、边界、顺序”钉死。

---

## Day 1 整体架构

今天你要同时看清楚两张图。

第一张图是当前 Mneme 更接近什么：

```text
Document
  -> Chunk
  -> Embedding
  -> Vector Retrieval
  -> RAG Answer
```

第二张图是目标 Mneme 要走向什么：

```text
Document
  -> Chunk
  -> MemoryEntry
  -> CanonicalMemory / Snapshot
  -> Chunk + Memory + Graph Retrieval
  -> Evidence-based Answer
  -> Eval / Debug / Analysis
```

你今天最重要的工作，就是把这两个形态之间的差距说清楚。

---

## 今天的边界要讲透

### 今天之后，各层职责应该怎么理解

从 Day 1 开始，你就要把后续架构按下面这套边界来理解：

```text
api
  负责入站请求、参数校验、响应结构

application service
  负责业务编排与主链路调度

domain
  负责 documents / retrieval / memory / graph / profile / tasks 等领域边界

workflow
  负责长任务、状态机、异步执行、回放

infra
  负责 vector store、graph store、cache、retry、rate limit 等基础设施适配
```

### 对当前仓库的处理原则

今天你不是来推翻仓库的。

当前仓库里这些位置要先按“现状入口”理解：

- `main.py`
- `routers/`
- `services/`
- `pipelines/`
- `clients/`
- `models/`
- `schemas/`
- `crud/`
- `infra/`

今天先做的是：

```text
看懂
归类
圈边界
找主链
记问题
```

不是：

```text
大改
大搬
大重命名
大拆目录
```

### 先不要急着做这些

今天先不要急着：

- 引入 LlamaIndex
- 引入 MongoDB
- 重构所有 `utils`
- 重写所有 `services`
- 先做完整 `workflow`
- 先做公司项目级插件化
- 先做复杂前端可视化

原因很简单：

> 如果 Day 1 连“当前系统是什么、目标系统是什么、为什么这样分层”都没讲清楚，后面任何技术选型都会失焦。

---

## 第 1 层：Day 1 的本质是什么

Day 1 的本质不是“开始重构”，而是：

```text
建立统一心智模型
```

你要把下面这句话讲顺：

> Mneme 当前已经不是一个空项目，它已经有上传、切分、向量化、检索、问答这些基础能力。  
> 现在的问题不是“功能完全没有”，而是“系统还停留在 Chunk RAG + 平铺结构 + 自研编排偏重”的阶段。  
> 所以本轮要做的是把它升级成长期记忆系统，同时把架构做成可持续演进的样子。

如果这句话你讲不顺，说明 Day 1 还没做完。

---

## 第 2 层：Day 1 的主链一定要从“当前真实仓库”出发

今天不要从想象中的新系统出发，  
一定要从当前真实仓库出发。

建议你重点审这几条真实链路：

```text
main.py
  -> routers/documents.py
  -> services/document_service.py
  -> pipelines/document_index_pipeline.py
  -> services/memory_service.py
  -> clients/vector_store_client.py
  -> clients/neo4j_client.py
```

你今天要看懂的是：

```text
当前的上传链路在哪里
当前的索引链路在哪里
当前的记忆抽取已经做到哪一步
当前的图层能力已经做到哪一步
当前的主入口为什么会逐渐变重
```

---

## 第 3 层：Day 1 必须先讲清楚“当前系统像什么”

你可以把当前 Mneme 暂时理解成：

```text
一个已经有基础文档索引和问答能力的 FastAPI 后端
一个开始具备 MemoryEntry 和 Graph 投影能力的 RAG 系统
一个还没有完成长期记忆主链闭环的工程化原型
```

它已经有这些东西：

- 文档上传与列表
- 文档索引任务入口
- Chunk 存储
- MemoryEntry 抽取
- 向量检索
- Neo4j 图投影基础
- TaskRecord / Celery / worker 雏形

但它还缺这些“真正决定下一阶段质量”的东西：

- 以 MemoryEntry 为中心的系统视角
- 统一的 Hybrid Search 编排
- 稳定的 GraphRAG 召回层
- 可解释的 Retrieval Debug
- 可量化的 Eval 闭环
- 更清楚的 `api / core / domains / workflow / infra` 分层

---

## 第 4 层：Day 1 必须先讲清楚“目标系统像什么”

目标 Mneme 不是：

```text
继续把更多 prompt、更多工具、更多检索逻辑塞进现有目录
```

目标 Mneme 应该更接近：

```text
长期记忆后端
  以 MemoryEntry 为主资产
  以 Chunk + Memory + Graph 联合检索为主回答链路
  以 Evidence 为回答约束
  以 TaskRecord / Outbox 保证可靠性
  以 Eval / DuckDB 建立反馈闭环
  以模块分层和可选框架减重保证后续可持续演进
```

这一天你一定要把“目标系统长什么样”说得足够具体，  
否则 Day 2 的架构分层会变成空话。

---

## 第 5 层：Day 1 最小架构输出应该有哪些

今天结束前，不要求你改业务代码，  
但要求你至少得到这 5 份输出：

```text
1. 当前主链路审计
2. 当前结构问题审计
3. 目标链路草图
4. 分层职责草图
5. 非目标清单
```

推荐输出文件放在：

```text
company_target/
  day1.md
  day1_boundary_audit.md
  day1_architecture_snapshot.md
  day1_non_goals.md
```

这里最重要的一点是：

> Day 1 的落点不是“新功能”，而是“可交给 Day 2 的清晰输入”。

---

## 第 6 层：结合当前仓库，Day 1 最小落点应该放在哪

今天建议重点观察这些真实文件：

| 文件 | 今天为什么要看 |
|---|---|
| `main.py` | 看入口当前有多重、后续为什么要变薄 |
| `routers/documents.py` | 看路由层是否已经开始承担过多编排 |
| `services/document_service.py` | 看任务提交和业务编排的边界 |
| `pipelines/document_index_pipeline.py` | 看“主链路阶段执行”是否已经有雏形 |
| `services/memory_service.py` | 看 MemoryEntry 目前进入系统的深度 |
| `clients/vector_store_client.py` | 看向量层现在多重、后续为什么有 LlamaIndex 接手空间 |
| `clients/neo4j_client.py` | 看图层当前只是存取层，还是已经具备更高层价值 |
| `company_target/day1-day20-summary.md` | 看 20 天总路线，确保 Day 1 不跑偏 |
| `Mneme_polish_v4.md` | 看详细阶段路线和架构收口方向 |

你今天不要试图看完整个仓库，  
而是要围绕这几条关键文件抓住主线。

---

## 第 7 层：Day 1 最小接口建议长什么样

Day 1 不需要新开业务接口，  
但如果你想辅助自己做审计，可以准备一个最小脚本或最小结构化输出。

例如你今天可以把“审计结果”收敛成这样的对象：

```text
CurrentArchitectureAudit
  current_core_chain
  heavy_entry_files
  boundary_problems
  target_direction
  non_goals
  day2_handoff
```

这样做的意义是：

```text
避免 Day 1 最后只留下散乱笔记
避免 Day 2 重新重新整理同一批事实
让后续 20 天计划有统一输入源
```

---

## 第 8 层：Day 1 不建议做什么

今天不建议做：

- 直接重写 `main.py`
- 直接新建全套 `app/mneme/` 目录
- 直接上 LlamaIndex 改主链
- 直接上 MongoDB 替主存储
- 直接重写 `documents` 领域
- 直接做 Eval 数据表
- 直接做前后端联调

今天真正要避免的坑只有一句话：

> 用“立刻改代码”的冲动，替代“先讲清楚架构方向”的工作。

---

## 上午学习：09:00 - 12:00

## 09:00 - 09:50：把 Day 1 的主问题讲顺

### 今天你必须能顺着说出来

```text
Mneme 现在是什么
Mneme 现在最关键的问题是什么
Mneme 要升级成什么
为什么本轮先做长期记忆与架构收口，而不是继续堆外围功能
```

### 你必须能回答这两个问题

1. 为什么当前 Mneme 不能只按“文档问答后端”理解？
2. 为什么 Day 1 不应该直接进入大重构？

---

## 09:50 - 10:40：沿真实链路做最小审计

### 建议你先顺着这条链路看

```text
main.py
-> routers/documents.py
-> services/document_service.py
-> pipelines/document_index_pipeline.py
-> services/memory_service.py
-> clients/vector_store_client.py
-> clients/neo4j_client.py
```

### 今天你要特别记 4 类东西

- 当前主入口位置
- 当前索引主链位置
- 当前记忆进入点
- 当前图层进入点

### 一个简单判断标准

如果一个文件同时承担下面多类职责，就要记为“后续可能过重”：

```text
参数处理
业务编排
外部依赖调用
任务调度
响应拼装
```

---

## 10:40 - 11:30：明确目标系统与非目标

### 本轮明确要做

- MemoryEntry 主链路化
- Evidence 回答
- Hybrid Search
- GraphRAG
- TaskRecord / Outbox
- Eval / DuckDB
- 入口变薄、领域收口、减重策略

### 本轮先不做主线

- 多模态
- 重插件化
- 复杂租户与 RBAC
- 过早平台型后台
- 先全量替换底层存储

### 这一步最重要的产出

你要得到一句非常稳定的话：

> 本轮优化的重点不是把 Mneme 做得更大，而是把它做得更像“长期记忆系统”并且更像“可继续演进的后端架构”。

---

## 11:30 - 12:00：先决定今天怎么验收

### Day 1 最直接的验收方式

- 你能自己画出当前系统主链路
- 你能自己画出目标系统主链路
- 你能说出今天明确不做什么
- 你能说出 Day 2 应该从哪些输入开始

### 如果你说不清楚，说明今天还没完成

不是因为代码没写够，  
而是因为 Day 1 本来就不是靠代码量验收的。

---

## 下午编码：14:00 - 18:00

## 14:00 - 14:40：整理 `company_target/day1_boundary_audit.md`

### 今天建议新增

- `company_target/day1_boundary_audit.md`
- 可选辅助脚本：`scripts/day1_repo_audit.py`

### `scripts/day1_repo_audit.py` 练手骨架版

```python
from pathlib import Path


class RepoAuditBuilder:
    def __init__(self, repo_root: Path) -> None:
        # 你要做的事情：
        # 1. 保存仓库根目录
        # 2. 准备今天要审计的关键文件列表
        # 3. 不要在初始化里做重 IO
        raise NotImplementedError

    def build_target_paths(self) -> list[Path]:
        # 你要做的事情：
        # 1. 返回 Day 1 重点审计的真实文件路径
        # 2. 路径应覆盖 main.py、routers/documents.py、services/document_service.py 等主链位置
        # 3. 只返回存在或应该重点关注的路径
        raise NotImplementedError

    def classify_path(self, path: Path) -> str:
        # 你要做的事情：
        # 1. 根据路径位置判断它更接近 entry / router / service / pipeline / client / infra
        # 2. 返回统一类别字符串
        # 3. 不要在这里写复杂业务判断
        raise NotImplementedError

    def build_markdown(self) -> str:
        # 你要做的事情：
        # 1. 组装审计 Markdown
        # 2. 包含当前主链、重点文件、结构问题、Day 2 输入
        # 3. 返回最终文本
        raise NotImplementedError


def main() -> None:
    # 你要做的事情：
    # 1. 以当前仓库根目录初始化 RepoAuditBuilder
    # 2. 生成 Markdown 审计内容
    # 3. 打印或写出结果，供 day1_boundary_audit.md 使用
    raise NotImplementedError


if __name__ == "__main__":
    main()
```

### `scripts/day1_repo_audit.py` 参考答案

```python
from pathlib import Path


class RepoAuditBuilder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self._targets = [
            "main.py",
            "routers/documents.py",
            "services/document_service.py",
            "pipelines/document_index_pipeline.py",
            "services/memory_service.py",
            "clients/vector_store_client.py",
            "clients/neo4j_client.py",
            "Mneme_polish_v4.md",
            "company_target/day1-day20-summary.md",
        ]

    def build_target_paths(self) -> list[Path]:
        return [self.repo_root / item for item in self._targets]

    def classify_path(self, path: Path) -> str:
        normalized = str(path).replace("\\", "/")
        if normalized.endswith("main.py"):
            return "entry"
        if "/routers/" in normalized:
            return "router"
        if "/services/" in normalized:
            return "service"
        if "/pipelines/" in normalized:
            return "pipeline"
        if "/clients/" in normalized:
            return "client"
        if "/infra/" in normalized:
            return "infra"
        return "support"

    def build_markdown(self) -> str:
        lines = [
            "# Day 1 边界审计表",
            "",
            "## 当前主链路",
            "",
            "- 入口：`main.py`",
            "- 上传与索引入口：`routers/documents.py`",
            "- 任务提交与业务编排：`services/document_service.py`",
            "- 阶段执行链路：`pipelines/document_index_pipeline.py`",
            "- 记忆抽取：`services/memory_service.py`",
            "- 向量层：`clients/vector_store_client.py`",
            "- 图层：`clients/neo4j_client.py`",
            "",
            "## 重点文件分类",
            "",
        ]
        for path in self.build_target_paths():
            lines.append(f"- `{path.relative_to(self.repo_root)}` -> {self.classify_path(path)}")
        lines.extend(
            [
                "",
                "## Day 2 输入",
                "",
                "- 当前主链路已经存在，但需要明确分层收口",
                "- 需要把长期记忆、GraphRAG 和任务可靠性串成统一架构",
            ]
        )
        return "\n".join(lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    builder = RepoAuditBuilder(repo_root=repo_root)
    print(builder.build_markdown())


if __name__ == "__main__":
    main()
```

### 这一步真正要得到什么

不是脚本本身，  
而是一份你自己能继续看的边界审计表。

---

## 14:40 - 15:20：整理 `company_target/day1_architecture_snapshot.md`

### 今天建议新增

- `company_target/day1_architecture_snapshot.md`
- 可选辅助脚本：`scripts/day1_architecture_snapshot.py`

### `scripts/day1_architecture_snapshot.py` 练手骨架版

```python
from pathlib import Path


class ArchitectureSnapshotBuilder:
    def __init__(self, repo_root: Path) -> None:
        # 你要做的事情：
        # 1. 保存仓库根目录
        # 2. 准备当前链路和目标链路的固定描述
        # 3. 保持这个类只负责输出结构化摘要
        raise NotImplementedError

    def current_chain(self) -> list[str]:
        # 你要做的事情：
        # 1. 返回当前 Mneme 的主链路描述
        # 2. 这条链路应以 Chunk RAG 为核心
        raise NotImplementedError

    def target_chain(self) -> list[str]:
        # 你要做的事情：
        # 1. 返回目标 Mneme 的主链路描述
        # 2. 这条链路应以 MemoryEntry + Graph + Evidence 为核心
        raise NotImplementedError

    def build_markdown(self) -> str:
        # 你要做的事情：
        # 1. 输出“当前是什么、目标是什么、差距是什么”
        # 2. 明确 Day 2 需要接住的分层任务
        raise NotImplementedError


def main() -> None:
    # 你要做的事情：
    # 1. 创建 ArchitectureSnapshotBuilder
    # 2. 输出 Markdown 结果
    raise NotImplementedError


if __name__ == "__main__":
    main()
```

### `scripts/day1_architecture_snapshot.py` 参考答案

```python
from pathlib import Path


class ArchitectureSnapshotBuilder:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def current_chain(self) -> list[str]:
        return [
            "Document",
            "Chunk",
            "Embedding",
            "Vector Retrieval",
            "RAG Answer",
        ]

    def target_chain(self) -> list[str]:
        return [
            "Document",
            "Chunk",
            "MemoryEntry",
            "CanonicalMemory / Snapshot",
            "Chunk + Memory + Graph Retrieval",
            "Evidence-based Answer",
        ]

    def build_markdown(self) -> str:
        current = " -> ".join(self.current_chain())
        target = " -> ".join(self.target_chain())
        return "\n".join(
            [
                "# Day 1 架构快照",
                "",
                "## 当前主链路",
                "",
                f"`{current}`",
                "",
                "## 目标主链路",
                "",
                f"`{target}`",
                "",
                "## Day 2 要接住的事情",
                "",
                "- 把目标链路拆成阶段",
                "- 把当前仓库映射到未来分层",
                "- 明确哪些位置先不改，只做收口设计",
            ]
        )


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    builder = ArchitectureSnapshotBuilder(repo_root=repo_root)
    print(builder.build_markdown())


if __name__ == "__main__":
    main()
```

### 你一定要看懂的点

- 当前链路和目标链路必须同时存在
- Day 1 不是只批判当前系统
- Day 1 的真正价值是把“升级方向”写成可传递文本

---

## 15:20 - 16:10：整理 Day 1 的非目标清单

### 建议直接写到 `company_target/day1_non_goals.md`

### 推荐至少写这几类

- 当前先不做的功能边界
- 当前先不做的架构边界
- 当前先不切换的技术栈边界
- 当前先不拆的目录边界

### 为什么 Day 1 一定要写这份东西

因为后面 Day 5、Day 10、Day 18 以后，  
你会非常想顺手多做很多事。

这份清单的作用，就是持续提醒你：

> 本轮优化是为了让主链更稳，不是为了让系统看起来更全。

---

## 16:10 - 17:00：整理 Day 2 的架构输入

### 今天建议你输出这张表

| 当前层 | 当前仓库真实位置 | 后续建议方向 |
|---|---|---|
| 入口层 | `main.py` | 变薄，进入 `bootstrap` 装配 |
| API 层 | `routers/` | 收口到 `api/` 与领域 router |
| 业务编排层 | `services/` | 逐步按 `documents / retrieval / memory / graph` 收口 |
| 阶段执行层 | `pipelines/` | 保留为主链路阶段执行层 |
| 外部依赖层 | `clients/` | 继续外部适配，但后续评估被 LlamaIndex 部分接管 |
| 可靠性层 | `infra/` | 保留并逐步增强 |
| 长任务层 | `tasks/` | 后续进入 `workflow/` |

### Day 2 最需要接住的一句话

> Day 2 不是凭空设计新架构，而是把 Day 1 看清楚的真实仓库，映射成一个可以逐步演进到 `api / core / domains / workflow / infra` 的结构。

---

## 17:00 - 18:00：自己讲一遍 Day 1 的完整结论

### 你至少要能独立讲顺这 8 个点

1. Mneme 当前已经具备哪些基础能力。
2. Mneme 当前为什么还不是真正的长期记忆系统。
3. 为什么本轮主线要围绕 MemoryEntry、GraphRAG、Evidence、Eval。
4. 为什么 Day 1 先不大改代码。
5. 当前仓库里最值得看的真实主链位置在哪。
6. 为什么后续要从平铺目录演进到领域化收口。
7. LlamaIndex 和 MongoDB 为什么今天不能直接重锤引入。
8. Day 2 具体应该从哪些输入继续做。

如果你讲不顺，今晚还要继续补。

---

## 晚上复盘：20:00 - 21:00

### 今晚你必须自己回答的 8 个问题

1. 当前 Mneme 和目标 Mneme 的核心差异是什么？
2. 为什么说本轮优化先是架构问题，再是功能问题？
3. 为什么 MemoryEntry 是后续主资产，而不是 Chunk？
4. 为什么 GraphRAG 必须进入回答链路，而不是只做展示？
5. 为什么 Day 1 要强调非目标？
6. 当前仓库最重的几个位置分别是什么？
7. 哪些目录现在可以保留，哪些目录后续要收口？
8. Day 2 最合理的输入材料是什么？

### 如果你答不出来，重点回看哪里

- `company_target/day1-day20-summary.md`
- `Mneme_polish_v4.md`
- `main.py`
- `routers/documents.py`
- `services/document_service.py`
- `pipelines/document_index_pipeline.py`

---

## 今日验收标准

- 你能用自己的话解释 Mneme 当前定位和目标定位。
- 你已经做出 `day1_boundary_audit` 和 `day1_architecture_snapshot` 的初稿。
- 你能指出当前仓库的关键主链文件落点。
- 你能明确说出本轮先不做什么。
- 你能给 Day 2 留下一份清楚的架构分层输入。

---

## 今天最容易踩的坑

### 坑 1：Day 1 就急着开始重构代码

问题：

今天最容易把“开始优化”理解成“马上动大刀”。

规避建议：

先把目标和边界讲清楚。  
Day 1 的主要产物是认知和输入，不是重代码。

### 坑 2：只讲功能，不讲架构

问题：

只说“以后要做长期记忆、GraphRAG、Eval”，但不说这些能力要怎么进入代码结构。

规避建议：

从 Day 1 起就同时看：

- 功能主线
- 执行模型
- 目录分层
- 减重顺序

### 坑 3：把架构优化理解成目录搬家

问题：

误以为把 `services/` 搬到 `domains/` 就算完成架构优化。

规避建议：

先收口职责，再迁目录。  
没有职责边界的搬家，只会制造更大混乱。

### 坑 4：今天就急着引入 LlamaIndex / MongoDB

问题：

看到成熟框架就想立刻切换。

规避建议：

今天只做判断：

- 哪些层值得接管
- 哪些层不能替换
- 引入顺序应该是什么

### 坑 5：今天没有留下给明天可复用的材料

问题：

Day 1 最后只剩脑子里的印象，没有留下结构化文档。

规避建议：

至少保留：

- `company_target/day1_boundary_audit.md`
- `company_target/day1_architecture_snapshot.md`
- `company_target/day1_non_goals.md`

---

## 给明天的交接提示

Day 2 要接住的不是一堆零散笔记，  
而是下面这条链：

```text
当前仓库现状
-> 当前主链路审计
-> 目标长期记忆系统链路
-> 本轮边界与非目标
-> 当前目录到目标分层的映射关系
-> Day 2 开始正式做架构分层蓝图
```

你明天开始前，先把今天的结论压缩成一句话：

> 我们不是要推翻 Mneme，而是要把它从一个已经能跑的 Chunk RAG 原型，稳稳推进成长期记忆系统，并且让它的结构开始像一个可以继续演进的后端。
