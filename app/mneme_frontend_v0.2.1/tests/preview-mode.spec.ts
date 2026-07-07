import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.clear();
  });
});

test('preview mode opens the populated workbench without a backend login', async ({ page }) => {
  await page.goto('/?preview=1');

  const sidebar = page.locator('aside');

  await expect(sidebar.getByRole('button', { name: /Demo Research Vault/ })).toBeVisible();
  await expect(sidebar.getByText('mneme.preview', { exact: true })).toBeVisible();
  await expect(page.getByText('Backend endpoint')).not.toBeVisible();
});

test('preview workbench uses the Sanctuary wide layout instead of a rail dashboard', async ({ page }) => {
  await page.goto('/?preview=1');

  const shell = page.getByTestId('obsidian-shell');
  const sidebar = page.getByTestId('sanctuary-sidebar');
  const topbar = page.getByTestId('sanctuary-topbar');
  const editorPane = page.getByTestId('obsidian-editor-pane');

  await expect(shell).toBeVisible();
  await expect(sidebar).toBeVisible();
  await expect(topbar).toBeHidden();
  await expect(editorPane).toBeVisible();
  await expect(sidebar).toContainText('Mneme Intelligence');
  await expect(sidebar).toContainText('Cognitive Sanctuary');
  await expect(sidebar.getByRole('button', { name: 'Knowledge Graph', exact: true })).toBeVisible();
  await expect(page.getByTestId('stitch-graph-layout')).toBeVisible();

  await expect(editorPane.getByText('Vaults', { exact: true })).not.toBeVisible();
  await expect(editorPane.getByText('Files', { exact: true })).toBeVisible();
  await expect(editorPane.getByText('Tasks', { exact: true })).not.toBeVisible();

  await expect(shell).toHaveCSS('background-color', 'rgb(9, 9, 11)');
  await expect(sidebar).toHaveCSS('width', '256px');
  await expect(sidebar.getByRole('button', { name: 'Research Vault', exact: true })).toBeVisible();
  await expect(sidebar.getByRole('button', { name: 'AI Laboratory', exact: true })).toBeVisible();
  await expect(sidebar.getByRole('button', { name: 'System Settings', exact: true })).toBeVisible();
});

test('knowledge graph file rail can collapse and expand from the canvas handle', async ({ page }) => {
  await page.goto('/?preview=1');

  const rail = page.getByTestId('graph-file-rail');
  const toggle = page.getByTestId('graph-file-rail-toggle');

  await expect(page.getByTestId('stitch-graph-layout')).toBeVisible();
  await expect(rail).toBeVisible();

  await toggle.click();
  await expect(rail).toBeHidden();
  await expect(toggle).toHaveAttribute('title', 'Expand file list');

  await toggle.click();
  await expect(rail).toBeVisible();
  await expect(toggle).toHaveAttribute('title', 'Collapse file list');
});

test('knowledge graph document panel appears only while long-pressing a node', async ({ page }) => {
  await page.goto('/?preview=1');

  await expect(page.getByText('Properties', { exact: true })).toBeHidden();

  const node = page.getByTestId('force-node').first();
  await expect(node).toBeVisible();
  await node.scrollIntoViewIfNeeded();
  const box = await node.boundingBox();
  expect(box).not.toBeNull();

  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(650);

  const panel = page.getByTestId('graph-document-preview-panel');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('Properties');

  await page.mouse.up();
  await expect(panel).toBeHidden();
});
