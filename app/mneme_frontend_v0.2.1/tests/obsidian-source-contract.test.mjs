import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const appSource = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const previewApiSource = readFileSync(new URL('../src/lib/previewApi.ts', import.meta.url), 'utf8');

for (const testId of [
  'data-testid="obsidian-shell"',
  'data-testid="obsidian-rail"',
  'data-testid="obsidian-explorer"',
  'data-testid="obsidian-active-tab"',
  'data-testid="obsidian-editor-pane"',
]) {
  assert.ok(appSource.includes(testId), `Expected App.tsx to expose ${testId}`);
}

assert.ok(
  appSource.includes('lg:grid-cols-[44px_260px_minmax(0,1fr)]'),
  'Expected the desktop workbench grid to use an Obsidian-like 44px rail and compact explorer',
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
