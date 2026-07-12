import { expect, test, type Page } from '@playwright/test';

const envelope = (data: unknown) => ({ code: 0, message: 'ok', data });

async function routeWorkspace(page: Page, heavyCalls: string[], graphStatus = 200) {
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const isHeavy = ['/kb/documents', '/graph/', '/memory/', '/profile/', '/analysis/', '/advice/', '/kb/chat/', '/settings/ai-models'].some((part) => path.includes(part));
    if (isHeavy) heavyCalls.push(path);

    if (path === '/auth/login') return route.fulfill({ json: envelope({ access_token: 'token-lazy', token_type: 'bearer' }) });
    if (path === '/auth/me') return route.fulfill({ json: envelope({ id: 7, username: 'lazy-user', display_name: 'Lazy User', avatar_url: '' }) });
    if (path === '/health') return route.fulfill({ json: envelope({ service: 'mneme', status: 'running' }) });
    if (path === '/health/readiness') return route.fulfill({ json: envelope({ overall_status: 'ready', checks: [], framework_decisions: [], default_stack: [], optional_stack: [], avoid_by_default: [], markdown: '' }) });
    if (path === '/users/7/knowledge-bases') return route.fulfill({ json: envelope({ items: [{ id: 'kb-7', user_id: 7, name: 'Lazy Vault', description: null, is_default: true, created_at: '2026-07-11T00:00:00Z' }], total: 1 }) });
    if (path === '/kb/documents') return route.fulfill({ json: envelope({ items: [{ id: 'doc-7', user_id: 7, knowledge_base_id: 'kb-7', file_name: 'Latency Notes.md', file_type: 'md', status: 'indexed', created_at: '2026-07-11T00:00:00Z' }], total: 1 }) });
    if (path.includes('/graph/knowledge-bases/kb-7')) {
      if (graphStatus !== 200) return route.fulfill({ status: graphStatus, json: { detail: 'Internal Server Error' } });
      return route.fulfill({ json: envelope({ scope: 'knowledge_base', generated_at: '2026-07-11T00:00:00Z', root_node_id: 'node-kb-7', include_memory: true, include_relationships: true, relationship_strategy: null, relationship_scope: null, min_shared_memory_count: null, min_relationship_score: null, max_related_edges: null, nodes: [{ id: 'node-kb-7', entity_id: 'kb-7', node_type: 'knowledge_base', label: 'Lazy Vault', parent_id: null, depth: 0, metadata: {} }], edges: [], node_count: 1, edge_count: 0, node_type_counts: { knowledge_base: 1 }, edge_type_counts: {} }) });
    }
    if (path === '/health/neo4j') return route.fulfill({ json: envelope({ enabled: true, backend: 'neo4j', database: 'neo4j', uri: 'bolt://neo4j:7687', ok: true, error: null }) });
    if (path === '/settings/ai-models') return route.fulfill({ json: envelope({ provider_presets: [], items: [], default_config_id: null }) });
    return route.fulfill({ status: 500, json: { detail: 'Internal Server Error' } });
  });
}

async function login(page: Page) {
  await page.goto('/');
  await page.getByLabel('Username').fill('lazy-user');
  await page.getByLabel('Password', { exact: true }).fill('password123');
  await page.locator('form').getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByTestId('obsidian-shell')).toBeVisible();
}

test('login renders the shell without eager feature requests and graph loads on navigation', async ({ page }) => {
  const heavyCalls: string[] = [];
  await routeWorkspace(page, heavyCalls);
  await login(page);
  await page.waitForTimeout(250);

  expect(heavyCalls).toEqual([]);
  await page.getByRole('button', { name: 'Knowledge Graph' }).click();
  await expect(page.getByTestId('graph-output-workspace')).toBeVisible();
  await expect.poll(() => heavyCalls).toEqual(expect.arrayContaining(['/kb/documents', '/graph/knowledge-bases/kb-7']));
  expect(heavyCalls.some((path) => path.includes('/profile/') || path.includes('/advice/'))).toBe(false);
});

test('a graph endpoint failure stays inside the graph view and hides raw server text', async ({ page }) => {
  const heavyCalls: string[] = [];
  await routeWorkspace(page, heavyCalls, 500);
  await login(page);
  await page.getByRole('button', { name: 'Knowledge Graph' }).click();

  await expect(page.getByTestId('graph-output-workspace')).toBeVisible();
  await expect(page.getByText('Internal Server Error')).toHaveCount(0);
  await expect(page.getByText('This feature is temporarily unavailable. Please try again later.')).toBeVisible();
});
