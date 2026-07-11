# Force-Directed Knowledge Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Mneme's static graph coordinates with a D3 force simulation that visibly converges, reheats for drag and restart actions, and stops after settling.

**Architecture:** Keep `useGraphInteraction.ts` as the graph-state boundary, but let it own exactly one D3 simulation over mutable copies of API nodes. Publish positions to Vue at most once per animation frame, keep filters outside the simulation identity signature, and expose explicit drag/restart/phase methods to `GraphView.vue`. Reduced-motion users receive a bounded synchronous layout with no continuous animation.

**Tech Stack:** Vue 3.5, TypeScript 5.8, D3 7.9 (`d3-force` APIs through `d3`), SVG pointer events, Playwright 1.60, Vite 6

## Global Constraints

- Reuse the existing `d3` dependency; do not add another physics or animation package.
- Preserve graph preview, GraphRAG, zoom, filters, node-type controls, file-rail collapse, and responsive behavior.
- Create no more than one force simulation for a mounted GraphView.
- Rebuild the simulation only when node or edge identities change, never when filters change.
- Publish Vue positions no more than once per animation frame.
- Stop D3 timers and cancel pending animation frames when data changes or the graph unmounts.
- Converged simulations remain stopped until drag, restart, or new graph data reheats them.
- `prefers-reduced-motion: reduce` performs bounded synchronous ticks and publishes once without continuous animation.
- Keep the current graph colors, typography, controls, and design tokens.
- Preserve all named production Docker volumes during deployment.

---

### Task 1: Build the force-simulation lifecycle

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Create: `app/mneme_frontend_v0.2.1/tests/force-directed-graph.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs`

**Interfaces:**
- Consumes: `ComputedRef<GraphNodeData[]>`, `ComputedRef<GraphEdgeData[]>`, existing node radius rules, and `window.matchMedia('(prefers-reduced-motion: reduce)')`.
- Produces: `simulationPhase: Ref<'idle' | 'running' | 'settled' | 'reduced'>`, reactive `positionedNodes`, `positionedEdges`, `restartLayout()`, and automatic teardown.

- [ ] **Step 1: Add failing source and browser contracts**

Extend `tests/obsidian-source-contract.test.mjs`:

```js
const graphInteractionSource = readFileSync(path.join(root, 'src', 'composables', 'useGraphInteraction.ts'), 'utf8');
for (const forceApi of ['forceSimulation', 'forceLink', 'forceManyBody', 'forceCollide', 'forceCenter']) {
  assert.ok(graphInteractionSource.includes(forceApi), `Expected graph physics to use ${forceApi}`);
}
assert.ok(graphInteractionSource.includes('requestAnimationFrame'), 'Expected graph positions to be frame-batched');
assert.ok(graphInteractionSource.includes('simulation.stop()'), 'Expected force timers to stop during teardown');
assert.ok(graphInteractionSource.includes('visibilitychange'), 'Expected hidden tabs to pause graph physics');
```

Create `tests/force-directed-graph.spec.ts`:

```ts
import { expect, test, type Locator } from '@playwright/test';

const coordinate = async (node: Locator) => ({
  x: Number(await node.locator('circle').getAttribute('cx')),
  y: Number(await node.locator('circle').getAttribute('cy')),
});

test('graph moves across frames and then settles', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  const node = page.locator('[data-node-id="node-doc-graph"]');
  await expect(node).toBeVisible();

  const first = await coordinate(node);
  await page.waitForTimeout(160);
  const second = await coordinate(node);
  expect(Math.hypot(second.x - first.x, second.y - first.y)).toBeGreaterThan(0.5);

  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });
  const settled = await coordinate(node);
  await page.waitForTimeout(250);
  const after = await coordinate(node);
  expect(Math.hypot(after.x - settled.x, after.y - settled.y)).toBeLessThan(0.2);
});
```

- [ ] **Step 2: Run the contracts and verify RED**

Run:

```powershell
cd app/mneme_frontend_v0.2.1
node tests/obsidian-source-contract.test.mjs
npx playwright test tests/force-directed-graph.spec.ts --project="Desktop Chrome" --workers=1
```

