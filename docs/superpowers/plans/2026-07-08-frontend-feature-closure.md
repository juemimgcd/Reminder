# Frontend Feature Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make visible Mneme frontend controls either call real APIs, perform clear local behavior, or display planned-state feedback while preserving the dark Stitch-style UI.

**Architecture:** Keep `useMnemeWorkspace()` as the application state and command boundary. Add one small backend support domain for planned Documentation/Support responses, then wire existing backend APIs into the current Vue shell without introducing a router or new state library.

**Tech Stack:** FastAPI, Pydantic response wrapper, Vue 3 Composition API, TypeScript, Vite, Tailwind v4, Playwright preview E2E, pytest.

---

## File Structure

- Create `app/mneme/domains/support/router.py`: planned Documentation and Support endpoints.
- Modify `app/mneme/bootstrap/router_registry.py`: register the support router.
- Modify `tests/test_final_backend_convergence.py`: assert planned support routes are public.
- Modify `app/mneme_frontend_v0.2.1/src/types.ts`: add planned support response type and small form/status types if needed.
- Modify `app/mneme_frontend_v0.2.1/src/lib/api.ts`: add support endpoints and any missing client method needed by UI.
- Modify `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`: mirror support endpoints and preview behavior for upload/document/model/session actions.
- Modify `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`: add command methods for planned feedback, upload, document actions, GraphRAG, session delete, and model actions.
- Modify `app/mneme_frontend_v0.2.1/src/App.vue`: wire existing controls to workspace methods and local UI state.
- Modify `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`: add E2E coverage for planned feedback and wired controls.
- Modify `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`: keep route/control contracts honest where source-level assertions are useful.

## Task 1: Planned Support Endpoints

**Files:**
- Create: `app/mneme/domains/support/router.py`
- Modify: `app/mneme/bootstrap/router_registry.py`
- Modify: `tests/test_final_backend_convergence.py`

- [ ] **Step 1: Write the failing backend route contract**

In `tests/test_final_backend_convergence.py`, extend `expected_paths` inside `test_public_routes_are_preserved`:

```python
expected_paths = {
    "/health",
    "/health/neo4j",
    "/health/readiness",
    "/auth/register",
    "/auth/login",
    "/auth/me",
    "/users/{user_id}/knowledge-bases",
    "/analysis/knowledge-bases/{knowledge_base_id}/growth",
    "/analysis/knowledge-bases/{knowledge_base_id}/analytics",
    "/tasks/{task_id}",
    "/tasks/{task_id}/cancel",
    "/tasks/{task_id}/retry",
    "/support/documentation",
    "/support/contact",
}
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_final_backend_convergence.py::FinalBackendConvergenceTest::test_public_routes_are_preserved -q
```

Expected: FAIL because `/support/documentation` and `/support/contact` are not registered.

- [ ] **Step 3: Implement the support router**

Create `app/mneme/domains/support/router.py`:

```python
from fastapi import APIRouter

from app.mneme.utils.response import success_response


router = APIRouter(prefix="/support", tags=["support"])


@router.get("/documentation")
def get_documentation_status():
    return success_response(
        {
            "status": "planned",
            "message": "Documentation workspace is reserved for a future release.",
        }
    )


@router.get("/contact")
def get_support_status():
    return success_response(
        {
            "status": "planned",
            "message": "Support contact workflow is reserved for a future release.",
        }
    )
```

Modify `app/mneme/bootstrap/router_registry.py` by adding:

```python
"app.mneme.domains.support.router",
```

to `ROUTER_MODULE_NAMES`.

- [ ] **Step 4: Verify the backend route contract passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_final_backend_convergence.py::FinalBackendConvergenceTest::test_public_routes_are_preserved -q
```

Expected: PASS.

## Task 2: API And Preview Client Coverage

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`

- [ ] **Step 1: Write source contract assertions**

Add assertions to `tests/obsidian-source-contract.test.mjs`:

```js
for (const apiMethod of [
  'documentationStatus',
  'supportStatus',
  'uploadDocument',
  'indexDocument',
  'deleteDocument',
  'testAiModelConfig',
  'setDefaultAiModelConfig',
  'updateAiModelConfig',
  'deleteChatSession',
  'graphRag',
]) {
  assert.ok(appSource.includes(apiMethod) || readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8').includes(apiMethod), `Expected client API/workspace method ${apiMethod}`);
}
```

