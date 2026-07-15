# Atomic Tools and Multi-Loop Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Mneme Agent tools return primitive structured evidence and let one outer Agent loop own tool selection, repeated tool use, and final answer synthesis.

**Architecture:** Keep the existing complete RAG pipeline for legacy non-Agent endpoints. Add a small primitive tool adapter layer for Agent execution, then replace the current fixed two-pass runner branch with a bounded model/tool state machine using the existing LangChain message protocol.

**Tech Stack:** Python 3.14, FastAPI, LangChain messages/ChatOpenAI, SQLAlchemy async, Pydantic v2.

---

## File map

- Create `app/mneme/agent/tools/primitives.py`: four primitive backend adapters returning structured evidence without composing a final LLM answer.
- Modify `app/mneme/agent/tools/contracts.py`: carry a JSON-safe evidence payload and expose it to the outer model.
- Modify `app/mneme/agent/tools/backend.py`: retain timeout/policy/error normalization and dispatch to primitive adapters.
- Modify `app/mneme/agent/runner.py`: bounded model/tool re-entry loop, actual loop metadata, grounding enforcement, deterministic fallback, and citation extraction.
- Modify `app/mneme/agent/prompt_builder.py`: tell the outer model that tools return evidence rather than ready-made answers.
- Modify `app/mneme/agent/guards.py`: allow enough bounded model entries for repeated tool use plus final synthesis.
- Do not create or modify tests under the current project test-addition policy.

### Task 1: Add primitive tool results

- [ ] Extend `BackendToolResult` with `evidence: dict[str, Any]` and a `success(...)` constructor.
- [ ] Serialize `evidence`, sources, confidence, and uncertainty in `to_model_text()` so the outer model receives the actual backend facts.
- [ ] Implement these adapters in `tools/primitives.py`:

```python
async def search_knowledge_base(*, query, top_k, context) -> BackendToolResult: ...
async def search_memory(*, query, top_k, context) -> BackendToolResult: ...
async def get_profile(*, context) -> BackendToolResult: ...
async def analyze_growth(*, context) -> BackendToolResult: ...
```

- [ ] `kb_search` calls `build_query_context()` and returns `context_text`, retrieval counts, and sources.
- [ ] `memory_search` calls `search_memory_entries_by_keywords()` and returns memory records plus source projections.
- [ ] `profile_get` and `growth_analysis` return their existing structured backend snapshots, not a separately composed chat answer.
- [ ] Empty mandatory evidence returns `ToolErrorKind.UNAVAILABLE`, preventing unsupported synthesis.

### Task 2: Dispatch tools without nested final-answer generation

- [ ] Replace the `generate_rag_answer()` call in `tools/backend.py` with a fixed executor map:

```python
TOOL_EXECUTORS = {
    "kb_search": search_knowledge_base,
    "memory_search": search_memory,
    "profile_get": get_profile,
    "growth_analysis": analyze_growth,
}
```

- [ ] Preserve trusted request scope, selected `answer_mode` policy, timeout, abort checks, and structured error classification.
- [ ] Keep `generate_rag_answer()` unchanged for existing non-Agent callers.

### Task 3: Replace the fixed two-pass flow with a bounded loop

- [ ] Use the selected-mode tool schema and run up to `AgentRunLimits.max_model_loops`.
- [ ] On the first model entry, require a tool. If the provider does not emit a structured tool call, inject one server-selected fallback call for the selected mode.
- [ ] For each model entry:

```text
call model -> collect tool calls -> validate policy/repetition/limits
           -> execute tools -> append ToolMessage -> re-enter model
           -> no tool calls + successful evidence -> final answer
```

- [ ] Append the model `AIMessage` before its matching `ToolMessage` values so LangChain tool-call pairing remains valid.
- [ ] Emit `loop_index`, `loop_reason`, and `selected_capability_ids` on lifecycle, assistant, and tool events.
- [ ] Block final factual output when required evidence failed or no successful tool execution occurred.
- [ ] Use the most recent successful tool result as deterministic recovery only when the final model response is empty.
- [ ] Build persisted citations only from source IDs explicitly referenced by the final answer.

### Task 4: Preserve compatibility and verify

- [ ] Run scoped Ruff and Python compile checks.
- [ ] Run an inline fake-model smoke check for two consecutive tool calls followed by a final answer; do not add a test file.
- [ ] Run the complete existing backend suite with project-local `--basetemp`.
- [ ] Confirm `rg "generate_rag_answer" app/mneme/agent/tools` returns no matches.
- [ ] Confirm `git diff --check` succeeds and review only files in this plan.

## Success criteria

- Agent tool execution performs no nested final-answer LLM call.
- One run can execute more than one model/tool round before finalizing.
- Tool failure or absent required evidence cannot produce a grounded final answer.
- Existing synchronous RAG endpoints retain their current behavior.
- Existing test suite and scoped static checks pass without modifying tests.
