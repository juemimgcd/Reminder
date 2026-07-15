# Explicit Answer Mode Pipelines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `test-driven-development` and execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each user-selected answer mode execute a meaningfully different, testable pipeline without inspecting the question text to infer intent.

**Architecture:** Keep `AnswerMode` as the explicit request contract. The Agent maps that value to a fixed route, retrieval scope, and prompt; `kb_qa` uses hybrid document and memory retrieval, while `memory_query` uses memory-only retrieval. Profile, growth, and general chat keep their existing non-retrieval paths. The UI explains the selected mode and displays the route used for each assistant response.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, SQLAlchemy async, LangChain prompts, Vue 3, TypeScript, pytest, Node source-contract tests, Playwright.

---

## File map

- Modify `app/mneme/agent/router.py`: own the fixed answer-mode-to-pipeline and retrieval-scope mappings.
- Modify `app/mneme/agent/orchestrator.py`: pass the explicit retrieval scope and select the evidence prompt from `answer_mode`.
- Modify `app/mneme/domains/retrieval/context_service.py`: skip document/vector recall for memory-only requests.
- Modify `app/mneme/utils/prompt_builder.py`: provide a prompt dedicated to long-term memory answers.
- Create `tests/test_answer_mode_pipelines.py`: cover fixed mode mapping, retrieval isolation, and prompt selection.
- Modify `app/mneme_frontend_v0.2.1/src/views/AiLabView.vue`: explain the selected mode and show the mode used by assistant messages.
- Modify `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`: verify mode selection and the outgoing request payload.
- Modify `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`: preserve the mode selector and route badge contract.
- Create `docs/answer-modes.md`: document the five public modes and their evidence behavior.

### Task 1: Isolate knowledge-base and long-term-memory retrieval

**Files:**
- Modify: `app/mneme/agent/router.py`
- Modify: `app/mneme/agent/orchestrator.py`
- Modify: `app/mneme/domains/retrieval/context_service.py`
- Create: `tests/test_answer_mode_pipelines.py`

- [ ] **Step 1: Write failing tests for fixed retrieval scopes**

```python
from app.mneme.agent.router import retrieval_scope_for_answer_mode


def test_knowledge_base_mode_uses_hybrid_retrieval():
    assert retrieval_scope_for_answer_mode("kb_qa") == "hybrid"


def test_memory_mode_uses_only_long_term_memory():
    assert retrieval_scope_for_answer_mode("memory_query") == "memory_only"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_answer_mode_pipelines.py -q -p no:cacheprovider
```

Expected: FAIL because `retrieval_scope_for_answer_mode` does not exist.

- [ ] **Step 3: Add the fixed retrieval-scope mapping**

Add to `app/mneme/agent/router.py`:

```python
from typing import Literal

RetrievalScope = Literal["hybrid", "memory_only"]


def retrieval_scope_for_answer_mode(answer_mode: AnswerMode) -> RetrievalScope:
    if answer_mode == "memory_query":
        return "memory_only"
    return "hybrid"
```

Only the two retrieval modes consume this value; profile, growth, and general chat return before context construction.

- [ ] **Step 4: Make context construction honor the scope**

Change the signature in `app/mneme/domains/retrieval/context_service.py`:

```python
async def build_query_context(
    query: str,
    *,
    db: AsyncSession,
    top_k: int = 4,
    user_id: int | None = None,
    knowledge_base_id: str | None = None,
    context_budget: int | None = None,
    retrieval_scope: RetrievalScope = "hybrid",
) -> dict[str, Any]:
```

Import `RetrievalScope` from `app.mneme.agent.router`. Construct vector and keyword tasks only for `hybrid`; for `memory_only`, initialize the corresponding results as empty lists and execute only `search_memory_entries_by_keywords`:

```python
raw_vector_items: list[tuple[LCDocument, float]] = []
chunk_rows: list[tuple[Chunk, float]] = []

if retrieval_scope == "hybrid":
    vector_task = asyncio.create_task(
        retrieve_documents_with_scores(
            query=query,
            top_k=vector_recall_k,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    async with open_read_session() as keyword_db:
        keyword_task = asyncio.create_task(
            search_chunks_by_keywords(
                keyword_db,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                query_terms=query_terms,
                limit=keyword_recall_k,
            )
        )
        raw_vector_items, chunk_rows = await asyncio.gather(vector_task, keyword_task)

async with open_read_session() as memory_db:
    memory_rows = await search_memory_entries_by_keywords(
        memory_db,
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        query_terms=query_terms,
        limit=memory_recall_k,
    )
```