- [ ] **Step 2: Run the source contract and verify it fails**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: FAIL for `documentationStatus` and `supportStatus`, and possibly workspace method names that do not exist yet.

- [ ] **Step 3: Add types and client methods**

In `src/types.ts`, add:

```ts
export interface PlannedSupportData {
  status: "planned";
  message: string;
}
```

In `src/lib/api.ts`, import `PlannedSupportData` and add to `realApi`:

```ts
documentationStatus() {
  return request<PlannedSupportData>("/support/documentation");
},
supportStatus() {
  return request<PlannedSupportData>("/support/contact");
},
```

In `src/lib/previewApi.ts`, import `PlannedSupportData` and add:

```ts
documentationStatus(): Promise<PlannedSupportData> {
  return delay({ status: "planned", message: "Documentation workspace is reserved for a future release." });
},
supportStatus(): Promise<PlannedSupportData> {
  return delay({ status: "planned", message: "Support contact workflow is reserved for a future release." });
},
```

- [ ] **Step 4: Verify source contract passes**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: PASS.

## Task 3: Workspace Commands For Real Actions

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`

- [ ] **Step 1: Add failing source contract for workspace command methods**

Extend `tests/obsidian-source-contract.test.mjs` with:

```js
const workspaceSource = readFileSync(new URL('../src/composables/useMnemeWorkspace.ts', import.meta.url), 'utf8');
for (const workspaceMethod of [
  'showDocumentationStatus',
  'showSupportStatus',
  'uploadFile',
  'indexDocument',
  'deleteDocument',
  'runGraphRag',
  'deleteActiveChatSession',
  'testAiModelConfig',
  'setDefaultAiModelConfig',
  'updateActiveModelContextWindow',
]) {
  assert.ok(workspaceSource.includes(workspaceMethod), `Expected workspace method ${workspaceMethod}`);
}
```

- [ ] **Step 2: Run the contract and verify it fails**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: FAIL for the missing workspace methods.

- [ ] **Step 3: Implement workspace state and methods**

In `useMnemeWorkspace.ts`, add refs:

```ts
const uploadInputKey = ref(0);
const documentActionStatus = ref("");
const graphRagQuestion = ref("");
const graphRagStatus = ref("");
const aiModelActionStatus = ref("");
const chatSessionFilter = ref("");
```

Add a computed:

```ts
const filteredChatSessions = computed(() => {
  const query = chatSessionFilter.value.trim().toLowerCase();
  if (!query) {
    return chatSessions.value;
  }
  return chatSessions.value.filter((session) => (session.title || "Untitled Chat").toLowerCase().includes(query));
});
```

Add methods:

```ts
async function showDocumentationStatus() {
  const result = await api.documentationStatus();
  banner.value = result.message;
}

async function showSupportStatus() {
  const result = await api.supportStatus();
  banner.value = result.message;
}

async function uploadFile(file: File | null | undefined) {
  if (!file || !token.value || !activeKnowledgeBaseId.value) {
    return;
  }
  const result = await api.uploadDocument(token.value, {
    file,
    userId: user.value?.id ?? null,
    knowledgeBaseId: activeKnowledgeBaseId.value,
  });
  banner.value = `Uploaded ${result.file_name}`;
  uploadInputKey.value += 1;
  await loadKnowledgeBasePanels();
}

async function indexDocument(documentId: string) {
  if (!token.value) {
    return;
  }
  const result = await api.indexDocument(documentId, token.value);
  documentActionStatus.value = result.message;
  await loadKnowledgeBasePanels();
}

async function deleteDocument(documentId: string) {
  if (!token.value) {
    return;
  }
  const result = await api.deleteDocument(documentId, token.value);
  documentActionStatus.value = `Deleted ${result.document_id}`;
  await loadKnowledgeBasePanels();
}

async function runGraphRag() {
  if (!token.value || !activeKnowledgeBaseId.value || !graphRagQuestion.value.trim()) {
    return;
  }
  const result = await api.graphRag(token.value, activeKnowledgeBaseId.value, {
    query: graphRagQuestion.value.trim(),
    top_k: 6,
    max_expansions: 8,
  });
  graphRagStatus.value = result.summary;
}

