# Turn Context Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Memory Agent answer a bounded, persisted conversation context made from a rolling summary and recent user/assistant messages, while preserving existing answer APIs and private-evidence rules.

**Architecture:** Mneme remains the owner of chat history and prepares a transport-safe `ConversationContext` before calling the Memory Agent. The Memory Agent accepts that context as an optional backward-compatible contract, propagates it to generation, and budgets it together with the current question and retrieved evidence. Existing `ChatSession.context_summary` fields store the rolling summary and watermark, so this milestone requires no database migration.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async ORM, pytest (existing suite only), Ruff

**Status:** Implemented inline and verified on 2026-07-16; checkboxes below preserve the executable task sequence rather than acting as live status.

---

## Scope and file map

This milestone deliberately stops before agent loops, tools, approvals, evaluation, and multi-agent orchestration.

- Create `app/mneme/domains/chat/context.py`: deterministic recent-message selection and rolling-summary logic.
- Modify `app/mneme/memoria/schemas/memory_agent.py`: API-side conversation context models.
- Modify `app/mneme/domains/chat/service.py`: prepare, persist, and send context.
- Modify `app/mneme/memoria/server/contracts/answers.py`: service-side mirror contract.
- Modify `app/mneme/memoria/server/runtime/contracts.py`: carry context into generation.
- Modify `app/mneme/memoria/server/runtime/orchestrator.py`: propagate request context.
- Modify `app/mneme/memoria/server/providers/llm.py`: unified prompt budget.
- Modify `app/mneme/memoria/server/runtime/prompts.py`: context-aware prompt rendering.
- Modify `docs/memoria-module.md`: ownership and safety semantics.

No test file is created or modified. The repository's test-addition policy is satisfied with disposable inline behavior contracts plus the existing suite.

### Task 1: Define backward-compatible conversation contracts

**Files:**
- Modify: `app/mneme/memoria/schemas/memory_agent.py`
- Modify: `app/mneme/memoria/server/contracts/answers.py`
- Modify: `app/mneme/memoria/server/runtime/contracts.py`

- [ ] **Step 1: Run a disposable RED contract**

Run an inline Python program that imports `ConversationContextData` from both boundary modules and constructs the two answer request types with populated context.

Expected: FAIL with an import or missing-field assertion before implementation.

- [ ] **Step 2: Add matching boundary models**

Use the same field names and limits in both boundary modules:

```python
ConversationRole = Literal["user", "assistant"]


class ConversationMessageData(BaseModel):
    message_id: str = Field(min_length=1, max_length=128)
    role: ConversationRole
    content: str = Field(min_length=1, max_length=20_000)


class ConversationContextData(BaseModel):
    summary: str = Field(default="", max_length=20_000)
    summary_through_message_id: str | None = Field(default=None, max_length=128)
    messages: list[ConversationMessageData] = Field(default_factory=list, max_length=24)
```

Add this field to both answer requests:

```python
conversation: ConversationContextData = Field(default_factory=ConversationContextData)
```

Old callers remain valid because the field has an empty default.

- [ ] **Step 3: Carry context into generation**

Import the service-side context type in `runtime/contracts.py` and add:

```python
conversation: ConversationContextData = Field(default_factory=ConversationContextData, repr=False)
```

to `GenerationRequest`.

- [ ] **Step 4: Re-run the inline contract**

Expected: PASS, including `model_dump()` round-tripping empty and populated context.

### Task 2: Prepare and persist bounded chat context

**Files:**
- Create: `app/mneme/domains/chat/context.py`
- Modify: `app/mneme/domains/chat/service.py`

- [ ] **Step 1: Run a disposable RED behavior contract**

Exercise exclusion of the current question, chronological ordering, recent-message limits, rolling compaction, watermark advancement, watermark reuse, and string bounds.

Expected: FAIL because `app.mneme.domains.chat.context` does not exist.

- [ ] **Step 2: Implement the focused pure helper**

Create immutable output data:

```python
@dataclass(frozen=True)
class PreparedConversationContext:
    context: ConversationContextData
    persisted_summary: str
    persisted_summary_through_message_id: str | None
```

Expose `prepare_conversation_context` with `messages`, `current_message_id`,
`existing_summary`, `summary_through_message_id`, `max_messages`, and
`summary_max_chars` arguments, returning `PreparedConversationContext`.
Its complete behavior is:

1. Keep only `user` and `assistant` messages and exclude `current_message_id`.
2. If the stored watermark is found, only later messages are unsummarized. If it is absent, preserve the existing summary and treat available history as unsummarized.
3. Keep the newest `max_messages` unsummarized messages verbatim, clipping individual content to 20,000 characters.
4. Render older unsummarized messages as normalized single-line `User: <content>` or `Assistant: <content>` entries and append them chronologically.
5. Bound the rolling summary to `summary_max_chars`, preferring newest complete lines; if one line exceeds the limit, keep its tail.
6. Advance the watermark only to the final message actually compacted.

- [ ] **Step 3: Integrate with the chat transaction**

After the current user message has an ID and before the existing commit:

