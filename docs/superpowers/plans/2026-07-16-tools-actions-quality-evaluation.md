# Controlled Tools, Action Proposals, and Agent Evaluation Implementation Plan

> **For agentic workers:** Execute the checklist in order. The repository policy forbids adding or modifying tests for this feature, so use disposable inline RED/GREEN contracts and then run the existing suites unchanged.

**Goal:** Let Memoria execute bounded, owner-scoped read tools during its reasoning loop, turn write intent into durable approval proposals instead of mutations, and evaluate answer plus tool-trajectory quality deterministically.

**Architecture:** Keep the current upfront retrieval for latency and backward compatibility. Add a small tool registry around the existing scoped retriever so the model may request source-specific follow-up searches within the selected answer-mode plan. The model may also request one of the existing write-action proposal definitions; these requests never execute in Memoria, and the Mneme chat boundary persists them as idempotent `ToolApprovalRequest` rows. Carry only bounded tool observations into the next model step, merge tool evidence into citation validation, and expose a sanitized trace. Extend the model-free evaluation contracts with optional trajectory expectations and publish separate agent gates so the existing answer gates remain stable.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, SQLAlchemy async, OpenAI-compatible JSON responses, existing Memoria evaluation runner

**Status:** Implemented inline and verified on 2026-07-16. The checklist remains as the executable delivery record.

---

## Scope and file map

- Create `app/mneme/memoria/server/runtime/tools.py`: tool definitions, scope intersection, execution, observation bounding, and sanitized trace records.
- Modify `app/mneme/memoria/server/config.py`: tool-call and observation hard limits.
- Modify `app/mneme/memoria/server/runtime/contracts.py`: optional tool execution context and generated tool evidence/trace.
- Modify `app/mneme/memoria/server/runtime/prompts.py`: structured `tool` decision and available-tool/observation payloads.
- Modify `app/mneme/memoria/server/providers/llm.py`: bounded tool execution inside the existing reasoning loop.
- Modify `app/mneme/memoria/server/api/answers.py`: share the scoped retriever with the tool executor.
- Modify `app/mneme/memoria/server/runtime/orchestrator.py` and `app/mneme/memoria/server/repositories/runs.py`: merge tool evidence before citation validation and persistence.
- Modify answer contracts in `app/mneme/memoria/server/contracts/answers.py` and `app/mneme/memoria/schemas/memory_agent.py`: expose sanitized `tool_calls`.
- Modify `app/mneme/memoria/chat_bridge.py` and `app/mneme/domains/chat/service.py`: translate tool traces, persist approval proposals idempotently, and attach them to assistant messages.
- Modify `app/mneme/memoria/server/eval/contracts.py`, `metrics.py`, and `runner.py`: optional trajectory expectations, metrics, agent gates, and live-response capture.
- Modify `app/mneme/memoria/server/eval/README.md` and `docs/memoria-module.md`: operational and evaluation semantics.
- Do not add or modify test files, database migrations, direct write executors, or multi-agent code.

### Task 1: Define and verify the tool boundary

- [ ] Run a disposable RED import/behavior contract for the absent `runtime.tools` module. It must require owner scope, reject a source tool outside the selected `RetrievalPlan`, cap `top_k`, remove raw read queries from the public trace, and mark every catalogued write action `approval_required` without calling a mutator.
- [ ] Implement immutable tool definitions for `search_documents`, `search_memories`, `search_profile`, and `search_relations`, plus the existing `WRITE_ACTION_CATALOG` proposals.
- [ ] Implement `ScopedToolExecutor` over the existing `EvidenceRetriever`. A read call builds a single-source plan intersected with the request plan; an action call validates its name and returns a proposal trace only.
- [ ] Re-run the disposable contract and cover allowed read, denied read, unknown tool, bounded result count, and write-proposal paths.

### Task 2: Integrate tools into the bounded reasoning loop

- [ ] Add `ANSWER_TOOL_MAX_CALLS` and `ANSWER_TOOL_OBSERVATION_MAX_CHARS` constrained settings.
- [ ] Extend the provider response decision to `tool | continue | final`; require non-empty tool calls for `tool`, reject tool decisions on the last reasoning step, and retain a complete candidate answer on every step.
- [ ] Describe only mode-allowed read tools and catalogued proposal tools in the system prompt. Treat arguments and observations as untrusted data.
- [ ] Execute requested calls in order up to the run budget, merge unique returned evidence, add bounded observation summaries to the next prompt, and append sanitized trace metadata. Never persist read queries, evidence content, prompts, hidden reasoning, or credentials.
- [ ] Return the latest complete candidate through the existing stop policy. Aggregate model token use exactly as before; tool calls do not reset reasoning or token budgets.
- [ ] Run an inline fake-provider GREEN contract proving: a read tool is called between two model steps, its evidence can be cited in the final candidate, a write tool remains `approval_required`, a denied tool becomes a safe observation, and max-call/max-step limits terminate safely.

### Task 3: Propagate evidence and durable action proposals

- [ ] Pass the request owner, knowledge-base scope, retrieval plan, and top-k to generation as an optional tool context.
- [ ] Merge generated tool evidence with upfront evidence before citation validation, response source IDs, and run persistence.
- [ ] Add sanitized `tool_calls` to Memoria response and client schemas without changing existing required fields.
- [ ] At the Mneme chat boundary, persist each `approval_required` catalog action with an idempotency key derived from user, message, and tool-call IDs. Copy the resulting approval ID/status into the saved assistant tool trace.
- [ ] Never persist approvals for unknown tools, read tools, completed traces, or malformed arguments. Never change `apply_enabled`; approval still does not execute a mutation.
- [ ] Run an inline persistence contract with a fake async repository call, then exercise Pydantic serialization across server and client response contracts.

### Task 4: Add deterministic trajectory quality evaluation

- [ ] Extend evaluation cases with optional expected/forbidden tool names, maximum call count, approval-required action names, stop reason, and prediction tool traces.
- [ ] Calculate tool selection precision/recall, tool-budget compliance, trajectory efficiency, stop correctness, and action-safety violations. Cases without trajectory expectations remain neutral at `1.0` with zero violations.
- [ ] Keep the existing answer `gates` unchanged. Add `agent_gates` requiring zero action-safety violations, full tool-budget compliance, and full stop correctness; make CLI success require both gate groups.
- [ ] Capture `tool_calls` from live `/v1/answers` responses and include the new report fields in JSON.
- [ ] Run disposable positive and negative cases proving a safe proposal passes, an executed write is flagged, a forbidden tool lowers selection quality, and an over-budget trace fails its agent gate.

### Task 5: Document and verify

- [ ] Document tool availability, scope intersection, hard limits, sanitized traces, approval-only writes, and the separation between answer gates and agent gates.
- [ ] Run `D:\python_mine\Mneme\.venv\Scripts\python.exe -m pytest tests\memoria -q`.
- [ ] Run the existing chat/client/boundary tests unchanged.
- [ ] Run Ruff on changed Python files, `compileall` for Memoria, the fixed answer-quality CLI, and `git diff --check`.
- [ ] Review the diff for unrelated edits, commit intentionally, and push `codex/tools-actions-evaluation`.
