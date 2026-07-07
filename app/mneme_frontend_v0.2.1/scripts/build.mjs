import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const viteBin = path.join(root, 'node_modules', 'vite', 'bin', 'vite.js');

const result = spawnSync(
  process.execPath,
  [viteBin, 'build', '--config', 'vite.config.mjs', '--configLoader', 'native'],
  {
    cwd: root,
    stdio: 'inherit',
    windowsHide: true,
  },
);

if (result.error) {
  throw result.error;
}

if (result.status !== 0) {
  throw new Error(`Vite production build exited with status ${result.status}`);
}