- [ ] **Step 5: Pass the scope from the orchestrator**

In `app/mneme/agent/orchestrator.py`, compute the scope only after the non-retrieval branches have returned:

```python
retrieval_scope = retrieval_scope_for_answer_mode(answer_mode)
context_packet = await build_query_context(
    query=question,
    db=db,
    top_k=top_k,
    user_id=user_id,
    knowledge_base_id=knowledge_base_id,
    retrieval_scope=retrieval_scope,
)
```

- [ ] **Step 6: Add an isolation test and verify GREEN**

Use `AsyncMock` to patch `retrieve_documents_with_scores`, `search_chunks_by_keywords`, and `search_memory_entries_by_keywords`. Assert that `memory_only` never awaits the first two and does await memory search once. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_answer_mode_pipelines.py tests/test_retrieval_fusion_service.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add app/mneme/agent/router.py app/mneme/agent/orchestrator.py app/mneme/domains/retrieval/context_service.py tests/test_answer_mode_pipelines.py
git commit -m "feat: isolate answer mode retrieval scopes"
```

### Task 2: Give long-term memory its own evidence prompt

**Files:**
- Modify: `app/mneme/utils/prompt_builder.py`
- Modify: `app/mneme/agent/orchestrator.py`
- Modify: `tests/test_answer_mode_pipelines.py`

- [ ] **Step 1: Write a failing prompt-selection test**

```python
from app.mneme.agent.orchestrator import get_evidence_prompt_for_mode


def test_memory_mode_selects_memory_prompt():
    prompt = get_evidence_prompt_for_mode("memory_query", "FORMAT")
    system_text = prompt.messages[0].prompt.template
    assert "long-term memory" in system_text.lower()
    assert "FORMAT" in system_text
```

- [ ] **Step 2: Run the test and verify RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_answer_mode_pipelines.py::test_memory_mode_selects_memory_prompt -q -p no:cacheprovider
```

Expected: FAIL because `get_evidence_prompt_for_mode` does not exist.

- [ ] **Step 3: Add a dedicated memory prompt**

Add to `app/mneme/utils/prompt_builder.py`:

```python
def get_memory_rag_prompt(format_instructions: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You answer only from the user's retrieved long-term memory evidence. "
                "Separate stable facts from uncertain recollections. "
                "Do not claim that a memory is current when its evidence is historical. "
                "Every citation must use a source_id present in context. "
                f"Return exactly this structure:\n{format_instructions}",
            ),
            ("human", "Long-term memory evidence:\n{context}\n\nUser question:\n{question}"),
        ]
    )
```

- [ ] **Step 4: Select the prompt explicitly**

Add to `app/mneme/agent/orchestrator.py`:

```python
def get_evidence_prompt_for_mode(answer_mode: AnswerMode, format_instructions: str):
    if answer_mode == "memory_query":
        return get_memory_rag_prompt(format_instructions)
    return get_evidence_rag_prompt(format_instructions)
```

Add `answer_mode: AnswerMode` to `invoke_evidence_answer`, pass it from `generate_rag_answer`, and build the chain with `get_evidence_prompt_for_mode`.

- [ ] **Step 5: Verify both prompt branches**

