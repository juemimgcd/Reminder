import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.clear();
  });
});

async function openPreview(page: { goto: (url: string, options: { waitUntil: 'domcontentloaded' }) => Promise<unknown> }) {
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
}

test('preview mode opens the populated workbench without a backend login', async ({ page }) => {
  await openPreview(page);

  const sidebar = page.locator('aside');

  await expect(sidebar.getByRole('button', { name: /Demo Research Vault/ })).toBeVisible();
  await expect(sidebar.getByText('mneme.preview', { exact: true })).toBeVisible();
  await expect(page.getByText('Backend endpoint')).not.toBeVisible();
});

test('preview workbench uses the Sanctuary wide layout instead of a rail dashboard', async ({ page }) => {
  await openPreview(page);

  const shell = page.getByTestId('obsidian-shell');
  const sidebar = page.getByTestId('sanctuary-sidebar');
  const resourceSidebar = page.getByTestId('resource-sidebar');
  const activityBar = page.getByTestId('activity-bar');
  const mobileNavigation = page.getByTestId('mobile-navigation');
  const topbar = page.getByTestId('sanctuary-topbar');
  const editorPane = page.getByTestId('obsidian-editor-pane');
  const viewport = page.viewportSize();

  await expect(shell).toBeVisible();
  await expect(topbar).toBeHidden();
  await expect(editorPane).toBeVisible();
  await expect(sidebar.getByRole('heading', { name: 'Mneme', exact: true })).toBeVisible();
  await expect(sidebar).toContainText('Cognitive Sanctuary');
  await expect(page.getByTestId('stitch-graph-layout')).toBeVisible();

  await expect(editorPane.getByText('Vaults', { exact: true })).not.toBeVisible();
  if (viewport && viewport.width < 1024) {
    await expect(editorPane.getByText('Files', { exact: true })).toBeHidden();
  } else {
    await expect(editorPane.getByText('Files', { exact: true })).toBeVisible();
  }
  await expect(editorPane.getByText('Tasks', { exact: true })).not.toBeVisible();

  await expect(page.locator('html')).toHaveAttribute('data-theme', /light|dark/);
  await expect(shell).not.toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  if (viewport && viewport.width < 768) {
    await expect(activityBar).toBeHidden();
    await expect(mobileNavigation).toBeVisible();
  } else {
    await expect(activityBar).toBeVisible();
    await expect(resourceSidebar).toHaveCSS('width', '256px');
    await expect(activityBar.getByRole('button', { name: 'Research Vault', exact: true })).toBeVisible();
    await expect(activityBar.getByRole('button', { name: 'AI Laboratory', exact: true })).toBeVisible();
    await expect(activityBar.getByRole('button', { name: 'System Settings', exact: true })).toBeVisible();
  }
});

test('knowledge graph file rail can collapse and expand from the canvas handle', async ({ page }) => {
  await openPreview(page);

  const rail = page.getByTestId('graph-file-rail');
  const toggle = page.getByTestId('graph-file-rail-toggle');

  await expect(page.getByTestId('stitch-graph-layout')).toBeVisible();
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 1024) {
    await expect(rail).toBeHidden();
    await toggle.click();
    await expect(rail).toBeVisible();
    await expect(toggle).toHaveAttribute('title', 'Collapse file list');
  } else {
    await expect(rail).toBeVisible();
    const expandedCanvas = await page.getByTestId('graph-output-workspace').boundingBox();
    await expect(rail).toContainText('memory-graph-design.pdf');
    await expect(rail).not.toContainText('Machine Learning');
    await toggle.click();
    await expect(rail).toBeHidden();
    await expect(toggle).toHaveAttribute('title', 'Expand file list');
    const collapsedCanvas = await page.getByTestId('graph-output-workspace').boundingBox();
    expect(collapsedCanvas!.width).toBeGreaterThan(expandedCanvas!.width);
    await toggle.click();
    await expect(rail).toBeVisible();
  }
});

