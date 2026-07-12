import { expect, test, type Locator } from '@playwright/test';
import { createGraphSignature } from '../src/composables/useGraphInteraction';

const coordinate = async (node: Locator) => ({
  x: Number(await node.locator('circle').getAttribute('cx')),
  y: Number(await node.locator('circle').getAttribute('cy')),
});

test('graph identity signature ignores node and edge order', () => {
  const nodes = [
    { id: 'root|child', parent_id: null },
    { id: 'child', parent_id: 'root|child' },
  ];
  const edges = [
    { id: 'edge:2', source: 'root|child', target: 'child' },
    { id: 'edge:1', source: 'child', target: 'root|child' },
  ];

  expect(createGraphSignature(nodes, edges)).toBe(
    createGraphSignature([...nodes].reverse(), [...edges].reverse()),
  );
  expect(createGraphSignature(
    [{ id: 'a:b', parent_id: 'c' }],
    [{ id: 'edge', source: 'a', target: 'b:c' }],
  )).not.toBe(createGraphSignature(
    [{ id: 'a', parent_id: 'b:c' }],
    [{ id: 'edge', source: 'a:b', target: 'c' }],
  ));
});

test('graph labels are deterministic and expand with zoom', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const visibleLabels = page.locator('[data-testid="force-node"][data-label-visible="true"]');
  await expect(visibleLabels).toHaveCount(4);
  await expect(page.locator('[data-node-id="node-kb-demo"]')).toHaveAttribute('data-label-visible', 'true');

  await page.getByRole('button', { name: 'Zoom in graph' }).click();
  await page.getByRole('button', { name: 'Zoom in graph' }).click();
  await page.getByRole('button', { name: 'Zoom in graph' }).click();
  await expect(visibleLabels).toHaveCount(6);
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

test('hidden graph rebuild stays paused until the page is visible', async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  const node = page.locator('[data-node-id="node-doc-graph"]');
  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });

  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.getByRole('button', { name: 'Restart graph layout' }).click();
  await expect(graph).toHaveAttribute('data-simulation-phase', 'running');
  const hiddenStart = await coordinate(node);
  await page.waitForTimeout(200);
  const hiddenEnd = await coordinate(node);
  expect(Math.hypot(hiddenEnd.x - hiddenStart.x, hiddenEnd.y - hiddenStart.y)).toBeLessThan(0.2);

  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.waitForTimeout(160);
  const resumed = await coordinate(node);
  expect(Math.hypot(resumed.x - hiddenEnd.x, resumed.y - hiddenEnd.y)).toBeGreaterThan(0.5);
  await expect(graph).toHaveAttribute('data-simulation-phase', 'settled', { timeout: 5000 });
});

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

test('reduced motion keeps restart and drag release synchronous and stable', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  const node = page.locator('[data-node-id="node-doc-graph"]');
  await expect(graph).toHaveAttribute('data-simulation-phase', 'reduced');
  const before = await coordinate(node);
  await page.waitForTimeout(300);
  expect(await coordinate(node)).toEqual(before);

  await page.getByRole('button', { name: 'Restart graph layout' }).click();
  await expect(graph).toHaveAttribute('data-simulation-phase', 'reduced');
  const restarted = await coordinate(node);
  expect(restarted).not.toEqual(before);
  await page.waitForTimeout(300);
  expect(await coordinate(node)).toEqual(restarted);

  const box = await node.boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width / 2 + 55, box!.y + box!.height / 2 + 28, { steps: 4 });
  await expect(graph).toHaveAttribute('data-simulation-phase', 'reduced');
  await page.mouse.up();
  await expect(graph).toHaveAttribute('data-simulation-phase', 'reduced');
  const released = await coordinate(node);
  await page.waitForTimeout(300);
  expect(await coordinate(node)).toEqual(released);
});
