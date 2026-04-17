---
name: agent-framework
description: Generate or refine FastAPI-based agent project blueprints and implementation plans. Use when the user wants to design a new agent backend, abstract an existing project's architecture/style, generate a `target.md`, or produce `dayX.md`-style execution docs. Especially use when the plan should emphasize layered boundaries, `utils` capability pipelines such as `llm + prompt + builder`, and optional modules that should not default to database, auth, file ingestion, or RAG unless the requirement truly needs them.
---

# Agent Framework

## Overview

Turn an agent idea into a concrete FastAPI project plan.

Keep the core structure minimal and demand-driven. Put database, auth, file ingestion, retrieval, and indexing behind explicit requirement checks instead of treating them as defaults.

## Choose The Output Mode

Pick the right output before drafting anything.

### Mode 1: `target.md`

Use when the user wants:

- project positioning
- layered architecture
- directory structure
- phased roadmap
- optional enhancement advice

### Mode 2: `dayX.md`-style plan

Use when the user wants:

- a day-by-day build plan
- a teaching-style implementation schedule
- a milestone document for a specific feature or day
- a structured execution guide for one phase

### Mode 3: Combined output

Use when the user wants both:

- a high-level project blueprint
- and one or more execution-day documents

In combined mode, define the project first, then break the work into days or milestones.

## Follow This Workflow

1. Classify the agent.
   - Decide whether it is question-answering, workflow orchestration, analysis/reporting, or mixed.
2. Infer the true minimum architecture.
   - Decide which layers are needed now.
   - Do not default to a full backend stack.
3. Design the core `utils` pipeline.
   - Treat `utils` as capability nodes, not a miscellaneous folder.
4. Produce the main planning artifact.
   - Generate `target.md`, `dayX.md`, or both depending on the request.
5. Append optional enhancements last.
   - Keep optional modules out of the default scaffold.

## Apply These Planning Rules

- Start from requirements, not from an inherited tree.
- Keep API handlers thin when the project exposes HTTP APIs.
- Push agent intelligence into reusable `utils` modules.
- Prefer function-oriented modules unless a stateful class model is clearly better.
- Use role-based names such as `prompt`, `builder`, `organizer`, and `service`.
- Explain why a module exists; do not just list files.
- Keep optional modules clearly marked as optional.

## Use These Layer Boundaries

Only include the layers the project truly needs.

### `router`

Include only when the project exposes HTTP APIs.

Use it for:

- request parsing
- parameter validation
- dependency injection
- thin orchestration
- response wrapping

Do not use it for:

- writing prompts
- directly calling low-level model SDKs
- hiding the full workflow inside one endpoint

### `utils`

Treat this as the core agent layer.

Use it for:

- model access
- prompt construction
- builder orchestration
- context organization
- retrieval or tool integration
- cross-step services

### `schemas`

Include when the project needs:

- request or response models
- structured LLM outputs
- stable contracts between modules

### `conf`

Include when the project needs centralized configuration, logging, or third-party settings.

### `crud`

Include only when the project has real persistent-state workflows.

Do not assume `crud` is needed for:

- single-run agents
- internal workflow tools
- stateless orchestration
- ephemeral analysis jobs

## Prefer These `utils` Patterns

### Pattern 1: Structured generation

Use for reports, plans, summaries, analyses, advice, and similar outputs.

Pipeline:

`input -> prompt -> llm -> parser -> normalized result`

Recommended modules:

- `<domain>_prompt.py`
- `<domain>_builder.py`
- `schemas/<domain>.py`

Rules:

- Normalize upstream context before prompting.
- Prefer structured parsing when the result will be reused.
- Return business-ready output from the builder, not raw model output.

### Pattern 2: Context organization

Use for timelines, grouped records, multi-source inputs, and pre-LLM shaping.

Pipeline:

`raw context -> organizer -> builder`

Recommended modules:

- `<domain>_organizer.py`
- `<domain>_builder.py`

### Pattern 3: Retrieval QA

Use only when the project truly needs retrieval.

