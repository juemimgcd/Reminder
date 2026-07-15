# Memory Agent Projection and Memory 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate the Agent-owned database with rebuildable document search projections and governed long-term memory derived from files, explicit requests, and eligible conversation evidence.

**Architecture:** Mneme emits versioned, batched projections and minimal conversation evidence through its Outbox. The Agent stages complete document versions before an atomic swap, performs pgvector retrieval, and governs candidate-to-canonical memory transitions with deterministic policy and hard source-deletion semantics.

**Tech Stack:** Python 3.13, SQLAlchemy 2 async, PostgreSQL 17, pgvector, Pydantic 2, Celery, existing embedding/LLM provider patterns

## Global Constraints

- The Agent stores document text chunks but never original binary files or complete conversations.
- Document projection batches are immutable, idempotent, hash-checked, and invisible until complete.
- Automatic promotion is limited to high-confidence low-risk content; secrets are always rejected.
- Do not create or modify test files in this plan.
- Reuse current provider configuration patterns; do not introduce Milvus, Neo4j, or a new model framework in the Agent.

---

### Task 1: Persist staged document projections and pgvector embeddings

**Files:**
- Create: `services/memory_agent/models/document_projection.py`
- Create: `services/memory_agent/models/document_chunk.py`
- Create: `services/memory_agent/models/projection_batch.py`
- Create: `services/memory_agent/repositories/projections.py`
- Create: `services/memory_agent/services/projections.py`
- Create: `services/memory_agent/services/embeddings.py`
- Create: `services/memory_agent/alembic/versions/20260714_02_add_document_projections.py`
- Modify: `services/memory_agent/contracts/events.py`
- Modify: `services/memory_agent/models/__init__.py`
- Modify: `services/memory_agent/services/event_dispatcher.py`

**Interfaces:**
- Produces: `DocumentProjectionBatch`, `stage_projection_batch()`, `finalize_projection()`, and searchable `DocumentChunk.embedding`.

- [ ] **Step 1: Define the batch contract**

```python
class DocumentChunkPayload(BaseModel):
    chunk_id: str
    chunk_index: int
    content: str
    content_hash: str
    page_no: int | None = None
    section_path: list[str] = Field(default_factory=list)

class DocumentProjectionPayload(BaseModel):
    projection_id: str
    document_id: str
    document_version: str
    file_name: str
    batch_index: int = Field(ge=0)
    batch_count: int = Field(gt=0)
    aggregate_hash: str
    chunks: list[DocumentChunkPayload]
```

- [ ] **Step 2: Add staging and active versions**

Model projection status as `staging`, `active`, `failed`, or `superseded`. Enforce uniqueness for `(projection_id, batch_index)`, `(document_id, document_version)`, and active chunk IDs. Enable the `vector` extension and use the embedding dimension from a single Agent setting.

- [ ] **Step 3: Stage and finalize atomically**

`stage_projection_batch()` validates stable metadata across batches. `finalize_projection()` requires every index from `0` through `batch_count - 1`, recomputes the ordered aggregate SHA-256, embeds chunks, marks the new version active, and supersedes the old version in one transaction. Failure leaves the prior active version searchable.

- [ ] **Step 4: Handle projection events**

Replace the foundation no-op for `document.projection.upserted`; only the final received batch schedules finalization. Replayed batches return the existing receipt without embedding twice.

- [ ] **Step 5: Check migration and commit**

Run: `python -m alembic -c services/memory_agent/alembic.ini heads`

Expected: one head at `20260714_02`.

```powershell
git add services/memory_agent
git commit -m "feat: add agent document projections"
```

### Task 2: Publish projection and deletion events from Mneme

**Files:**
- Create: `app/mneme/domains/documents/agent_projection.py`
- Modify: `app/mneme/domains/documents/pipeline.py`
- Modify: `app/mneme/domains/documents/resources.py`
- Modify: `app/mneme/domains/tasks/outbox.py`
- Modify: `app/mneme/schemas/memory_agent.py`

**Interfaces:**
- Consumes: persisted Mneme `Document` and `Chunk` rows.
- Produces: `enqueue_document_agent_projection()`, `enqueue_document_deleted()`, and `enqueue_knowledge_base_deleted()`.

- [ ] **Step 1: Build deterministic projection batches**

```python
async def build_document_projection_batches(
    db: AsyncSession, *, document: Document, batch_size: int = 50
) -> list[MemoryAgentEvent]: ...
```

Use stable `projection_id = sha256(document.id + document.updated_at.isoformat() + aggregate_hash)`. Sort chunks by `(chunk_index, id)`, hash normalized UTF-8 content, and never include `file_path` or the original binary.

