# Mneme Obsidian Aesthetic Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Mneme Vue frontend as a refined Obsidian-inspired workspace with responsive desktop/tablet/mobile layouts, light and dark themes, and Chinese/English localization without changing backend API contracts.

**Architecture:** Keep `useMnemeWorkspace` as the business-data boundary, move appearance and locale state into focused composables, and reduce `App.vue` to shell composition. Build small shell and UI components around semantic CSS tokens, then migrate the existing vault, graph, AI, and settings experiences into view components while preserving current preview API behavior.

**Tech Stack:** Vue 3.5, TypeScript 5.8, Tailwind CSS 4, Lucide Vue, D3, Vite 6, Playwright.

## Global Constraints

- Preserve all current backend API contracts and preview-mode behavior.
- Support `light`, `dark`, and `system` theme modes.
- Support `zh-CN` and `en-US` locales.
- Persist explicit theme and locale choices in `localStorage`.
- Do not introduce a new UI framework or a new visual language outside the approved Obsidian-inspired design.
- All primary interactive elements require hover, focus-visible, active, and disabled states.
- Desktop, tablet, and mobile layouts must be intentional; primary content must not require horizontal page scrolling.
- Every remote-data view must expose loading, empty, and error states.
- Preserve current D3 graph, API client, authentication, upload, chat, model settings, and sync actions.

---

### Task 1: Preference and Locale Foundations

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/composables/usePreferences.ts`
- Create: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`
- Create: `app/mneme_frontend_v0.2.1/src/composables/useI18n.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/preferences.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/main.ts`

**Interfaces:**
- Produces: `ThemeMode = "light" | "dark" | "system"` and `Locale = "zh-CN" | "en-US"`.
- Produces: `usePreferences(): { themeMode, resolvedTheme, locale, setThemeMode, setLocale }`.
- Produces: `useI18n(): { locale, t, formatDate, formatNumber }` where `t(key, params?)` returns a localized string.
- Applies: `data-theme="light|dark"` and `lang="zh-CN|en-US"` to `document.documentElement`.

- [ ] **Step 1: Write failing preference E2E tests**

```ts
test('theme and locale preferences persist across reloads', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.getByRole('button', { name: /settings|设置/i }).click();
  await page.getByRole('button', { name: /light|浅色/i }).click();
  await page.getByRole('button', { name: /简体中文/i }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
});
```

- [ ] **Step 2: Run the test and verify the missing preference controls fail**

Run: `npm run test:e2e -- tests/preferences.spec.ts --project="Desktop Chrome"`

Expected: FAIL because the settings view does not expose persistent theme and locale controls.

- [ ] **Step 3: Implement typed preferences and translation lookup**

```ts
export type ThemeMode = "light" | "dark" | "system";
export type Locale = "zh-CN" | "en-US";

const themeMode = ref<ThemeMode>(readTheme());
const locale = ref<Locale>(readLocale());
const resolvedTheme = computed(() =>
  themeMode.value === "system" ? (media.matches ? "dark" : "light") : themeMode.value,
);

function applyPreferences() {
  document.documentElement.dataset.theme = resolvedTheme.value;
  document.documentElement.lang = locale.value;
}
```

Create translation resources as nested immutable objects and implement dot-path lookup with explicit English fallback. Initialize preferences before mounting the app in `main.ts`.

- [ ] **Step 4: Run typecheck and preference E2E tests**

Run: `npm run lint && npm run test:e2e -- tests/preferences.spec.ts --project="Desktop Chrome"`

Expected: PASS with the theme and locale attributes surviving reload.