Add a second assertion that `kb_qa` selects the ordinary evidence prompt and does not contain `long-term memory`. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_answer_mode_pipelines.py tests/test_citation_validation_service.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add app/mneme/utils/prompt_builder.py app/mneme/agent/orchestrator.py tests/test_answer_mode_pipelines.py
git commit -m "feat: add memory-specific answer prompt"
```

### Task 3: Explain and display the selected mode in chat

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/AiLabView.vue`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`

- [ ] **Step 1: Write failing browser assertions**

In `preview-mode.spec.ts`, intercept `POST /kb/chat/sessions/*/messages`, select `Long-term memory`, send `What changed in my notes?`, and assert:

```ts
expect(request.postDataJSON()).toMatchObject({
  question: "What changed in my notes?",
  answer_mode: "memory_query",
});
await expect(page.getByTestId("answer-mode-description")).toContainText("stored memory");
```

In the source-contract test, require `data-testid="answer-mode-badge"`.

- [ ] **Step 2: Run the frontend tests and verify RED**

```powershell
cd app/mneme_frontend_v0.2.1
node tests/obsidian-source-contract.test.mjs
npx playwright test tests/preview-mode.spec.ts --grep "answer mode"
```

Expected: source contract fails because the badge is missing; Playwright fails because the description is missing.

- [ ] **Step 3: Add descriptions and response badges**

Change the `answerModes` entries in `AiLabView.vue` to:

```ts
const answerModes = [
  { value: "kb_qa", label: "Knowledge base", description: "Answer from indexed documents and supporting memory." },
  { value: "memory_query", label: "Long-term memory", description: "Answer only from stored memory evidence." },
  { value: "profile_query", label: "Profile", description: "Summarize stable themes, abilities, and expression style." },
  { value: "analysis_query", label: "Growth", description: "Analyze recent focus, progress, blockers, and next actions." },
  { value: "general_chat", label: "General chat", description: "Answer without using knowledge-base evidence." },
] as const;
```

Add:

```ts
const selectedAnswerMode = computed(() => answerModes.find((mode) => mode.value === props.workspace.chatAnswerMode.value) ?? answerModes[0]);
const answerModeLabel = (queryType?: string | null) => answerModes.find((mode) => mode.value === queryType)?.label ?? "Assistant";
```

Render the description under the selector and the stored route on assistant messages:

```vue
<small data-testid="answer-mode-description">{{ selectedAnswerMode.description }}</small>
<span v-if="message.role === 'assistant' && message.route" data-testid="answer-mode-badge">
  {{ answerModeLabel(message.route.query_type) }}
</span>
```

- [ ] **Step 4: Verify responsive UI behavior**

Run the source contract and the focused Playwright test at desktop and mobile project sizes. Expected: all five buttons remain keyboard reachable, the selected button has `aria-pressed="true"`, and the send button remains visually separate.

- [ ] **Step 5: Commit**

```powershell
git add app/mneme_frontend_v0.2.1/src/views/AiLabView.vue app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs
git commit -m "feat: explain answer modes in chat"
```

### Task 4: Establish the five-mode contract and documentation

**Files:**
- Modify: `tests/test_answer_mode_pipelines.py`
- Create: `docs/answer-modes.md`

- [ ] **Step 1: Add a complete mode matrix test**

```python
import pytest


@pytest.mark.parametrize(
    ("answer_mode", "query_type", "pipeline", "retrieval_scope"),
    [
        ("kb_qa", "kb_qa", "evidence_rag", "hybrid"),
        ("memory_query", "memory_query", "memory_rag", "memory_only"),
        ("profile_query", "profile_query", "profile", None),
        ("analysis_query", "analysis_query", "growth_analysis", None),
        ("general_chat", "general_chat", "general_chat", None),
    ],
)
def test_answer_mode_contract(answer_mode, query_type, pipeline, retrieval_scope):
    route = route_answer_mode(answer_mode)
    assert route.query_type == query_type
    assert route.target_pipeline == pipeline
    if route.requires_retrieval:
        assert retrieval_scope_for_answer_mode(answer_mode) == retrieval_scope
```

- [ ] **Step 2: Document observable behavior**

Create `docs/answer-modes.md` with a table containing these exact columns: `answer_mode`, UI label, retrieval sources, prompt, citations, fallback. State that no mode is inferred from question text and omitted mode defaults to `kb_qa` for backward compatibility.

- [ ] **Step 3: Run the final focused verification**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_answer_mode_pipelines.py tests/test_agent_module_boundary.py tests/test_retrieval_fusion_service.py tests/test_citation_validation_service.py -q -p no:cacheprovider
cd app/mneme_frontend_v0.2.1
node tests/obsidian-source-contract.test.mjs
npm run lint
```

Expected: all focused Python tests pass, the source contract exits 0, and `vue-tsc --noEmit` exits 0 after the existing frontend dependencies are restored.

- [ ] **Step 4: Commit**

```powershell
git add tests/test_answer_mode_pipelines.py docs/answer-modes.md
git commit -m "docs: define answer mode contracts"
```

## Completion criteria

- No online Agent path calls `route_query(question)` or inspects question text to choose a mode.
- `kb_qa` searches vector chunks, keyword chunks, and memory entries.
- `memory_query` never calls vector or chunk keyword retrieval and cites only memory-backed evidence.
- Profile, growth, and general chat keep their fixed non-retrieval behavior.
- Every chat request sends `answer_mode`, and every assistant response shows the stored route label.
- The five-mode matrix, citation behavior, focused backend tests, frontend contract, and TypeScript check pass.
