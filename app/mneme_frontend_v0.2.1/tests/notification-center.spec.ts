import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
});

test("heartbeat notifications are reachable and can be marked read", async ({ page }) => {
  const toggle = page.getByTestId("notification-center-toggle");

  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-label", /unread notifications/);
  await toggle.click();

  const panel = page.getByTestId("notification-center-panel");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Weekly memory review");
  await expect(panel).toContainText("Three new notes are ready for review");

  await panel.getByRole("button", { name: /Weekly memory review/ }).click();
  await expect(toggle).toHaveAttribute("aria-label", "Notifications");
});