async function deleteActiveChatSession() {
  if (!token.value || !activeChatSessionId.value) {
    return;
  }
  await api.deleteChatSession(token.value, activeChatSessionId.value);
  banner.value = "Chat session deleted";
  await loadChatSessions();
}

async function testAiModelConfig(configId: string) {
  if (!token.value) {
    return;
  }
  const result = await api.testAiModelConfig(token.value, configId);
  aiModelActionStatus.value = result.message;
}

async function setDefaultAiModelConfig(configId: string) {
  if (!token.value) {
    return;
  }
  const updated = await api.setDefaultAiModelConfig(token.value, configId);
  aiModelConfigs.value = aiModelConfigs.value.map((config) => ({ ...config, is_default: config.id === updated.id }));
  activeAiModelConfigId.value = updated.id;
  aiModelActionStatus.value = `${updated.label} is now default`;
}

async function updateActiveModelContextWindow(value: number) {
  if (!token.value || !activeAiModelConfigId.value) {
    return;
  }
  const updated = await api.updateAiModelConfig(token.value, activeAiModelConfigId.value, {
    context_window: value,
  });
  aiModelConfigs.value = aiModelConfigs.value.map((config) => (config.id === updated.id ? updated : config));
  aiModelActionStatus.value = `Context window updated to ${updated.context_window.toLocaleString()}`;
}
```

Return all new refs/computed/methods from the composable.

- [ ] **Step 4: Verify source contract passes**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: PASS.

## Task 4: Wire Research Vault And Shell Controls

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Write failing E2E tests**

Add preview tests:

```ts
test('documentation and support show planned backend feedback', async ({ page }) => {
  await openPreview(page);

  await page.getByRole('button', { name: 'Documentation' }).click();
  await expect(page.getByText('Documentation workspace is reserved for a future release.')).toBeVisible();

  await page.getByRole('button', { name: 'Support' }).click();
  await expect(page.getByText('Support contact workflow is reserved for a future release.')).toBeVisible();
});

test('research vault upload and document actions are wired', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'Research Vault', exact: true }).click();

  await page.getByTestId('workspace-upload-input').setInputFiles({
    name: 'closure-notes.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from('# Closure notes'),
  });
  await expect(page.getByTestId('stitch-research-vault-layout')).toContainText('closure-notes.md');

  const card = page.getByTestId('document-card').filter({ hasText: 'closure-notes.md' });
  await card.getByRole('button', { name: 'Index' }).click();
  await expect(card).toContainText('indexed');

  await card.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByTestId('stitch-research-vault-layout')).not.toContainText('closure-notes.md');
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "documentation and support|research vault upload" --project "Desktop Chrome"
```

Expected: FAIL because controls are not wired.

- [ ] **Step 3: Wire shell buttons and Research Vault controls**

In `App.vue`, replace `Documentation` and `Support` anchors with buttons:

```vue
<button class="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-on-surface-variant hover:text-primary" @click="workspace.showDocumentationStatus">
  <BookOpen class="size-4" />
  Documentation
</button>
<button class="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-on-surface-variant hover:text-primary" @click="workspace.showSupportStatus">
  <LifeBuoy class="size-4" />
  Support
</button>
```

Show `workspace.banner.value` in the editor shell where it is visible across views:

```vue
<p v-if="workspace.banner.value" class="mx-5 mt-4 rounded-md border border-outline-variant/30 bg-surface-container-low px-4 py-3 text-sm text-on-surface-variant lg:mx-8">
  {{ workspace.banner.value }}
</p>
```

Add upload input to the upload command panel:

```vue
<input
  :key="workspace.uploadInputKey.value"
  data-testid="workspace-upload-input"
  class="premium-input w-full rounded-md p-3 text-sm"
  type="file"
  @change="workspace.uploadFile(($event.target as HTMLInputElement).files?.[0])"
/>
```

Add `data-testid="document-card"` and actions to document cards:

```vue
<article v-for="doc in workspace.selectedDocuments.value" :key="doc.id" data-testid="document-card" class="stitch-card rounded-lg p-4">
  ...
  <div class="mt-4 grid grid-cols-2 gap-2">
    <button class="premium-action-btn rounded-md px-3 py-2 text-xs" @click="workspace.indexDocument(doc.id)">Index</button>
    <button class="premium-action-btn rounded-md px-3 py-2 text-xs text-rose-200" @click="workspace.deleteDocument(doc.id)">Delete</button>
  </div>
