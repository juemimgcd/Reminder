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

test('knowledge graph document panel stays open after long-pressing a node', async ({ page }) => {
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
  await expect(panel).toBeVisible();
  await expect(panel.getByRole('link', { name: /Read full note/ })).toBeVisible();

  await panel.getByRole('button', { name: 'Close preview' }).click();
  await expect(panel).toBeHidden();
});

test('ai chat history rail can collapse and expand from the chat handle', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();
  const viewport = page.viewportSize();

  const layout = page.getByTestId('stitch-ai-laboratory-layout');
  const rail = page.getByTestId('ai-history-rail');
  const chat = page.getByTestId('chat-function-grid');
  const toggle = page.getByTestId('ai-history-rail-toggle');

  await expect(layout).toBeVisible();
  await expect(rail).toBeVisible();
  const expandedChatBox = await chat.boundingBox();
  expect(expandedChatBox).not.toBeNull();

  await toggle.click();
  await expect(rail).toBeHidden();
  await expect(toggle).toHaveAttribute('title', 'Expand chat history');
  const collapsedChatBox = await chat.boundingBox();
  expect(collapsedChatBox).not.toBeNull();
  if ((viewport?.width ?? 0) >= 1024) {
    expect(collapsedChatBox!.width).toBeGreaterThan(expandedChatBox!.width);
  }

  await toggle.click();
  await expect(rail).toBeVisible();
  await expect(toggle).toHaveAttribute('title', 'Collapse chat history');
});

test('ai laboratory renders API-backed sessions and appends sent messages', async ({ page }) => {
  await page.goto('/?preview=1');
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();

  await expect(page.getByTestId('ai-history-rail')).toContainText('Preview Vault Review');
  await expect(page.getByTestId('chat-function-grid')).toContainText('How should I review this vault?');
  await expect(page.getByTestId('chat-function-grid')).toContainText('Start with the indexed documents');

  const composer = page.getByPlaceholder('Message Cognitive Sanctuary... (/ for commands, @ for nodes)');
  await composer.fill('Summarize the graph contradictions');
  await page.getByTestId('workspace-chat-command').getByRole('button').click();

  await expect(page.getByTestId('chat-function-grid')).toContainText('Summarize the graph contradictions');
  await expect(page.getByTestId('chat-function-grid')).toContainText('Preview answer for: Summarize the graph contradictions');

  await page.getByRole('button', { name: 'System Settings', exact: true }).click();
  await expect(page.getByTestId('stitch-settings-layout')).toContainText('Preview DeepSeek');
});
