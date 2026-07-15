# Memory Agent Service Design

**Date:** 2026-07-14  
**Status:** Approved for implementation planning  
**Scope:** Extract Mneme's answer orchestration and long-term memory into an independently deployed service, then evolve file and conversation memory into a governed, user-correctable system.

## 1. Goals

Mneme's primary product value is retrieval-augmented answering over user files and durable user memory. The next architecture must make those capabilities independently operable without turning the project into a general multi-agent platform.

This design will:

- create a separately deployed Memory Agent Service in the existing repository;
- give that service exclusive ownership of answer orchestration, memory data, document retrieval projections, and vector indexes;
- preserve explicit user-selected answer modes instead of inferring intent from the question;
- form long-term memory from files, explicit user requests, and eligible conversation content;
- make every durable memory explainable, correctable, versioned, and deletable;
- separate synchronous answering from asynchronous projection and memory formation;
- migrate existing documents and memories without a big-bang database replacement.

## 2. Assumptions and non-goals

### Assumptions

- The main Mneme backend continues to own users, authentication, authorization, original files, chat sessions, and chat messages.
- PostgreSQL, pgvector, Redis, Celery, and the existing transactional Outbox remain the infrastructure baseline.
- The current explicit answer-mode work is the behavioral starting point for the new service.
- Development may use one PostgreSQL server and one Redis server, but each service uses a separate database, migrations, Celery queues, and configuration namespace.

### Non-goals

- No separate Git repository in this phase.
- No Kafka, workflow engine, dedicated vector database, general multi-agent framework, or unconstrained tool loop.
- No automatic intent classification that overrides the user's selected answer mode.
- No silent fallback to the legacy RAG implementation or ordinary LLM chat when the Memory Agent is unavailable.
- No storage of credentials, secrets, tokens, or private keys as long-term memory.
- No general-purpose knowledge graph. Memory relations remain intentionally small and typed.

## 3. System architecture

The repository becomes a monorepo containing two independently deployed services:

- `app/mneme/`: the existing business backend;
- `services/memory_agent/`: the new Memory Agent API and worker runtime.

Each service owns its persistence model. Neither service may import the other's ORM models, CRUD modules, database session factories, or Celery task implementations. Cross-service communication uses versioned HTTP contracts only.

### 3.1 Mneme backend ownership

The main backend owns:

- users and authentication;
- knowledge bases and file metadata;
- original uploaded files;
- chat sessions and messages;
- user-to-resource authorization;
- transactional Outbox records;
- orchestration of the user-facing request lifecycle.

For an online answer, it authenticates the user, checks access to the requested knowledge base and session, persists the user message, calls the Memory Agent, then persists the returned assistant message. It does not perform retrieval or answer generation itself.

### 3.2 Memory Agent ownership

The Memory Agent owns:

- explicit answer-mode execution;
- document retrieval projections and vector indexes;
- memory evidence, candidates, canonical memories, revisions, and relations;
- retrieval planning and bounded tool execution;
- model-provider integration;
- citation validation;
- answer-run records, latency, token use, cost, and error details;
- asynchronous memory extraction, reconciliation, deletion, and index maintenance.

### 3.3 Storage boundary

The Memory Agent uses an independent PostgreSQL database with pgvector. It never reads Mneme business tables, and the Mneme backend never reads Agent tables.

Original files remain solely in Mneme. After parsing, Mneme sends a rebuildable document projection containing normalized text chunks, source metadata, hashes, and versions. The Agent stores those chunks and their vectors but not the original binary file. Deleting a source document removes its entire Agent-side retrieval projection.

Conversation data follows a stricter rule. The Agent does not copy complete conversations. It stores only the minimum excerpt required to support a memory candidate or canonical memory, plus the source message ID, timestamp, content hash, and version.

## 4. Communication and consistency

### 4.1 Synchronous answer path

The synchronous flow is:

