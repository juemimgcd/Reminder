# Frontend Feature Closure Design

## Goal

Complete the Mneme frontend feature surface so visible controls either call real backend APIs, perform clear local UI behavior, or show an explicit planned-state response. Preserve the current Stitch-style dark frontend layout and avoid removing useful front-end affordances just because a full backend workflow is not ready yet.

## Current Evidence

Recent verification showed that the frontend API client routes match backend FastAPI routes: all real `api.ts` calls have corresponding backend endpoints, and the backend test suite passes. The remaining gap is visible UI controls that look actionable but are not wired to behavior.

## Design Principles

- Keep the current visual layout and navigation.
- Prefer wiring existing backend APIs over adding new backend domains.
- Use lightweight planned endpoints for `Documentation` and `Support` so those entries remain visible but no longer point to `#`.
- For UI-only controls, implement local behavior when it is useful and bounded.
- Avoid adding a full document center, support ticketing system, or advanced model-management console in this pass.

## Backend Additions

Add a small support/documentation domain with response-wrapped planned endpoints:

- `GET /support/documentation`
- `GET /support/contact`

Each returns a stable payload with `status: "planned"` and a reader-facing message. These endpoints are placeholders by design and should be covered by lightweight contract tests.

No other backend capability is expected to be added unless implementation reveals a missing endpoint for an already visible control.

## Frontend Behavior

### Shell

Keep `Documentation` and `Support` in the sidebar. Clicking either calls the new planned endpoint and displays the message in the existing workspace feedback/banner area.

### Research Vault

Keep the current vault and document layout. Wire `Upload File` to the existing document upload API with a hidden or compact file input. After upload, refresh the active vault documents and show status feedback.

Add document-card actions for existing backend capabilities:

- `Index` calls the document indexing endpoint.
- `Delete` calls the document delete endpoint and refreshes the document list.

Keep filter and grid controls. Implement simple local behavior:

- Filter toggles showing indexed/all documents.
- Grid control toggles compact/comfortable card density.

### Knowledge Graph

Keep the graph toolbar. Implement bounded local behavior for visual controls:

- Zoom in/out adjusts the SVG viewBox scale.
- Center resets viewBox and simulation alpha.
- Play restarts the graph simulation.

Keep the graph search box and wire it to `graphRag` for the active vault. Display GraphRAG decision/status near the graph canvas or command area without changing the graph data model.

### AI Laboratory

Keep the session rail and top-right search/more controls.

- Search filters chat sessions locally.
- More opens a compact menu with existing session management actions.
- Delete session uses the existing delete chat session API and refreshes the list.

### Settings

Keep the model cards and configuration layout. Wire existing model APIs:

- `Test` calls model test.
- `Set Default` calls default model endpoint.
- Context window updates the active model via existing update endpoint, with a conservative save action or debounced change only if clear in the UI.

Do not build a full provider onboarding flow in this pass. If the add-provider affordance remains visible, it should show planned feedback or open a minimal form only if the existing `createAiModelConfig` contract can be satisfied simply.

## State And Errors

Use existing workspace state where possible. Add small status refs only where necessary for:

- upload status,
- document action status,
- planned endpoint feedback,
- model test/update feedback,
- GraphRAG feedback.

Errors should surface in the existing banner/status area or near the relevant panel. Avoid silent failures.

## Verification

Implementation is ready when these pass:

- Backend tests, including new planned support endpoint tests.
- Frontend typecheck: `npm run lint`.
- Frontend production build: `npm run build`.
- Preview E2E, expanded to cover:
  - Documentation/Support planned feedback,
  - upload control presence and preview mock behavior,
  - document index/delete actions,
  - chat session filtering/deletion,
  - model test/default/update feedback,
  - graph search and toolbar behavior.

## Out Of Scope

- Full documentation CMS.
- Support ticketing or live help.
- Complex model provider onboarding.
- Replacing the graph renderer or adding persistent graph viewport storage.
- Large backend schema changes unless a missing endpoint is discovered during implementation.
