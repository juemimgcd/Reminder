# Day 2 分层映射表

| 当前目录 | 目标落位 | 原因 |
|---|---|---|
| `routers` | `api/routes` | 当前已经是入站层雏形，应继续收口为 API 层。 |
| `schemas` | `api/schemas 或 domains/*/schemas.py` | 当前承担请求响应和 DTO 角色，后续按用途分流。 |
| `services` | `domains/*/service.py` | 当前是业务入口与领域逻辑混层，后续要按领域回收。 |
| `pipelines` | `domains/*/pipeline.py 或 workflow/jobs` | 当前是主链编排雏形，后续再决定保留在领域侧还是下沉到 workflow。 |
| `clients` | `infra/*` | 当前本质上是外部依赖适配层。 |
| `infra` | `core/* 或 infra/*` | 当前是运行时能力集合，后续需要更清晰地区分核心规则和底层适配。 |
| `tasks` | `workflow/jobs` | 当前是异步任务入口，适合演进成 workflow jobs。 |
| `models` | `domains/*/models.py` | 当前是主数据模型层，后续按领域收口更清晰。 |
| `crud` | `domains/*/repository.py` | 当前是数据访问层，后续适合演进成 repository 语义。 |