- [ ] **Step 2: Enqueue only after chunk persistence**

At the end of a successful document pipeline, insert all projection batches into the Outbox. Remove direct Milvus reindex and graph-sync execution from the new Agent-enabled branch, but keep legacy behavior when `MEMORY_AGENT_ENABLED` is false during the migration window.

- [ ] **Step 3: Publish deletion before removing source metadata**

Insert `document.deleted` or `knowledge_base.deleted` through the caller-owned `AsyncSession` added in the foundation plan, in the same database transaction that deletes the business record. The payload contains IDs and source version only, never deleted text.

- [ ] **Step 4: Check source and commit**

Run: `python -m ruff check app/mneme/domains/documents app/mneme/domains/tasks/outbox.py app/mneme/schemas/memory_agent.py`

Expected: no lint errors.

```powershell
git add app/mneme/domains/documents app/mneme/domains/tasks/outbox.py app/mneme/schemas/memory_agent.py
git commit -m "feat: publish agent document projections"
```

### Task 3: Add hybrid retrieval inside the Agent

**Files:**
- Create: `services/memory_agent/retrieval/contracts.py`
- Create: `services/memory_agent/retrieval/vector.py`
- Create: `services/memory_agent/retrieval/keyword.py`
- Create: `services/memory_agent/retrieval/fusion.py`
- Create: `services/memory_agent/retrieval/documents.py`

**Interfaces:**
- Produces: `DocumentRetriever.search(scope: RetrievalScope, query: str, top_k: int) -> list[RetrievedEvidence]`.

- [ ] **Step 1: Define evidence output**

```python
class RetrievalScope(BaseModel):
    owner_id: int
    knowledge_base_id: str

class RetrievedEvidence(BaseModel):
    evidence_id: str
    source_type: Literal["document", "memory"]
    source_id: str
    content: str
    score: float
    metadata: dict[str, Any]
```

- [ ] **Step 2: Implement scoped vector and PostgreSQL text search**

Every SQL query must filter `owner_id`, `knowledge_base_id`, and active projection status before ranking. Vector search uses pgvector cosine distance; keyword search uses a stored `tsvector` with `websearch_to_tsquery`.

- [ ] **Step 3: Fuse deterministically**

Use reciprocal-rank fusion with a fixed constant of 60, deduplicate by chunk ID, and return at most `top_k`. Do not ask the model to choose retrieval results.

- [ ] **Step 4: Check source and commit**

Run: `python -m ruff check services/memory_agent/retrieval`

Expected: no lint errors.

```powershell
git add services/memory_agent/retrieval
git commit -m "feat: add scoped agent hybrid retrieval"
```

### Task 4: Add governed memory persistence and policy

**Files:**
- Create: `services/memory_agent/models/evidence.py`
- Create: `services/memory_agent/models/memory_candidate.py`
- Create: `services/memory_agent/models/canonical_memory.py`
- Create: `services/memory_agent/models/memory_revision.py`
- Create: `services/memory_agent/models/memory_relation.py`
- Create: `services/memory_agent/models/memory_settings.py`
- Create: `services/memory_agent/repositories/memories.py`
- Create: `services/memory_agent/memory/identity.py`
- Create: `services/memory_agent/memory/policy.py`
- Create: `services/memory_agent/memory/reconciliation.py`
- Create: `services/memory_agent/alembic/versions/20260714_03_add_governed_memory.py`
- Modify: `services/memory_agent/models/__init__.py`

**Interfaces:**
- Produces: `classify_candidate()`, `reconcile_candidate()`, `confirm_candidate()`, `reject_candidate()`, `revise_memory()`, and `hard_delete_memory()`.

- [ ] **Step 1: Create exact enums**

```python
MemoryType = Literal["preference", "profile_fact", "project_context", "decision", "goal", "constraint"]
CandidateStatus = Literal["pending", "promoted", "rejected", "expired"]
MemoryStatus = Literal["active", "superseded", "invalidated"]
Sensitivity = Literal["low", "sensitive", "secret"]
```

- [ ] **Step 2: Persist evidence and revisions**

Evidence contains owner scope, source type/ID/version, minimum text, hash, and occurrence time. Canonical memory points to one active revision; revision rows store normalized subject/predicate/value, validity interval, reason, and actor. Evidence membership is many-to-many and cascade-safe.

Persist one `MemorySettings` row per owner with `automatic_conversation_memory=False` as the privacy-preserving default. File-derived and explicit-request memory remain enabled independently of this setting.