Expected: the source contract fails because D3 force APIs are absent, and the browser test fails because coordinates remain static and no `data-simulation-phase` exists.

- [ ] **Step 3: Replace static coordinates with simulation-node copies**

In `useGraphInteraction.ts`, import the D3 APIs and Vue lifecycle functions:

```ts
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3";
import { computed, onBeforeUnmount, ref, watch, type ComputedRef } from "vue";

type SimulationPhase = "idle" | "running" | "settled" | "reduced";
type SimulationGraphNode = GraphNodeData & SimulationNodeDatum & {
  x: number;
  y: number;
  fx: number | null;
  fy: number | null;
};
type SimulationGraphLink = SimulationLinkDatum<SimulationGraphNode> & GraphEdgeData;
```

Use one mutable simulation collection and a frame-batched publisher:

```ts
const simulationPhase = ref<SimulationPhase>("idle");
const publishedPositions = ref(new Map<string, { x: number; y: number }>());
let simulation: Simulation<SimulationGraphNode, SimulationGraphLink> | null = null;
let simulationNodes: SimulationGraphNode[] = [];
let frameId: number | null = null;

function publishPositions() {
  if (frameId !== null) return;
  frameId = window.requestAnimationFrame(() => {
    frameId = null;
    publishedPositions.value = new Map(
      simulationNodes.map((node) => [node.id, { x: node.x, y: node.y }]),
    );
  });
}

function stopSimulation() {
  simulation?.stop();
  simulation = null;
  if (frameId !== null) window.cancelAnimationFrame(frameId);
  frameId = null;
}
```

Pause an active simulation while the document is hidden and resume only if it was still converging:

```ts
let pausedForVisibility = false;

function handleVisibilityChange() {
  if (document.hidden) {
    pausedForVisibility = simulationPhase.value === "running";
    if (pausedForVisibility) simulation?.stop();
    return;
  }
  if (pausedForVisibility && simulation) {
    pausedForVisibility = false;
    simulation.restart();
  }
}

document.addEventListener("visibilitychange", handleVisibilityChange);
onBeforeUnmount(() => {
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  stopSimulation();
});
```

Create deterministic starting coordinates without mutating API nodes:

```ts
function startingPosition(node: GraphNodeData, index: number, total: number) {
  if (node.depth === 0) return { x: 380, y: 300 };
  const angle = (Math.PI * 2 * Math.max(index - 1, 0)) / Math.max(total - 1, 1) - Math.PI / 2;
  const radius = 135 + Math.min(node.depth, 3) * 42;
  return { x: 380 + Math.cos(angle) * radius, y: 340 + Math.sin(angle) * radius };
}
```

- [ ] **Step 4: Configure forces, convergence, and reduced motion**

Add a graph identity signature that excludes filters:

```ts
const graphSignature = computed(() => [
  ...nodes.value.map((node) => `n:${node.id}:${node.parent_id ?? ""}`),
  ...edges.value.map((edge) => `e:${edge.id}:${edge.source}:${edge.target}`),
].join("|"));
```

Rebuild the simulation from node and edge identities:

