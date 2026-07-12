<script setup lang="ts">
import { Download, Files, PanelRight, Trash2, WandSparkles, X } from "@lucide/vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import DocumentProperties from "../components/documents/DocumentProperties.vue";
import DocumentReader from "../components/documents/DocumentReader.vue";
import DocumentTree from "../components/documents/DocumentTree.vue";
import { useI18n } from "../composables/useI18n";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const { t } = useI18n();
defineEmits<{ create: [] }>();
const treeOpen = ref(true);
const propertiesOpen = ref(false);
const treeError = ref("");
const filesTrigger = ref<HTMLButtonElement | null>(null);
const propertiesTrigger = ref<HTMLButtonElement | null>(null);
const activeTab = computed(() => props.workspace.openDocumentTabs.value.find((tab) => tab.documentId === props.workspace.activeDocumentId.value));
const blobUrl = computed(() => activeTab.value?.blobUrl ?? null);

async function openDocument(documentId: string) {
  await props.workspace.openDocument(documentId);
  if (window.matchMedia("(max-width: 1100px)").matches) treeOpen.value = false;
}

async function createFolder(parentId: string, name: string) {
  treeError.value = "";
  try {
    const folder = await props.workspace.createFolder(parentId, name);
    props.workspace.selectedFolderId.value = folder.id;
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.createFolderError");
  }
}

async function renameFolder(folderId: string, name: string) {
  treeError.value = "";
  try {
    await props.workspace.updateFolder(folderId, { name });
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.renameFolderError");
  }
}

async function deleteFolder(folderId: string) {
  treeError.value = "";
  const hasDocuments = props.workspace.selectedDocuments.value.some((document) => document.folder_id === folderId);
  const hasChildren = props.workspace.documentFolders.value.some((folder) => folder.parent_id === folderId && folder.id !== folderId);
  if (hasDocuments || hasChildren) {
    treeError.value = t("reader.folderNotEmpty");
    return;
  }
  try {
    await props.workspace.deleteFolder(folderId);
    props.workspace.selectedFolderId.value = "";
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.folderNotEmpty");
  }
}

async function moveFolder(folderId: string, parentId: string) {
  treeError.value = "";
  try {
    await props.workspace.updateFolder(folderId, { parent_id: parentId });
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.moveFolderError");
  }
}

async function moveDocument(documentId: string, folderId: string) {
  treeError.value = "";
  try {
    await props.workspace.moveDocument(documentId, folderId);
    await props.workspace.loadKnowledgeBasePanels();
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.moveDocumentError");
  }
}

watch(
  () => [props.workspace.documentContent.value?.document_id, props.workspace.documentContent.value?.render_mode] as const,
  ([documentId, renderMode]) => {
    if (documentId && renderMode === "pdf") void props.workspace.ensureDocumentBlob(documentId);
  },
  { immediate: true },
);
watch(
  () => props.workspace.activeDocumentId.value,
  (documentId) => {
    if (documentId && window.matchMedia("(max-width: 1100px)").matches) treeOpen.value = false;
    if (documentId) void nextTick(() => document.querySelector<HTMLElement>('[data-testid="document-reader"]')?.focus());
  },
  { immediate: true },
);

function handleEscape(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (propertiesOpen.value) {
    propertiesOpen.value = false;
    void nextTick(() => propertiesTrigger.value?.focus());
  } else if (treeOpen.value && window.matchMedia("(max-width: 1100px)").matches) {
    treeOpen.value = false;
    void nextTick(() => filesTrigger.value?.focus());
  }
}

function toggleTree() {
  treeOpen.value = !treeOpen.value;
  if (treeOpen.value) propertiesOpen.value = false;
}

function toggleProperties() {
  propertiesOpen.value = !propertiesOpen.value;
  if (propertiesOpen.value) treeOpen.value = false;
}

onMounted(() => window.addEventListener("keydown", handleEscape));
onBeforeUnmount(() => window.removeEventListener("keydown", handleEscape));
</script>

