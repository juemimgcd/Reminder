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
