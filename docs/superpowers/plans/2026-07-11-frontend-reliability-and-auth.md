# Frontend Reliability and Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Mneme authenticate and render quickly, add registration, isolate failed feature requests, implement every visible graph interaction, and repair settings/sidebar layouts across desktop, tablet, and mobile.

**Architecture:** Keep the existing Vue 3 shell and FastAPI contracts. Split `useMnemeWorkspace` into shared session state plus view-scoped loaders, use explicit load states and stale-request guards, and make graph/layout behavior deterministic and testable. Production uses the internal Neo4j Compose address and is rebuilt only after local tests and browser checks pass.

**Tech Stack:** Vue 3.5, TypeScript 5.8, Vite 6, Playwright 1.60, FastAPI, Docker Compose, Neo4j, Nginx

## Global Constraints

- Base all work on `origin/master` commit `893c974` or later.
- Reuse the existing shell, UI primitives, design tokens, API response envelope, and preview mode.
- Do not expose PostgreSQL, Redis, Neo4j, or application port 8000 publicly.
- Production must use `NEO4J_URI=bolt://neo4j:7687`.
- Login must not wait for graph, memory, profile, analysis, advice, chat, or model endpoints.
- Every data view must expose loading, empty, ready, and error states.
- Every visible control must perform its advertised action or be removed.
- Verify 1440px, 1024px, 768px, and 390px layouts.
- Preserve existing named Docker volumes and user data.

---

### Task 1: Add observable frontend load-state and storage primitives

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/composables/loadState.ts`
- Create: `app/mneme_frontend_v0.2.1/src/lib/safeStorage.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/reliability-contract.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/types.ts`

**Interfaces:**
- Produces: `LoadPhase`, `LoadState`, `createLoadState()`, `safeStorageGet()`, `safeStorageSet()`, and `safeStorageRemove()` for later authentication and view loaders.
- Consumes: browser `localStorage` when available; no backend dependency.

- [ ] **Step 1: Write failing contract tests for storage and load-state modules**

Create `tests/reliability-contract.spec.ts` with source-level contracts that run before browser behavior exists:

```ts
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const source = (path: string) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');

test('workspace reliability primitives exist', () => {
  expect(source('composables/loadState.ts')).toContain('export type LoadPhase');
  expect(source('composables/loadState.ts')).toContain('createLoadState');
  expect(source('lib/safeStorage.ts')).toContain('safeStorageSet');
  expect(source('lib/safeStorage.ts')).toContain('catch');
});
```

- [ ] **Step 2: Run the contract test and verify RED**

```powershell
cd app/mneme_frontend_v0.2.1
npx playwright test tests/reliability-contract.spec.ts --project="Desktop Chrome"
```

Expected: FAIL because `loadState.ts` and `safeStorage.ts` do not exist.

- [ ] **Step 3: Implement load-state and safe-storage primitives**

Use these interfaces:

```ts
// composables/loadState.ts
import { ref } from 'vue';

export type LoadPhase = 'idle' | 'loading' | 'ready' | 'empty' | 'error';
export type LoadState = ReturnType<typeof createLoadState>;

export function createLoadState() {
  return {
    phase: ref<LoadPhase>('idle'),
    message: ref(''),
  };
}
```

```ts
// lib/safeStorage.ts
export function safeStorageGet(key: string): string {
  try { return window.localStorage.getItem(key) ?? ''; } catch { return ''; }
}

export function safeStorageSet(key: string, value: string): boolean {
  try { window.localStorage.setItem(key, value); return true; } catch { return false; }
}

export function safeStorageRemove(key: string): void {
  try { window.localStorage.removeItem(key); } catch { /* session remains in memory */ }
}
```

Add to `types.ts`:

```ts
export type AuthMode = 'login' | 'register';
```

- [ ] **Step 4: Run the contract test and typecheck**

```powershell
npx playwright test tests/reliability-contract.spec.ts --project="Desktop Chrome"
npm run lint
```

Expected: both commands exit 0.

- [ ] **Step 5: Commit the reliability primitives**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/loadState.ts app/mneme_frontend_v0.2.1/src/lib/safeStorage.ts app/mneme_frontend_v0.2.1/src/types.ts app/mneme_frontend_v0.2.1/tests/reliability-contract.spec.ts
git commit -m "refactor(frontend): add reliable load and storage state"
```

