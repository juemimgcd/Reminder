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
