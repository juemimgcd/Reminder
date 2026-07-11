import { execFileSync, execSync, spawnSync } from 'node:child_process';

function fail(message, error) {
  console.error(`\n[prebuild] ${message}`);
  if (error) {
    console.error(`[prebuild] ${error.code || error.name}: ${error.message}`);
  }
  console.error('[prebuild] Vite still needs basic Node child_process support during production builds.');
  console.error('[prebuild] If this is Windows, check antivirus/AppLocker/Controlled Folder Access and reinstall dependencies with npm ci.');
  process.exit(1);
}

function warn(message, error) {
  console.warn(`\n[prebuild] ${message}`);
  if (error) {
    console.warn(`[prebuild] ${error.code || error.name}: ${error.message}`);
  }
  console.warn('[prebuild] Continuing with the Windows-safe production build script.');
}

const childProcessProbe = spawnSync(process.execPath, ['-e', 'process.exit(0)'], {
  stdio: 'ignore',
  windowsHide: true,
});

if (childProcessProbe.error) {
  fail('Node cannot start child processes in this environment.', childProcessProbe.error);
}

if (childProcessProbe.status !== 0) {
  fail(`Node child-process probe exited with status ${childProcessProbe.status}.`);
}

try {
  execFileSync(process.execPath, ['-e', 'process.exit(0)'], { stdio: 'ignore', windowsHide: true });
  execSync(`${JSON.stringify(process.execPath)} -e "process.exit(0)"`, { stdio: 'ignore', windowsHide: true });
} catch (error) {
  fail('Node child_process exec probes are blocked in this environment.', error);
}

const childProcessPipeProbe = spawnSync(process.execPath, ['-e', 'process.exit(0)'], {
  windowsHide: true,
});

if (childProcessPipeProbe.error) {
  warn('Node child_process stdio pipe probes are blocked in this environment.', childProcessPipeProbe.error);
}
