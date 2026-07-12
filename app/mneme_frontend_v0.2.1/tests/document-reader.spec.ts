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
  await expect(page.getByTestId("folder-Research").getByRole("treeitem", { name: /zettelkasten-principles/i })).toBeVisible();
});

test("folder rename, nesting, and non-empty delete keep actionable feedback", async ({ page }) => {
  await openVault(page);
  for (const name of ["Research", "Archive"]) {
    await page.getByRole("button", { name: "New folder" }).click();
    await page.getByLabel("Folder name").fill(name);
    await page.getByRole("button", { name: "Create folder" }).click();
    if (name === "Research") await page.getByRole("button", { name: "Vault root", exact: true }).click();
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

test("sanitizer allowlist blocks SVG and every automatic resource URL", async ({ page }) => {
  await openVault(page);
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().startsWith("https://reader-attacker.invalid")) externalRequests.push(request.url());
  });
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    api.documentContent = async (_token: string, documentId: string) => ({
      document_id: documentId,
      folder_id: "fld-preview-root",
      file_name: "zettelkasten-principles.md",
      render_mode: "markdown",
      mime_type: "text/markdown",
      text: "# Safe\n<svg><image href=https://reader-attacker.invalid/a><use xlink:href=https://reader-attacker.invalid/b></use></svg><math><mtext>bad</mtext></math><input type=image src=https://reader-attacker.invalid/c><video poster=https://reader-attacker.invalid/d src=https://reader-attacker.invalid/e></video><a href=https://example.com>safe link</a>",
      sections: [],
      parse_warning: null,
    });
  });
  await page.getByTestId("document-tree").getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  const markdown = page.getByTestId("document-markdown");
  await expect(markdown.locator("svg, math, image, use, input, video, audio, source, img")).toHaveCount(0);
  await expect(markdown.locator("[src], [srcset], [poster], [xlink\\:href]")).toHaveCount(0);
  await expect(markdown.getByRole("link", { name: "safe link" })).toHaveAttribute("rel", "noopener noreferrer");
  await page.waitForTimeout(100);
  expect(externalRequests).toEqual([]);
});

test("PDF raw failures are recoverable without unhandled rejection or permanent loading", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await openVault(page);
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    let attempt = 0;
    api.documentRawBlob = async () => {
      attempt += 1;
      if (attempt === 1) throw new Error("401: PDF access expired");
      return new Blob(["%PDF-retry"], { type: "application/pdf" });
    };
  });
  await page.getByTestId("document-tree").getByRole("button", { name: "memory-graph-design.pdf", exact: true }).click();
  await expect(page.getByTestId("document-pdf-error")).toContainText("PDF authorization expired");
  await expect(page.getByRole("button", { name: "Download original" })).toBeVisible();
  await page.getByRole("button", { name: "Retry PDF" }).click();
  await expect(page.getByTestId("document-pdf")).toHaveAttribute("src", /^blob:/);
  expect(pageErrors).toEqual([]);
});

for (const pdfFailure of [
  { error: "403 forbidden", message: "PDF authorization expired" },
  { error: "404 missing", message: "no longer available" },
  { error: "500 upstream", message: "temporarily unavailable" },
  { error: "NetworkError: Failed to fetch", message: "network error" },
]) {
  test(`PDF ${pdfFailure.error} reaches a localized recoverable state`, async ({ page }) => {
    await openVault(page);
    await page.evaluate(async (failure) => {
      const importModule = (path: string) => import(/* @vite-ignore */ path);
      const { api } = await importModule("/src/lib/api.ts");
      api.documentRawBlob = async () => { throw new Error(failure); };
    }, pdfFailure.error);
    await page.getByTestId("document-tree").getByRole("button", { name: "memory-graph-design.pdf", exact: true }).click();
    await expect(page.getByTestId("document-pdf-error")).toContainText(pdfFailure.message);
    await expect(page.getByRole("button", { name: "Retry PDF" })).toBeVisible();
  });
}

