# Preview Backend Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the live FastAPI backend and Vue frontend with the Stitch/preview product surface, starting with persistent AI conversations, user-configurable model access, and document-backed graph previews.

**Architecture:** Keep the current domain-owned backend layout and API response envelope. Add missing domain models and routers instead of overloading preview-only UI state. Preserve the existing `/kb/chat/query` path as a compatibility endpoint, then add session/message endpoints used by the AI Laboratory.

**Tech Stack:** FastAPI, SQLAlchemy async sessions, Alembic, Pydantic v2, Vue 3, TypeScript, Vite, Playwright, Python `unittest`.

---

## Current Contract Audit

### Already Backed By Real APIs

- Authentication: `/auth/register`, `/auth/login`, `/auth/me`.
- Knowledge bases: `/users/{user_id}/knowledge-bases`.
- Documents: `/kb/documents`, upload, index, delete.
- Graph data: `/graph`, `/graph/knowledge-bases/{knowledge_base_id}`, `/graph/documents/{document_id}`, rebuild, GraphRAG planning.
- Memory and analytics: `/memory/*`, `/profile/*`, `/analysis/*`, `/advice/*`.
- One-shot RAG chat: `/kb/chat/query`.
- Companion answer: `/companion/knowledge-bases/{knowledge_base_id}/reply`.
- Health/readiness: `/health`, `/health/neo4j`, `/health/readiness`.

### Preview Features Not Yet Backed Properly

