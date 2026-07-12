import { expect, test } from "@playwright/test";

async function revealRecentFiles(page: import("@playwright/test").Page) {
  const recentFiles = page.getByTestId("sidebar-group-files");
  if (!(await recentFiles.isVisible())) {
    await page.getByRole("button", { name: "Open resources" }).click();
  }
  await expect(recentFiles).toBeVisible();
  return recentFiles;
}

test("opening a recent file reaches the unified reader", async ({ page }) => {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  await (await revealRecentFiles(page))
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
  const recentFiles = await revealRecentFiles(page);
  await expect(
    recentFiles.getByRole("button", { name: /workspace-state/i }),
  ).toBeVisible();
});

for (const scenario of ["switch-away-and-back", "close-and-reopen", "logout-and-relogin"] as const) {
  test(`late PDF raw responses cannot cross the ${scenario} boundary`, async ({ page }) => {
    await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
    const createdUrls = await page.evaluate(async (boundary) => {
      const importModule = (path: string) => import(/* @vite-ignore */ path);
      const vue = await importModule("/node_modules/.vite/deps/vue.js");
      const { api } = await importModule("/src/lib/api.ts");
      const { useDocumentWorkspace } = await importModule("/src/composables/useDocumentWorkspace.ts");
      const token = vue.ref("token-pdf");
      const view = vue.ref("notes");
      const activeKnowledgeBaseId = vue.computed(() => "kb-pdf");
      const resolvers: Array<(blob: Blob) => void> = [];
      const urls: string[] = [];
      Object.defineProperty(URL, "createObjectURL", {
        configurable: true,
        value: (blob: Blob) => {
          const url = `blob:${blob.size === 3 ? "old" : "new"}`;
          urls.push(url);
          return url;
        },
      });
      Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: () => undefined });
      api.documentContent = async (_token: string, documentId: string) => ({ document_id: documentId, folder_id: "fld-root", file_name: `${documentId}.pdf`, render_mode: "pdf", mime_type: "application/pdf", text: null, sections: [], parse_warning: null });
      api.documentPreview = async (_token: string, documentId: string) => ({ document_id: documentId, knowledge_base_id: "kb-pdf", file_name: `${documentId}.pdf`, file_type: "pdf", status: "indexed", summary: "", chunks: [], memory_entries: [] });
      api.documentVersions = async () => ({ items: [], total: 0 });
      api.documentRawBlob = () => new Promise<Blob>((resolve) => resolvers.push(resolve));
      const workspace = useDocumentWorkspace({ token, activeKnowledgeBaseId, view, invalidateWorkspace: () => undefined });

      await workspace.openDocument("doc-a");
      const oldRaw = workspace.ensureDocumentBlob("doc-a");
      if (boundary === "switch-away-and-back") {
        await workspace.openDocument("doc-b");
        await workspace.openDocument("doc-a");
      } else if (boundary === "close-and-reopen") {
        workspace.closeDocument("doc-a");
        await workspace.openDocument("doc-a");
      } else {
        token.value = "";
        await vue.nextTick();
        token.value = "token-pdf-2";
        await workspace.openDocument("doc-a");
      }
      const newRaw = workspace.ensureDocumentBlob("doc-a");
      resolvers[0](new Blob(["old"]));
      await oldRaw;
      resolvers[1](new Blob(["new!"]));
      await newRaw;
      return urls;
    }, scenario);

    expect(createdUrls).toEqual(["blob:new"]);
  });
}

test("preview deduplication is scoped to the target knowledge base", async ({ page }) => {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  const results = await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    const bytes = "# Atomic notes";
    const duplicate = await api.uploadDocument("token", { file: new File([bytes], "copy.md", { type: "text/markdown" }), userId: 1, knowledgeBaseId: "kb-demo-research" });
    const independent = await api.uploadDocument("token", { file: new File([bytes], "copy.md", { type: "text/markdown" }), userId: 1, knowledgeBaseId: "kb-product-notes" });
    return { duplicate, independent };
  });

  expect(results.duplicate).toMatchObject({ disposition: "duplicate", document_id: "doc-zettelkasten", canonical_document_id: "doc-zettelkasten", knowledge_base_id: "kb-demo-research", file_name: "zettelkasten-principles.md" });
  expect(results.independent).toMatchObject({ disposition: "created", knowledge_base_id: "kb-product-notes" });
  expect(results.independent.document_id).toBe(results.independent.canonical_document_id);
});

test("preview duplicate response fields come from the actual target-KB canonical document", async ({ page }) => {
  await page.goto("/?preview=1", { waitUntil: "domcontentloaded" });
  const results = await page.evaluate(async () => {
    const importModule = (path: string) => import(/* @vite-ignore */ path);
    const { api } = await importModule("/src/lib/api.ts");
    const bytes = "canonical bytes for product vault";
    const canonical = await api.uploadDocument("token", { file: new File([bytes], "original.md", { type: "text/markdown" }), userId: 1, knowledgeBaseId: "kb-product-notes" });
    const duplicate = await api.uploadDocument("token", { file: new File([bytes], "renamed.txt", { type: "text/plain" }), userId: 1, knowledgeBaseId: "kb-product-notes" });
    return { canonical, duplicate };
  });

  expect(results.canonical.disposition).toBe("created");
  expect(results.duplicate.disposition).toBe("duplicate");
  expect(results.duplicate).toMatchObject({
    document_id: results.canonical.document_id,
    canonical_document_id: results.canonical.document_id,
    user_id: results.canonical.user_id,
    knowledge_base_id: results.canonical.knowledge_base_id,
    folder_id: results.canonical.folder_id,
    folder_path: results.canonical.folder_path,
    file_name: results.canonical.file_name,
    file_type: results.canonical.file_type,
    file_size: results.canonical.file_size,
    status: results.canonical.status,
    version_group_id: results.canonical.version_group_id,
    version_number: results.canonical.version_number,
  });
});
