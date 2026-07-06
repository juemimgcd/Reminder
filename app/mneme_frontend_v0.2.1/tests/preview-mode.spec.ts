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

test('preview workbench uses an Obsidian-inspired shell instead of a card dashboard', async ({ page }) => {
  await page.goto('/?preview=1');

  const shell = page.getByTestId('obsidian-shell');
  const rail = page.getByTestId('obsidian-rail');
  const explorer = page.getByTestId('obsidian-explorer');
  const editorPane = page.getByTestId('obsidian-editor-pane');
  const tab = page.getByTestId('obsidian-active-tab');

  await expect(shell).toBeVisible();
  await expect(rail).toBeVisible();
  await expect(explorer).toBeVisible();
  await expect(editorPane).toBeVisible();
  await expect(tab).toContainText('Workspace');

  await expect(editorPane.getByText('Vaults', { exact: true })).not.toBeVisible();
  await expect(editorPane.getByText('Files', { exact: true })).not.toBeVisible();
  await expect(editorPane.getByText('Tasks', { exact: true })).not.toBeVisible();

  await expect(shell).toHaveCSS('background-color', 'rgb(25, 25, 25)');
  await expect(rail).toHaveCSS('width', '44px');
});
