import { readFileSync, readdirSync, statSync } from 'node:fs';
import { strict as assert } from 'node:assert';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const appSource = readFileSync(path.join(root, 'src', 'App.vue'), 'utf8');
const cssSource = readFileSync(path.join(root, 'src', 'index.css'), 'utf8');
const apiSource = readFileSync(path.join(root, 'src', 'lib', 'api.ts'), 'utf8');
const previewApiSource = readFileSync(path.join(root, 'src', 'lib', 'previewApi.ts'), 'utf8');
const workspaceSource = readFileSync(path.join(root, 'src', 'composables', 'useMnemeWorkspace.ts'), 'utf8');

function collectVueSources(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const fullPath = path.join(directory, entry);
    return statSync(fullPath).isDirectory() ? collectVueSources(fullPath) : fullPath.endsWith('.vue') ? [readFileSync(fullPath, 'utf8')] : [];
  });
}

const vueSource = collectVueSources(path.join(root, 'src')).join('\n');

for (const testId of [
  'data-testid="obsidian-shell"',
  'data-testid="sanctuary-sidebar"',
  'data-testid="sanctuary-topbar"',
  'data-testid="obsidian-editor-pane"',
  'data-testid="stitch-dashboard-grid"',
  'data-testid="stitch-research-vault-layout"',
  'data-testid="stitch-graph-layout"',
  'data-testid="stitch-ai-laboratory-layout"',
  'data-testid="stitch-settings-layout"',
  'data-testid="graph-file-rail"',
  'data-testid="graph-document-preview-panel"',
  'data-testid="ai-history-rail"',
  'data-testid="workspace-chat-command"',
]) {
  assert.ok(vueSource.includes(testId), `Expected the composed Vue workspace to expose ${testId}`);
}

assert.ok(appSource.split('\n').length < 500, 'Expected App.vue to remain a focused shell component');
for (const view of ['DashboardView', 'VaultView', 'GraphView', 'AiLabView', 'SettingsView']) {
  assert.ok(appSource.includes(`<${view}`), `Expected App.vue to compose ${view}`);
}

for (const navLabel of ['Knowledge Graph', 'Research Vault', 'Semantic Map', 'AI Laboratory', 'System Settings']) {
  assert.ok(appSource.includes(`label: "${navLabel}"`), `Expected primary navigation to include ${navLabel}`);
}

for (const token of ['--bg-canvas', '--bg-sidebar', '--bg-panel', '--text-primary', '--border-muted', '--accent', '--focus-ring']) {
  assert.ok(cssSource.includes(token), `Expected semantic design token ${token}`);
}
assert.ok(cssSource.includes('[data-theme="light"]'), 'Expected a calibrated light theme');
assert.ok(cssSource.includes('prefers-reduced-motion'), 'Expected reduced-motion support');
assert.ok(!vueSource.includes('bg-[#070708]') && !vueSource.includes('bg-[#08080a]'), 'Expected views to use semantic surfaces');

for (const referenceText of [
  'Machine Learning',
  'Neural Networks',
  'All Nodes',
  'Orphans',
  'Long press to preview',
  'Backlinks',
  'Laboratory Sessions',
  'Referenced Context Nodes',
  'AI Models Configuration',
  'Knowledge Graph Health',
  'New Research Space',
]) {
  assert.ok(vueSource.includes(referenceText), `Expected polished workspace reference text: ${referenceText}`);
}

assert.ok(workspaceSource.includes('ref<WorkspaceView>("graph")'), 'Expected preview/default workspace to open the graph');
assert.ok(previewApiSource.includes('import.meta.env.MODE === "preview"'), 'Expected explicit preview mode');
assert.ok(previewApiSource.includes('window.location.hash'), 'Expected hash preview detection');

for (const apiMethod of ['uploadDocument', 'indexDocument', 'deleteDocument', 'testAiModelConfig', 'setDefaultAiModelConfig', 'updateAiModelConfig', 'deleteChatSession', 'graphRag']) {
  assert.ok(apiSource.includes(apiMethod) || previewApiSource.includes(apiMethod), `Expected client API method ${apiMethod}`);
}

for (const workspaceMethod of ['showDocumentationStatus', 'showSupportStatus', 'uploadFile', 'indexDocument', 'deleteDocument', 'runGraphRag', 'deleteActiveChatSession', 'testAiModelConfig', 'setDefaultAiModelConfig', 'updateActiveModelContextWindow']) {
  assert.ok(workspaceSource.includes(workspaceMethod), `Expected workspace method ${workspaceMethod}`);
}
