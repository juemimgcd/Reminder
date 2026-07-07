import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const appSource = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8');
const previewApiSource = readFileSync(new URL('../src/lib/previewApi.ts', import.meta.url), 'utf8');

for (const testId of [
  'data-testid="obsidian-shell"',
  'data-testid="sanctuary-sidebar"',
  'data-testid="sanctuary-topbar"',
  'data-testid="sanctuary-active-view"',
  'data-testid="obsidian-editor-pane"',
]) {
  assert.ok(appSource.includes(testId), `Expected App.vue to expose ${testId}`);
}

assert.ok(
  appSource.includes('grid-cols-[256px_minmax(0,1fr)]'),
  'Expected the workbench grid to match the 256px Stitch Sanctuary sidebar',
);

for (const navLabel of ['Knowledge Graph', 'Research Vault', 'Semantic Map', 'AI Laboratory', 'System Settings']) {
  assert.ok(appSource.includes(`label: "${navLabel}"`), `Expected Stitch navigation to include ${navLabel}`);
}

assert.ok(
  appSource.includes('{ id: "graph", label: "Knowledge Graph"'),
  'Expected the node graph canvas to be exposed as the Knowledge Graph module',
);

assert.ok(
  appSource.includes('{ id: "dashboard", label: "Semantic Map"'),
  'Expected the overview workspace to stop owning the Knowledge Graph label',
);

assert.ok(
  readFileSync(new URL('../src/composables/useMnemeWorkspace.ts', import.meta.url), 'utf8').includes('ref<WorkspaceView>("graph")'),
  'Expected preview/default workspace to open the node graph module first',
);

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
  'data-testid="stitch-research-vault-layout"',
  'data-testid="stitch-ai-laboratory-layout"',
  'data-testid="stitch-settings-layout"',
  'data-testid="stitch-graph-layout"',
]) {
  assert.ok(appSource.includes(stitchLayoutHook), `Expected App.vue to expose ${stitchLayoutHook}`);
}

for (const stitchText of ['Mneme Intelligence', 'Cognitive Sanctuary', 'New Research']) {
  assert.ok(appSource.includes(stitchText), `Expected Stitch shell copy: ${stitchText}`);
}

assert.ok(
  appSource.includes("workspace.view.value === 'graph'") && appSource.includes("'p-0'"),
  'Expected the Graph view to remove the ordinary page padding and behave like the Stitch full-canvas page',
);

assert.ok(
  appSource.includes("workspace.view.value !== 'graph' && workspace.view.value !== 'notes' && workspace.view.value !== 'ai'"),
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
  'data-testid="graph-output-workspace"',
  'data-testid="memory-function-grid"',
  'data-testid="memory-output-workspace"',
  'data-testid="insights-function-grid"',
  'data-testid="insights-output-workspace"',
]) {
  assert.ok(appSource.includes(layoutHook), `Expected App.vue to separate controls and outputs with ${layoutHook}`);
}

for (const invalidVueAttribute of [
  'testId="graph-output-workspace"',
  'testId="memory-output-workspace"',
  'testId="insights-output-workspace"',
]) {
  assert.ok(!appSource.includes(invalidVueAttribute), `Expected Vue template to avoid React-style ${invalidVueAttribute}`);
}

for (const graphReferenceText of [
  'Machine Learning',
  'Neural Networks',
  'All Nodes',
  'Orphans',
  'Long press to preview',
  'Backlinks',
]) {
  assert.ok(appSource.includes(graphReferenceText), `Expected Knowledge Graph to mirror Stitch graph reference text: ${graphReferenceText}`);
}

assert.ok(
  appSource.includes('xl:grid-cols-[320px_minmax(0,1fr)_376px]'),
  'Expected Knowledge Graph to use the wider Stitch graph properties panel',
);

for (const graphInteractionText of [
  'forceSimulation',
  'forceManyBody',
  'forceLink',
  'graphFileRailCollapsed',
  'data-testid="graph-file-rail"',
  'data-testid="graph-file-rail-toggle"',
  'data-testid="force-node"',
  '@pointerdown="startGraphNodeDrag',
  '@pointermove="moveGraphNodeDrag"',
]) {
  assert.ok(appSource.includes(graphInteractionText), `Expected Knowledge Graph to implement interactive graph behavior: ${graphInteractionText}`);
}

for (const aiReferenceText of [
  'Deep Thought Mode',
  'New Memory',
  'Search history...',
  'Today, 14:03',
  'Context: Node B',
  'AI responses may be structurally imperfect',
]) {
  assert.ok(appSource.includes(aiReferenceText), `Expected AI Laboratory to mirror Stitch chat reference text: ${aiReferenceText}`);
}

assert.ok(
  appSource.includes('fixed bottom-0 right-0') || appSource.includes('sticky bottom-0'),
  'Expected AI Laboratory input to stay anchored near the bottom like the Stitch chat reference',
);

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
  appSource.includes('title="Graph Workspace"') && appSource.includes('h-screen min-h-screen'),
  'Expected Graph to use a full-height Obsidian-like workspace instead of a small split canvas',
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
  readFileSync(new URL('../src/composables/useMnemeWorkspace.ts', import.meta.url), 'utf8').includes('type WorkspaceCommandTab') &&
    appSource.includes('workspace.workspaceCommandTab.value'),
  'Expected Workspace Commands to behave like tabs instead of showing every form at once',
);
