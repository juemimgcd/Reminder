import { onBeforeUnmount, ref, watch, type ComputedRef, type Ref } from "vue";
import { api } from "../lib/api";
import type {
  DocumentContentData,
  DocumentFolderData,
  DocumentPreviewData,
  DocumentTab,
  DocumentUploadData,
  DocumentVersionData,
  WorkspaceView,
} from "../types";

type ContentPhase = "idle" | "loading" | "ready" | "empty" | "error";

export function useDocumentWorkspace(params: {
  token: Ref<string>;
  activeKnowledgeBaseId: ComputedRef<string>;
  view: Ref<WorkspaceView>;
  invalidateWorkspace: () => void;
}) {
  const activeDocumentId = ref("");
  const selectedFolderId = ref("");
  const openDocumentTabs = ref<DocumentTab[]>([]);
  const documentFolders = ref<DocumentFolderData[]>([]);
  const documentContent = ref<DocumentContentData | null>(null);
  const documentPreview = ref<DocumentPreviewData | null>(null);
  const documentVersions = ref<DocumentVersionData[]>([]);
  const documentContentPhase = ref<ContentPhase>("idle");
  const documentContentError = ref("");
  const duplicateUpload = ref<DocumentUploadData | null>(null);
  const contentCache = new Map<string, DocumentContentData>();
  let contentAbort: AbortController | null = null;
  let openGeneration = 0;

  function revokeTabBlob(documentId: string) {
    const tab = openDocumentTabs.value.find((item) => item.documentId === documentId);
    if (!tab?.blobUrl) return;
    URL.revokeObjectURL(tab.blobUrl);
    tab.blobUrl = null;
  }

  function clearDocumentSession() {
    openGeneration += 1;
    contentAbort?.abort();
    contentAbort = null;
    openDocumentTabs.value.forEach((tab) => {
      if (tab.blobUrl) URL.revokeObjectURL(tab.blobUrl);
    });
    openDocumentTabs.value = [];
    documentFolders.value = [];
    activeDocumentId.value = "";
    selectedFolderId.value = "";
    documentContent.value = null;
    documentPreview.value = null;
    documentVersions.value = [];
    documentContentPhase.value = "idle";
    documentContentError.value = "";
    duplicateUpload.value = null;
    contentCache.clear();
  }

  async function openDocument(documentId: string) {
    if (!documentId || !params.token.value) return;

    const previousDocumentId = activeDocumentId.value;
    if (previousDocumentId && previousDocumentId !== documentId) revokeTabBlob(previousDocumentId);
    activeDocumentId.value = documentId;
    params.view.value = "notes";
    contentAbort?.abort();
    const controller = new AbortController();
    contentAbort = controller;
    const generation = ++openGeneration;
    documentContentPhase.value = "loading";
    documentContentError.value = "";

    try {
      const cachedContent = contentCache.get(documentId);
      const [content, preview, versions] = await Promise.all([
        cachedContent ?? api.documentContent(params.token.value, documentId, { signal: controller.signal }),
        api.documentPreview(params.token.value, documentId),
        api.documentVersions(params.token.value, documentId),
      ]);
      if (generation !== openGeneration || controller.signal.aborted || activeDocumentId.value !== documentId) return;

      contentCache.set(documentId, content);
      documentContent.value = content;
      documentPreview.value = preview;
      documentVersions.value = versions.items;
      selectedFolderId.value = content.folder_id;
      documentContentPhase.value = content.text || content.sections.length || content.render_mode === "pdf" ? "ready" : "empty";
      if (!openDocumentTabs.value.some((tab) => tab.documentId === documentId)) {
        openDocumentTabs.value = [
          ...openDocumentTabs.value,
          { documentId, title: content.file_name, blobUrl: null },
        ];
      }
    } catch (error) {
      if (generation !== openGeneration || (error instanceof Error && error.name === "AbortError")) return;
      documentContent.value = null;
      documentPreview.value = null;
      documentVersions.value = [];
      documentContentPhase.value = "error";
      documentContentError.value = error instanceof Error ? error.message : "Unable to open this document.";
    } finally {
      if (contentAbort === controller) contentAbort = null;
    }
  }

  async function ensureDocumentBlob(documentId = activeDocumentId.value) {
    const tab = openDocumentTabs.value.find((item) => item.documentId === documentId);
    if (!tab || tab.blobUrl) return tab?.blobUrl ?? null;
    const blob = await api.documentRawBlob(params.token.value, documentId, "inline");
    if (activeDocumentId.value !== documentId) return null;
    const currentTab = openDocumentTabs.value.find((item) => item.documentId === documentId);
    if (!currentTab) return null;
    if (currentTab.blobUrl) return currentTab.blobUrl;
    currentTab.blobUrl = URL.createObjectURL(blob);
    return currentTab.blobUrl;
  }

  function closeDocument(documentId: string) {
    revokeTabBlob(documentId);
    const remaining = openDocumentTabs.value.filter((item) => item.documentId !== documentId);
    openDocumentTabs.value = remaining;
    if (activeDocumentId.value !== documentId) return;
    const next = remaining.at(-1);
    if (next) {
      void openDocument(next.documentId);
      return;
    }
    openGeneration += 1;
    contentAbort?.abort();
    activeDocumentId.value = "";
    documentContent.value = null;
    documentPreview.value = null;
    documentVersions.value = [];
    documentContentPhase.value = "idle";
    documentContentError.value = "";
  }

  async function refreshDocumentFolders() {
    if (!params.token.value || !params.activeKnowledgeBaseId.value) {
      documentFolders.value = [];
      return;
    }
    documentFolders.value = await api.listDocumentFolders(params.token.value, params.activeKnowledgeBaseId.value);
  }

  async function createFolder(parentId: string, name: string) {
    const created = await api.createDocumentFolder(params.token.value, {
      knowledge_base_id: params.activeKnowledgeBaseId.value,
      parent_id: parentId,
      name,
    });
    params.invalidateWorkspace();
    await refreshDocumentFolders();
    return created;
  }

  async function updateFolder(folderId: string, payload: { name?: string; parent_id?: string }) {
    const updated = await api.updateDocumentFolder(params.token.value, folderId, payload);
    params.invalidateWorkspace();
    await refreshDocumentFolders();
    return updated;
  }

  async function deleteFolder(folderId: string) {
    const deleted = await api.deleteDocumentFolder(params.token.value, folderId);
    params.invalidateWorkspace();
    await refreshDocumentFolders();
    return deleted;
  }

  async function moveDocument(documentId: string, folderId: string) {
    const moved = await api.moveDocument(params.token.value, documentId, folderId);
    params.invalidateWorkspace();
    selectedFolderId.value = folderId;
    return moved;
  }

  async function uploadDocument(file: File, userId: number | null, folderId?: string | null) {
    const result = await api.uploadDocument(params.token.value, {
      file,
      userId,
      knowledgeBaseId: params.activeKnowledgeBaseId.value,
      ...(folderId ? { folderId } : {}),
    });
    if (result.disposition === "duplicate") {
      duplicateUpload.value = result;
      return result;
    }
    duplicateUpload.value = null;
    params.invalidateWorkspace();
    await openDocument(result.canonical_document_id);
    return result;
  }

  function openDuplicateUpload() {
    const canonicalId = duplicateUpload.value?.canonical_document_id;
    if (canonicalId) void openDocument(canonicalId);
  }

  function dismissDuplicateUpload() {
    duplicateUpload.value = null;
  }

  watch(params.token, (nextToken, previousToken) => {
    if (!nextToken && previousToken) clearDocumentSession();
  });
  watch(params.activeKnowledgeBaseId, () => {
    clearDocumentSession();
  });
  onBeforeUnmount(clearDocumentSession);

  return {
    activeDocumentId,
    closeDocument,
    createFolder,
    deleteFolder,
    dismissDuplicateUpload,
    documentContent,
    documentContentError,
    documentContentPhase,
    documentFolders,
    documentPreview,
    documentVersions,
    duplicateUpload,
    ensureDocumentBlob,
    moveDocument,
    openDocument,
    openDocumentTabs,
    openDuplicateUpload,
    refreshDocumentFolders,
    selectedFolderId,
    updateFolder,
    uploadDocument,
  };
}
