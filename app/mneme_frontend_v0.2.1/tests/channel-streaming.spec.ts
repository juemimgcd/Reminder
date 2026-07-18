import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
});

test("AI Laboratory exposes the durable SSE run trace", async ({ page }) => {
  await page.getByRole("button", { name: "AI Laboratory", exact: true }).click();

  const composer = page.getByTestId("workspace-chat-command");
  await composer.locator("textarea").fill("Trace this retrieval run");
  await composer.getByRole("button", { name: "Send message" }).click();

  const trace = page.getByTestId("agent-run-trace");
  await expect(trace).toBeVisible();
  await expect(trace).toContainText("Retrieval started");
  await expect(trace).toContainText("2 evidence items selected");
  await expect(trace).toContainText("Answer completed");
  await expect(trace.locator("header > span")).toHaveAttribute("data-state", "completed");
});

test("analysis mode exposes bounded multi-agent role progress", async ({ page }) => {
  await page.getByRole("button", { name: "AI Laboratory", exact: true }).click();

  const composer = page.getByTestId("workspace-chat-command");
  await page.getByTestId("answer-mode-selector").getByRole("button", { name: "Analysis" }).click();
  await composer.locator("textarea").fill("Compare all available evidence");
  await composer.getByRole("button", { name: "Send message" }).click();

  const trace = page.getByTestId("agent-run-trace");
  await expect(trace).toContainText("Coordinator · 4 sources");
  await expect(trace).toContainText("document_retriever · 2 results");
  await expect(trace).toContainText("Evidence Judge · 4 kept · 1 conflicts");
});

test("settings manages Feishu binding, routing, and delivery retry", async ({ page }) => {
  await page.getByRole("button", { name: "System Settings", exact: true }).click();

  const panel = page.getByTestId("channel-gateway-panel");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Feishu gateway");
  await expect(panel).toContainText("Credentials stay deployment-managed");
  await expect(panel).toContainText("ou_preview_operator");

  await panel.getByRole("button", { name: "Generate code" }).click();
  await expect(panel).toContainText("/bind MNEME-4821");

  await panel.getByRole("button", { name: "Save route" }).click();
  await expect(panel).toContainText("Conversation route saved");

  await panel.getByRole("button", { name: "Retry" }).click();
  await expect(panel).toContainText("Delivery queued for retry");

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  expect(overflow).toBe(false);
});
