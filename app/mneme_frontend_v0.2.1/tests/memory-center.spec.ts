import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /Memory Center|Memory \(/ }).click();
  await expect(page.locator('.memory-center > header h1')).toContainText('Memory Center');
});

test('memory workflows are reachable without hover at desktop and mobile sizes', async ({ page }, testInfo) => {
  await expect(page.getByText('Automatically learn from conversations')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Clear this knowledge base' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Clear all my memory' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Pending review/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();

  const memory = page.getByRole('button', { name: /user prefers/ }).first();
  await expect(memory).toBeVisible();
  await memory.click();
  await expect(page.getByRole('heading', { name: 'Revision history' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Evidence' })).toBeVisible();
  await expect(page.getByText('Atomic notes are easier to reuse.')).toBeVisible();
  for (const name of ['Save revision', 'Invalidate', 'Hard delete', 'Clear this source']) {
    await expect(page.getByRole('button', { name })).toBeVisible();
  }

  const viewport = page.viewportSize();
  const action = page.getByRole('button', { name: 'Hard delete' });
  const box = await action.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual((viewport?.width ?? 0) + 1);

  if (testInfo.project.name === 'Desktop Chrome') {
    const toggle = page.getByRole('checkbox', { name: 'Automatically learn from conversations' });
    await toggle.check();
    await expect(toggle).toBeChecked();
    await page.getByLabel('Memory value').fill('Deterministic revised value');
    await page.getByRole('button', { name: 'Save revision' }).click();
    await expect(page.getByLabel('Memory value')).toHaveValue('Deterministic revised value');
  }
});