1. The UI submits the question and explicit answer mode to Mneme.
2. Mneme authenticates the request, checks resource access, and saves the user message.
3. Mneme calls `POST /v1/answers` on the Memory Agent with an authorized scope.
4. The Agent executes the selected bounded pipeline and returns the answer, citations, confidence, uncertainty, route, and run ID.
5. Mneme saves and returns the assistant message.

The client has a strict timeout and limited transport retry. If the Agent remains unavailable, Mneme keeps the user message and returns a retryable service error. It does not invoke a second answer implementation.

### 4.2 Asynchronous event path

File, conversation, and deletion changes use the existing transactional Outbox:

1. Mneme writes the business change and an Outbox event in one database transaction.
2. The Outbox dispatcher calls `POST /internal/v1/events` on the Memory Agent.
3. The Agent validates the service token and event schema, persists the event by unique `event_id`, and returns success.
4. Agent-owned Celery workers process extraction, projection, reconciliation, indexing, or deletion.

Duplicate deliveries are successful no-ops. Transport and processing failures use bounded exponential retry. Exhausted Mneme deliveries enter an observable dead-letter state; exhausted Agent jobs retain their error state for operator retry.

Initial event types are:

- `document.projection.upserted`;
- `document.deleted`;
- `knowledge_base.deleted`;
- `conversation.completed`;
- `conversation.deleted`;
- `user.memory_requested`;
- `user.memory_settings.changed`.

Every event includes `event_id`, event type, schema version, occurrence time, owner ID, authorization scope, and a type-specific payload. Breaking payload changes require a new schema version.

Document projections may exceed a safe single-request size. Mneme therefore sends one immutable `projection_id` as ordered, idempotent batches containing `batch_index`, `batch_count`, and the document version. The Agent builds the new projection in a staging state and makes it searchable only after every batch has arrived and its aggregate hash matches. It then atomically replaces the previous document version. A missing or failed batch leaves the prior searchable projection unchanged.

## 5. Long-term memory model

Long-term memory is a governed projection, not a collection of unrelated text rows.

### 5.1 Evidence

Evidence is the immutable basis for a memory decision. It records the source type and ID, minimum necessary text snapshot, source timestamp, content hash, version, and owner scope. File evidence may reference an Agent-owned document chunk. Conversation evidence contains only the supporting excerpt.

Evidence text is not edited. A changed source produces a new evidence version. Source deletion physically deletes the corresponding evidence content.

### 5.2 Memory candidates

A candidate is an extracted proposition that has not yet qualified as canonical memory. It contains:

- normalized subject, predicate, and value;
- one fixed memory type;
- confidence and extraction provenance;
- sensitivity classification;
- supporting evidence IDs;
- possible conflicting memory IDs;
- a state of `pending`, `promoted`, `rejected`, or `expired`.

### 5.3 Canonical memories

A canonical memory represents the currently accepted value of a user fact, preference, project context, decision, goal, or constraint. It includes its active revision, validity interval, status, evidence set, retrieval weight, and confidence.

The fixed initial memory types are:

- `preference`;
- `profile_fact`;
- `project_context`;
- `decision`;
- `goal`;
- `constraint`.

New types require a deliberate schema change. Arbitrary model-generated categories are not persisted.

### 5.4 Revisions and relations

Every confirmation, correction, replacement, or invalidation creates a revision. Old values remain historically inspectable unless the user requests hard deletion.

Typed relations connect a small set of useful entities, such as a decision belonging to a project or a constraint affecting a goal. Relations support retrieval and explanation; they are not intended to become an open-ended graph platform.

## 6. Memory governance

### 6.1 Promotion rules

- A user statement explicitly requesting memory is promoted immediately after safety validation.
- High-confidence, low-sensitivity candidates from ordinary conversation may be promoted automatically.
- Uncertain, ambiguous, or conflicting candidates remain pending for user confirmation.
- Sensitive categories such as identity, health, finance, and authentication data are not automatically promoted.
- Credentials, secrets, access tokens, private keys, and equivalent high-risk values are rejected even when the user asks to remember them.

Promotion thresholds and sensitivity rules are deterministic application policy. The model may supply signals, but it does not make the final policy decision.

