import { expect, test } from '@playwright/test';

const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'compact-desktop', width: 1024, height: 768 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
];

for (const viewport of viewports) {
  test(`settings layout remains aligned at ${viewport.width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.addInitScript(() => window.localStorage.setItem('mneme.locale', 'zh-CN'));
    await page.goto('/?preview=1');

    if (viewport.width === 1440) {
      await page.getByRole('button', { name: '使用文档' }).click();
    }
    await page.getByRole('button', { name: '设置', exact: true }).click();
    await expect(page.getByTestId('stitch-settings-layout')).toBeVisible();

    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await expect(page.getByRole('heading', { name: '设置', exact: true })).toHaveCount(1);

    const topbar = await page.getByTestId('sanctuary-topbar').boundingBox();
    const firstCard = await page.getByTestId('stitch-settings-layout').locator('article').first().boundingBox();
    expect(topbar).not.toBeNull();
    expect(firstCard).not.toBeNull();
    expect(firstCard!.y).toBeGreaterThanOrEqual(topbar!.y + topbar!.height - 1);

    const banner = page.locator('.workspace-banner').first();
    if (await banner.count()) {
      const bannerBox = await banner.boundingBox();
      expect(bannerBox).not.toBeNull();
      expect(firstCard!.y).toBeGreaterThanOrEqual(bannerBox!.y + bannerBox!.height - 1);
    }

    if (viewport.width >= 1024) {
      const main = page.locator('.mneme-shell__main');
      const expandedMain = await main.boundingBox();
      await page.getByRole('button', { name: 'Toggle resources' }).click();
      await expect(page.getByTestId('resource-sidebar')).toBeHidden();
      const collapsedMain = await main.boundingBox();
      expect(collapsedMain!.width).toBeGreaterThan(expandedMain!.width);
    }

    await page.screenshot({ path: testInfo.outputPath(`settings-${viewport.name}.png`), fullPage: true });
  });
}

test('document workspace keeps the reader primary across desktop, tablet, and mobile', async ({ page }) => {
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1024, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/?preview=1');
    await page.getByRole('button', { name: 'Research Vault', exact: true }).click();
    await page.getByTestId('document-tree').getByRole('button', { name: 'zettelkasten-principles.md', exact: true }).click();
    await expect(page.getByTestId('document-reader')).toBeVisible();
    const columns = await page.getByTestId('document-workspace').evaluate((element) => getComputedStyle(element).gridTemplateColumns);
    if (viewport.width === 1440) expect(columns.split(' ')).toHaveLength(3);
    else expect(columns.split(' ')).toHaveLength(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    await page.screenshot({ path: `../../.tmp/document-workspace-visual/reader-${viewport.width}x${viewport.height}.png` });
  }
});
