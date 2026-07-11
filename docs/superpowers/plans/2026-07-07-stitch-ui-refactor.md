# Stitch UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Vue frontend so it matches the Stitch Mneme Intelligence screens while preserving the current API, preview mode, and build contracts.

**Architecture:** Keep `useMnemeWorkspace()` as the data and command source, and rebuild the visual shell and view layouts in `App.vue`. Use `index.css` for reusable Stitch-style utilities and Tailwind v4 theme tokens. Update existing source and preview tests before implementation so layout expectations are checked first.

**Tech Stack:** Vue 3 SFC, TypeScript, Tailwind CSS v4, Vite, Playwright, Node ESM contract tests, `@lucide/vue`.

---

## File Structure

- Modify `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`: update source-level expectations from the intermediate Sanctuary layout to the approved Stitch view labels, valid Vue attributes, and specialized layout hooks.
- Modify `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`: update preview assertions to the new sidebar brand and navigation labels.
- Modify `app/mneme_frontend_v0.2.1/src/App.vue`: refactor the authenticated shell, Research Vault, Knowledge Graph, AI Laboratory, and System Settings layouts.
- Modify `app/mneme_frontend_v0.2.1/src/index.css`: adjust reusable utility classes for the Stitch dark glass UI and add small helpers for graph/chat/file cards.
- Modify `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts` only if needed to fix user-facing mojibake or command defaults.

## Task 1: Update Source Contract For Stitch Layout

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`

- [ ] **Step 1: Write the failing source contract**

Replace the old nav-label and layout-hook assertions with these expectations:

```js
for (const navLabel of ['Knowledge Graph', 'Research Vault', 'Semantic Map', 'AI Laboratory', 'System Settings']) {
  assert.ok(appSource.includes(`label: "${navLabel}"`), `Expected Stitch navigation to include ${navLabel}`);
}

for (const invalidVueAttribute of ['testId="graph-output-workspace"', 'testId="memory-output-workspace"', 'testId="insights-output-workspace"']) {
  assert.ok(!appSource.includes(invalidVueAttribute), `Expected Vue template to avoid React-style ${invalidVueAttribute}`);
}

for (const layoutHook of [
  'data-testid="stitch-dashboard-grid"',
  'data-testid="stitch-research-vault-layout"',
  'data-testid="stitch-graph-layout"',
  'data-testid="stitch-ai-laboratory-layout"',
  'data-testid="stitch-settings-layout"',
  'data-testid="graph-output-workspace"',
  'data-testid="memory-output-workspace"',
  'data-testid="insights-output-workspace"',
]) {
  assert.ok(appSource.includes(layoutHook), `Expected App.vue to expose ${layoutHook}`);
}

for (const stitchText of ['Mneme Intelligence', 'Cognitive Sanctuary', 'New Research']) {
  assert.ok(appSource.includes(stitchText), `Expected Stitch shell copy: ${stitchText}`);
}
```

Keep the existing assertions for Vue dependencies, design tokens, `data-testid="obsidian-shell"`, `data-testid="sanctuary-sidebar"`, and preview-mode detection.

- [ ] **Step 2: Run the contract and verify it fails**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: FAIL because `App.vue` still contains old labels such as `Dashboard`, `Notes`, `AI Chat`, old hooks such as `stitch-notes-layout`, and React-style `testId` attributes.

- [ ] **Step 3: Do not change production code in this task**

The failure is the red test for the UI refactor.

## Task 2: Update Preview Contract For New Sidebar

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Write the failing Playwright expectations**

Update the second test so it expects the Stitch shell:

```ts
await expect(sidebar).toContainText('Mneme Intelligence');
await expect(sidebar).toContainText('Cognitive Sanctuary');
await expect(activeView).toContainText('Knowledge Graph');
await expect(sidebar.getByRole('button', { name: /Research Vault/ })).toBeVisible();
await expect(sidebar.getByRole('button', { name: /AI Laboratory/ })).toBeVisible();
await expect(sidebar.getByRole('button', { name: /System Settings/ })).toBeVisible();
```

Update the first test so it no longer expects the literal `Preview` brand line, and instead keeps:

```ts
await expect(sidebar.getByRole('button', { name: /Demo Research Vault/ })).toBeVisible();
await expect(sidebar.getByText('mneme.preview', { exact: true })).toBeVisible();
await expect(page.getByText('Backend endpoint')).not.toBeVisible();
```

- [ ] **Step 2: Run the Playwright test and verify it fails**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npm run dev:preview -- --host=127.0.0.1
```

In a second shell after the server is ready:

```powershell
cd app\mneme_frontend_v0.2.1
npx playwright test tests/preview-mode.spec.ts
```

Expected: FAIL because the current UI still exposes `Dashboard`, `Notes`, and `AI Chat` in the sidebar.