### 6.2 Reinforcement, conflict, and time

- Repeated compatible evidence strengthens an existing memory instead of creating duplicates.
- A conflicting value creates a pending candidate and does not overwrite the active memory.
- A user-confirmed change closes the old revision's validity interval and activates the new revision.
- Memories not used for a long time may receive a lower retrieval weight, but inactivity alone never physically deletes them.
- Retrieval favors currently valid memories and may include historical revisions only when the question explicitly asks about the past.

### 6.3 User control

The product exposes a Memory Center where users can:

- view canonical memories, pending candidates, revisions, and evidence sources;
- confirm or reject candidates;
- edit, invalidate, or hard-delete a memory;
- clear memory by source, project, or entire account;
- disable automatic conversation memory while preserving explicit “remember this” actions.

Hard deletion removes content from active records and revision history. It is not represented as a soft-deleted copy containing the original value.

### 6.4 Source deletion

When a source file or conversation is deleted:

1. its Agent-side document projection and evidence snapshots are physically deleted;
2. affected candidates are removed or recomputed;
3. canonical memories supported only by the deleted evidence are deleted;
4. memories with other valid evidence remain and have their confidence recalculated;
5. the deletion event and processing result remain auditable without retaining deleted source content.

## 7. Agent runtime

The runtime is a bounded pipeline:

1. **Validate:** validate mode, owner scope, knowledge-base scope, limits, and request contract.
2. **Plan:** map the explicit mode to a predefined retrieval plan.
3. **Retrieve:** invoke only the tools permitted by that plan.
4. **Answer:** generate from retrieved context, validate citations, persist run details, and return a typed result.

Each phase has a timeout and item limit. The runtime permits at most one retrieval expansion when the initial evidence is insufficient. It does not allow open-ended model-directed tool loops.

### 7.1 Mode capabilities

| Mode | Allowed private sources |
| --- | --- |
| `kb_qa` | Document vector search, document keyword search, relevant canonical memory |
| `memory_query` | Canonical memory and its evidence only |
| `profile_query` | Profile facts, preferences, goals, and constraints |
| `analysis_query` | Documents, canonical memory, and typed relations with a larger context budget |
| `general_chat` | No private retrieval tools |

The UI-selected mode is authoritative. The Agent may reject an invalid or unauthorized mode but may not silently replace it.

### 7.2 Internal ports

The service defines focused internal interfaces for:

- `DocumentRetriever`;
- `MemoryRetriever`;
- `ProfileReader`;
- `ModelGateway`;
- `CitationValidator`;
- `RunRepository`.

These interfaces isolate implementation details inside the service. They are not shared Python packages between services.

## 8. HTTP contracts

Initial public-to-backend-facing Agent endpoints are:

- `POST /v1/answers`;
- `GET /v1/runs/{run_id}`;
- `GET /v1/memories`;
- `GET /v1/memory-candidates`;
- `PATCH /v1/memories/{memory_id}`;
- `DELETE /v1/memories/{memory_id}`.

The internal event endpoint is:

- `POST /internal/v1/events`.

Service-to-service requests use short-lived signed credentials with audience validation. The Agent trusts the authenticated owner and resource scope supplied by Mneme for that request; it never expands the scope. Response citations expose only metadata allowed by the supplied scope.

An answer result contains at least:

- `answer`, `mode`, and `route`;
- validated `citations`;
- `confidence`, `uncertainty`, and `insufficient_evidence`;
- contributing `memory_ids` and `document_ids`;
- `run_id`.

Expected failures use stable error codes that distinguish invalid scope, insufficient service capacity, model failure, timeout, and internal error. No-evidence is a successful answer result with an explicit insufficiency marker, not a transport error.

## 9. Product changes

The chat interface will:

- keep explicit answer-mode buttons;
- persist the selected mode per chat session;
- allow an existing question to be regenerated with another mode;
- display whether an answer used files, memory, profile, or no private source;
- show document citations, memory timestamps, and the answer run ID;
- preserve a failed user message and expose retry.

