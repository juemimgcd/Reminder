import { expect, test } from "@playwright/test";

test("opening a recent file reaches the unified reader", async ({ page }) => {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  await page
    .getByTestId("sidebar-group-files")
    .getByRole("button", { name: /zettelkasten/i })
    .click();
  await expect(page.getByTestId("document-reader")).toBeVisible();
  await expect(page.getByTestId("document-reader-title")).toContainText(
    "zettelkasten-principles.md",
  );
});

test("duplicate upload exposes the canonical open action", async ({ page }) => {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  const recentFiles = page.getByTestId("sidebar-group-files").getByRole("button");
  const initialFileCount = await recentFiles.count();
  await page.getByLabel("Upload document").setInputFiles({
    name: "copy.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Atomic notes"),
  });
  await expect(page.getByTestId("duplicate-upload-notice")).toContainText(
    "already exists",
  );
  await expect(recentFiles).toHaveCount(initialFileCount);
  await page.getByRole("button", { name: "Open existing file" }).click();
  await expect(page.getByTestId("document-reader-title")).toContainText(
    "zettelkasten-principles.md",
  );
});

test("a created upload invalidates the notes list and opens its canonical document", async ({ page }) => {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  await page.getByLabel("Upload document").setInputFiles({
    name: "workspace-state.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Workspace state\n\nA changed document version."),
  });
  await expect(page.getByTestId("document-reader-title")).toContainText("workspace-state.md");
  await expect(
    page.getByTestId("sidebar-group-files").getByRole("button", { name: /workspace-state/i }),
  ).toBeVisible();
});
