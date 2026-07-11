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