### Task 2: Implement registration and storage-tolerant authentication

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/api.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/lib/previewApi.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/auth-flow.spec.ts`

**Interfaces:**
- Consumes: `safeStorage*`, `/auth/register`, `/auth/login`, `/auth/me`.
- Produces: `authMode`, `registerForm`, `authPending`, `authNotice`, `login()`, `register()`, and `setAuthMode()` on `MnemeWorkspace`.

- [ ] **Step 1: Write failing browser tests for login and registration**

Create `tests/auth-flow.spec.ts` that intercepts the real API contract:

```ts
import { expect, test } from '@playwright/test';

test('registration creates an account and automatically enters the shell', async ({ page }) => {
  await page.route('**/auth/register', route => route.fulfill({ json: { code: 0, message: 'register success', data: { id: 9, username: 'new-user', display_name: 'New User', avatar_url: '/avatar.png' } } }));
  await page.route('**/auth/login', route => route.fulfill({ json: { code: 0, message: 'login success', data: { access_token: 'token-9', token_type: 'bearer' } } }));
  await page.route('**/auth/me', route => route.fulfill({ json: { code: 0, message: 'ok', data: { id: 9, username: 'new-user', display_name: 'New User', avatar_url: '/avatar.png' } } }));
  await page.route('**/health*', route => route.fulfill({ json: { code: 0, message: 'ok', data: { status: 'running', overall_status: 'ready' } } }));
  await page.route('**/users/9/knowledge-bases', route => route.fulfill({ json: { code: 0, message: 'ok', data: { items: [], total: 0 } } }));
  await page.goto('/');
  await page.getByRole('button', { name: '注册' }).click();
  await page.getByLabel('用户名').fill('new-user');
  await page.getByLabel('显示名称').fill('New User');
  await page.getByLabel('密码', { exact: true }).fill('password123');
  await page.getByLabel('确认密码').fill('password123');
  await page.getByRole('button', { name: '创建账户' }).click();
  await expect(page.getByTestId('obsidian-shell')).toBeVisible();
});

test('blocked localStorage does not block login', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked'); } }));
  // Reuse login/me routes and assert the shell becomes visible.
});
```

Also test mismatched passwords, duplicate username 400, disabled pending button, and invalid credentials 401.

- [ ] **Step 2: Run auth tests and verify RED**

```powershell
npx playwright test tests/auth-flow.spec.ts --project="Desktop Chrome"
```

Expected: FAIL because the register mode and storage-tolerant flow are absent.

- [ ] **Step 3: Implement authentication state and actions**

In `useMnemeWorkspace.ts`, replace direct storage calls and expose:

```ts
const authMode = ref<AuthMode>('login');
const authPending = ref(false);
const authNotice = ref('');
const registerForm = ref({ username: '', displayName: '', password: '', confirmPassword: '' });

async function establishSession(accessToken: string) {
  token.value = accessToken;
  if (!safeStorageSet(TOKEN_KEY, accessToken)) authNotice.value = t('auth.sessionOnly');
  await authenticateWithToken();
}

async function register() {
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    authError.value = t('auth.passwordMismatch');
    return;
  }
  authPending.value = true;
  try {
    await api.register({ username: registerForm.value.username, display_name: registerForm.value.displayName || null, password: registerForm.value.password });
    const auth = await api.login({ username: registerForm.value.username, password: registerForm.value.password });
    await establishSession(auth.access_token);
  } catch (error) { authError.value = errorMessage(error, t('auth.registerFailed')); }
  finally { authPending.value = false; }
}
```

Make `login()` call `establishSession()` before storage can interrupt control flow. Normalize FastAPI validation `detail` arrays in `api.ts` to a readable message.

- [ ] **Step 4: Build the login/register card**

Use one card with a two-button segmented mode switch. Keep current tokens and add labels, autocomplete values, required/minlength attributes, pending text, disabled buttons, `aria-live` errors, and a session-only notice. Do not create a separate page or router.

- [ ] **Step 5: Run auth tests, preview tests, and typecheck**

```powershell
npx playwright test tests/auth-flow.spec.ts tests/preview-mode.spec.ts --project="Desktop Chrome"
npm run lint
```

Expected: all pass.

- [ ] **Step 6: Commit authentication**

```powershell
git add app/mneme_frontend_v0.2.1/src/App.vue app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts app/mneme_frontend_v0.2.1/src/i18n/messages.ts app/mneme_frontend_v0.2.1/src/lib/api.ts app/mneme_frontend_v0.2.1/src/lib/previewApi.ts app/mneme_frontend_v0.2.1/tests/auth-flow.spec.ts
git commit -m "feat(frontend): add reliable login and registration"
```

### Task 3: Replace eager startup with view-scoped loaders and error isolation

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/composables/useWorkspaceLoaders.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/ui/UiStatusPanel.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/lazy-loading.spec.ts`

