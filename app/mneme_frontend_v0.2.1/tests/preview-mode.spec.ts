import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.clear();
  });
});

test('preview mode opens the populated workbench without a backend login', async ({ page }) => {
  await page.goto('/?preview=1');

  const sidebar = page.locator('aside');

  await expect(sidebar.getByText('Preview', { exact: true })).toBeVisible();
  await expect(sidebar.getByRole('button', { name: /Demo Research Vault/ })).toBeVisible();
  await expect(sidebar.getByText('mneme.preview', { exact: true })).toBeVisible();
  await expect(page.getByText('Backend endpoint')).not.toBeVisible();
});