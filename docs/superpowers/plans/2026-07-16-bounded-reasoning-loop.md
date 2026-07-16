# Bounded Reasoning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one Memory Agent answer request perform a bounded sequence of model self-review steps before returning a final candidate, with explicit stop reasons, aggregate usage, and no exposed chain-of-thought.

**Architecture:** Keep retrieval and citation validation single-pass. Add a pure runtime state transition for `continue` versus `final`, while the existing provider gateway performs repeated structured model calls and carries only a short outcome-level progress summary between calls. Bound execution by step count and aggregate completion-token budget; persist sanitized step/decision/stop metadata through the existing `model_attempts` JSON without a schema migration.

**Tech Stack:** Python 3.12, Pydantic v2, OpenAI-compatible chat completions, existing Memory Agent runtime and pytest suite

**Status:** Implemented inline and verified on 2026-07-16; the checkboxes preserve the executable task sequence.

---

## Scope and file map

- Create `app/mneme/memoria/server/runtime/reasoning.py`: pure bounded-loop transition and stop-reason contract.
- Modify `app/mneme/memoria/server/config.py`: maximum steps, summary size, and total completion-token budget.
- Modify `app/mneme/memoria/server/runtime/prompts.py`: step control, progress summary, and no-chain-of-thought output contract.
- Modify `app/mneme/memoria/server/providers/llm.py`: repeated structured calls, retries per step, aggregate usage, and sanitized trajectory metadata.
- Modify `docs/memoria-module.md`: runtime semantics and milestone boundary.
- Do not modify database migrations, API response shape, retrieval, citation validation, tests, tools, or multi-agent code.

### Task 1: Define the pure bounded-loop transition

**Files:**
- Create: `app/mneme/memoria/server/runtime/reasoning.py`

- [ ] **Step 1: Run a disposable RED contract**

Import `transition_reasoning_step` and assert that a continue decision advances, a final decision stops with `model_final`, the last allowed step stops with `max_steps`, and an exhausted token budget stops with `token_budget`.

Expected: FAIL because the runtime module does not exist.

- [ ] **Step 2: Implement the transition contract**

```python
ReasoningDecision = Literal["continue", "final"]
ReasoningStopReason = Literal["model_final", "max_steps", "token_budget"]


@dataclass(frozen=True)
class ReasoningTransition:
    should_continue: bool
    next_step_index: int
    summary: str
    stop_reason: ReasoningStopReason | None


def transition_reasoning_step(
    *,
    step_index: int,
    max_steps: int,
    decision: ReasoningDecision,
    summary: str,
    max_summary_chars: int,
    budget_exhausted: bool,
) -> ReasoningTransition:
    if not 1 <= step_index <= max_steps:
        raise ValueError("step_index must be within max_steps")
    normalized = " ".join(summary.split())[:max_summary_chars]
    if decision == "final":
        return ReasoningTransition(False, step_index, normalized, "model_final")
    if budget_exhausted:
        return ReasoningTransition(False, step_index, normalized, "token_budget")
    if step_index == max_steps:
        return ReasoningTransition(False, step_index, normalized, "max_steps")
    return ReasoningTransition(True, step_index + 1, normalized, None)
```

- [ ] **Step 3: Re-run the inline transition contract**

Expected: PASS for all four stop/continue paths and invalid step bounds.

### Task 2: Configure hard execution bounds

**Files:**
- Modify: `app/mneme/memoria/server/config.py`

- [ ] **Step 1: Add three constrained settings**

```python
ANSWER_REASONING_MAX_STEPS: int = Field(default=3, ge=1, le=5)
ANSWER_REASONING_SUMMARY_MAX_CHARS: int = Field(default=600, ge=100, le=2000)
ANSWER_REASONING_TOTAL_OUTPUT_TOKENS: int = Field(default=3600, ge=100, le=16000)
```

Each configured provider receives at most this many reasoning steps and this aggregate completion-token allowance. Existing single-step providers remain compatible because the new response decision defaults to `final`.

### Task 3: Add structured step prompts without chain-of-thought

**Files:**
- Modify: `app/mneme/memoria/server/runtime/prompts.py`
- Modify: `app/mneme/memoria/server/providers/llm.py`