test('research vault directory rail clips long folder labels inside the rail', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'Research Vault', exact: true }).click();

  const layout = page.getByTestId('stitch-research-vault-layout');
  const directoryRail = layout.locator('aside').first();
  const directoryButton = directoryRail.getByRole('button', { name: /Demo Research Vault/ });

  await expect(layout).toBeVisible();
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 768) {
    await expect(directoryRail).toBeHidden();
    const hasPageOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(hasPageOverflow).toBe(false);
    return;
  }
  await expect(directoryButton).toBeVisible();

  const railBox = await directoryRail.boundingBox();
  const buttonBox = await directoryButton.boundingBox();
  expect(railBox).not.toBeNull();
  expect(buttonBox).not.toBeNull();
  expect(buttonBox!.x + buttonBox!.width).toBeLessThanOrEqual(railBox!.x + railBox!.width + 1);

  const hasHorizontalOverflow = await directoryRail.evaluate((element) => element.scrollWidth > element.clientWidth + 1);
  expect(hasHorizontalOverflow).toBe(false);
});

test('documentation and support show planned backend feedback', async ({ page }) => {
  await openPreview(page);
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 768) {
    await page.getByRole('button', { name: 'Open resources' }).click();
  }

  await page.getByRole('button', { name: 'Documentation' }).click();
  await expect(page.getByText('Documentation workspace is reserved for a future release.')).toBeVisible();

  await page.getByRole('button', { name: 'Support' }).click();
  await expect(page.getByText('Support contact workflow is reserved for a future release.')).toBeVisible();
});

test('research vault upload and document actions are wired', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'Research Vault', exact: true }).click();

  await page.getByTestId('workspace-upload-input').setInputFiles({
    name: 'closure-notes.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from('# Closure notes'),
  });
  await expect(page.getByTestId('stitch-research-vault-layout')).toContainText('closure-notes.md');

  const card = page.getByTestId('document-card').filter({ hasText: 'closure-notes.md' });
  await card.getByRole('button', { name: 'Index' }).click();
  await expect(card).toContainText('indexed');

  await card.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByTestId('stitch-research-vault-layout')).not.toContainText('closure-notes.md');
});

test('knowledge graph document panel opens on click and canvas clears selection', async ({ page }) => {
  await openPreview(page);

  await expect(page.getByText('Properties', { exact: true })).toBeHidden();

  const node = page.locator('[data-node-id="node-doc-graph"]');
  await expect(node).toBeVisible();
  await node.click();

  const panel = page.getByTestId('graph-document-preview-panel');
  await expect(panel).toBeVisible();
  await expect(panel).toContainText('Properties');
  await expect(panel).toContainText('memory-graph-design.pdf');
  await expect(panel).toContainText('Graph neighborhoods can provide retrieval context');

  await expect(panel).toBeVisible();
  await expect(panel.getByRole('link', { name: /Read full note/ })).toBeVisible();

  const canvas = page.locator('svg[aria-label="Knowledge graph"]');
  const canvasBox = await canvas.boundingBox();
  await page.mouse.click(canvasBox!.x + canvasBox!.width - 24, canvasBox!.y + canvasBox!.height - 24);
  await expect(panel).toBeHidden();
});

test('graph filters, node type controls, dragging, and restart layout are functional', async ({ page }) => {
  await openPreview(page);
  const documentNode = page.locator('[data-node-id="node-doc-graph"]');
  await expect(documentNode).toBeVisible();

  await page.getByRole('button', { name: 'Tags' }).click();
  await expect(documentNode).toBeHidden();
  await page.getByRole('button', { name: 'All Nodes' }).click();
  await expect(documentNode).toBeVisible();
  await page.getByRole('button', { name: 'Orphans' }).click();
  await expect(documentNode).toBeHidden();
  await page.getByRole('button', { name: 'All Nodes' }).click();

  await page.getByRole('button', { name: 'Graph filters' }).click();
  const filterPanel = page.getByTestId('graph-node-type-filters');
  await expect(filterPanel).toBeVisible();
  await filterPanel.getByRole('button', { name: 'Documents' }).click();
  await expect(documentNode).toBeHidden();
  await filterPanel.getByRole('button', { name: 'Documents' }).click();
  await expect(documentNode).toBeVisible();

  const circle = documentNode.locator('circle');
  const originalX = Number(await circle.getAttribute('cx'));
  const originalY = Number(await circle.getAttribute('cy'));
  const nodeBox = await documentNode.boundingBox();
  await page.mouse.move(nodeBox!.x + nodeBox!.width / 2, nodeBox!.y + nodeBox!.height / 2);
  await page.mouse.down();
  await page.mouse.move(nodeBox!.x + nodeBox!.width / 2 + 60, nodeBox!.y + nodeBox!.height / 2 + 35, { steps: 4 });
  await page.mouse.up();
  await expect.poll(async () => Number(await circle.getAttribute('cx'))).not.toBe(originalX);
  const draggedX = Number(await circle.getAttribute('cx'));

  await page.getByRole('button', { name: 'Restart graph layout' }).click();
  await expect.poll(async () => Number(await circle.getAttribute('cx'))).not.toBe(draggedX);
  expect(Number(await circle.getAttribute('cy'))).not.toBe(originalY);
});

