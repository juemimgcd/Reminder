import { expect, test } from '@playwright/test';

test('desktop exposes the activity bar and resource sidebar', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/?preview=1');

  await expect(page.getByTestId('activity-bar')).toBeVisible();
  await expect(page.getByTestId('resource-sidebar')).toBeVisible();
  await expect(page.getByTestId('mobile-navigation')).toBeHidden();
});

test('tablet keeps activity navigation and starts with the resource drawer closed', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 1100 });
  await page.goto('/?preview=1');

  await expect(page.getByTestId('activity-bar')).toBeVisible();
  await expect(page.getByTestId('mobile-navigation')).toBeHidden();
  await expect(page.getByTestId('resource-sidebar')).not.toHaveClass(/resource-sidebar--open/);

  await page.getByTestId('activity-bar').getByRole('button', { name: 'Research Vault' }).click();
  await expect(page.getByTestId('document-workspace')).toBeVisible();
  const statusBarBox = await page.locator('.status-bar').boundingBox();
  expect(statusBarBox).not.toBeNull();
  expect(statusBarBox!.y + statusBarBox!.height).toBeGreaterThan(1090);
});

test('mobile uses bottom navigation without horizontal page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/?preview=1');

  await expect(page.getByTestId('mobile-navigation')).toBeVisible();
  await expect(page.getByTestId('activity-bar')).toBeHidden();
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});

test('mobile graph canvas occupies the first workspace screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/?preview=1');

  await expect(page.getByTestId('graph-file-rail')).toBeHidden();
  const graphBox = await page.getByTestId('graph-output-workspace').boundingBox();
  expect(graphBox).not.toBeNull();
  expect(graphBox!.y).toBeLessThan(16);
  expect(graphBox!.width).toBeLessThanOrEqual(390);
  await expect(page.getByPlaceholder('Search knowledge base...')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Restart graph layout' })).toBeInViewport();
});