The new Memory Center will provide canonical-memory, candidate, revision, evidence, privacy-setting, and deletion workflows described in Section 6.3.

## 10. Observability and privacy

Every cross-service operation carries `request_id`, `run_id`, or `event_id` so logs can be correlated without logging user content.

The system records:

- answer latency by mode and pipeline phase;
- retrieval counts, hit rates, and evidence insufficiency;
- model tokens, cost, retries, and error rate;
- Outbox age, delivery retries, dead letters, Agent job backlog, and projection lag;
- memory candidate, promotion, rejection, correction, conflict, and deletion counts.

Application logs do not contain document text, conversation excerpts, prompts containing private context, or memory values. Identifiers and sensitive configuration values are redacted where appropriate.

Health endpoints distinguish liveness from readiness. Agent readiness requires its database and required model configuration; worker and queue health are reported separately so online answering is not marked healthy merely because the HTTP process is alive.

## 11. Migration strategy

### Phase 1: Establish the service boundary

- Create the Memory Agent application, independent configuration, database, migrations, Docker image, and health endpoints.
- Define versioned answer and event contracts.
- Add the Mneme Agent client and service authentication.
- Extend the existing Outbox dispatcher with reliable HTTP delivery.

### Phase 2: Build projections and memory 2.0

- Publish file projection events after parsing and indexing.
- Backfill current document chunks, vectors, and existing memory into the Agent database.
- Add evidence, candidates, canonical memories, revisions, relations, and governance policy.
- Add conversation extraction and source-deletion processing.
- Run the new projection path without serving user answer traffic and compare counts, ownership, hashes, and retrieval samples with the source state.

### Phase 3: Switch the product

- Route all five answer modes through the Memory Agent API behind a deployment configuration switch.
- Add session mode persistence, regeneration, source display, Memory Center, and privacy controls.
- Keep the legacy path unchanged and inactive for rollback during the cutover window. Do not dual-write answer or memory databases.

### Phase 4: Concentrated verification and removal

The project rule for this task is that phases 1–3 do not add or modify test files. After all business implementation is complete, phase 4 adds and runs the complete test and evaluation set in one concentrated step.

Verification then covers:

- memory policy, identity, revisions, conflicts, and hard deletion;
- answer and event contract compatibility;
- event idempotency, retries, ordering tolerance, and dead-letter recovery;
- database and service-boundary assertions;
- cross-service authorization and citation filtering;
- complete file projection, backfill, rebuild, and deletion flows;
- all answer modes in backend and browser end-to-end flows;
- a fixed answer-quality evaluation set with retrieval and citation baselines;
- deployment, health, migration, rollback, and clean-install checks.

Only after verification succeeds is the old RAG orchestration, old memory query implementation, and temporary compatibility code removed in a separate commit. Relevant verification is rerun after removal.

## 12. Rollback

Before legacy removal, a deployment configuration switch controls whether Mneme calls the old in-process runtime or the Memory Agent. A rollback switches traffic back to the unchanged legacy runtime, pauses Agent event consumption, and leaves Agent data intact for diagnosis. It does not attempt to merge Agent records back into Mneme tables.

After the legacy implementation is removed, rollback is performed by deploying the previous application version and its compatible schema versions. Agent migrations must therefore use expand-then-contract changes during the cutover window and avoid destructive schema changes until the new release is established.

## 13. Completion criteria

The initiative is complete when:

- Mneme contains no answer-time retrieval, memory-query, prompt-building, or answer-orchestration implementation;
- the Memory Agent does not read Mneme tables and Mneme does not read Agent tables;
- document, conversation, and deletion events can be delivered and replayed idempotently;
- all existing source data has a reconciled Agent projection or an explicit migration error;
- users can inspect, confirm, correct, invalidate, and hard-delete durable memory;
- every private-source answer has valid, authorized evidence citations;
- all five explicit modes meet the fixed end-to-end and evaluation baselines;
- service, worker, database, queue, deployment, and rollback documentation is current;
- the concentrated verification phase passes after legacy code removal.
