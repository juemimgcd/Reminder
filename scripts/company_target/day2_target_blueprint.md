# Day 2 目标架构蓝图

## 当前主链
- main.py
- routers/documents.py
- services/document_service.py
- pipelines/document_index_pipeline.py
- services/query_service.py
- clients/vector_store_client.py
- answer

## 目标主链
- Document
- Chunk
- MemoryEntry
- CanonicalMemory / Profile Snapshot
- Hybrid Retrieval
- GraphRAG Expansion
- Evidence-based Answer
- Debug / Eval / Analysis

## 阶段顺序
- `Phase A`：Day 3 - Day 7：MemoryEntry、Evidence、Hybrid Retrieval
- `Phase B`：Day 8 - Day 11：GraphRAG、Graph Projection、Outbox
- `Phase C`：Day 12 - Day 14：CanonicalMemory、Snapshot、Timeline
- `Phase D`：Day 15 - Day 17：Debug、Eval、DuckDB Analysis
- `Phase E`：Day 18 - Day 20：thin entry、分层收口、LlamaIndex / MongoDB 减重

## Day 3 要接住的事情
- 把 `MemoryEntry` 正式拉进主链。
- 不再让它只是附属分析结果。
- 为后续 Evidence 和 GraphRAG 提供统一核心对象。