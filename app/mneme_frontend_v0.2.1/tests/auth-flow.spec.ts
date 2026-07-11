import { expect, test, type Page, type Route } from '@playwright/test';

const envelope = (data: unknown, message = 'ok') => ({ code: 0, message, data });

async function useChinese(page: Page) {
  await page.addInitScript(() => window.localStorage.setItem('mneme.locale', 'zh-CN'));
}

async function routeBootstrap(page: Page, options: { register?: (route: Route) => Promise<void>; loginStatus?: number; loginDetail?: string; loginDelay?: number } = {}) {
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const { pathname } = new URL(route.request().url());
    if (pathname === '/auth/register' && options.register) {
      await options.register(route);
      return;
    }
    if (pathname === '/auth/register') {
      await route.fulfill({ json: envelope({ id: 9, username: 'new-user', display_name: 'New User', avatar_url: '/avatar.png' }, 'register success') });
      return;
    }
    if (pathname === '/auth/login' && options.loginStatus) {
      if (options.loginDelay) await new Promise((resolve) => setTimeout(resolve, options.loginDelay));
      await route.fulfill({ status: options.loginStatus, json: { detail: options.loginDetail ?? 'Invalid username or password' } });
      return;
    }
    if (pathname === '/auth/login') {
      await route.fulfill({ json: envelope({ access_token: 'token-9', token_type: 'bearer' }, 'login success') });
      return;
    }
    if (pathname === '/auth/me') {
      await route.fulfill({ json: envelope({ id: 9, username: 'new-user', display_name: 'New User', avatar_url: '/avatar.png' }) });
      return;
    }
    if (pathname === '/health') {
      await route.fulfill({ json: envelope({ service: 'mneme', status: 'running' }) });
      return;
    }
    if (pathname === '/health/neo4j') {
      await route.fulfill({ json: envelope({ enabled: true, backend: 'neo4j', database: 'neo4j', uri: 'bolt://neo4j:7687', ok: true, error: null }) });
      return;
    }
    if (pathname === '/health/readiness') {
      await route.fulfill({ json: envelope({ overall_status: 'ready', checks: [], framework_decisions: [], default_stack: [], optional_stack: [], avoid_by_default: [], markdown: '' }) });
      return;
    }
    if (pathname === '/users/9/knowledge-bases') {
      await route.fulfill({ json: envelope({ items: [], total: 0 }) });
      return;
    }
    if (pathname === '/ai/model-configs') {
      await route.fulfill({ json: envelope({ provider_presets: [], items: [], default_config_id: null }) });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: `Unexpected test request: ${pathname}` } });
  });
}

test('registration creates an account and automatically enters the shell', async ({ page }) => {
  await useChinese(page);
  await routeBootstrap(page);
  await page.goto('/');

  await page.getByRole('button', { name: '注册' }).click();
  await page.getByLabel('用户名').fill('new-user');
  await page.getByLabel('显示名称').fill('New User');
  await page.getByLabel('密码', { exact: true }).fill('password123');
  await page.getByLabel('确认密码').fill('password123');
  await page.getByRole('button', { name: '创建账户' }).click();

  await expect(page.getByTestId('obsidian-shell')).toBeVisible();
});

test('blocked localStorage does not block login', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked'); } }));
  await routeBootstrap(page);
  await page.goto('/');

  await page.getByLabel('Username').fill('new-user');
  await page.getByLabel('Password', { exact: true }).fill('password123');
  await page.locator('form').getByRole('button', { name: 'Sign in' }).click();

  await expect(page.getByTestId('obsidian-shell')).toBeVisible();
  await expect(page.getByText('This session will remain in this tab only.')).toBeVisible();
});

test('registration rejects mismatched passwords before calling the API', async ({ page }) => {
  await useChinese(page);
  let registerCalls = 0;
  await routeBootstrap(page, { register: async (route) => { registerCalls += 1; await route.fulfill({ json: envelope({}) }); } });
  await page.goto('/');
  await page.getByRole('button', { name: '注册' }).click();
  await page.getByLabel('用户名').fill('new-user');
  await page.getByLabel('密码', { exact: true }).fill('password123');
  await page.getByLabel('确认密码').fill('password456');
  await page.getByRole('button', { name: '创建账户' }).click();

  await expect(page.getByText('两次输入的密码不一致')).toBeVisible();
  expect(registerCalls).toBe(0);
});

test('duplicate username displays the backend detail', async ({ page }) => {
  await useChinese(page);
  await routeBootstrap(page, { register: async (route) => { await route.fulfill({ status: 400, json: { detail: '用户名已存在' } }); } });
  await page.goto('/');
  await page.getByRole('button', { name: '注册' }).click();
  await page.getByLabel('用户名').fill('existing-user');
  await page.getByLabel('密码', { exact: true }).fill('password123');
  await page.getByLabel('确认密码').fill('password123');
  await page.getByRole('button', { name: '创建账户' }).click();

  await expect(page.getByText('用户名已存在')).toBeVisible();
});

test('auth submit is disabled while pending and invalid credentials remain readable', async ({ page }) => {
  await useChinese(page);
  await routeBootstrap(page, { loginStatus: 401, loginDetail: '用户名或密码错误', loginDelay: 300 });
  await page.goto('/');
  await page.getByLabel('用户名').fill('new-user');
  await page.getByLabel('密码', { exact: true }).fill('wrong-password');
  const submit = page.locator('form').getByRole('button', { name: '登录' });
  await submit.click();

  await expect(submit).toBeDisabled();
  await expect(page.getByText('用户名或密码错误')).toBeVisible();
});