<template>
  <section
    data-testid="document-workspace"
    class="document-workspace"
    :class="{ 'tree-open': treeOpen, 'properties-open': propertiesOpen }"
  >
    <div class="reader-mobile-tools">
      <button ref="filesTrigger" type="button" :aria-label="t('reader.files')" aria-controls="document-tree-pane" :aria-expanded="treeOpen" @click="toggleTree"><Files />{{ t("reader.files") }}</button>
      <span>{{ workspace.documentContent.value?.file_name ?? workspace.selectedKnowledgeBase.value?.name }}</span>
      <button ref="propertiesTrigger" type="button" :aria-label="t('reader.properties')" aria-controls="document-properties-pane" :aria-expanded="propertiesOpen" @click="toggleProperties"><PanelRight />{{ t("reader.properties") }}</button>
    </div>

    <DocumentTree
      :folders="workspace.documentFolders.value"
      :documents="workspace.selectedDocuments.value"
      :active-document-id="workspace.activeDocumentId.value"
      :selected-folder-id="workspace.selectedFolderId.value"
      :error="treeError"
      @open-document="openDocument"
      @create-folder="createFolder"
      @rename-folder="renameFolder"
      @delete-folder="deleteFolder"
      @move-folder="moveFolder"
      @interaction-error="treeError = $event"
      @move-document="moveDocument"
      @select-folder="workspace.selectedFolderId.value = $event"
    />

    <section class="reader-center">
      <div v-if="workspace.activeDocumentId.value" class="document-actions" :aria-label="t('reader.documentActions')">
        <button type="button" @click="workspace.downloadDocument()"><Download />{{ t("reader.download") }}</button>
        <button type="button" :disabled="workspace.documentPreview.value?.status === 'indexed'" @click="workspace.indexDocument(workspace.activeDocumentId.value)"><WandSparkles />{{ t("reader.index") }}</button>
        <button type="button" class="danger" @click="workspace.deleteDocument(workspace.activeDocumentId.value)"><Trash2 />{{ t("reader.delete") }}</button>
      </div>
      <DocumentReader
        :tabs="workspace.openDocumentTabs.value"
        :active-document-id="workspace.activeDocumentId.value"
        :content="workspace.documentContent.value"
        :phase="workspace.documentContentPhase.value"
        :error="workspace.documentContentError.value"
        :blob-url="blobUrl"
        :blob-phase="workspace.documentBlobPhase.value"
        :blob-error="workspace.documentBlobError.value"
        @select-tab="openDocument"
        @close-tab="workspace.closeDocument"
        @download="workspace.downloadDocument()"
        @retry="workspace.retryDocumentBlob()"
      />
    </section>

    <DocumentProperties
      :preview="workspace.documentPreview.value"
      :versions="workspace.documentVersions.value"
      :active-document-id="workspace.activeDocumentId.value"
      @select-version="openDocument"
    />
    <button v-if="treeOpen" class="overlay-dismiss tree-dismiss" :aria-label="t('reader.closeFiles')" @click="treeOpen = false; filesTrigger?.focus()"><X /></button>
    <button v-if="propertiesOpen" class="overlay-dismiss properties-dismiss" :aria-label="t('reader.closeProperties')" @click="propertiesOpen = false; propertiesTrigger?.focus()"><X /></button>
  </section>
</template>

<style scoped>
.document-workspace { position: relative; display: grid; width: 100%; height: 100%; min-height: 0; grid-template-columns: 230px minmax(0, 1fr) 270px; overflow: hidden; background: var(--bg-canvas); }
.reader-center { display: grid; min-width: 0; min-height: 0; grid-template-rows: auto minmax(0, 1fr); }
.document-actions { display: flex; min-height: 2.2rem; align-items: center; justify-content: flex-end; gap: 0.25rem; padding: 0.25rem 0.55rem; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-muted); }
.document-actions button { display: inline-flex; min-height: 1.7rem; align-items: center; gap: 0.3rem; padding: 0 0.45rem; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 0.3rem; font-size: 0.65rem; }
.document-actions button:hover:not(:disabled) { color: var(--text-primary); background: var(--bg-elevated); border-color: var(--border-muted); }
.document-actions button:disabled { opacity: 0.36; }
.document-actions button.danger { color: var(--danger); }
.document-actions svg { width: 0.75rem; }
.reader-mobile-tools, .overlay-dismiss { display: none; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

@media (max-width: 1100px) {
  .document-workspace { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
  .reader-mobile-tools { display: grid; z-index: 3; min-height: 2.6rem; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.5rem; padding: 0 0.55rem; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-muted); }
  .reader-mobile-tools button { display: flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0.45rem; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-muted); border-radius: 0.35rem; font-size: 0.68rem; }
  .reader-mobile-tools svg { width: 0.8rem; }
  .reader-mobile-tools span { overflow: hidden; color: var(--text-tertiary); text-align: center; text-overflow: ellipsis; white-space: nowrap; font: 0.62rem var(--font-mono); }
  .reader-center { grid-row: 2; grid-column: 1; }
  :deep([data-testid="document-tree-pane"]), :deep([data-testid="document-properties"]) { position: absolute; z-index: 12; top: 2.6rem; bottom: 0; display: none; width: min(86vw, 280px); box-shadow: var(--shadow-float); }
  :deep([data-testid="document-tree-pane"]) { left: 0; }
  :deep([data-testid="document-properties"]) { right: 0; }
  .tree-open :deep([data-testid="document-tree-pane"]), .properties-open :deep([data-testid="document-properties"]) { display: block; }
  .overlay-dismiss { position: absolute; z-index: 13; top: 3rem; display: grid; width: 1.8rem; height: 1.8rem; place-items: center; color: var(--text-secondary); background: var(--bg-elevated); border: 1px solid var(--border-muted); border-radius: 50%; box-shadow: var(--shadow-float); }
  .overlay-dismiss svg { width: 0.8rem; }
  .tree-dismiss { left: min(calc(86vw - 2.2rem), 240px); }
  .properties-dismiss { right: min(calc(86vw - 2.2rem), 240px); }
}

@media (max-width: 767px) {
  .document-actions { justify-content: space-between; }
  .document-actions button { flex: 1; justify-content: center; }
  .reader-mobile-tools { grid-template-columns: 1fr 1fr; }
  .reader-mobile-tools button { font-size: 0.62rem; }
  .reader-mobile-tools button svg { width: 1rem; }
  .reader-mobile-tools span { display: none; }
}
</style>
