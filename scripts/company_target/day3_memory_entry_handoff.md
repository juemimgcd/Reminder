# Day 3 MemoryEntry 入链交接

## 当前主链
- `tasks/index_tasks.py`
- `pipelines/document_index_pipeline.py`
- `crud.chunk.create_chunks(...)`
- `services.memory_service.rebuild_memory_entries_for_document(...)`
- `clients.vector_store_client.add_documents_to_vector_store_in_batches(...)`

## 当前 MemoryEntry 真实落点
- `models/memory.py`
- `schemas/memory_entry.py`
- `services/memory_service.py`
- `pipelines/memory_extract_pipeline.py`
- `routers/memory.py`
- `services/graph_projection_service.py`

## Day 3 要确认的事情
- 把 `MemoryEntry` 从“附属分析结果”提升成主链一级产物。
- 在 `pipelines/document_index_pipeline.py` 里显式承认 memory 阶段。
- 在 `schemas/document.py` 的 `DocumentIndexPipelineResult` 里补上 memory 统计。
- 保持 `chunk -> memory -> vector` 这条链清晰可解释。

## 最小 MemoryEntry 字段
- `id`
- `document_id`
- `chunk_id`
- `entry_name`
- `entry_type`
- `summary`
- `evidence_text`
- `importance_score`

## Day 3 最小链路
- `Document`
- `Chunk`
- `extract_entries_from_chunks(...)`
- `deduplicate_memory_entries(...)`
- `create_memory_entries(...)`
- `sync_document_memory_projection(...)`

## Day 4 要接住的事情
- 消费 `summary` 做回答压缩上下文。
- 消费 `evidence_text` 做引用和证据绑定。
- 消费 `chunk_id` / `document_id` 保证可追溯。
- 消费 `importance_score` 为后续 rerank 留信号。