test("selected-folder create and folder drag share move validation", async ({ page }) => {
  await openVault(page);
  await page.getByRole("button", { name: "New folder" }).click();
  await page.getByLabel("Folder name").fill("Parent");
  await page.getByRole("button", { name: "Create folder" }).click();
  await page.getByTestId("folder-Parent").getByRole("button", { name: "Parent", exact: true }).click();
  await page.getByRole("button", { name: "New folder" }).click();
  await page.getByLabel("Folder name").fill("Child");
  await page.getByRole("button", { name: "Create folder" }).click();
  await expect(page.getByTestId("folder-Parent")).toContainText("Child");

  await page.getByTestId("folder-Parent").locator(".folder-row").first().dragTo(page.getByTestId("folder-Child"));
  await expect(page.getByRole("alert")).toContainText(/descendant|itself/i);
  await page.getByTestId("folder-Child").locator(".folder-row").first().dragTo(page.getByRole("treeitem", { name: /Vault root/i }));
  await expect(page.getByRole("tree", { name: "Vault folders" })).toContainText("Child");
});

test("Chinese locale covers reader tree, properties, and actions", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("mneme.locale", "zh-CN"));
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "研究库", exact: true }).click();
  await expect(page.getByRole("heading", { name: "文件", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "新建文件夹" })).toBeVisible();
  await page.getByRole("button", { name: /移动 zettelkasten-principles/i }).click();
  await expect(page.getByRole("listbox", { name: "移动文档" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    const originalContent = api.documentContent.bind(api);
    api.documentContent = async (token: string, documentId: string, options = {}) => documentId === "doc-zettelkasten"
      ? { document_id: documentId, folder_id: "fld-preview-root", file_name: "archive.bin", render_mode: "unsupported", mime_type: "application/octet-stream", text: null, sections: [], parse_warning: null }
      : originalContent(token, documentId, options);
    api.documentRawBlob = async () => { throw new Error("404 missing"); };
  });
  await page.getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  await expect(page.getByRole("button", { name: "下载", exact: true })).toBeVisible();
  await expect(page.getByText("阅读器暂不支持显示此文件。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "下载原文件" })).toBeVisible();
  if (!(await page.getByRole("heading", { name: "属性", exact: true }).isVisible())) {
    await page.getByRole("button", { name: "属性", exact: true }).click();
  }
  await expect(page.getByRole("heading", { name: "属性", exact: true })).toBeVisible();
  await expect(page.getByText("版本历史", { exact: true })).toBeVisible();
  if (!(await page.getByTestId("document-tree-pane").isVisible())) await page.getByRole("button", { name: "文件", exact: true }).click();
  await page.getByRole("button", { name: "memory-graph-design.pdf", exact: true }).click();
  await expect(page.getByTestId("document-pdf-error")).toContainText("原始 PDF 已不可用");
  await expect(page.getByRole("button", { name: "重试 PDF" })).toBeVisible();
});

test("mobile drawers and upload are keyboard operable with focus restoration", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openVault(page);
  const filesTrigger = page.getByRole("button", { name: "Files", exact: true });
  const propertiesTrigger = page.getByRole("button", { name: "Properties", exact: true });
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("document-tree-pane")).toBeHidden();
  await filesTrigger.click();
  await expect.poll(() => page.evaluate(() => Boolean(document.activeElement?.closest("#document-tree-pane")))).toBe(true);
  const upload = page.getByTestId("document-tree-pane").locator("label.upload-control");
  await upload.focus();
  await expect(upload).toBeFocused();
  await expect(page.getByRole("treeitem", { name: /Vault root/i })).toBeVisible();
  await expect(filesTrigger).toHaveAttribute("aria-controls", "document-tree-pane");
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("document-tree-pane")).toBeHidden();
  await expect(filesTrigger).toBeFocused();
  await propertiesTrigger.click();
  await expect(propertiesTrigger).toHaveAttribute("aria-controls", "document-properties-pane");
  await expect.poll(() => page.evaluate(() => Boolean(document.activeElement?.closest("#document-properties-pane")))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("document-properties")).toBeHidden();
  await expect(propertiesTrigger).toBeFocused();
  await filesTrigger.click();
  await page.getByRole("button", { name: "zettelkasten-principles.md", exact: true }).click();
  await expect(page.getByTestId("document-reader")).toBeFocused();
  await expect(page.getByLabel("Upload document")).toHaveCount(1);
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
