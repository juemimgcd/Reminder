import { expect, test, type Page } from "@playwright/test";

async function openVault(page: Page) {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Research Vault", exact: true }).click();
  await expect(page.getByTestId("document-workspace")).toBeVisible();
}

test("vault tree opens complete markdown and exposes the newest version", async ({ page }) => {
  await openVault(page);

  await page.getByTestId("document-tree").getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();

  await expect(page.getByTestId("document-reader-title")).toContainText("zettelkasten-principles.md");
  await expect(page.getByTestId("document-markdown")).toContainText("Atomic notes");
  await expect(page.getByTestId("document-version-history")).toContainText("v1");
  await expect(page.getByTestId("document-tree").getByText("zettelkasten-principles.md", { exact: true })).toHaveCount(1);
});

test("folder creation and keyboard document move use the real nested tree", async ({ page }) => {
  await openVault(page);
  await page.getByRole("button", { name: "New folder" }).click();
  await page.getByLabel("Folder name").fill("Research");
  await page.getByRole("button", { name: "Create folder" }).click();

  await page.getByRole("button", { name: /move zettelkasten-principles/i }).click();
  await page.getByRole("option", { name: "Research", exact: true }).click();

  await expect(page.getByTestId("folder-Research")).toContainText("zettelkasten-principles.md");
});

test("folder rename, nesting, and non-empty delete keep actionable feedback", async ({ page }) => {
  await openVault(page);
  for (const name of ["Research", "Archive"]) {
    await page.getByRole("button", { name: "New folder" }).click();
    await page.getByLabel("Folder name").fill(name);
    await page.getByRole("button", { name: "Create folder" }).click();
  }
  await page.getByTestId("folder-Research").getByRole("button", { name: "Research", exact: true }).click();
  await page.getByRole("button", { name: "Rename folder" }).click();
  await page.getByLabel("Folder name").fill("Research notes");
  await page.locator(".folder-form").getByRole("button", { name: "Rename folder" }).click();
  await expect(page.getByTestId("folder-Research notes")).toBeVisible();

  await page.getByRole("button", { name: "Move folder" }).click();
  await page.getByRole("option", { name: "Archive", exact: true }).click();
  await expect(page.getByTestId("folder-Archive")).toContainText("Research notes");

  await page.getByRole("button", { name: /move zettelkasten-principles/i }).click();
  await page.getByRole("option", { name: "Research notes", exact: true }).click();
  await page.getByTestId("folder-Research notes").getByRole("button", { name: "Research notes", exact: true }).click();
  await page.getByRole("button", { name: "Delete folder" }).click();
  await expect(page.getByRole("alert")).toContainText(/empty|contains/i);
  await expect(page.getByTestId("folder-Research notes")).toBeVisible();
  await page.getByRole("button", { name: "Move folder" }).click();
  await page.getByRole("option", { name: "Vault root", exact: true }).click();
  await expect(page.getByTestId("document-tree").getByTestId("folder-Research notes")).toBeVisible();
});

test("dragging a document and keyboard move converge on the same folder destination", async ({ page }) => {
  await openVault(page);
  await page.getByRole("button", { name: "New folder" }).click();
  await page.getByLabel("Folder name").fill("Drag target");
  await page.getByRole("button", { name: "Create folder" }).click();
  await page.getByRole("button", { name: "memory-graph-design.pdf", exact: true }).dragTo(page.getByTestId("folder-Drag target"));
  await expect(page.getByTestId("folder-Drag target")).toContainText("memory-graph-design.pdf");
});

test("version history switches between uploaded revisions", async ({ page }) => {
  await openVault(page);
  await page.getByLabel("Upload document").setInputFiles({
    name: "zettelkasten-principles.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Atomic notes\n\nRevision two."),
  });
  if (!(await page.getByTestId("document-version-history").isVisible())) {
    await page.getByRole("button", { name: "Properties" }).click();
  }
  await expect(page.getByTestId("document-version-history")).toContainText("v2");
  await page.getByTestId("document-version-history").getByRole("button", { name: /v1/i }).click();
  await expect(page.getByTestId("document-reader-title")).toContainText("zettelkasten-principles.md");
});

