import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/?preview=1');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole('button', { name: 'System Settings' }).click();
});

test('theme preference persists across reloads', async ({ page }) => {
  await page.getByRole('button', { name: 'Light theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');

  await page.reload();

  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

test('locale preference persists across reloads', async ({ page }) => {
  await page.getByRole('button', { name: '简体中文' }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');

  await page.reload();

  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
});