- [ ] **Step 5: Commit the preference foundation**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/usePreferences.ts app/mneme_frontend_v0.2.1/src/composables/useI18n.ts app/mneme_frontend_v0.2.1/src/i18n/messages.ts app/mneme_frontend_v0.2.1/src/main.ts app/mneme_frontend_v0.2.1/tests/preferences.spec.ts
git commit -m "feat(frontend): add theme and locale preferences"
```

### Task 2: Semantic Theme and UI Primitives

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiButton.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiIconButton.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiEmptyState.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiStatusPanel.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/ui/UiSkeleton.vue`
- Create: `app/mneme_frontend_v0.2.1/tests/design-system-contract.test.mjs`
- Modify: `app/mneme_frontend_v0.2.1/src/index.css`
- Modify: `app/mneme_frontend_v0.2.1/package.json`

**Interfaces:**
- Consumes: `data-theme` from Task 1.
- Produces: semantic CSS variables including `--bg-canvas`, `--bg-sidebar`, `--bg-panel`, `--text-primary`, `--text-secondary`, `--border-muted`, `--accent`, and `--focus-ring`.
- Produces: shared UI components with native button semantics and slots for icon, title, description, and action.

- [ ] **Step 1: Add a failing source contract for semantic tokens**

```js
const css = readFileSync(path.join(root, 'src', 'index.css'), 'utf8');
for (const token of ['--bg-canvas', '--bg-sidebar', '--text-primary', '--border-muted', '--focus-ring']) {
  assert.ok(css.includes(token), `Expected semantic token ${token}`);
}
assert.ok(css.includes('[data-theme="light"]'), 'Expected a calibrated light theme');
assert.ok(css.includes('prefers-reduced-motion'), 'Expected reduced motion support');
```

- [ ] **Step 2: Run the contract and verify it fails**

Run: `node tests/design-system-contract.test.mjs`

Expected: FAIL on missing semantic theme tokens.

- [ ] **Step 3: Replace mixed glass/premium styling with semantic layers**

Define separate `:root` dark values and `[data-theme="light"]` light values. Create reusable classes for the application canvas, panel, divider, focus ring, selected row, floating surface, and scrollbars. Remove broad class-substring overrides and persistent glow effects. Add reduced-motion rules.

Implement `UiButton` variants `primary | secondary | ghost | danger` and sizes `sm | md`; implement icon buttons with required `aria-label`; implement empty, loading, and error primitives.

- [ ] **Step 4: Run contract, typecheck, and build**

Run: `node tests/design-system-contract.test.mjs && npm run lint && npm run build`

Expected: all commands exit 0.

- [ ] **Step 5: Commit semantic design foundations**

```powershell
git add app/mneme_frontend_v0.2.1/src/index.css app/mneme_frontend_v0.2.1/src/components/ui app/mneme_frontend_v0.2.1/tests/design-system-contract.test.mjs app/mneme_frontend_v0.2.1/package.json
git commit -m "feat(frontend): establish semantic Obsidian design system"
```