</article>
```

- [ ] **Step 4: Verify E2E passes**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "documentation and support|research vault upload" --project "Desktop Chrome"
```

Expected: PASS.

## Task 5: Wire Graph And AI Controls

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Write failing E2E tests**

Add:

```ts
test('graph search and toolbar produce visible behavior', async ({ page }) => {
  await openPreview(page);

  await page.getByPlaceholder('Search knowledge base...').fill('memory graph');
  await page.getByRole('button', { name: 'Run GraphRAG' }).click();
  await expect(page.getByTestId('graph-output-workspace')).toContainText('Preview GraphRAG found');

  const graph = page.locator('svg[aria-label="Knowledge graph"]');
  const before = await graph.getAttribute('viewBox');
  await page.getByRole('button', { name: 'Zoom in graph' }).click();
  await expect(graph).not.toHaveAttribute('viewBox', before ?? '');
  await page.getByRole('button', { name: 'Center graph' }).click();
  await expect(graph).toHaveAttribute('viewBox', '0 0 760 680');
});

test('ai laboratory filters and deletes chat sessions', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();

  await page.getByPlaceholder('Search history...').fill('Preview Vault');
  await expect(page.getByTestId('ai-history-rail')).toContainText('Preview Vault Review');
  await page.getByRole('button', { name: 'Delete active chat' }).click();
  await expect(page.getByTestId('ai-history-rail')).not.toContainText('Preview Vault Review');
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "graph search|ai laboratory filters" --project "Desktop Chrome"
```

Expected: FAIL.

- [ ] **Step 3: Implement graph state and bindings**

In `App.vue`, add refs in script:

```ts
const graphViewBox = ref("0 0 760 680");
const graphZoom = ref(1);
```

Add functions:

```ts
function setGraphZoom(nextZoom: number) {
  graphZoom.value = Math.min(1.6, Math.max(0.7, nextZoom));
  const width = 760 / graphZoom.value;
  const height = 680 / graphZoom.value;
  graphViewBox.value = `${(760 - width) / 2} ${(680 - height) / 2} ${width} ${height}`;
}

function centerGraph() {
  graphZoom.value = 1;
  graphViewBox.value = "0 0 760 680";
  graphSimulation?.alpha(0.6).restart();
}
```

Bind SVG:

```vue
:viewBox="graphViewBox"
```

Replace search placeholder div with a form:

```vue
<form class="glass-panel flex h-12 w-[328px] items-center gap-3 rounded-lg px-5 text-text-muted" @submit.prevent="workspace.runGraphRag">
  <Search class="size-5" />
  <input v-model="workspace.graphRagQuestion.value" class="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none" placeholder="Search knowledge base..." />
  <button class="sr-only">Run GraphRAG</button>
</form>
```

Add visible result:

```vue
<p v-if="workspace.graphRagStatus.value" class="glass-panel absolute left-5 top-40 z-10 max-w-md rounded-md px-4 py-3 text-sm text-on-surface-variant">
  {{ workspace.graphRagStatus.value }}
</p>
```

Give toolbar buttons accessible names and behavior:

```vue
<button aria-label="Zoom in graph" class="premium-action-btn grid size-12 place-items-center rounded-md" @click="setGraphZoom(graphZoom + 0.15)"><ZoomIn class="size-5" /></button>
<button aria-label="Zoom out graph" class="premium-action-btn grid size-12 place-items-center rounded-md" @click="setGraphZoom(graphZoom - 0.15)"><ZoomOut class="size-5" /></button>
<button aria-label="Center graph" class="premium-action-btn grid size-12 place-items-center rounded-md" @click="centerGraph"><Target class="size-5" /></button>
<button aria-label="Restart graph layout" class="premium-action-btn grid size-12 place-items-center rounded-md" @click="graphSimulation?.alpha(0.8).restart()"><Play class="size-5" /></button>
```

- [ ] **Step 4: Implement AI filter/delete bindings**

Replace search history display with:

