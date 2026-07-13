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
contracts, port, and service do not depend on FastAPI, SQLAlchemy, CRUD, or ORM
models. Infrastructure dependencies are isolated in `agent/adapters`.

During the first migration phase, `agent/orchestrator.py` delegates to the
existing retrieval, profile, LLM, and citation services. No database schema or
public response contract changes are part of this phase.