test("markdown sanitization blocks executable markup and external resources", async ({ page }) => {
  await openVault(page);
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    api.documentContent = async (_token: string, documentId: string) => ({
      document_id: documentId,
      folder_id: "fld-preview-root",
      file_name: "zettelkasten-principles.md",
      render_mode: "markdown",
      mime_type: "text/markdown",
      text: "# Safe\n<script>window.__readerPwned = true</script><img src=https://example.com/tracker.png onerror=window.__readerPwned=true><a href=javascript:alert(1)>bad</a>",
      sections: [],
      parse_warning: null,
    });
  });

  await page.getByTestId("document-tree").getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  const markdown = page.getByTestId("document-markdown");
  await expect(markdown.locator("script, iframe, object, embed, style")).toHaveCount(0);
  await expect(markdown.locator("img")).toHaveCount(0);
  await expect(markdown.locator("a")).not.toHaveAttribute("href", /javascript:/i);
  await expect.poll(() => page.evaluate(() => Boolean((window as typeof window & { __readerPwned?: boolean }).__readerPwned))).toBe(false);
});

test("structured content is rendered as text and never through HTML", async ({ page }) => {
  await openVault(page);
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    api.documentContent = async (_token: string, documentId: string) => ({
      document_id: documentId,
      folder_id: "fld-preview-root",
      file_name: "zettelkasten-principles.md",
      render_mode: "structured",
      mime_type: "application/json",
      text: "<img src=x onerror=window.__structuredPwned=true>",
      sections: [],
      parse_warning: null,
    });
  });
  await page.getByTestId("document-tree").getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  await expect(page.getByTestId("document-structured")).toContainText("<img src=x");
  await expect(page.getByTestId("document-structured").locator("img")).toHaveCount(0);
});

test("PDF uses an authenticated Blob frame and closing its tab revokes it", async ({ page }) => {
  await openVault(page);
  await page.evaluate(() => {
    (window as typeof window & { __revokedUrls?: string[] }).__revokedUrls = [];
    URL.revokeObjectURL = (url: string) => (window as typeof window & { __revokedUrls: string[] }).__revokedUrls.push(url);
  });
  await page.getByTestId("document-tree").getByRole("button", { name: "memory-graph-design.pdf", exact: true }).click();
  await expect(page.getByTestId("document-pdf")).toHaveAttribute("src", /^blob:/);
  await page.getByRole("button", { name: /close memory-graph-design/i }).click();
  await expect.poll(() => page.evaluate(() => (window as typeof window & { __revokedUrls: string[] }).__revokedUrls.length)).toBeGreaterThan(0);
});

test("Office sections and parse warnings keep a download fallback", async ({ page }) => {
  await openVault(page);
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    api.documentContent = async (_token: string, documentId: string) => ({
      document_id: documentId,
      folder_id: "fld-preview-root",
      file_name: "zettelkasten-principles.docx",
      render_mode: "office",
      mime_type: "text/markdown",
      text: "# Overview\nConverted body",
      sections: [{ title: "Overview", text: "Converted body" }],
      parse_warning: "Some embedded media could not be converted.",
    });
  });
  await page.getByTestId("document-tree").getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  await expect(page.getByTestId("document-office")).toContainText("Converted body");
  await expect(page.getByRole("status")).toContainText("embedded media");
  await expect(page.getByRole("button", { name: "Download original" })).toBeVisible();
});

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 1024, height: 768 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`reader layout is intentional at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openVault(page);
    await page.getByTestId("document-tree").getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
    await expect(page.getByTestId("document-reader")).toBeVisible();
    if (viewport.name === "desktop") {
      await expect(page.getByTestId("document-tree-pane")).toBeVisible();
      await expect(page.getByTestId("document-properties")).toBeVisible();
    } else {
      await expect(page.getByRole("button", { name: "Files" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Properties" })).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  });
}