## Task 3: Rebuild App Shell And Research Vault

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/index.css`

- [ ] **Step 1: Implement the shell data constants**

In `App.vue`, replace `VIEW_ITEMS` labels with:

```ts
const VIEW_ITEMS: Array<{ id: WorkspaceView; label: string; icon: unknown; hint: string }> = [
  { id: "dashboard", label: "Knowledge Graph", icon: Network, hint: "Workspace overview and semantic health" },
  { id: "notes", label: "Research Vault", icon: FolderOpen, hint: "Documents and durable memory" },
  { id: "graph", label: "Semantic Map", icon: GitBranch, hint: "GraphRAG structure" },
  { id: "ai", label: "AI Laboratory", icon: FlaskConical, hint: "Ask and companion replies" },
  { id: "settings", label: "System Settings", icon: SlidersHorizontal, hint: "Health, profile, and analytics" },
];
```

Import the needed lucide icons from `@lucide/vue`, keeping only icons used by the final template.

- [ ] **Step 2: Replace the authenticated shell template**

Keep `data-testid="obsidian-shell"`, `data-testid="sanctuary-sidebar"`, `data-testid="sanctuary-topbar"`, and `data-testid="obsidian-editor-pane"`. The sidebar must contain:

```vue
<h1>Mneme Intelligence</h1>
<p>Cognitive Sanctuary</p>
```

The `New Research` button should set:

```ts
workspace.workspaceCommandTab.value = "create";
workspace.view.value = "dashboard";
```

- [ ] **Step 3: Replace the Research Vault view**

Rename the notes layout hook to:

```vue
data-testid="stitch-research-vault-layout"
```

Render a directory rail from `workspace.knowledgeBases.value` and document cards from `workspace.selectedDocuments.value`. Keep a valid output hook:

```vue
data-testid="memory-output-workspace"
```

Show an empty state with the text:

```text
No documents in this vault yet.
```

- [ ] **Step 4: Update CSS utilities**

In `index.css`, keep existing token values and add these reusable classes:

```css
.stitch-sidebar {
  background: rgba(28, 27, 29, 0.94);
  border-right: 1px solid rgba(74, 68, 85, 0.32);
}

.stitch-panel {
  background: rgba(19, 19, 21, 0.82);
  border: 1px solid rgba(74, 68, 85, 0.34);
}

.stitch-card {
  background: linear-gradient(145deg, rgba(42, 42, 44, 0.74), rgba(14, 14, 16, 0.92));
  border: 1px solid rgba(149, 141, 161, 0.18);
}
```

- [ ] **Step 5: Run the source contract**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: It may still fail for graph, AI, and settings hooks until later tasks, but it should no longer fail for nav labels, shell copy, or React-style `testId` attributes already fixed in this task.

## Task 4: Rebuild Graph And AI Views

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`

- [ ] **Step 1: Implement graph view**

Rename the graph root hook to:

```vue
data-testid="stitch-graph-layout"
```

Keep:

```vue
data-testid="graph-function-grid"
data-testid="graph-output-workspace"
```

Render three columns on wide screens: file rail, graph canvas, properties panel. Reuse `graphNodePositions` and `workspace.graphData.value?.edges`.

- [ ] **Step 2: Implement AI Laboratory view**

Rename the AI root hook to:

```vue
data-testid="stitch-ai-laboratory-layout"
```

Keep:

```vue
data-testid="chat-function-grid"
data-testid="workspace-chat-command"
```

Use the current `workspace.chatQuestion`, `workspace.chatResult`, `workspace.companionQuestion`, and `workspace.companionResult`. Do not add persistent sessions.

- [ ] **Step 3: Run the source contract**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: It may still fail for settings-specific assertions until Task 5.

## Task 5: Rebuild Settings And Dashboard Overview

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`

- [ ] **Step 1: Implement dashboard overview**

Keep:

```vue
data-testid="dashboard-overview"
data-testid="stitch-dashboard-grid"
data-testid="unified-command-module"
```

Show summary cards for documents, memory, graph, and readiness using existing computed values and refs.

- [ ] **Step 2: Implement settings**

Keep:

```vue
data-testid="stitch-settings-layout"
data-testid="insights-function-grid"
data-testid="insights-output-workspace"
```

Render cards for Cognitive Engine Selection, API Access & Security, Vault Synchronization, and Insights using existing health/readiness/analytics/advice/profile data. Avoid fake editable behavior; switches and token fields are visual indicators unless backed by current commands.

- [ ] **Step 3: Run the source contract**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: PASS.

## Task 6: Typecheck, Build, And Preview Verification

**Files:**
- Modify only files required by compiler or test failures.

- [ ] **Step 1: Run typecheck**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npm run lint
```

Expected: PASS with `vue-tsc --noEmit`.

- [ ] **Step 2: Run production build**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npm run build
```

Expected: PASS and production files generated under `dist`.

- [ ] **Step 3: Run preview E2E**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npx playwright test tests/preview-mode.spec.ts
```

Expected: PASS.

- [ ] **Step 4: Commit implementation**

Run:

```powershell
git add app\mneme_frontend_v0.2.1 docs\superpowers\plans\2026-07-07-stitch-ui-refactor.md
git commit -m "feat: refactor frontend to stitch ui"
```

Expected: commit succeeds after verification passes.

## Self-Review

- Spec coverage: The plan covers shell, view mapping, data flow preservation, styling constraints, and verification.
- Red-flag scan: No unresolved planning markers are present.
- Type consistency: The plan uses existing `WorkspaceView`, `WorkspaceCommandTab`, `useMnemeWorkspace`, and current test file paths.