**Interfaces:**
- Consumes: shared user/token/knowledge-base refs and existing `api` methods.
- Produces: `ensureViewLoaded(view, force?)`, `viewLoadStates`, `dismissBanner()`, and request-generation protection.

- [ ] **Step 1: Write failing lazy-loading and isolation tests**

Intercept every heavy endpoint, record calls, complete only session/bootstrap routes, and assert the shell appears without graph/profile/advice calls. Navigate to Graph and assert only graph/document calls begin. Fail advice with 500 while returning graph and documents; assert graph remains visible and the raw text `Internal Server Error` does not appear.

```ts
expect(heavyCalls).toEqual([]);
await page.getByRole('button', { name: 'Knowledge Graph' }).click();
expect(heavyCalls).toEqual(expect.arrayContaining(['/graph/', '/kb/documents']));
await expect(page.getByTestId('graph-output-workspace')).toBeVisible();
await expect(page.getByText('Internal Server Error')).toBeHidden();
```

- [ ] **Step 2: Run lazy-loading tests and verify RED**

```powershell
npx playwright test tests/lazy-loading.spec.ts --project="Desktop Chrome"
```

Expected: FAIL because startup still fans out across all feature endpoints.

- [ ] **Step 3: Implement the loader boundary**

`useWorkspaceLoaders.ts` accepts refs and callbacks, maintains one load state per `WorkspaceView`, and increments a generation counter whenever the knowledge base changes:

```ts
const generation = ref(0);
const viewLoadStates = {
  dashboard: createLoadState(), notes: createLoadState(), graph: createLoadState(), ai: createLoadState(), settings: createLoadState(),
};

async function settle<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try { return await promise; } catch { return fallback; }
}
```

Do not use one `Promise.all` for unrelated features. Apply results only when the captured generation still matches.

- [ ] **Step 4: Route navigation through `ensureViewLoaded`**

Authentication loads `/auth/me`, health, readiness, and knowledge bases, marks authenticated, and returns. A watcher or `navigate()` loads the active view. Knowledge-base selection increments the generation, clears view cache, and loads only the current view. Refresh passes `force: true`.

- [ ] **Step 5: Repair global notification behavior**

Make `UiStatusPanel` accept `variant`, `title`, `detail`, and `dismissible`; use normal flow with no overlapping text. Map generic 500s to `该功能暂时不可用，请稍后重试` and keep diagnostic detail in the affected view. Reserve the shell banner for user-triggered actions.

- [ ] **Step 6: Run lazy-loading, auth, preview, lint, and build**

```powershell
npx playwright test tests/lazy-loading.spec.ts tests/auth-flow.spec.ts tests/preview-mode.spec.ts --project="Desktop Chrome"
npm run lint
npm run build
```

Expected: all pass and the build emits hashed assets.

- [ ] **Step 7: Commit lazy loading**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/useWorkspaceLoaders.ts app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts app/mneme_frontend_v0.2.1/src/App.vue app/mneme_frontend_v0.2.1/src/components/ui/UiStatusPanel.vue app/mneme_frontend_v0.2.1/src/i18n/messages.ts app/mneme_frontend_v0.2.1/tests/lazy-loading.spec.ts
git commit -m "refactor(frontend): lazy-load workspace features"
```

### Task 4: Implement the graph as a real interactive workspace

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

**Interfaces:**
- Consumes: graph nodes/edges, selected documents, `loadDocumentPreview`, and workspace navigation.
- Produces: `activeFilter`, `enabledNodeTypes`, `visibleNodes`, `visibleEdges`, `selectedNode`, `selectNode()`, `dragNode()`, `restartLayout()`, and `openSelectedDocument()`.

- [ ] **Step 1: Replace placeholder graph tests with failing behavior tests**

Update preview tests to require single-click preview, real document names, all/tags/orphans filters, node-type filter panel, canvas deselection, drag movement, a changed layout after restart, and a collapsed canvas wider than the expanded canvas.

```ts
await node.click();
await expect(page.getByTestId('graph-document-preview-panel')).toBeVisible();
await page.getByRole('button', { name: 'Orphan nodes' }).click();
await expect(page.locator('[data-node-id="node-doc-graph"]')).toBeHidden();
expect(collapsedCanvas!.width).toBeGreaterThan(expandedCanvas!.width);
```

- [ ] **Step 2: Run graph tests and verify RED**

```powershell
npx playwright test tests/preview-mode.spec.ts -g "graph|file rail" --project="Desktop Chrome"
```

Expected: failures for single click, filters, placeholder removal, drag, restart, and width release.

- [ ] **Step 3: Implement graph state and derived filters**

Create `useGraphInteraction.ts` with deterministic seeded radial positions. Filter visible edges to edges whose endpoints are visible. Compute orphan IDs from node degree. Maintain local `Map<string, {x: number; y: number}>` overrides for drag without backend writes.

- [ ] **Step 4: Replace inert GraphView controls**

Remove hard-coded Machine Learning/Architecture items. Bind the rail to `selectedDocuments`. Bind node click, keyboard Enter/Space, pointer drag, filters, selection clearing, and document navigation. Keep GraphRAG submission separate from local node search. Remove any remaining control with no handler.

- [ ] **Step 5: Fix graph rail layout**

Apply a class to `graph-grid`:

```css
.graph-grid { grid-template-columns: 280px minmax(0, 1fr); }
.graph-grid.graph-grid--rail-closed { grid-template-columns: 0 minmax(0, 1fr); }
```

Keep overlay drawer behavior below 1024px. Ensure the toggle moves to the canvas edge and remains keyboard reachable.

- [ ] **Step 6: Run graph tests at desktop and mobile**

```powershell
npx playwright test tests/preview-mode.spec.ts -g "graph|file rail" --project="Desktop Chrome" --project="Mobile Chrome"
npm run lint
```

Expected: all graph tests pass.

- [ ] **Step 7: Commit graph implementation**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts app/mneme_frontend_v0.2.1/src/views/GraphView.vue app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts app/mneme_frontend_v0.2.1/src/i18n/messages.ts app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts
git commit -m "feat(frontend): complete graph workspace interactions"
```

