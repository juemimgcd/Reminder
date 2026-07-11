import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { strict as assert } from 'node:assert';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const css = readFileSync(path.join(root, 'src', 'index.css'), 'utf8');

for (const token of [
  '--bg-canvas',
  '--bg-sidebar',
  '--bg-panel',
  '--text-primary',
  '--text-secondary',
  '--border-muted',
  '--accent',
  '--focus-ring',
]) {
  assert.ok(css.includes(token), `Expected semantic token ${token}`);
}

assert.ok(css.includes('[data-theme="light"]'), 'Expected a calibrated light theme');
assert.ok(css.includes('prefers-reduced-motion'), 'Expected reduced motion support');
assert.ok(css.includes(':focus-visible'), 'Expected visible keyboard focus styling');
assert.ok(!css.includes('fonts.googleapis.com'), 'Expected fonts to remain available offline');

for (const component of [
  'UiButton.vue',
  'UiIconButton.vue',
  'UiEmptyState.vue',
  'UiStatusPanel.vue',
  'UiSkeleton.vue',
]) {
  assert.ok(existsSync(path.join(root, 'src', 'components', 'ui', component)), `Expected ${component}`);
}