- [ ] **Step 1: Extend the parsed provider answer**

Add `decision: Literal["continue", "final"] = "final"` and a bounded optional `reasoning_summary`. A Pydantic after-validator rejects `continue` unless the summary contains a non-empty outcome-level review note. The `answer` remains mandatory on every step so the latest candidate can safely terminate at a hard limit.

- [ ] **Step 2: Extend prompt construction**

Add optional `reasoning_summary`, `max_reasoning_chars`, `step_index`, and `max_steps` arguments. The system contract must:

- request `decision` and `reasoning_summary` in the JSON object;
- allow `continue` only for a material correctness, grounding, or completeness issue;
- require `final` on the last step;
- prohibit revealing hidden chain-of-thought and restrict the summary to an outcome-level note.

Include the previous bounded note inside `<reasoning_progress>` in the final user payload. Never include it in the final API response or persisted attempt metadata.

- [ ] **Step 3: Budget the progress note**

Extend `_PromptBudget` with `reasoning_chars`. After bounding the question, private modes reserve at least two thirds of remaining characters for evidence; the progress note and conversation share the other third. General chat gives the note at most one third of remaining characters and gives the rest to conversation.

### Task 4: Execute repeated model steps

**Files:**
- Modify: `app/mneme/memoria/server/providers/llm.py`

- [ ] **Step 1: Add a reasoning-step loop around existing retries**

For each resolved provider configuration:

1. Start at step 1 with an empty progress note and the configured total output-token allowance.
2. Build a fresh budget and messages for the current step.
3. Keep the existing retry/classification behavior inside that step.
4. Parse the candidate answer and transition through `transition_reasoning_step`.
5. On continue, carry only the normalized note into the next step.
6. On any stop reason, return the latest complete candidate.
7. If a step exhausts provider retries, move to the existing fallback provider policy.

- [ ] **Step 2: Aggregate and cap usage**

Set each call's `max_tokens` to the smaller of the per-call model budget and remaining aggregate output budget. Sum prompt/completion tokens across successful reasoning calls. Charge the requested allowance when provider usage is missing, ensuring the next call cannot exceed the configured aggregate cap.

- [ ] **Step 3: Persist sanitized trajectory metadata**

Extend each `model_attempts` entry with `reasoning_step`. Successful entries also carry `decision` and, when terminal, `stop_reason`. Do not persist the progress summary, prompt, answer, API key, or hidden reasoning.

- [ ] **Step 4: Run an inline fake-provider GREEN contract**

Use a fake OpenAI-compatible client that returns:

1. step 1 with `decision="continue"`, a candidate answer, and a short review note;
2. step 2 with `decision="final"` and the corrected candidate.

Assert two model calls, final step-2 answer, aggregate token counts, `model_final` metadata, and step-2 prompt inclusion of the bounded progress note. Add separate inline cases for forced `max_steps`, `token_budget`, and legacy responses without a decision.

### Task 5: Document and verify

**Files:**
- Modify: `docs/memoria-module.md`

- [ ] **Step 1: Document bounded-loop semantics**

State that retrieval remains single-pass, each model step must provide a complete candidate, only an outcome-level note crosses steps, stop reasons are sanitized, and tools/multi-agent remain later milestones.

- [ ] **Step 2: Run existing tests**

```powershell
New-Item -ItemType Directory -Force .tmp | Out-Null
D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest tests\memoria -q --basetemp .tmp\pytest-bounded-reasoning
D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest tests\test_chat_session_persistence.py tests\test_memory_agent_chat_cutover.py tests\test_memory_agent_boundary.py tests\test_memory_agent_client.py -q --basetemp .tmp\pytest-bounded-reasoning-boundary
```

Expected: all selected tests PASS.

- [ ] **Step 3: Run static and scope checks**

```powershell
D:\python_mine\Mneme\.venv\Scripts\python.exe -m ruff check app\mneme\memoria\server\config.py app\mneme\memoria\server\runtime\reasoning.py app\mneme\memoria\server\runtime\prompts.py app\mneme\memoria\server\providers\llm.py
D:\python_mine\Mneme\.venv\Scripts\python.exe -m compileall -q app\mneme\memoria\server
git diff --check
```

Confirm no migration, test, tool, or multi-agent file changed.