```python
history = await list_chat_messages(db, session_id=session.id)
prepared_context = prepare_conversation_context(
    history,
    current_message_id=user_message.id,
    existing_summary=session.context_summary or "",
    summary_through_message_id=session.context_summary_through_message_id,
    max_messages=settings.AGENT_HISTORY_MAX_TURNS * 2,
    summary_max_chars=settings.AGENT_SUMMARY_MAX_CHARS,
)
session.context_summary = prepared_context.persisted_summary or None
session.context_summary_through_message_id = (
    prepared_context.persisted_summary_through_message_id
)
```

Pass `prepared_context.context` to `answer_via_memory_agent`. Keep non-session callers compatible with a default empty context parameter.

- [ ] **Step 4: Re-run the inline helper contract**

Expected: PASS for exclusion, ordering, compaction, watermark, and length bounds.

### Task 3: Propagate context through the runtime

**Files:**
- Modify: `app/mneme/domains/chat/service.py`
- Modify: `app/mneme/memoria/server/runtime/orchestrator.py`

- [ ] **Step 1: Set `conversation=conversation` on `MemoryAgentAnswerRequest`**

The existing client's `model_dump()` path transports the field without client-specific branching.

- [ ] **Step 2: Set `conversation=request.conversation` on `GenerationRequest`**

This is a direct typed propagation; no runtime state store is added.

- [ ] **Step 3: Run existing boundary/client checks**

```powershell
D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest tests\test_memory_agent_boundary.py tests\test_memory_agent_client.py tests\test_memory_agent_chat_cutover.py -q --basetemp .tmp\pytest-turn-context-boundary
```

Expected: all selected tests PASS; legacy fixtures remain valid.

### Task 4: Apply one model-aware prompt budget

**Files:**
- Modify: `app/mneme/memoria/server/providers/llm.py`
- Modify: `app/mneme/memoria/server/runtime/prompts.py`

- [ ] **Step 1: Extend `_PromptBudget`**

```python
@dataclass(frozen=True)
class _PromptBudget:
    question: str
    conversation_chars: int
    evidence_chars: int
    output_tokens: int
```

- [ ] **Step 2: Allocate one input window**

Update `_prompt_budget` to accept conversation context, preserve output/system reserves, clip the current question first, and return non-negative budgets. For `general_chat`, assign the remaining input characters to conversation. For private modes, let conversation consume at most one third of the remaining characters so current retrieved evidence retains at least two thirds; keep the existing evidence cap.

- [ ] **Step 3: Render context with explicit trust semantics**

Change `build_messages` to accept `conversation` and `max_conversation_chars`. Build:

1. the existing mode-specific system instruction, augmented in private modes to say conversation resolves intent but prior assistant claims are not evidence;
2. a bounded `<conversation_summary>` reference;
3. recent typed user/assistant messages that fit, dropping oldest turns first;
4. the current question exactly once as the final user message, plus current evidence in private modes.

- [ ] **Step 4: Wire the budgets into generation**

```python
messages = build_messages(
    mode=request.mode,
    question=budget.question,
    evidence=request.evidence,
    conversation=request.conversation,
    max_conversation_chars=budget.conversation_chars,
    max_context_chars=budget.evidence_chars,
)
```

- [ ] **Step 5: Run prompt/runtime checks**

Use an inline contract to confirm tiny budgets drop oldest recent turns first, the current question remains, private modes label conversation as non-evidence, and rendered text respects the assigned bounds.

Then run:

```powershell
D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest tests\test_answer_mode_pipelines.py tests\memoria\test_runtime_modes.py tests\memoria\test_runtime_failures.py tests\memoria\test_citation_validation.py -q --basetemp .tmp\pytest-turn-context-runtime
```

Expected: all selected tests PASS.

### Task 5: Document and verify the milestone

**Files:**
- Modify: `docs/memoria-module.md`

- [ ] **Step 1: Document ownership and safety**

Document that Mneme owns history/summary/watermark; the Memory Agent receives only a bounded snapshot; the field is optional for compatibility; prior assistant text is not private evidence; and tool execution/multi-step loops remain future milestones.

- [ ] **Step 2: Run the focused baseline**

```powershell
D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest tests\test_chat_session_persistence.py tests\test_memory_agent_chat_cutover.py tests\test_answer_mode_pipelines.py tests\memoria\test_runtime_modes.py tests\memoria\test_runtime_failures.py tests\memoria\test_citation_validation.py -q --basetemp .tmp\pytest-turn-context-final
```

Expected: at least the 25 baseline tests PASS.

- [ ] **Step 3: Run static and hygiene checks**

```powershell
D:\python_mine\Mneme\.venv\Scripts\python.exe -m compileall -q app\mneme
D:\python_mine\Mneme\.venv\Scripts\python.exe -m ruff check app\mneme\domains\chat\context.py app\mneme\domains\chat\service.py app\mneme\memoria\schemas\memory_agent.py app\mneme\memoria\server\contracts\answers.py app\mneme\memoria\server\runtime\contracts.py app\mneme\memoria\server\runtime\orchestrator.py app\mneme\memoria\server\runtime\prompts.py app\mneme\memoria\server\providers\llm.py
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 4: Review milestone boundaries**

Confirm the diff contains no schema migration, no test-file change, no tool loop, no approval flow, and no multi-agent code. Record exact verification evidence in the handoff.