### Task 5: Repair settings hierarchy and shell collapse behavior

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/views/SettingsView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/index.css`
- Modify: `app/mneme_frontend_v0.2.1/src/components/shell/ResourceSidebar.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useResponsiveShell.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/layout-regression.spec.ts`

**Interfaces:**
- Consumes: existing design tokens, `resourceOpen`, view navigation, and settings actions.
- Produces: one settings title hierarchy, compact section navigation, independent resource/graph collapse, and breakpoint-safe geometry.

- [ ] **Step 1: Write visual geometry regression tests**

At 1440, 1024, 768, and 390 widths, open Settings and assert no document horizontal overflow, one visible `设置` page heading, non-overlapping banner/card boxes, and content expansion after resource collapse. Capture screenshots into Playwright output for review.

```ts
expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
await expect(page.getByRole('heading', { name: '设置', exact: true })).toHaveCount(1);
expect(collapsedMain!.width).toBeGreaterThan(expandedMain!.width);
```

- [ ] **Step 2: Run layout tests and verify RED**

```powershell
npx playwright test tests/layout-regression.spec.ts --project="Desktop Chrome"
```

Expected: current duplicate hierarchy/collapse geometry fails.

- [ ] **Step 3: Simplify settings hierarchy**

Remove the internal settings `h1`; keep the workspace top bar as the page title. Use a `settings-section-nav` sticky row/column with compact anchors. Add `min-width: 0`, consistent `line-height`, and responsive grid rules. All Chinese interface copy uses `var(--font-sans)`; serif remains only for editorial content, not control labels.

- [ ] **Step 4: Separate sidebar collapse geometry**

Ensure `mneme-shell--resource-closed` removes only the 256px resource track on desktop. Graph rail state remains inside GraphView. Tablet uses fixed overlay and scrim; mobile uses bottom navigation. Breakpoint synchronization must not reopen a sidebar after a user closes it unless the viewport crosses a breakpoint.

- [ ] **Step 5: Run layout tests and inspect screenshots**

```powershell
npx playwright test tests/layout-regression.spec.ts --project="Desktop Chrome" --project="Mobile Chrome"
npm run lint
npm run build
```

Expected: all geometry assertions pass and screenshots show aligned headings/cards without text collision.

- [ ] **Step 6: Commit layout repair**

```powershell
git add app/mneme_frontend_v0.2.1/src/views/SettingsView.vue app/mneme_frontend_v0.2.1/src/App.vue app/mneme_frontend_v0.2.1/src/index.css app/mneme_frontend_v0.2.1/src/components/shell/ResourceSidebar.vue app/mneme_frontend_v0.2.1/src/composables/useResponsiveShell.ts app/mneme_frontend_v0.2.1/tests/layout-regression.spec.ts
git commit -m "fix(frontend): repair settings and collapsed layouts"
```

### Task 6: Configure internal Neo4j and degrade model-backed failures safely

**Files:**
- Modify: `deploy/env/backend.production.example`
- Modify: `tests/test_docker_compose_contract.py`
- Modify if traceback proves missing translation: `app/mneme/api/errors.py`
- Test if backend changes: `tests/test_final_backend_convergence.py`
- Modify on server: `/root/project/Reminder/.env`

**Interfaces:**
- Consumes: Compose service name `neo4j`, existing API exception boundary, and production environment.
- Produces: no connection attempts to the retired IP and stable user-safe 5xx responses.

- [ ] **Step 1: Write a failing production environment contract**

```python
def test_production_template_uses_internal_neo4j_service():
    text = Path('deploy/env/backend.production.example').read_text(encoding='utf-8')
    assert 'NEO4J_URI=bolt://neo4j:7687' in text
    assert '8.147.57.104' not in text