### Task 3: Responsive Application Shell

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/ActivityBar.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/ResourceSidebar.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/WorkspaceHeader.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/ContextPanel.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/StatusBar.vue`
- Create: `app/mneme_frontend_v0.2.1/src/components/shell/MobileNavigation.vue`
- Create: `app/mneme_frontend_v0.2.1/src/composables/useResponsiveShell.ts`
- Create: `app/mneme_frontend_v0.2.1/tests/responsive-shell.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`

**Interfaces:**
- Consumes: `t()` from Task 1 and UI primitives from Task 2.
- Produces: `useResponsiveShell(): { isMobile, isTablet, resourceOpen, contextOpen, toggleResource, toggleContext, closeOverlays }`.
- Emits: shell navigation events with existing view ids `notes | graph | ai | settings`.

- [ ] **Step 1: Write failing desktop and mobile layout tests**

```ts
test('mobile uses bottom navigation without horizontal page overflow', async ({ page }) => {
  await page.goto('/?preview=1');
  await expect(page.getByTestId('mobile-navigation')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test('desktop exposes collapsible resource and context panels', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/?preview=1');
  await expect(page.getByTestId('activity-bar')).toBeVisible();
  await expect(page.getByTestId('resource-sidebar')).toBeVisible();
});
```

- [ ] **Step 2: Run responsive tests and verify failure**

Run: `npm run test:e2e -- tests/responsive-shell.spec.ts`

Expected: FAIL because the current mobile layout keeps desktop columns and overflows.

- [ ] **Step 3: Build the responsive shell**

Use CSS grid for desktop, activity-bar plus main content for tablet, and a single-column main surface with fixed bottom navigation for mobile. Resource and context panels become accessible overlay drawers below desktop width. Keep panel open state local to the shell and close overlays after navigation.

- [ ] **Step 4: Run responsive tests across both Playwright projects**

Run: `npm run lint && npm run test:e2e -- tests/responsive-shell.spec.ts`

Expected: desktop shell assertions pass, mobile navigation is visible, and page overflow is false.

- [ ] **Step 5: Commit the application shell**

```powershell
git add app/mneme_frontend_v0.2.1/src/App.vue app/mneme_frontend_v0.2.1/src/components/shell app/mneme_frontend_v0.2.1/src/composables/useResponsiveShell.ts app/mneme_frontend_v0.2.1/tests/responsive-shell.spec.ts
git commit -m "refactor(frontend): build responsive workspace shell"
```

### Task 4: Extract and Restyle Business Views

**Files:**
- Create: `app/mneme_frontend_v0.2.1/src/views/VaultView.vue`
- Create: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Create: `app/mneme_frontend_v0.2.1/src/views/AiLabView.vue`
- Create: `app/mneme_frontend_v0.2.1/src/views/SettingsView.vue`
- Create: `app/mneme_frontend_v0.2.1/tests/view-boundary-contract.test.mjs`
- Modify: `app/mneme_frontend_v0.2.1/src/App.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts`

**Interfaces:**
- Consumes: existing refs and actions returned by `useMnemeWorkspace` without changing API request signatures.
- Produces: view components whose props are typed from `src/types.ts` and whose events call existing workspace actions.
- Keeps: existing E2E-visible names and `data-testid` hooks where they encode behavior rather than layout.

- [ ] **Step 1: Add a failing boundary contract**

```js
for (const view of ['VaultView.vue', 'GraphView.vue', 'AiLabView.vue', 'SettingsView.vue']) {
  assert.ok(existsSync(path.join(root, 'src', 'views', view)), `Expected extracted ${view}`);
}
const app = readFileSync(path.join(root, 'src', 'App.vue'), 'utf8');
assert.ok(app.split('\n').length < 500, 'Expected App.vue to become shell composition');
```

- [ ] **Step 2: Run the boundary contract and verify failure**

Run: `node tests/view-boundary-contract.test.mjs`

Expected: FAIL because the view files do not exist and `App.vue` remains monolithic.

- [ ] **Step 3: Extract the four views without changing behavior**

Move view-specific markup and local interaction state into focused components. Replace the oversized navigation brand block, repeated premium cards, and mixed surfaces with the shell and UI primitives. Keep uploads, document actions, graph interactions, chat sessions, model controls, and synchronization callbacks wired to the same workspace methods.

- [ ] **Step 4: Run contracts, typecheck, and existing E2E regression tests**

Run: `node tests/view-boundary-contract.test.mjs && npm run lint && npm run test:e2e -- tests/preview-mode.spec.ts`

Expected: extracted-view contract passes and all existing preview-mode behaviors pass on desktop and mobile.

- [ ] **Step 5: Commit the view extraction**

```powershell
git add app/mneme_frontend_v0.2.1/src/App.vue app/mneme_frontend_v0.2.1/src/views app/mneme_frontend_v0.2.1/src/composables/useMnemeWorkspace.ts app/mneme_frontend_v0.2.1/tests/view-boundary-contract.test.mjs
git commit -m "refactor(frontend): extract polished workspace views"
```

### Task 5: Complete Localization and View States

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/i18n/messages.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/views/VaultView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/views/AiLabView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/views/SettingsView.vue`
- Modify: `app/mneme_frontend_v0.2.1/src/components/shell/*.vue`
- Create: `app/mneme_frontend_v0.2.1/tests/localization-states.spec.ts`

**Interfaces:**
- Consumes: `t`, `formatDate`, and `formatNumber` from Task 1.
- Consumes: loading, empty, and error primitives from Task 2.
- Produces: full UI copy coverage in both locales and localized summaries for raw backend errors.

- [ ] **Step 1: Write failing localization and state tests**

```ts
test('switching to Chinese localizes global navigation without losing the active view', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.getByRole('button', { name: /settings/i }).click();
  await page.getByRole('button', { name: '简体中文' }).click();
  await expect(page.getByRole('button', { name: '知识图谱' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
});
```

Add preview API fixtures for an empty vault and a rejected request, then assert visible primary actions and a retry button.

- [ ] **Step 2: Run localization tests and verify untranslated copy fails**

Run: `npm run test:e2e -- tests/localization-states.spec.ts`

Expected: FAIL on missing Chinese labels or missing state UI.

- [ ] **Step 3: Replace user-visible hard-coded strings and wire state primitives**

Use translation keys for navigation, headings, actions, status labels, confirmation messages, empty-state copy, and errors. Format dates and counts through locale helpers. Preserve raw server messages only in expandable technical detail.

- [ ] **Step 4: Run localization tests and typecheck**

Run: `npm run lint && npm run test:e2e -- tests/localization-states.spec.ts`

Expected: locale changes are immediate, active view remains stable, and empty/error actions are usable.

- [ ] **Step 5: Commit localization and state coverage**

```powershell
git add app/mneme_frontend_v0.2.1/src/i18n/messages.ts app/mneme_frontend_v0.2.1/src/views app/mneme_frontend_v0.2.1/src/components/shell app/mneme_frontend_v0.2.1/tests/localization-states.spec.ts
git commit -m "feat(frontend): localize workspace and complete data states"
```

### Task 6: Visual QA, Accessibility, and Final Verification

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/tests/preferences.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/responsive-shell.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/index.css`
- Modify: affected Vue components identified by browser inspection.

**Interfaces:**
- Verifies all interfaces from Tasks 1–5.
- Produces no new product behavior; only closes visual, accessibility, and regression gaps.

- [ ] **Step 1: Capture six reference screenshots**

Run the preview app and capture desktop, tablet, and mobile screenshots in both light and dark themes using Playwright. Store them under the ignored `.tmp/visual-qa` directory.

```ts
await page.setViewportSize({ width: 1440, height: 900 });
await page.screenshot({ path: '../../.tmp/visual-qa/desktop-dark.png', fullPage: true });
```

- [ ] **Step 2: Inspect hierarchy, overflow, focus, and both locales**

Verify each screenshot against the design specification. Use keyboard navigation to check visible focus in activity bar, resource rows, graph controls, AI composer, settings controls, drawers, and dialogs. Correct only observed violations.

- [ ] **Step 3: Run the complete frontend verification suite**

Run: `npm run lint && npm run build && node tests/design-system-contract.test.mjs && node tests/view-boundary-contract.test.mjs && npm run test:e2e`

Expected: typecheck and build exit 0; all contract and Playwright tests pass on Desktop Chrome and Mobile Chrome.

- [ ] **Step 4: Run repository regression tests and inspect Git state**

Run: `.venv\Scripts\python.exe -m pytest -q && git diff --check && git status --short`

Expected: backend tests pass, `git diff --check` reports no whitespace errors, and only intended frontend files are modified.

- [ ] **Step 5: Commit final QA corrections**

```powershell
git add app/mneme_frontend_v0.2.1
git commit -m "test(frontend): verify responsive bilingual workspace"
```

## Execution Order

Execute Tasks 1–6 sequentially. Each task begins with a failing test or source contract, ends with fresh verification evidence, and creates a focused commit. Do not restore the pre-sync stashes during implementation because they contain obsolete React-era logs and a one-character README edit unrelated to this design.