```ts
function rebuildSimulation() {
  stopSimulation();
  if (!nodes.value.length) {
    simulationNodes = [];
    publishedPositions.value = new Map();
    simulationPhase.value = "idle";
    return;
  }

  simulationNodes = nodes.value.map((node, index) => ({
    ...node,
    ...startingPosition(node, index, nodes.value.length),
    vx: 0,
    vy: 0,
    fx: null,
    fy: null,
  }));
  const links: SimulationGraphLink[] = edges.value.map((edge) => ({ ...edge, source: edge.source, target: edge.target }));
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  simulation = forceSimulation<SimulationGraphNode>(simulationNodes)
    .alpha(1)
    .alphaMin(0.015)
    .alphaDecay(0.045)
    .velocityDecay(0.36)
    .force("link", forceLink<SimulationGraphNode, SimulationGraphLink>(links).id((node) => node.id).distance(118).strength(0.42))
    .force("charge", forceManyBody<SimulationGraphNode>().strength((node) => node.depth === 0 ? -360 : -245).distanceMax(540))
    .force("collision", forceCollide<SimulationGraphNode>().radius((node) => node.depth === 0 ? 54 : 38).strength(0.9))
    .force("center", forceCenter(380, 340).strength(0.12))
    .force("x", forceX<SimulationGraphNode>(380).strength((node) => node.depth === 0 ? 0.1 : 0.025))
    .force("y", forceY<SimulationGraphNode>(340).strength((node) => node.depth === 0 ? 0.1 : 0.025))
    .on("tick", publishPositions)
    .on("end", () => {
      publishPositions();
      simulationPhase.value = "settled";
    });

  if (reducedMotion) {
    simulation.stop();
    for (let index = 0; index < 120; index += 1) simulation.tick();
    publishedPositions.value = new Map(simulationNodes.map((node) => [node.id, { x: node.x, y: node.y }]));
    simulationPhase.value = "reduced";
  } else {
    simulationPhase.value = "running";
  }
}

watch(graphSignature, rebuildSimulation, { immediate: true });
```

Make `positionedNodes` consume `publishedPositions`; retain current deterministic coordinates only as a pre-first-frame fallback. Keep `visibleNodes` and `visibleEdges` derived from filters so filter changes do not affect `graphSignature`.

- [ ] **Step 5: Expose phase in the rendered graph**

Return `simulationPhase` from `useGraphInteraction`. In `GraphView.vue`, add:

```vue
<section
  data-testid="graph-output-workspace"
  class="graph-canvas"
  :data-simulation-phase="interaction.simulationPhase.value"
>
```

- [ ] **Step 6: Run lifecycle tests and typecheck**

Run:

```powershell
node tests/obsidian-source-contract.test.mjs
npx playwright test tests/force-directed-graph.spec.ts --project="Desktop Chrome" --workers=1
npm run lint
```

Expected: source contract passes; the node moves, reaches `settled` within five seconds, remains stable, and TypeScript reports no errors.

- [ ] **Step 7: Commit the simulation lifecycle**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts app/mneme_frontend_v0.2.1/src/views/GraphView.vue app/mneme_frontend_v0.2.1/tests/force-directed-graph.spec.ts app/mneme_frontend_v0.2.1/tests/obsidian-source-contract.test.mjs
git commit -m "feat(frontend): add force-directed graph settling"
```

### Task 2: Integrate physical drag, restart, filtering, and reduced motion

**Files:**
- Modify: `app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts`
- Modify: `app/mneme_frontend_v0.2.1/src/views/GraphView.vue`
- Modify: `app/mneme_frontend_v0.2.1/tests/force-directed-graph.spec.ts`
- Modify: `app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts`

**Interfaces:**
- Consumes: Task 1's single D3 simulation and `simulationPhase`.
- Produces: `startDrag(nodeId)`, `dragNode(nodeId, x, y)`, `endDrag(nodeId)`, and reheating `restartLayout()` methods.

- [ ] **Step 1: Add failing drag, restart, filter-stability, and reduced-motion tests**

Append to `tests/force-directed-graph.spec.ts`:

```ts
test('drag reheats the graph and release allows it to settle', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });
  const node = page.locator('[data-node-id="node-doc-graph"]');
  const box = await node.boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width / 2 + 70, box!.y + box!.height / 2 + 35, { steps: 5 });
  await expect(graph).toHaveAttribute('data-simulation-phase', 'running');
  await page.mouse.up();
  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });
});

test('filters preserve settled positions and restart reheats', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  const node = page.locator('[data-node-id="node-doc-graph"]');
  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });
  const before = await coordinate(node);
  await page.getByRole('button', { name: 'Tags' }).click();
  await page.getByRole('button', { name: 'All Nodes' }).click();
  expect(await coordinate(node)).toEqual(before);
  await page.getByRole('button', { name: 'Restart graph layout' }).click();
  await expect(graph).toHaveAttribute('data-simulation-phase', 'running');
  await page.waitForTimeout(160);
  expect(await coordinate(node)).not.toEqual(before);
  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });
});

