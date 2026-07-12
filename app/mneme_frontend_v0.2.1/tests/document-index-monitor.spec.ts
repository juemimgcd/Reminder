import { expect, test, type Page } from "@playwright/test";

const envelope = (data: unknown) => ({ code: 0, message: "ok", data });

async function routeIndexWorkspace(page: Page, taskStatuses: string[]) {
  let taskCalls = 0;
  let documentCalls = 0;
  await page.route("http://127.0.0.1:8000/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/auth/login") return route.fulfill({ json: envelope({ access_token: "token-index", token_type: "bearer" }) });
    if (path === "/auth/me") return route.fulfill({ json: envelope({ id: 7, username: "index-user", display_name: "Index User", avatar_url: "" }) });
    if (path === "/health") return route.fulfill({ json: envelope({ service: "mneme", status: "running" }) });
    if (path === "/health/readiness") return route.fulfill({ json: envelope({ overall_status: "ready", checks: [], framework_decisions: [], default_stack: [], optional_stack: [], avoid_by_default: [], markdown: "" }) });
    if (path === "/users/7/knowledge-bases") return route.fulfill({ json: envelope({ items: [{ id: "kb-7", user_id: 7, name: "Index Vault", description: null, is_default: true, created_at: "2026-07-11T00:00:00Z" }], total: 1 }) });
    if (path === "/kb/documents") {
      documentCalls += 1;
      return route.fulfill({ json: envelope({ items: [{ id: "doc-7", user_id: 7, knowledge_base_id: "kb-7", folder_id: "fld-root", file_name: "Index me.md", file_type: "md", status: documentCalls > 1 ? "indexed" : "uploaded", version_group_id: "vg-7", version_number: 1, duplicate_of_document_id: null, created_at: "2026-07-11T00:00:00Z" }], total: 1 }) });
    }
    if (path === "/kb/document-folders") return route.fulfill({ json: envelope([{ id: "fld-root", parent_id: "fld-root", name: "", is_root: true, children: [] }]) });
    if (path === "/kb/documents/doc-7/content") return route.fulfill({ json: envelope({ document_id: "doc-7", folder_id: "fld-root", file_name: "Index me.md", render_mode: "markdown", mime_type: "text/markdown", text: "# Index me", sections: [], parse_warning: null }) });
    if (path === "/kb/documents/doc-7/preview") return route.fulfill({ json: envelope({ document_id: "doc-7", knowledge_base_id: "kb-7", file_name: "Index me.md", file_type: "md", status: documentCalls > 1 ? "indexed" : "uploaded", summary: "Index monitor fixture", chunks: [], memory_entries: [] }) });
    if (path === "/kb/documents/doc-7/versions") return route.fulfill({ json: envelope({ items: [{ document_id: "doc-7", version_group_id: "vg-7", version_number: 1, file_name: "Index me.md", created_at: "2026-07-11T00:00:00Z" }], total: 1 }) });
    if (path === "/memory/knowledge-bases/kb-7/library") return route.fulfill({ json: envelope({ timeline: [], by_type: {}, by_theme: [] }) });
    if (path === "/kb/documents/doc-7/index") return route.fulfill({ json: envelope({ task_id: "task-7", document_id: "doc-7", knowledge_base_id: "kb-7", status: "pending", message: "Index task submitted" }) });
    if (path === "/tasks/task-7") {
      const status = taskStatuses[Math.min(taskCalls, taskStatuses.length - 1)];
      taskCalls += 1;
      return route.fulfill({ json: envelope({ id: "task-7", task_type: "document_index", target_id: "doc-7", status, progress_stage: status === "running" ? "embedding" : null, queue_name: "default", celery_task_id: null, attempt_count: 1, max_attempts: 3, result_summary: status === "succeeded" ? "Indexed" : null, error_message: status === "failed" ? "Parser failed" : null, created_at: "2026-07-11T00:00:00Z", updated_at: "2026-07-11T00:00:01Z" }) });
    }
    return route.fulfill({ status: 500, json: { detail: `Unhandled ${path}` } });
  });
  return { taskCalls: () => taskCalls, documentCalls: () => documentCalls };
}

async function loginAndOpenVault(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("index-user");
  await page.getByLabel("Password", { exact: true }).fill("password123");
  await page.locator("form").getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByTestId("obsidian-shell")).toBeVisible();
  await page.getByRole("button", { name: "Research Vault" }).click();
  const document = page.getByTestId("document-tree").getByRole("button", { name: "Index me.md", exact: true });
  await expect(document).toBeVisible();
  await document.click();
  await expect(page.getByTestId("document-reader-title")).toContainText("Index me.md");
}

test("index monitoring reaches terminal success and refreshes notes again", async ({ page }) => {
  const calls = await routeIndexWorkspace(page, ["running", "succeeded"]);
  await loginAndOpenVault(page);

  await page.getByRole("button", { name: "Index", exact: true }).click();

  await expect(page.getByTestId("document-action-status")).toContainText("Indexing completed");
  await expect.poll(calls.taskCalls).toBe(2);
  await expect.poll(calls.documentCalls).toBeGreaterThanOrEqual(2);
  await expect(page.getByRole("button", { name: "Index", exact: true })).toBeDisabled();
});

test("index monitoring stops at failure and surfaces the task error", async ({ page }) => {
  const calls = await routeIndexWorkspace(page, ["running", "failed"]);
  await loginAndOpenVault(page);

  await page.getByRole("button", { name: "Index", exact: true }).click();

  await expect(page.getByTestId("document-action-status")).toContainText(/Indexing failed: Parser failed/);
  await expect.poll(calls.taskCalls).toBe(2);
});

test("logout cancels an active bounded index monitor", async ({ page }) => {
  const calls = await routeIndexWorkspace(page, ["running"]);
  await loginAndOpenVault(page);
  await page.getByRole("button", { name: "Index", exact: true }).click();
  await expect.poll(calls.taskCalls).toBeGreaterThan(0);

  await page.getByRole("button", { name: "Log out" }).click();
  const callsAtLogout = calls.taskCalls();
  await page.waitForTimeout(900);
  expect(calls.taskCalls()).toBe(callsAtLogout);
});
