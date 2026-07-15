# Mneme Agent Module

`app.mneme.agent` is the single in-process entry point for online AI answers.
It owns request routing and answer orchestration while keeping the public HTTP
API unchanged.

The surrounding domains retain their existing ownership:

- `domains/documents` owns file ingestion, chunking, and indexing.
- `domains/memory` owns durable file-derived memory and memory governance.
- `domains/chat` owns sessions, messages, authorization context, and persistence.
- `domains/retrieval` owns retrieval implementations used by the Agent.

Backend callers construct a `MnemeAgent` through the RAG adapter, submit an
`AgentRequest`, and persist the resulting `AgentResponse`. The Agent core
contracts, port, and service do not depend on FastAPI or HTTP routing.
Infrastructure dependencies are isolated in adapters and runtime-event
subscribers.

`agent/capabilities.py` indexes the trusted backend capabilities. An
`answer_mode` is treated as an intent hint and projected into the smallest
eligible tool set for the current request. Every projection records eligible,
selected, and excluded capability IDs with exclusion reasons; the Runner and
tool policy consume the projection rather than a fixed answer-mode/tool map.

`agent/runtime_events.py` is independent from the public SSE DTO. A trace-aware
dispatcher publishes run, context, capability, model, tool, and persistence
events to structured logging, bounded metrics, and best-effort PostgreSQL audit
subscribers. The audit table stores identifiers, timings, token counts, error
kinds, and capability IDs only; prompts, answers, tool arguments, and evidence
payloads are not runtime-audit data. The SSE adapter preserves existing event
types while attaching trace identity to lifecycle and tool events.
