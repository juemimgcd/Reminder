import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const appSource = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const previewApiSource = readFileSync(new URL('../src/lib/previewApi.ts', import.meta.url), 'utf8');

for (const testId of [
  'data-testid="obsidian-shell"',
  'data-testid="sanctuary-sidebar"',
  'data-testid="sanctuary-topbar"',
  'data-testid="sanctuary-active-view"',
  'data-testid="obsidian-editor-pane"',
]) {
  assert.ok(appSource.includes(testId), `Expected App.tsx to expose ${testId}`);
}

assert.ok(
  appSource.includes('lg:grid-cols-[256px_minmax(0,1fr)]'),
  'Expected the desktop workbench grid to match the 256px Stitch Sanctuary sidebar',
);

for (const navLabel of ['Dashboard', 'Notes', 'Graph', 'AI Chat', 'Settings']) {
  assert.ok(appSource.includes(`label: "${navLabel}"`), `Expected Sanctuary navigation to include ${navLabel}`);
}

for (const designToken of ['--color-surface-base: #09090b', '--color-primary-container: #7c3aed']) {
  assert.ok(
    readFileSync(new URL('../src/index.css', import.meta.url), 'utf8').toLowerCase().includes(designToken),
    `Expected Obsidian Flux design token ${designToken}`,
  );
}

assert.ok(
  appSource.includes('data-testid="dashboard-overview"'),
  'Expected the Workspace view to read as a Sanctuary dashboard overview',
);

for (const stitchClass of ['premium-card', 'glass-panel', 'premium-input', 'premium-tag']) {
  assert.ok(appSource.includes(stitchClass) || readFileSync(new URL('../src/index.css', import.meta.url), 'utf8').includes(stitchClass), `Expected Stitch export style hook ${stitchClass}`);
}

for (const stitchLayoutHook of [
  'data-testid="stitch-dashboard-grid"',
  'data-testid="stitch-notes-layout"',
  'data-testid="stitch-ai-layout"',
  'data-testid="stitch-settings-layout"',
  'data-testid="stitch-graph-canvas"',
]) {
  assert.ok(appSource.includes(stitchLayoutHook), `Expected App.tsx to expose ${stitchLayoutHook}`);
}

assert.ok(
  appSource.includes('view === "graph" ? "p-0"'),
  'Expected the Graph view to remove the ordinary page padding and behave like the Stitch full-canvas page',
);

assert.ok(
  appSource.includes('view !== "graph" && view !== "notes" && view !== "ai"'),
  'Expected the generic page heading to be skipped for Stitch-specialized views',
);

assert.ok(
  !appSource.includes('<MetricCard label="Vaults"'),
  'Expected the editor pane to drop the bulky Vaults/Files/Tasks dashboard cards',
);

assert.ok(
  previewApiSource.includes('import.meta.env.MODE === "preview"'),
  'Expected npm run dev:preview to force preview mode through Vite mode',
);

assert.ok(
  previewApiSource.includes('window.location.hash'),
  'Expected preview mode detection to handle preview flags inside hash URLs',
);

for (const layoutHook of [
  'data-testid="graph-function-grid"',
  'testId="graph-output-workspace"',
  'data-testid="memory-function-grid"',
  'testId="memory-output-workspace"',
  'data-testid="insights-function-grid"',
  'testId="insights-output-workspace"',
]) {
  assert.ok(appSource.includes(layoutHook), `Expected App.tsx to separate controls and outputs with ${layoutHook}`);
}

assert.ok(
  !appSource.includes('{ id: "chat", label: "Chat"'),
  'Expected chat to be centralized in Workspace instead of remaining a separate page',
);

for (const centralizedHook of [
  'data-testid="unified-command-module"',
  'data-testid="workspace-command-tabs"',
  'data-testid="workspace-command-panel"',
  'data-testid="workspace-chat-command"',
  'data-testid="workspace-upload-command"',
  'data-testid="workspace-create-kb-command"',
]) {
  assert.ok(appSource.includes(centralizedHook), `Expected Workspace to centralize app commands with ${centralizedHook}`);
}

assert.ok(
  appSource.includes('title="Graph Workspace"') && appSource.includes('min-h-[calc(100vh-164px)]'),
  'Expected Graph to use a large Obsidian-like workspace instead of a small split canvas',
);

assert.ok(
  !appSource.includes('data-testid="explorer-upload-command"') && !appSource.includes('data-testid="explorer-create-kb-command"'),
  'Expected the explorer to remain navigation-only instead of owning create/upload commands',
);

for (const sidebarHook of [
  'data-testid="sidebar-group-vaults"',
  'data-testid="sidebar-group-files"',
]) {
  assert.ok(appSource.includes(sidebarHook), `Expected explorer to follow shadcn Sidebar group structure with ${sidebarHook}`);
}

assert.ok(
  appSource.includes('type WorkspaceCommandTab') && appSource.includes('setWorkspaceCommandTab'),
  'Expected Workspace Commands to behave like shadcn Tabs instead of showing every form at once',
);
