import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { strict as assert } from 'node:assert';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
for (const view of [
  'DashboardView.vue',
  'VaultView.vue',
  'GraphView.vue',
  'AiLabView.vue',
  'SettingsView.vue',
]) {
  assert.ok(existsSync(path.join(root, 'src', 'views', view)), `Expected extracted ${view}`);
}

const app = readFileSync(path.join(root, 'src', 'App.vue'), 'utf8');
assert.ok(app.split('\n').length < 500, 'Expected App.vue to contain shell composition instead of full views');
assert.ok(app.includes('<GraphView'), 'Expected App.vue to compose GraphView');
assert.ok(app.includes('<AiLabView'), 'Expected App.vue to compose AiLabView');
assert.ok(app.includes('<UiStatusPanel'), 'Expected the shell to render non-blocking status feedback');
assert.ok(app.includes('<UiSkeleton'), 'Expected the shell to render a stable loading state');

const viewSource = ['VaultView.vue', 'GraphView.vue', 'AiLabView.vue']
  .map((view) => readFileSync(path.join(root, 'src', 'views', view), 'utf8'))
  .join('\n');
assert.ok(viewSource.includes('<UiEmptyState'), 'Expected data views to share an empty-state primitive');
