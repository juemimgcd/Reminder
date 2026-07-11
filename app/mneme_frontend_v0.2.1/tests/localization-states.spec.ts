import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'domcontentloaded' });
});

test('Chinese locale updates navigation and graph tools without losing the active workspace', async ({ page }) => {
  await page.getByRole('button', { name: 'System Settings' }).click();
  await page.getByRole('button', { name: '简体中文' }).click();

  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN');
  await page.getByRole('button', { name: '知识图谱' }).click();
  await expect(page.getByPlaceholder('搜索知识库…')).toBeVisible();
  await expect(page.getByTestId('stitch-graph-layout')).toBeVisible();

  await page.getByRole('button', { name: '研究库' }).click();
  await expect(page.getByText('上传文件', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'AI 实验室' }).click();
  await expect(page.getByPlaceholder('向 Mneme 提问…')).toBeVisible();

  await page.getByRole('button', { name: '语义地图' }).click();
  await expect(page.getByText('捕捉资料、连接想法，并随时回到重要的工作。')).toBeVisible();
});

test('English locale can be restored immediately', async ({ page }) => {
  await page.getByRole('button', { name: 'System Settings' }).click();
  await page.getByRole('button', { name: '简体中文' }).click();
  await page.getByRole('button', { name: '设置' }).click();
  await page.getByRole('button', { name: 'English' }).click();

  await expect(page.locator('html')).toHaveAttribute('lang', 'en-US');
  await expect(page.getByRole('button', { name: 'Knowledge Graph' })).toBeVisible();
});
