# Agent Module Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a dedicated in-process Agent module and route every online AI answer request through it without changing public APIs, database tables, or answer behavior.

**Architecture:** `app.mneme.agent` owns the request/response contract and the single `MnemeAgent.run()` entry point. A small adapter delegates to the existing RAG implementation during this behavior-preserving phase; backend services construct that adapter with their database session, while the Agent core stays free of FastAPI, SQLAlchemy, CRUD, and ORM imports.

**Tech Stack:** Python 3.13, Pydantic 2, FastAPI, SQLAlchemy async sessions, pytest

---

### Task 1: Define the Agent core boundary

**Files:**
- Create: `app/mneme/agent/__init__.py`
- Create: `app/mneme/agent/contracts.py`
- Create: `app/mneme/agent/ports.py`
- Create: `app/mneme/agent/service.py`
- Test: `tests/test_agent_module_boundary.py`

- [ ] **Step 1: Define serializable input and output contracts**

Create `AgentRequest` with `question`, `knowledge_base_id`, `user_id`, `top_k`, and optional `llm_config`. Create `AgentResponse` with the same answer, source, citation, confidence, uncertainty, route, and debug fields currently returned by `generate_rag_answer()`.

- [ ] **Step 2: Define the answer-engine port**

```python
class AgentAnswerEngine(Protocol):
    async def generate(self, request: AgentRequest) -> AgentResponse: ...
```

The port must depend only on Agent contracts.

- [ ] **Step 3: Add the single Agent entry point**

```python
class MnemeAgent:
    def __init__(self, answer_engine: AgentAnswerEngine):
        self.answer_engine = answer_engine

    async def run(self, request: AgentRequest) -> AgentResponse:
        return await self.answer_engine.generate(request)
```

- [ ] **Step 4: Add architecture assertions**

Verify the core Agent files do not import FastAPI, SQLAlchemy, `app.mneme.crud`, `app.mneme.models`, or `app.mneme.conf.database`. Verify a fake answer engine can be passed to `MnemeAgent` and receives the complete request.

### Task 2: Adapt the existing RAG implementation

**Files:**
- Create: `app/mneme/agent/adapters/__init__.py`
- Create: `app/mneme/agent/adapters/rag_answer.py`
- Test: `tests/test_agent_module_boundary.py`

- [ ] **Step 1: Implement the legacy RAG adapter**

Create `RagAnswerEngine`, initialized with an `AsyncSession`, which passes the Agent request fields to the existing `generate_rag_answer()` function and validates the returned dictionary as `AgentResponse`.

- [ ] **Step 2: Add a backend-facing factory**

```python
def build_mneme_agent(db: AsyncSession) -> MnemeAgent:
    return MnemeAgent(answer_engine=RagAnswerEngine(db))
```

This keeps SQLAlchemy at the adapter edge and out of Agent core files.

- [ ] **Step 3: Verify mapping behavior**

Patch only the existing RAG callable, submit an `AgentRequest`, and assert every input and output field is preserved by the adapter.

### Task 3: Route online answer consumers through the Agent

**Files:**
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/domains/retrieval/router.py`
- Modify: `app/mneme/pipelines/companion_pipeline.py`
- Test: `tests/test_agent_module_boundary.py`

- [ ] **Step 1: Update chat-session answering**

Replace the direct `generate_rag_answer()` call with `build_mneme_agent(db).run(AgentRequest(...))`. Convert the validated response to a plain dictionary only at the existing persistence boundary so chat-message storage remains unchanged.

- [ ] **Step 2: Update stateless chat querying**

Route the no-session branch of `POST /kb/chat/query` through the same Agent entry point while preserving the existing `ChatQueryData` response.

- [ ] **Step 3: Update Companion orchestration**

Route Companion's initial RAG answer through the Agent and pass its dumped result to the existing companion response builder.

- [ ] **Step 4: Assert direct-call convergence**

Verify these three consumer files no longer import `app.mneme.domains.retrieval.query_service.generate_rag_answer` and instead import Agent contracts plus the adapter factory.

### Task 4: Document and verify the phase-one boundary

**Files:**
- Modify: `README.md`
- Test: `tests/test_agent_module_boundary.py`

- [ ] **Step 1: Document module ownership**

Add `agent/` to the backend directory overview and explain that it is the in-process online AI entry point, while `domains/memory` continues to own durable file-derived memory and `domains/documents` continues to own indexing.

- [ ] **Step 2: Run focused tests after implementation**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agent_module_boundary.py tests/test_chat_session_persistence.py tests/test_query_router_service.py tests/test_retrieval_debug_service.py tests/test_retrieval_fusion_service.py tests/test_citation_validation_service.py -q --basetemp .tmp/pytest-agent
```

Expected: all selected tests pass.

- [ ] **Step 3: Run lint for touched Python files**

Run:

```powershell
.\.venv\Scripts\python.exe -m ruff check app/mneme/agent app/mneme/domains/chat/service.py app/mneme/domains/retrieval/router.py app/mneme/pipelines/companion_pipeline.py tests/test_agent_module_boundary.py
```

Expected: no lint errors.

- [ ] **Step 4: Run the complete backend suite with a workspace temp directory**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp .tmp/pytest-all
```

Compare failures with the recorded baseline of 109 passed, 8 failed, 27 environment-related errors, and 8 passed subtests. Do not attribute pre-existing route compatibility or CRLF failures to this change.