test('graph search and toolbar produce visible behavior', async ({ page }) => {
  await openPreview(page);

  await page.getByPlaceholder('Search knowledge base...').fill('memory graph');
  await page.getByRole('button', { name: 'Run GraphRAG' }).click();
  await expect(page.getByTestId('graph-output-workspace')).toContainText('Preview GraphRAG found');

  const graph = page.locator('svg[aria-label="Knowledge graph"]');
  const before = await graph.getAttribute('viewBox');
  await page.getByRole('button', { name: 'Zoom in graph' }).click();
  await expect(graph).not.toHaveAttribute('viewBox', before ?? '');
  await page.getByRole('button', { name: 'Center graph' }).click();
  await expect(graph).toHaveAttribute('viewBox', '0 0 760 680');
});

test('ai chat history rail can collapse and expand from the chat handle', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();
  const viewport = page.viewportSize();

  const layout = page.getByTestId('stitch-ai-laboratory-layout');
  const rail = page.getByTestId('ai-history-rail');
  const chat = page.getByTestId('chat-function-grid');
  const toggle = page.getByTestId('ai-history-rail-toggle');

  await expect(layout).toBeVisible();
  if (viewport && viewport.width < 1024) {
    await expect(rail).toBeHidden();
    await toggle.click();
  }
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

test('ai laboratory filters and deletes chat sessions', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 1024) {
    await page.getByTestId('ai-history-rail-toggle').click();
  }

  await page.getByPlaceholder('Search history...').fill('Preview Vault');
  await expect(page.getByTestId('ai-history-rail')).toContainText('Preview Vault Review');
  if (viewport && viewport.width < 1024) {
    await page.getByTestId('ai-history-rail-toggle').click();
  }
  await page.getByRole('button', { name: 'Delete active chat' }).click();
  await expect(page.getByTestId('ai-history-rail')).not.toContainText('Preview Vault Review');
});

test('ai laboratory renders API-backed sessions and appends sent messages', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();

  await expect(page.getByTestId('ai-history-rail')).toContainText('Preview Vault Review');
  await expect(page.getByTestId('chat-function-grid')).toContainText('How should I review this vault?');
  await expect(page.getByTestId('chat-function-grid')).toContainText('Start with the indexed documents');

  const composer = page.getByTestId('workspace-chat-command').locator('textarea');
  await composer.fill('Summarize the graph contradictions');
  await page.getByTestId('workspace-chat-command').getByRole('button').click();

  await expect(page.getByTestId('chat-function-grid')).toContainText('Summarize the graph contradictions');
  await expect(page.getByTestId('chat-function-grid')).toContainText('Preview answer for: Summarize the graph contradictions');

  await page.getByRole('button', { name: 'System Settings', exact: true }).click();
  await expect(page.getByTestId('stitch-settings-layout')).toContainText('Preview DeepSeek');
});

test('settings can trigger graph and memory sync actions', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'System Settings', exact: true }).click();

  const settings = page.getByTestId('stitch-settings-layout');
  await settings.getByRole('button', { name: 'Rebuild Graph' }).click();
  await expect(settings).toContainText('Graph rebuild completed for Demo Research Vault');

  await settings.getByRole('button', { name: 'Rebuild Memory' }).click();
  await expect(settings).toContainText('Memory rebuild processed 2 documents');
});

test('settings model controls call preview API actions', async ({ page }) => {
  await openPreview(page);
  await page.getByRole('button', { name: 'System Settings', exact: true }).click();

  const settings = page.getByTestId('stitch-settings-layout');
  await settings.getByRole('button', { name: /Test Preview DeepSeek/ }).click();
  await expect(settings).toContainText('Preview model config is ready.');

  await settings.getByRole('slider').fill('32');
  await settings.getByRole('button', { name: 'Save context window' }).click();
  await expect(settings).toContainText('Context window updated to 32,000');
});