```

If current exception middleware returns raw framework errors, add a test asserting a stable envelope with a Chinese user-safe message and a request ID, never a traceback.

- [ ] **Step 2: Run backend contracts and verify RED**

```powershell
python -m pytest tests/test_docker_compose_contract.py tests/test_final_backend_convergence.py -q -p no:cacheprovider
```

Expected: production Neo4j template assertion fails before modification.

- [ ] **Step 3: Update the production template and proven exception translation only**

Set the template URI exactly to `bolt://neo4j:7687`. Do not change model-provider credentials in code. If logs identify provider configuration errors, return a typed degraded response and preserve the detailed exception only in server logs.

- [ ] **Step 4: Run the complete backend suite**

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall app/mneme alembic main.py
```

Expected: all tests and compilation pass.

- [ ] **Step 5: Commit production reliability changes**

```powershell
git add deploy/env/backend.production.example tests/test_docker_compose_contract.py app/mneme/api/errors.py tests/test_final_backend_convergence.py
git commit -m "fix: use internal Neo4j and safe degraded errors"
```

Stage only files that actually changed.

### Task 7: Full validation, production deployment, and acceptance

**Files:**
- No new source files.
- Modify on server: `/root/project/Reminder/.env`
- Deploy to server: corrected source tree and rebuilt `reminder-app:local` image.

**Interfaces:**
- Consumes: Tasks 1–6 and the existing `mneme` Compose volumes.
- Produces: verified production behavior at `https://www.mneme.com.cn`.

- [ ] **Step 1: Run all local checks**

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall app/mneme alembic main.py
cd app/mneme_frontend_v0.2.1
npm ci --no-audit --no-fund
npm run lint
npm run build
npx playwright test --project="Desktop Chrome" --project="Mobile Chrome"
```

Expected: every command exits 0.

- [ ] **Step 2: Inspect the application in a browser at required widths**

Use real Chrome at 1440x900, 1024x768, 768x1024, and 390x844. Verify login, registration, shell entry, settings, graph selection/filter/drag/zoom/restart/collapse, resource collapse, loading, empty, and error states. Compare settings and collapsed layouts against the reported screenshots; no overlap or reserved empty track may remain.

- [ ] **Step 3: Back up production state and set internal Neo4j**

```bash
cp /root/project/Reminder/.env /root/reminder-env-before-frontend-reliability-20260711
sed -i 's|^NEO4J_URI=.*|NEO4J_URI=bolt://neo4j:7687|' /root/project/Reminder/.env
docker volume ls --format '{{.Name}}' | grep '^mneme_'
```

Expected: all named volumes are present and no secret is printed.

- [ ] **Step 4: Deploy and rebuild without deleting volumes**

```bash
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose up -d --build
COMPOSE_PROJECT_NAME=mneme docker compose ps -a
```

Expected: migration exits 0, app/storage services are healthy, worker is ready.

- [ ] **Step 5: Verify startup performance and route isolation**

Use a disposable registered user. Measure login-to-shell with browser performance timing and assert no graph/profile/advice calls occur before navigation. Enter Graph and confirm Neo4j responses complete without a 30-second timeout. Trigger or simulate one model-backed failure and confirm navigation/settings/graph remain usable with a panel-level message.

- [ ] **Step 6: Verify logs and public routes**

```bash
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose logs --since=15m app worker | grep -E '8\.147\.57\.104:7687|Traceback|Internal Server Error' && exit 1 || true
curl -fsS https://www.mneme.com.cn/health
```

Expected: no old Neo4j address, no unhandled traceback from exercised flows, and health returns running.

- [ ] **Step 7: Commit any final test-only corrections, push, and create the review handoff**

```powershell
git status --short
git diff --check
git push -u origin codex/frontend-reliability
```

Expected: only intended commits are pushed; production secrets and screenshots outside Playwright output are not committed.