Pipeline:

`retrieve -> format_context -> prompt -> llm -> answer`

Recommended modules:

- `retriever.py`
- `rag_service.py` or `<domain>_service.py`

Do not include retrieval modules in non-retrieval projects.

## Use Portable Naming

Abstract concrete business features into reusable role names.

Prefer names like:

- `analysis_prompt.py`
- `analysis_builder.py`
- `plan_prompt.py`
- `plan_builder.py`
- `summary_organizer.py`

Do not copy old feature names into a new project unless they still match the new domain.

## Generate `target.md` Like This

When writing `target.md`, include at least:

1. project positioning
2. core capabilities
3. core workflow
4. layer design
5. directory structure
6. key module responsibilities
7. phase-based implementation plan
8. optional enhancement advice

Structure the document so that:

- the main body describes only the modules the project needs now
- optional modules appear at the end as enhancement advice
- the directory tree reflects current scope, not speculative future scope

## Generate `dayX.md` Like This

When the user wants a day-level or milestone-level plan, reuse the structure from `docs/dayX.md`.

Keep this section order:

1. total-goal section
2. end-of-day deliverables section
3. optional concept-introduction section
4. morning-learning section
5. afternoon-coding section
6. evening-review section
7. next-day handoff section

Within this structure:

- Use plain-language explanation for concept sections.
- Use concrete questions in learning sections.
- Tie coding sections to actual files the day should land.
- Use acceptance criteria and pitfalls to keep the plan executable.

## Use `dayX.md` Sections Correctly

### Concept section

Use only when the day needs conceptual onboarding.

Break it into layered explanation, for example:

- core concept
- deeper understanding
- practical meaning

### Morning section

Use it to define:

- what must be understood before coding
- what questions the developer must be able to answer
- how to explain the idea in plain language

### Afternoon section

Use it to define:

- which files should be created or edited
- what implementation step should happen first
- what concrete deliverable should exist by the end of the session

Only include skeleton code blocks or reference-answer blocks when the user explicitly wants tutorial-style material or training-oriented scaffolding.

### Evening section

Use it to define:

- review questions
- acceptance criteria
- common pitfalls

### Handoff section

Use it to connect the current day to the next milestone.

## Combine `target.md` And `dayX.md` Properly

When the user asks for both:

1. Define the product and architecture first.
2. Decide the smallest useful milestone sequence.
3. Map each milestone to a `dayX.md`-style document.
4. Keep each day focused on one real progression step.

Good progression examples:

- Day 1: project skeleton and entry path
- Day 2: core `utils` pipeline
- Day 3: first structured generation flow
- Day 4: API integration or workflow assembly
- Day 5: optional persistence or retrieval enhancement

Adjust the sequence to the real project. Do not force a fake day count.

## Put Optional Enhancements Last

Do not place these in the default scaffold unless the requirement clearly needs them.

### Persistence

Add only when the project needs durable state.

Typical additions:

- `conf/database.py`
- `crud/`
- `models/`

### Auth

Add only when the project has multi-user boundaries or protected APIs.

Typical additions:

- `routers/auth.py`
- `schemas/auth.py`
- `utils/auth.py`
- `utils/security.py`

### File ingestion

Add only when the project must read uploaded or local files.

Typical additions:

- `utils/file_loader.py`

### Retrieval and indexing

Add only when the project is knowledge-base or retrieval driven.

Typical additions:

- `utils/text_splitter.py`
- `utils/retriever.py`
- `utils/rag_service.py`
- `utils/index_service.py`
- `utils/embeddings.py`
- `utils/vector_store.py`

### Multi-domain structured outputs

Add multiple `<domain>_prompt.py + <domain>_builder.py` pairs only when the project truly has multiple independent structured capabilities.

## Output Style

When using this skill:

- write concise, explicit plans
- explain tradeoffs directly
- keep the architecture minimal by default
- keep optional modules clearly marked as optional
- preserve the idea that `utils` is a capability pipeline, not a dump folder
- use `dayX.md` as an execution template, not as filler