- AI conversation history rail is currently static UI. Backend has `ChatSession`, but no message table and no session CRUD/list endpoints.
- `/kb/chat/query` accepts `session_id`, but the router ignores it and does not persist user/assistant messages.
- AI transcript in `App.vue` is mostly static Stitch content plus one `chatResult`; it does not render a real session message list.
- Settings AI Models panel is static. Backend only supports process-wide environment variables (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL_NAME`, `LLM_BASE_URL`).
- Users cannot create, test, select, or delete custom OpenAI-compatible model configurations.
- `get_llm()` only uses global settings; RAG/companion/advice/profile calls cannot use a per-user active model.
- Graph long-press preview is frontend-only. Backend lacks a document detail/source preview endpoint that returns the node's document title, summary, chunks, and metadata for the panel.
- Settings sync controls are visual only; no frontend command is connected to graph/memory rebuild or sync status.
- API access token display/copy is visual only; no token management endpoint exists.

## Target API Surface

### Chat Sessions

- `GET /kb/chat/sessions?knowledge_base_id=...`
  - Lists sessions for current user and knowledge base.
- `POST /kb/chat/sessions`
  - Creates an empty session with optional title.
- `GET /kb/chat/sessions/{session_id}`
  - Returns session metadata and ordered messages.
- `PATCH /kb/chat/sessions/{session_id}`
  - Renames or archives a session.
- `DELETE /kb/chat/sessions/{session_id}`
  - Soft-deletes or deletes a session and messages.
- `POST /kb/chat/sessions/{session_id}/messages`
  - Runs RAG, stores the user message and assistant answer, and returns updated message data.
- Keep `POST /kb/chat/query`
  - Compatibility wrapper. If `session_id` is provided, persist messages into that session; if not, return the current one-shot `ChatQueryData`.

### User Model Configuration

- `GET /settings/ai-models`
  - Returns provider presets, saved user configs, and active default config.
- `POST /settings/ai-models`
  - Creates a user model config.
- `PATCH /settings/ai-models/{config_id}`
  - Updates label, provider, base URL, model, temperature, context window, and API key.
- `POST /settings/ai-models/{config_id}/test`
  - Sends a small health-check prompt with the saved config.
- `POST /settings/ai-models/{config_id}/default`
  - Makes the config the user's active default.
- `DELETE /settings/ai-models/{config_id}`
  - Deletes non-default or inactive configs.

### Document Preview For Graph Nodes

- `GET /kb/documents/{document_id}`
  - Returns document metadata and latest index status.
- `GET /kb/documents/{document_id}/preview?chunk_limit=5`
  - Returns source preview data for the graph node details panel: title, file type, status, summary, representative chunks, and backlinks/memory entries.

### Settings Actions

- `POST /graph/knowledge-bases/{knowledge_base_id}/rebuild`
  - Already exists; frontend should expose it in Settings/Sync.
- `POST /memory/knowledge-bases/{knowledge_base_id}/rebuild`
  - Already exists; frontend should expose it in Settings/Sync.
- `GET /tasks/{task_id}`
  - Already exists; frontend should poll submitted rebuild/index tasks where applicable.

## File Structure

Create:

- `app/mneme/models/chat_message.py`
- `app/mneme/models/ai_model_config.py`
- `app/mneme/crud/chat_session.py`
- `app/mneme/crud/chat_message.py`
- `app/mneme/crud/ai_model_config.py`
- `app/mneme/domains/chat/router.py`
- `app/mneme/domains/chat/service.py`
- `app/mneme/domains/settings/router.py`
- `app/mneme/domains/settings/ai_models.py`
- `app/mneme/schemas/chat_session.py`
- `app/mneme/schemas/ai_model_config.py`
- `alembic/versions/20260707_01_add_chat_messages_and_ai_model_configs.py`
- `tests/test_chat_session_persistence.py`
- `tests/test_user_ai_model_config.py`

Modify:

- `app/mneme/bootstrap/router_registry.py`
- `app/mneme/models/__init__.py`
- `app/mneme/models/chat_session.py`
- `app/mneme/schemas/chat.py`
- `app/mneme/domains/retrieval/router.py`
- `app/mneme/domains/retrieval/query_service.py`
- `app/mneme/domains/companion/router.py`
- `app/mneme/clients/llm_client.py`
- `app/mneme/domains/documents/router.py`
- `app/mneme_frontend_v0.2.1/src/types.ts`
- `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- `app/mneme_frontend_v0.2.1/src/App.vue`
- `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`
- `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`

## Tasks

### Task 1: Chat Session Persistence

**Files:**
- Create: `app/mneme/models/chat_message.py`
- Create: `app/mneme/crud/chat_session.py`
- Create: `app/mneme/crud/chat_message.py`
- Create: `app/mneme/schemas/chat_session.py`
- Create: `app/mneme/domains/chat/service.py`
- Create: `app/mneme/domains/chat/router.py`
- Create: `tests/test_chat_session_persistence.py`
- Modify: `app/mneme/models/chat_session.py`
- Modify: `app/mneme/models/__init__.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/domains/retrieval/router.py`

- [ ] **Step 1: Write failing route/model contract test**

Add `tests/test_chat_session_persistence.py` with assertions that:

```python
def test_chat_session_router_is_registered():
    from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES

    assert "app.mneme.domains.chat.router" in ROUTER_MODULE_NAMES


def test_chat_message_model_is_registered():
    import app.mneme.models as models

    assert hasattr(models, "ChatSession")
    assert hasattr(models, "ChatMessage")
```

- [ ] **Step 2: Run red test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_chat_session_persistence
```

Expected: fails because `ChatMessage` and `app.mneme.domains.chat.router` do not exist.

- [ ] **Step 3: Add data model and schemas**

Implement `ChatMessage` with:

- `id: str`
- `session_id: str`
- `user_id: int`
- `knowledge_base_id: str`
- `knowledge_base_pk: int`
- `role: str` constrained by service logic to `user` or `assistant`
- `content: str`
- `sources_json: JSON`
- `citations_json: JSON`
- `route_json: JSON`
- `model_config_id: str | None`

Extend `ChatSession` with:

- `message_count: int`
- `last_message_at: datetime | None`
- `archived_at: datetime | None`

Add Pydantic schemas:

- `ChatSessionData`
- `ChatMessageData`
- `ChatSessionListData`
- `ChatSessionDetailData`
- `ChatSessionCreateRequest`
- `ChatSessionUpdateRequest`
- `ChatSessionMessageRequest`

- [ ] **Step 4: Add service behavior**

In `app/mneme/domains/chat/service.py`, implement:

- `create_chat_session(db, current_user, knowledge_base, title)`
- `list_chat_sessions(db, current_user, knowledge_base_id)`
- `get_chat_session_detail(db, current_user, session_id)`
- `rename_or_archive_chat_session(db, current_user, session_id, payload)`
- `delete_chat_session(db, current_user, session_id)`
- `ask_in_chat_session(db, current_user, session_id, question, top_k)`

`ask_in_chat_session` must call existing `generate_rag_answer`, create a `user` message, create an `assistant` message containing answer/citations/sources/route, update `message_count`, and update `last_message_at`.

- [ ] **Step 5: Add routes**

Expose the target `/kb/chat/sessions` endpoints from `app/mneme/domains/chat/router.py`, and register it in `ROUTER_MODULE_NAMES`.

- [ ] **Step 6: Keep `/kb/chat/query` compatible**

Modify `app/mneme/domains/retrieval/router.py` so `payload.session_id` is honored:

- if absent, current behavior remains.
- if present, validate ownership and persist into that session using chat service.

- [ ] **Step 7: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_chat_session_persistence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_citation_validation_service
```

Expected: all pass.

### Task 2: User AI Model Configurations

**Files:**
- Create: `app/mneme/models/ai_model_config.py`
- Create: `app/mneme/crud/ai_model_config.py`
- Create: `app/mneme/schemas/ai_model_config.py`
- Create: `app/mneme/domains/settings/router.py`
- Create: `app/mneme/domains/settings/ai_models.py`
- Create: `tests/test_user_ai_model_config.py`
- Modify: `app/mneme/models/__init__.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `app/mneme/clients/llm_client.py`

- [ ] **Step 1: Write failing settings contract test**

Add `tests/test_user_ai_model_config.py` with assertions that:

```python
def test_settings_router_is_registered():
    from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES

    assert "app.mneme.domains.settings.router" in ROUTER_MODULE_NAMES


def test_ai_model_config_model_is_registered():
    import app.mneme.models as models

    assert hasattr(models, "AiModelConfig")
```

- [ ] **Step 2: Run red test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_user_ai_model_config
```

Expected: fails because settings router and model config do not exist.

- [ ] **Step 3: Add model config table**

Create `AiModelConfig` fields:

- `id: str`
- `user_id: int`
- `label: str`
- `provider: str`
- `base_url: str`
- `model_name: str`
- `api_key_ciphertext: str | None`
- `temperature: float`
- `context_window: int`
- `is_default: bool`
- `enabled: bool`

Store no plaintext API key in response schemas. Until encryption is added, the implementation must either use environment variable references or add a minimal encryption helper before accepting user-entered secrets.

- [ ] **Step 4: Add settings API**

Implement:

- `GET /settings/ai-models`
- `POST /settings/ai-models`
- `PATCH /settings/ai-models/{config_id}`
- `POST /settings/ai-models/{config_id}/test`
- `POST /settings/ai-models/{config_id}/default`
- `DELETE /settings/ai-models/{config_id}`

Responses must mask API keys with `has_api_key: bool`, not echo the secret.

- [ ] **Step 5: Make LLM client accept overrides**

Extend `build_llm_kwargs` to accept an optional user config object. `get_llm()` keeps the current global behavior; add `get_llm_for_user_config(config)` for chat/companion flows.

- [ ] **Step 6: Wire chat to active user config**

When a session message is generated, resolve the current user's default model config. If none exists, fall back to global settings.

- [ ] **Step 7: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_user_ai_model_config tests.test_llm_provider_config tests.test_chat_session_persistence
```

Expected: all pass.

### Task 3: Frontend AI Laboratory Binding

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Test: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Add failing Playwright test**

Extend `preview-mode.spec.ts` to assert:

- AI history rail lists sessions from API state.
- Clicking a session renders its stored user/assistant messages.
- Submitting chat appends a user message and assistant message.
- Settings page renders saved AI model configs and active default.

- [ ] **Step 2: Run red test**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "ai sessions"
```

Expected: fails because AI transcript is static and session methods do not exist.

- [ ] **Step 3: Add TypeScript contracts and API methods**

Add frontend types:

- `ChatSessionData`
- `ChatMessageData`
- `ChatSessionDetailData`
- `ChatSessionListData`
- `AiModelConfigData`
- `AiModelConfigListData`

Add API methods:

- `listChatSessions`
- `createChatSession`
- `getChatSession`
- `deleteChatSession`
- `sendChatSessionMessage`
- `listAiModelConfigs`
- `createAiModelConfig`
- `updateAiModelConfig`
- `testAiModelConfig`
- `setDefaultAiModelConfig`
- `deleteAiModelConfig`

- [ ] **Step 4: Replace static AI transcript**

In `useMnemeWorkspace.ts`, add:

- `chatSessions`
- `activeChatSessionId`
- `chatMessages`
- `aiModelConfigs`
- `activeAiModelConfigId`
- `loadChatSessions`
- `selectChatSession`
- `sendChatMessage`
- `loadAiModelConfigs`

In `App.vue`, render history and transcript from those refs instead of static Stitch-only messages.

- [ ] **Step 5: Verify frontend**

Run:

```powershell
node tests\obsidian-source-contract.test.mjs
npm run lint
npx playwright test tests/preview-mode.spec.ts
npm run build
```

Expected: all pass.

### Task 4: Graph Node Document Preview API

**Files:**
- Modify: `app/mneme/domains/documents/router.py`
- Modify: `app/mneme/schemas/document.py`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Test: `tests/test_documents_domain_convergence.py`
- Test: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Add backend document preview test**

Assert that `GET /kb/documents/{document_id}/preview` is registered and returns document metadata plus representative chunks for an owned document.

- [ ] **Step 2: Add schemas and route**

Add `DocumentPreviewData` with:

- `document_id`
- `knowledge_base_id`
- `file_name`
- `file_type`
- `status`
- `summary`
- `chunks`
- `memory_entries`

- [ ] **Step 3: Bind graph long-press panel**

When long-pressing a document node, call `documentPreview(documentId)`. For memory nodes, use `entity_id` and show memory metadata. Keep preview data fixture-compatible.

- [ ] **Step 4: Verify**

Run backend document tests and frontend preview tests.

### Task 5: Settings Sync Actions

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Test: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Add settings action tests**

Assert that Settings can trigger graph rebuild and memory rebuild for the active knowledge base.

- [ ] **Step 2: Wire existing APIs**

Use existing:

- `api.rebuildKnowledgeBaseGraph`
- `api.rebuildMemory`
- `api.getTask`

Show submitted task/status in Settings.

- [ ] **Step 3: Verify**

Run frontend lint, preview tests, and build.

## Recommended Execution Order

1. Task 1: Chat session persistence.
2. Task 3 partial: frontend AI session binding for history/transcript.
3. Task 2: user model configurations.
4. Task 3 remaining: settings page model binding.
5. Task 4: graph document preview API.
6. Task 5: settings sync actions.

This order makes the AI Laboratory useful first, then makes Settings real, then removes remaining graph/settings preview-only gaps.

## Verification Rollup

After all tasks:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_chat_session_persistence tests.test_user_ai_model_config tests.test_llm_provider_config tests.test_documents_domain_convergence tests.test_query_router_service tests.test_retrieval_debug_service tests.test_retrieval_fusion_service tests.test_graph_domain_convergence tests.test_graph_rag_service
node tests\obsidian-source-contract.test.mjs
npm run lint
npx playwright test tests/preview-mode.spec.ts
npm run build
git diff --check
```

Expected: backend tests pass, frontend tests pass, build passes, and no whitespace errors.

## Self-Review

- Spec coverage: Covers preview-visible gaps for AI history, chat persistence, user model access, graph node document preview, and Settings sync actions.
- Placeholder scan: The plan names exact endpoint paths, files, tests, fields, and verification commands.
- Type consistency: Chat session/message/model config names are consistent across backend schemas and frontend TypeScript types.