```vue
<label class="premium-input mb-5 flex h-10 items-center gap-3 rounded px-3 text-text-muted">
  <Search class="size-4" />
  <input v-model="workspace.chatSessionFilter.value" class="min-w-0 flex-1 bg-transparent text-sm text-on-surface outline-none" placeholder="Search history..." />
</label>
```

Change session loop to `workspace.filteredChatSessions.value`.

Add a delete button near AI header actions:

```vue
<button class="premium-action-btn rounded-md px-3 py-2 text-sm text-rose-200" @click="workspace.deleteActiveChatSession">
  Delete active chat
</button>
```

- [ ] **Step 5: Verify E2E passes**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "graph search|ai laboratory filters" --project "Desktop Chrome"
```

Expected: PASS.

## Task 6: Wire Settings Model Actions

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

- [ ] **Step 1: Write failing E2E test**

Add:

```ts
test('settings model controls call preview API actions', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'System Settings', exact: true }).click();

  const settings = page.getByTestId('stitch-settings-layout');
  await settings.getByRole('button', { name: /Test Preview DeepSeek/ }).click();
  await expect(settings).toContainText('Preview model config is ready.');

  await settings.getByRole('slider').fill('32');
  await settings.getByRole('button', { name: 'Save context window' }).click();
  await expect(settings).toContainText('Context window updated to 32,000');
});
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "settings model controls" --project "Desktop Chrome"
```

Expected: FAIL.

- [ ] **Step 3: Wire settings UI**

In each model card add:

```vue
<div class="mt-4 flex gap-2">
  <button class="premium-action-btn rounded-md px-3 py-2 text-xs" :aria-label="`Test ${config.label}`" @click="workspace.testAiModelConfig(config.id)">Test</button>
  <button v-if="!config.is_default" class="premium-action-btn rounded-md px-3 py-2 text-xs" :aria-label="`Set ${config.label} default`" @click="workspace.setDefaultAiModelConfig(config.id)">Set Default</button>
</div>
```

Add status:

```vue
<p v-if="workspace.aiModelActionStatus.value" class="mt-4 rounded-md border border-outline-variant/30 bg-surface-container-low px-4 py-3 text-sm text-on-surface-variant">
  {{ workspace.aiModelActionStatus.value }}
</p>
```

Add a local context input model in script:

```ts
const settingsContextWindow = computed({
  get: () => activeAiModelConfig.value ? Math.round(activeAiModelConfig.value.context_window / 1000) : 64,
  set: (value: number) => {
    if (activeAiModelConfig.value) {
      activeAiModelConfig.value.context_window = Number(value) * 1000;
    }
  },
});
```

Bind range and button:

```vue
<input v-model.number="settingsContextWindow" class="premium-range w-full" type="range" min="8" max="128" />
<button class="premium-action-btn mt-3 rounded-md px-3 py-2 text-xs" @click="workspace.updateActiveModelContextWindow(settingsContextWindow * 1000)">
  Save context window
</button>
```

- [ ] **Step 4: Verify E2E passes**

Run:

```powershell
npx playwright test tests/preview-mode.spec.ts -g "settings model controls" --project "Desktop Chrome"
```

Expected: PASS.

## Task 7: Full Verification

**Files:**
- Modify only files required by failures.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: `62 passed` or higher if new tests were added.

- [ ] **Step 2: Run frontend source contract**

Run:

```powershell
node app\mneme_frontend_v0.2.1\tests\obsidian-source-contract.test.mjs
```

Expected: PASS.

- [ ] **Step 3: Run frontend typecheck**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npm run lint
```

Expected: PASS.

- [ ] **Step 4: Run preview E2E**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npx playwright test tests/preview-mode.spec.ts
```

Expected: all preview tests pass.

- [ ] **Step 5: Run production build**

Run:

```powershell
cd app\mneme_frontend_v0.2.1
npm run build
```

Expected: PASS. The existing empty `vendor` chunk warning may remain.

## Self-Review

- Spec coverage: planned support endpoints, upload, document actions, graph controls/Search, AI session controls, settings model actions, and verification are covered.
- Placeholder scan: no TBD/TODO/fill-in instructions remain; every task has concrete files, snippets, and commands.
- Type consistency: method names match the intended workspace/API methods and preview tests.