test('reduced motion publishes one stable layout without animation', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  const node = page.locator('[data-node-id="node-doc-graph"]');
  await expect(graph).toHaveAttribute('data-simulation-phase', 'reduced');
  const before = await coordinate(node);
  await page.waitForTimeout(300);
  expect(await coordinate(node)).toEqual(before);
});
```

- [ ] **Step 2: Run the new tests and verify RED**

```powershell
npx playwright test tests/force-directed-graph.spec.ts --project="Desktop Chrome" --workers=1
```

Expected: drag does not set D3 fixation or reheat alpha, restart does not expose a running phase, and reduced-motion phase is absent until implemented.

- [ ] **Step 3: Implement D3 drag fixation and release**

In `useGraphInteraction.ts`:

```ts
function simulationNode(nodeId: string) {
  return simulationNodes.find((node) => node.id === nodeId) ?? null;
}

function startDrag(nodeId: string) {
  const node = simulationNode(nodeId);
  if (!node || !simulation) return;
  node.fx = node.x;
  node.fy = node.y;
  simulation.alphaTarget(0.22).restart();
  simulationPhase.value = "running";
}

function dragNode(nodeId: string, x: number, y: number) {
  const node = simulationNode(nodeId);
  if (!node) return;
  node.fx = x;
  node.fy = y;
  node.x = x;
  node.y = y;
  publishPositions();
}

function endDrag(nodeId: string) {
  const node = simulationNode(nodeId);
  if (!node || !simulation) return;
  node.fx = null;
  node.fy = null;
  simulation.alphaTarget(0).alpha(Math.max(simulation.alpha(), 0.32)).restart();
  simulationPhase.value = "running";
}
```

Return all three methods. Remove the old position-override map because D3 positions are now the only mutable coordinate source.

- [ ] **Step 4: Connect pointer capture and cancellation in GraphView**

Update the existing pointer handlers:

```ts
function startGraphNodeDrag(node: GraphNodeData, event: PointerEvent) {
  event.stopPropagation();
  dragState = { nodeId: node.id, pointerId: event.pointerId };
  (event.currentTarget as SVGGElement).setPointerCapture(event.pointerId);
  interaction.startDrag(node.id);
  void selectGraphNode(node);
}

function endGraphNodeDrag(event?: PointerEvent) {
  if (!dragState || (event && event.pointerId !== dragState.pointerId)) return;
  interaction.endDrag(dragState.nodeId);
  dragState = null;
}
```

Add `@pointercancel="endGraphNodeDrag"` to the graph SVG. `moveGraphNodeDrag` continues to translate screen coordinates into SVG coordinates, but now calls the D3-backed `dragNode`.

- [ ] **Step 5: Reheat with deterministic restart jitter**

Replace `restartLayout()` in `useGraphInteraction.ts`:

```ts
function restartLayout() {
  if (!simulation) return;
  layoutSeed.value += 1;
  simulationNodes.forEach((node, index) => {
    node.fx = null;
    node.fy = null;
    if (node.depth === 0) return;
    const angle = (index + 1) * 1.618 + layoutSeed.value * 0.43;
    node.x += Math.cos(angle) * 26;
    node.y += Math.sin(angle) * 26;
    node.vx = 0;
    node.vy = 0;
  });
  simulation.alphaTarget(0).alpha(1).restart();
  simulationPhase.value = "running";
  publishPositions();
}
```

Keep GraphView's current `centerGraph()` call so restart resets zoom as well as physics.

- [ ] **Step 6: Run focused graph tests on desktop and mobile**

```powershell
npx playwright test tests/force-directed-graph.spec.ts tests/preview-mode.spec.ts -g "graph|force|motion|drag|filter|rail" --project="Desktop Chrome" --project="Mobile Chrome" --workers=2
npm run lint
```

Expected: all force, drag, restart, reduced-motion, preview, filter, and rail tests pass on both projects.

- [ ] **Step 7: Commit physical interactions**

```powershell
git add app/mneme_frontend_v0.2.1/src/composables/useGraphInteraction.ts app/mneme_frontend_v0.2.1/src/views/GraphView.vue app/mneme_frontend_v0.2.1/tests/force-directed-graph.spec.ts app/mneme_frontend_v0.2.1/tests/preview-mode.spec.ts
git commit -m "feat(frontend): add physical graph drag and restart"
```

### Task 3: Full validation, push, deployment, and production acceptance

**Files:**
- No new source files.
- Deploy source to: `/root/project/Reminder`
- Preserve environment backup: `/root/reminder-env-before-force-graph-20260711`

**Interfaces:**
- Consumes: Tasks 1 and 2 plus the existing `codex/frontend-reliability` branch and `mneme_*` Compose volumes.
- Produces: pushed commits and a verified force-directed graph at `https://www.mneme.com.cn`.

