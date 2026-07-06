import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { compile, optimize } from '@tailwindcss/node';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const distDir = path.join(root, 'dist');
const assetsDir = path.join(distDir, 'assets');
const entryFile = path.join(root, 'src', 'main.tsx');
const cssFile = path.join(root, 'src', 'index.css');
const esbuildExe = path.join(root, 'node_modules', '@esbuild', 'win32-x64', 'esbuild.exe');

function walkFiles(dir, extensions, files = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkFiles(fullPath, extensions, files);
    } else if (extensions.has(path.extname(entry.name))) {
      files.push(fullPath);
    }
  }
  return files;
}

function collectTailwindCandidates() {
  const candidates = new Set();
  const sourceFiles = walkFiles(path.join(root, 'src'), new Set(['.ts', '.tsx', '.js', '.jsx']));
  const tokenPattern = /[A-Za-z0-9_!:@/.[\]()%#,+-]+/g;

  for (const file of sourceFiles) {
    const source = readFileSync(file, 'utf8');
    for (const match of source.matchAll(tokenPattern)) {
      const token = match[0].replace(/^[^A-Za-z0-9_![\]-]+|[^A-Za-z0-9_\])%#-]+$/g, '');
      if (token) {
        candidates.add(token);
      }
    }
  }

  return [...candidates];
}

async function buildCss() {
  const css = readFileSync(cssFile, 'utf8');
  const compiler = await compile(css, {
    base: root,
    from: cssFile,
    onDependency() {},
  });
  const builtCss = compiler.build(collectTailwindCandidates());
  const optimized = optimize(builtCss, { file: cssFile, minify: false });
  writeFileSync(path.join(assetsDir, 'app.css'), optimized.code);
}

function buildJs() {
  const result = spawnSync(
    esbuildExe,
    [
      entryFile,
      '--bundle',
      '--format=esm',
      '--target=es2022',
      '--jsx=automatic',
      '--loader:.css=empty',
      '--outfile=dist/assets/app.js',
      '--define:import.meta.env.VITE_API_BASE_URL=""',
      '--define:import.meta.env.VITE_MNEME_PREVIEW="false"',
      '--define:import.meta.env.MODE="production"',
    ],
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
    throw new Error(`esbuild exited with status ${result.status}`);
  }
}

function writeHtml() {
  writeFileSync(
    path.join(distDir, 'index.html'),
    `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mneme Workspace</title>
    <script type="module" crossorigin src="/assets/app.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/app.css" />
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
`,
  );
}

mkdirSync(assetsDir, { recursive: true });
await buildCss();
buildJs();
writeHtml();
