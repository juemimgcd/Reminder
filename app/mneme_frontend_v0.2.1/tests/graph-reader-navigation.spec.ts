import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
});

test('graph focus keeps one-hop neighbors visible and canvas clears focus', async ({ page }) => {
  const selected = page.locator('[data-node-id="node-doc-zettel"]');
  await selected.click();

  await expect(selected).toHaveAttribute('data-focus-state', 'selected');
  await expect(page.locator('[data-node-id="node-memory-atomic"]')).toHaveAttribute('data-focus-state', 'neighbor');
  await expect(page.locator('[data-node-id="node-doc-graph"]')).toHaveAttribute('data-focus-state', 'dimmed');

  const canvas = page.locator('svg[aria-label="Knowledge graph"]');
  const box = await canvas.boundingBox();
  await page.mouse.click(box!.x + box!.width - 20, box!.y + box!.height - 20);
  await expect(selected).toHaveAttribute('data-focus-state', 'normal');
});

test('pending single-click intent is cancelled by canvas clear and filters', async ({ page }) => {
  const node = page.locator('[data-node-id="node-doc-zettel"]');
  await node.dispatchEvent('pointerdown', { pointerId: 31, clientX: 500, clientY: 400 });
  const canvas = page.locator('svg[aria-label="Knowledge graph"]');
  await canvas.dispatchEvent('pointerdown', { pointerId: 32 });
  await page.waitForTimeout(320);
  await expect(page.getByTestId('graph-document-preview-panel')).toHaveCount(0);

  await node.dispatchEvent('pointerdown', { pointerId: 33, clientX: 500, clientY: 400 });
  await page.getByRole('button', { name: 'Tags' }).dispatchEvent('click');
  await page.waitForTimeout(320);
  await expect(page.getByTestId('graph-document-preview-panel')).toHaveCount(0);
});

test('pending single-click intent is cancelled on view unmount', async ({ page }) => {
  await page.locator('[data-node-id="node-doc-zettel"]').dispatchEvent('pointerdown', { pointerId: 41, clientX: 500, clientY: 400 });
  const desktopVault = page.getByTestId('activity-bar').getByRole('button', { name: 'Research Vault' });
  const vaultButton = await desktopVault.isVisible()
    ? desktopVault
    : page.getByTestId('mobile-navigation').getByRole('button', { name: 'Research Vault' });
  await vaultButton.click();
  await page.waitForTimeout(320);
  await expect(page.getByTestId('graph-document-preview-panel')).toHaveCount(0);
});

test('late preview responses cannot overwrite the newer graph selection', async ({ page }) => {
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule('/src/lib/api.ts');
    const original = api.documentPreview.bind(api);
    api.documentPreview = async (token: string, documentId: string) => {
      if (documentId === 'doc-zettelkasten') await new Promise((resolve) => window.setTimeout(resolve, 650));
      return original(token, documentId);
    };
  });
  await page.locator('[data-node-id="node-doc-zettel"]').click();
  await page.waitForTimeout(280);
  await page.locator('[data-node-id="node-doc-graph"]').click();
  await expect(page.getByTestId('graph-document-preview-panel')).toContainText('memory-graph-design.pdf');
  await page.waitForTimeout(700);
  await expect(page.getByTestId('graph-document-preview-panel')).toContainText('memory-graph-design.pdf');
  await expect(page.getByTestId('graph-document-preview-panel')).not.toContainText('zettelkasten-principles.md');
});

test('a newer graph selection owns the delayed preview intent', async ({ page }) => {
  await page.locator('[data-node-id="node-doc-zettel"]').dispatchEvent('pointerdown', { pointerId: 51, clientX: 500, clientY: 400 });
  await page.locator('[data-node-id="node-doc-graph"]').dispatchEvent('pointerdown', { pointerId: 52, clientX: 650, clientY: 400 });
  await expect(page.getByTestId('graph-document-preview-panel')).toContainText('memory-graph-design.pdf');
  await expect(page.getByTestId('graph-document-preview-panel')).not.toContainText('zettelkasten-principles.md');
});

test('double-click opens a document by entity id in the unified reader', async ({ page }) => {
  await expect(page.getByTestId('graph-output-workspace')).toHaveAttribute('data-simulation-phase', 'settled');
  await page.locator('[data-node-id="node-doc-graph"] circle').dblclick();
  await expect(page.getByTestId('document-reader-title')).toContainText('memory-graph-design.pdf');
});

test('Enter opens while Space only selects the graph document', async ({ page }) => {
  const node = page.locator('[data-node-id="node-doc-zettel"]');
  await node.focus();
  await node.press('Space');
  await expect(node).toHaveAttribute('data-focus-state', 'selected');
  await expect(page.getByTestId('document-reader-title')).toHaveCount(0);

  await node.press('Enter');
  await expect(page.getByTestId('document-reader-title')).toContainText('zettelkasten-principles.md');
});

test('Read full and graph file rail use the same document reader path', async ({ page }) => {
  await page.locator('[data-node-id="node-doc-zettel"]').click();
  await page.getByRole('link', { name: /Read full note|阅读全文/ }).click();
  await expect(page.getByTestId('document-reader-title')).toContainText('zettelkasten-principles.md');

  await page.getByRole('button', { name: /Knowledge Graph|知识图谱/ }).click();
  const rail = page.getByTestId('graph-file-rail');
  if (await rail.isHidden()) await page.getByTestId('graph-file-rail-toggle').click();
  await rail.getByRole('button', { name: 'memory-graph-design.pdf' }).click();
  await expect(page.getByTestId('document-reader-title')).toContainText('memory-graph-design.pdf');
});

test('dragging a document node never opens the reader or converts into a double-open', async ({ page }) => {
  const node = page.locator('[data-node-id="node-doc-graph"]');
  const box = await node.boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width / 2 + 70, box!.y + box!.height / 2 + 35, { steps: 5 });
  await page.mouse.up();
  await node.dispatchEvent('dblclick');
  await expect(page.getByTestId('document-reader-title')).toHaveCount(0);
});

test('mobile and reduced-motion graph retain focus and finite layout behavior', async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.reload({ waitUntil: 'domcontentloaded' });
  const graph = page.getByTestId('graph-output-workspace');
  await expect(graph).toHaveAttribute('data-simulation-phase', 'reduced');
  await page.locator('[data-node-id="node-doc-zettel"]').click();
  await expect(page.locator('[data-node-id="node-memory-atomic"]')).toHaveAttribute('data-focus-state', 'neighbor');
  if (testInfo.project.name === 'Mobile Chrome') {
    await expect(page.getByTestId('graph-file-rail')).toBeHidden();
  }
});