- [ ] **Step 1: Run all local source and backend contracts**

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall -q app/mneme alembic main.py
cd app/mneme_frontend_v0.2.1
Get-ChildItem tests -Filter '*.test.mjs' | Sort-Object Name | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: 71 backend tests plus subtests pass, compilation exits 0, and all source contracts exit 0.

- [ ] **Step 2: Run the complete frontend validation**

```powershell
npm ci --no-audit --no-fund
npm run lint
npm run build
npx playwright test --project="Desktop Chrome" --project="Mobile Chrome" --workers=2
```

Expected: clean install, typecheck, hashed production build, and the complete desktop/mobile Playwright suite all exit 0.

- [ ] **Step 3: Inspect motion in a real browser**

At 1440x900 and 390x844, open `/?preview=1` and verify:

- Entry motion is visible but settles within five seconds.
- Labels remain legible and nodes do not form a single overlapping pile.
- Dragging causes connected nodes to respond.
- Release and Restart Graph Layout each create a new settling pass.
- Filters preserve positions of nodes that remain visible.
- Reduced-motion emulation produces a stable, non-animated graph.

- [ ] **Step 4: Commit final test-only corrections and push**

```powershell
git status --short
git diff --check
git push origin codex/frontend-reliability
```

Expected: the working tree is clean and upstream resolves to the same commit as HEAD.

- [ ] **Step 5: Back up production and verify named volumes**

On the server:

```bash
cd /root/project/Reminder
cp .env /root/reminder-env-before-force-graph-20260711
docker volume ls --format '{{.Name}}' | grep '^mneme_' | sort
```

Expected: `mneme_postgres_data`, `mneme_redis_data`, `mneme_neo4j_data`, and existing optional-stack volumes remain present. Do not run `docker compose down -v`.

- [ ] **Step 6: Deploy and rebuild without deleting data**

Upload a `git archive` of the verified HEAD into `/root/project/Reminder`, preserve `.env`, then run:

```bash
cd /root/project/Reminder
COMPOSE_PROJECT_NAME=mneme docker compose config -q
COMPOSE_PROJECT_NAME=mneme docker compose up -d --build
COMPOSE_PROJECT_NAME=mneme docker compose ps -a
```

Expected: migration exits 0, app/Neo4j/PostgreSQL/Redis are healthy, and worker remains running.

- [ ] **Step 7: Verify production motion and logs**

Use headless Chrome against `https://www.mneme.com.cn/?preview=1` and assert the same coordinate movement, convergence, drag, restart, filter stability, and reduced-motion behaviors from local tests. Then run:

```bash
cd /root/project/Reminder
curl -fsS https://www.mneme.com.cn/health
logs="$(COMPOSE_PROJECT_NAME=mneme docker compose logs --since=10m app worker 2>&1)"
test "$(printf '%s' "$logs" | grep -c 'Traceback' || true)" = 0
test "$(printf '%s' "$logs" | grep -c 'Internal Server Error' || true)" = 0
```

Expected: health returns code 0, the deployed graph visibly settles, and log error counts remain zero.
