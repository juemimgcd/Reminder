import { expect, test } from '@playwright/test';

test('desktop exposes the activity bar and resource sidebar', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/?preview=1');

  await expect(page.getByTestId('activity-bar')).toBeVisible();
  await expect(page.getByTestId('resource-sidebar')).toBeVisible();
  await expect(page.getByTestId('mobile-navigation')).toBeHidden();
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
