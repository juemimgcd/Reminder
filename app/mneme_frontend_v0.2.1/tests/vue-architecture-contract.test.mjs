import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { strict as assert } from 'node:assert';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const packageJson = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8'));
const viteConfig = readFileSync(path.join(root, 'vite.config.mjs'), 'utf8');
const tsconfig = JSON.parse(readFileSync(path.join(root, 'tsconfig.json'), 'utf8'));

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    const fullPath = path.join(dir, entry);
    if (statSync(fullPath).isDirectory()) {
      walk(fullPath, files);
    } else {
      files.push(fullPath);
    }
  }
  return files;
}

assert.ok(packageJson.dependencies.vue, 'Expected Vue to be a runtime dependency');
assert.ok(packageJson.dependencies['@lucide/vue'], 'Expected Lucide Vue icons to be installed');
assert.ok(packageJson.devDependencies['@vitejs/plugin-vue'], 'Expected Vite Vue plugin to be installed');

for (const reactPackage of ['react', 'react-dom', 'react-markdown', 'lucide-react', 'lucide-vue-next']) {
  assert.ok(!packageJson.dependencies[reactPackage], `Expected ${reactPackage} to be removed from runtime dependencies`);
}

assert.ok(viteConfig.includes('@vitejs/plugin-vue'), 'Expected Vite config to use the Vue plugin');
assert.ok(!viteConfig.includes('@vitejs/plugin-react'), 'Expected Vite config to stop using the React plugin');
assert.ok(!('jsx' in tsconfig.compilerOptions), 'Expected tsconfig to drop React JSX settings');

assert.ok(existsSync(path.join(root, 'src', 'main.ts')), 'Expected Vue TypeScript entrypoint src/main.ts');
assert.ok(existsSync(path.join(root, 'src', 'App.vue')), 'Expected Vue root component src/App.vue');
assert.ok(!existsSync(path.join(root, 'src', 'main.tsx')), 'Expected old React entrypoint src/main.tsx to be removed');
assert.ok(!existsSync(path.join(root, 'src', 'App.tsx')), 'Expected old React root component src/App.tsx to be removed');

const appFiles = walk(path.join(root, 'src')).filter((file) => /\.(ts|vue)$/.test(file));
for (const file of appFiles) {
  const source = readFileSync(file, 'utf8');
  assert.ok(!source.includes('from "react"') && !source.includes("from 'react'"), `Expected no React imports in ${file}`);
  assert.ok(!source.includes('lucide-react'), `Expected no lucide-react imports in ${file}`);
  assert.ok(!source.includes('lucide-vue-next'), `Expected no deprecated lucide-vue-next imports in ${file}`);
}