- [ ] **Step 3: Implement deterministic policy**

`secret` always returns `reject`. Explicit user requests return `promote` unless secret. Low-sensitivity candidates require confidence at least `0.85` for automatic promotion. Sensitive, conflicting, or lower-confidence candidates return `pending`. Keep these thresholds in code constants, not environment configuration.

- [ ] **Step 4: Reconcile without destructive overwrite**

Compatible fingerprints add evidence and recompute confidence. Conflicts remain pending. User-confirmed replacements close the old revision's `valid_to` and create a new active revision in one transaction.

- [ ] **Step 5: Check migration and commit**

Run: `python -m alembic -c services/memory_agent/alembic.ini heads`

Expected: one head at `20260714_03`.

```powershell
git add services/memory_agent
git commit -m "feat: add governed long term memory"
```

### Task 5: Extract file, conversation, and explicit-request memory

**Files:**
- Create: `services/memory_agent/memory/extraction.py`
- Create: `services/memory_agent/memory/schemas.py`
- Create: `services/memory_agent/memory/sensitivity.py`
- Create: `services/memory_agent/services/memory_events.py`
- Modify: `services/memory_agent/services/event_dispatcher.py`
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/domains/tasks/outbox.py`

**Interfaces:**
- Produces: `extract_candidates(evidence: EvidenceInput) -> list[ExtractedCandidate]` and handlers for conversation and explicit memory events.

- [ ] **Step 1: Require structured extraction**

Use a Pydantic model containing type, subject, predicate, value, confidence, sensitivity signals, evidence quote boundaries, and temporal hints. Reject output whose evidence substring is not present in the supplied excerpt.

- [ ] **Step 2: Apply policy outside the model**

Run deterministic secret patterns and sensitivity classification before `classify_candidate()`. The model's requested status is ignored.

- [ ] **Step 3: Publish minimal conversation evidence**

After an assistant response is persisted, enqueue `conversation.completed` with the user message ID, assistant message ID, timestamps, and only the current user/assistant exchange. Do not send chat history.

The Agent handler must read `MemorySettings` before extraction. When automatic conversation memory is disabled, mark the event successfully processed without creating evidence or candidates. Handle `user.memory_settings.changed` idempotently and apply the new value before later conversation events for the same owner.

- [ ] **Step 4: Handle explicit memory requests**

Publish `user.memory_requested` from an explicit product action, not inferred wording. Route eligible extracted candidates directly through policy with `explicit_request=True`.

- [ ] **Step 5: Commit**

```powershell
git add services/memory_agent app/mneme/domains/chat/service.py app/mneme/domains/tasks/outbox.py
git commit -m "feat: extract file and conversation memory"
```

### Task 6: Implement source deletion and rebuildable backfill

**Files:**
- Create: `services/memory_agent/services/deletion.py`
- Create: `services/memory_agent/cli/backfill.py`
- Create: `app/mneme/cli/export_agent_projection.py`
- Modify: `services/memory_agent/services/event_dispatcher.py`
- Modify: `README.md`
- Modify: `deploy/DEPLOY.md`

**Interfaces:**
- Produces: `delete_source_evidence()`, `delete_document_projection()`, and resumable `projection_id`-based backfill commands.

- [ ] **Step 1: Hard-delete source content**

On document or conversation deletion, delete projections and evidence text, remove unsupported candidates, delete canonical memories with no evidence, and recalculate confidence for memories that retain evidence. Keep only event IDs, counts, status, and timestamps in the audit result.

- [ ] **Step 2: Backfill existing data through contracts**

The Mneme CLI reads documents/chunks and legacy memory in stable ID order, emits the same version-1 projection/event DTOs used online, and writes a checkpoint after every accepted batch. The Agent CLI reports staged, active, failed, and hash-mismatched projections.

- [ ] **Step 3: Add dry-run and resume**

Support `--dry-run`, `--owner-id`, `--knowledge-base-id`, `--resume-from`, and `--batch-size`. Dry-run must not insert Outbox or Agent records.

- [ ] **Step 4: Run non-test verification**

Run: `python -m compileall -q services/memory_agent app/mneme`

Expected: exit code 0.

Run: `python -m ruff check services/memory_agent app/mneme/cli app/mneme/domains/documents app/mneme/domains/chat/service.py`

Expected: no lint errors.

- [ ] **Step 5: Commit**

```powershell
git add services/memory_agent app/mneme/cli README.md deploy/DEPLOY.md
git commit -m "feat: add memory deletion and projection backfill"
```
