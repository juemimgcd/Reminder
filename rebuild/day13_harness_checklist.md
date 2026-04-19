# Day 13 Harness Checklist

## Runtime Harness
- [x] `tasks/index_tasks.py` 已存在
- [x] `services/task_state_service.py` 已存在
- [x] `infra/rate_limit.py` 已存在
- [x] `infra/retry.py` 已存在
- [x] `infra/circuit_breaker.py` 已存在
- [x] `scripts2/debug_day10.py` 可演示限流 / retry / breaker

## Context Harness
- [x] `services/context_service.py` 已存在
- [x] 去重逻辑已存在
- [x] 相邻合并逻辑已存在
- [x] budget 裁剪逻辑已存在
- [x] `services/query_service.py` 已改成只消费治理后的 context packet

## Module Boundary Harness
- [x] `routers/`、`services/`、`pipelines/`、`clients/`、`infra/` 已分层
- [x] `document_index_pipeline.py` 已是文档域主流程承载层
- [x] `memory_extract_pipeline.py` 已开始预埋
- [ ] `routers/profile.py`、`routers/companion.py` 仍有 knowledge base 口径未完全收口

## Dual Pipeline Foundation
- [x] `pipelines/document_index_pipeline.py` 已存在
- [x] `pipelines/memory_extract_pipeline.py` 已存在
- [x] `profile_service.py`、`growth_service.py` 已开始围绕记忆产物消费
- [ ] 记忆域还未正式任务化