# Mneme Agent Module

`services.memory_agent` is the independent online answer runtime. Mneme owns
authorization, chat/session persistence, and event publication; it calls the
Agent through `MemoryAgentClient` and never performs answer-time retrieval or
prompt construction in-process.

The surrounding domains retain their existing ownership:

- `domains/documents` owns file ingestion, chunking, and indexing.
- `domains/memory` owns durable file-derived memory and memory governance.
- `domains/chat` owns sessions, messages, authorization context, and persistence.
- `domains/retrieval` retains compatibility utilities during the cleanup
  window; online answer requests do not call them.

Backend callers construct a scoped `MemoryAgentAnswerRequest`, submit it over
the service-token HTTP contract, and persist the validated response and run ID.
The Agent owns retrieval, answer modes, citations, memory policy, and answer
quality evaluation in its own database and worker.

The old `app.mneme.agent` contracts and compatibility retrieval modules remain
only for migration-era tests and document-pipeline cleanup; they are not an
online fallback. Removing those compatibility files is a follow-up after the
remaining document/resource branches are migrated.
