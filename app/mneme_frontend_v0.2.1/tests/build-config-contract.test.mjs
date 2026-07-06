import { readFileSync, existsSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const prebuildCheckSource = readFileSync(new URL('../scripts/prebuild-check.mjs', import.meta.url), 'utf8');
const buildScriptSource = readFileSync(new URL('../scripts/build.mjs', import.meta.url), 'utf8');

assert.equal(
  packageJson.scripts.build,
  'node scripts/prebuild-check.mjs && node scripts/build.mjs',
  'Expected npm run build to run the prebuild check and the Windows-safe production build script',
);

assert.equal(
  packageJson.scripts['dev:embed'],
  'node scripts/prebuild-check.mjs && vite build --watch --config vite.config.mjs --configLoader native',
  'Expected embedded watch builds to use the same stable Vite config path',
);

assert.ok(existsSync(new URL('../scripts/prebuild-check.mjs', import.meta.url)), 'Expected a prebuild environment diagnostic script');
assert.ok(existsSync(new URL('../scripts/build.mjs', import.meta.url)), 'Expected a Windows-safe production build script');
assert.ok(existsSync(new URL('../vite.config.mjs', import.meta.url)), 'Expected Vite config to be plain ESM JavaScript');

for (const scriptName of ['dev', 'dev:embed', 'preview', 'dev:preview']) {
  const script = packageJson.scripts[scriptName];
  assert.ok(script.includes('--config vite.config.mjs'), `Expected ${scriptName} to use the JavaScript Vite config explicitly`);
  assert.ok(script.includes('--configLoader native'), `Expected ${scriptName} to avoid Vite's bundled config loader`);
}

assert.ok(!('esbuild@0.27.7' in (packageJson.allowScripts ?? {})), 'Expected stale denied esbuild install-script entry to be removed');
assert.equal(packageJson.allowScripts?.['esbuild@0.25.12'], true, 'Expected the installed esbuild version install script to stay allowed');

for (const buildScriptText of [
  "'@tailwindcss/node'",
  "'node_modules', '@esbuild', 'win32-x64', 'esbuild.exe'",
  "stdio: 'inherit'",
  '--loader:.css=empty',
]) {
  assert.ok(buildScriptSource.includes(buildScriptText), `Expected build script to keep the Windows-safe build path: ${buildScriptText}`);
}

for (const diagnosticText of [
  'Node child_process exec probes are blocked',
  'Node child_process stdio pipe probes are blocked',
  'Windows-safe production build script',
]) {
  assert.ok(prebuildCheckSource.includes(diagnosticText), `Expected prebuild diagnostic text: ${diagnosticText}`);
}
