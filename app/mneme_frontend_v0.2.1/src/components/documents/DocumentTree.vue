<script setup lang="ts">
import { FileText, FolderInput, FolderOpen, Pencil, Plus, Trash2, Upload } from "@lucide/vue";
import { computed, ref } from "vue";
import type { DocumentFolderData, DocumentListItem } from "../../types";
import DocumentTreeNode from "./DocumentTreeNode.vue";
import { useI18n } from "../../composables/useI18n";

const { t } = useI18n();

const props = defineProps<{
  folders: DocumentFolderData[];
  documents: DocumentListItem[];
  activeDocumentId: string;
  selectedFolderId: string;
  error: string;
}>();
const emit = defineEmits<{
  openDocument: [documentId: string];
  createFolder: [parentId: string, name: string];
  renameFolder: [folderId: string, name: string];
  moveDocument: [documentId: string, folderId: string];
  moveFolder: [folderId: string, parentId: string];
  deleteFolder: [folderId: string];
  selectFolder: [folderId: string];
  interactionError: [message: string];
}>();

const creating = ref(false);
const renaming = ref(false);
const movingFolder = ref(false);
const folderName = ref("");
const movingRootDocumentId = ref("");

const flatFolders = computed(() => {
  const byId = new Map<string, DocumentFolderData>();
  const visit = (folder: DocumentFolderData) => {
    if (byId.has(folder.id)) return;
    byId.set(folder.id, { ...folder, children: [] });
    folder.children?.forEach(visit);
  };
  props.folders.forEach(visit);
  return [...byId.values()];
});
const rootFolder = computed(() => flatFolders.value.find((folder) => folder.is_root) ?? flatFolders.value[0]);
const topFolders = computed(() => flatFolders.value.filter((folder) => !folder.is_root && folder.parent_id === rootFolder.value?.id));

const latestDocuments = computed(() => {
  const latest = new Map<string, DocumentListItem>();
  props.documents.filter((document) => !document.duplicate_of_document_id).forEach((document) => {
    const key = document.version_group_id || document.id;
    const current = latest.get(key);
    if (!current || document.version_number > current.version_number || (document.version_number === current.version_number && document.created_at > current.created_at)) {
      latest.set(key, document);
    }
  });
  return [...latest.values()];
});
const rootDocuments = computed(() => latestDocuments.value.filter((document) => document.folder_id === rootFolder.value?.id));
const parentForNewFolder = computed(() => selectedFolder.value?.id || rootFolder.value?.id || "");
const selectedFolder = computed(() => flatFolders.value.find((folder) => folder.id === props.selectedFolderId));

function submitCreate() {
  const name = folderName.value.trim();
  if (!name || !parentForNewFolder.value) return;
  emit("createFolder", parentForNewFolder.value, name);
  folderName.value = "";
  creating.value = false;
}

function submitRename() {
  const name = folderName.value.trim();
  if (!name || !selectedFolder.value || selectedFolder.value.is_root) return;
  emit("renameFolder", selectedFolder.value.id, name);
  folderName.value = "";
  renaming.value = false;
}

function startRootDrag(event: DragEvent, documentId: string) {
  event.dataTransfer?.setData("application/x-mneme-document", documentId);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}

function isDescendant(folderId: string, possibleDescendantId: string) {
  let current = flatFolders.value.find((folder) => folder.id === possibleDescendantId);
  const visited = new Set<string>();
  while (current && !current.is_root && !visited.has(current.id)) {
    if (current.parent_id === folderId) return true;
    visited.add(current.id);
    current = flatFolders.value.find((folder) => folder.id === current?.parent_id);
  }
  return false;
}

function requestFolderMove(folderId: string, parentId: string) {
  if (folderId === parentId || isDescendant(folderId, parentId)) {
    emit("interactionError", t("reader.folderCycleError"));
    return;
  }
  emit("moveFolder", folderId, parentId);
}

function dropOnRoot(event: DragEvent) {
  const folderId = event.dataTransfer?.getData("application/x-mneme-folder");
  if (folderId && rootFolder.value) requestFolderMove(folderId, rootFolder.value.id);
  const documentId = event.dataTransfer?.getData("application/x-mneme-document");
  if (documentId && rootFolder.value) emit("moveDocument", documentId, rootFolder.value.id);
}

function triggerUpload() {
  document.getElementById("workspace-upload")?.click();
}
</script>

<template>
  <aside id="document-tree-pane" data-testid="document-tree-pane" class="tree-pane" :aria-label="t('reader.files')">
    <header>
      <div><small>{{ t("vault.active") }}</small><h2>{{ t("reader.files") }}</h2></div>
      <label class="upload-control" for="workspace-upload" tabindex="0" :title="t('reader.uploadDocument')" @keydown.enter.prevent="triggerUpload" @keydown.space.prevent="triggerUpload"><Upload /><span>{{ t("reader.upload") }}</span></label>
    </header>
    <div class="tree-toolbar">
      <button type="button" @click="creating = !creating; renaming = false; folderName = ''"><Plus />{{ t("reader.newFolder") }}</button>
      <button type="button" :disabled="!selectedFolder || selectedFolder.is_root" :aria-label="t('reader.renameFolder')" @click="renaming = !renaming; creating = false; folderName = selectedFolder?.name ?? ''"><Pencil /></button>
      <button type="button" :disabled="!selectedFolder || selectedFolder.is_root" :aria-label="t('reader.moveFolder')" @click="movingFolder = !movingFolder"><FolderInput /></button>
      <button type="button" :disabled="!selectedFolder || selectedFolder.is_root" :aria-label="t('reader.deleteFolder')" @click="selectedFolder && emit('deleteFolder', selectedFolder.id)"><Trash2 /></button>
    </div>
    <div v-if="movingFolder && selectedFolder" class="folder-move-menu" role="listbox" :aria-label="t('reader.moveFolder')" @keydown.esc.stop="movingFolder = false">
      <button
        v-for="target in flatFolders.filter((item) => item.id !== selectedFolder?.id)"
        :key="target.id"
        type="button"
        role="option"
        :aria-selected="false"
        @click="requestFolderMove(selectedFolder.id, target.id); movingFolder = false"
      >{{ target.is_root ? t("reader.vaultRoot") : target.name }}</button>
    </div>
    <form v-if="creating || renaming" class="folder-form" @submit.prevent="creating ? submitCreate() : submitRename()">
      <label for="folder-name">{{ t("reader.folderName") }}</label>
      <input id="folder-name" v-model="folderName" autofocus maxlength="255" />
      <div><button type="submit">{{ creating ? t("reader.createFolder") : t("reader.renameFolder") }}</button><button type="button" @click="creating = false; renaming = false">{{ t("reader.cancel") }}</button></div>
    </form>
    <p v-if="error" class="tree-error" role="alert">{{ error }}</p>

    <nav data-testid="document-tree" class="tree-scroll" :aria-label="t('reader.documentFiles')">
      <ul role="tree" :aria-label="t('reader.vaultFolders')">
        <li v-if="rootFolder" role="treeitem" aria-expanded="true" class="root-node" @dragover.prevent @drop.prevent.stop="dropOnRoot">
          <button type="button" class="root-name" @click="emit('selectFolder', rootFolder.id)"><FolderOpen />{{ t("reader.vaultRoot") }}</button>
          <ul role="group">
        <li v-for="document in rootDocuments" :key="document.id" role="treeitem" class="root-document" :class="{ active: activeDocumentId === document.id }">
          <button type="button" draggable="true" @dragstart="startRootDrag($event, document.id)" @click="emit('openDocument', document.id)"><FileText /><span>{{ document.file_name }}</span><small v-if="document.version_number > 1">v{{ document.version_number }}</small></button>
          <button type="button" :aria-label="t('reader.moveDocument', { name: document.file_name })" @click="movingRootDocumentId = movingRootDocumentId === document.id ? '' : document.id" @keydown.esc.stop="movingRootDocumentId = ''"><FolderInput /></button>
          <div v-if="movingRootDocumentId === document.id" class="root-move-menu" role="listbox" :aria-label="t('reader.moveDocumentMenu')" @keydown.esc.stop="movingRootDocumentId = ''">
            <button
              v-for="target in flatFolders.filter((item) => !item.is_root)"
              :key="target.id"
              type="button"
              role="option"
              :aria-selected="false"
              @click="emit('moveDocument', document.id, target.id); movingRootDocumentId = ''"
            >{{ target.name }}</button>
          </div>
        </li>
        <DocumentTreeNode
          v-for="folder in topFolders"
          :key="folder.id"
          :folder="folder"
          :folders="flatFolders"
          :documents="latestDocuments"
          :active-document-id="activeDocumentId"
          :depth="0"
          @open-document="emit('openDocument', $event)"
          @select-folder="emit('selectFolder', $event)"
          @move-document="(documentId, folderId) => emit('moveDocument', documentId, folderId)"
          @move-folder="requestFolderMove"
        />
          </ul>
        </li>
      </ul>
      <p v-if="!latestDocuments.length" class="tree-empty">{{ t("reader.noDocuments") }}</p>
    </nav>
  </aside>
</template>

<style scoped>
.tree-pane { min-width: 0; min-height: 0; overflow: hidden; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.tree-pane > header { display: flex; min-height: 3.9rem; align-items: center; justify-content: space-between; gap: 0.75rem; padding: 0.7rem 0.8rem; border-bottom: 1px solid var(--border-muted); }
.tree-pane small { color: var(--text-tertiary); font: 0.58rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.08em; }
.tree-pane h2 { margin: 0.12rem 0 0; font: 600 1rem var(--font-serif); }
.upload-control { display: inline-flex; min-width: 2rem; min-height: 2rem; align-items: center; justify-content: center; gap: 0.3rem; padding: 0 0.45rem; color: var(--text-secondary); border: 1px solid var(--border-muted); border-radius: 0.35rem; cursor: pointer; font-size: 0.65rem; }
.upload-control:hover { color: var(--accent); background: var(--accent-soft); }
.upload-control svg { width: 0.9rem; }
.tree-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) 2rem 2rem 2rem; gap: 0.25rem; padding: 0.5rem; border-bottom: 1px solid var(--border-muted); }
.tree-toolbar button { display: flex; min-height: 2rem; align-items: center; justify-content: center; gap: 0.35rem; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 0.35rem; font-size: 0.68rem; }
.tree-toolbar button:first-child { justify-content: flex-start; padding: 0 0.5rem; }
.tree-toolbar button:hover:not(:disabled) { color: var(--text-primary); background: var(--bg-elevated); border-color: var(--border-muted); }
.tree-toolbar button:disabled { opacity: 0.32; }
.tree-toolbar svg { width: 0.8rem; }
.folder-form { display: grid; gap: 0.4rem; padding: 0.65rem; background: var(--bg-panel); border-bottom: 1px solid var(--border-muted); }
.folder-form label { color: var(--text-tertiary); font: 0.6rem var(--font-mono); }
.folder-form input { min-width: 0; height: 2rem; padding: 0 0.5rem; color: var(--text-primary); background: var(--bg-canvas); border: 1px solid var(--accent); border-radius: 0.3rem; }
.folder-form div { display: flex; gap: 0.3rem; }
.folder-form button { padding: 0.35rem 0.5rem; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-muted); border-radius: 0.3rem; font-size: 0.65rem; }
.folder-move-menu { display: grid; gap: 0.15rem; padding: 0.35rem 0.5rem; background: var(--bg-panel); border-bottom: 1px solid var(--border-muted); }
.folder-move-menu button { padding: 0.4rem 0.5rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.3rem; font-size: 0.7rem; }
.folder-move-menu button:hover { color: var(--text-primary); background: var(--accent-soft); }
.tree-error { margin: 0; padding: 0.55rem 0.7rem; color: var(--danger); background: color-mix(in srgb, var(--danger) 8%, transparent); border-bottom: 1px solid var(--border-muted); font-size: 0.68rem; }
.tree-scroll { height: calc(100% - 7rem); overflow: auto; padding: 0.35rem 0; }
.tree-scroll ul { margin: 0; padding: 0; list-style: none; }
.root-name { display: flex; width: 100%; min-height: 1.9rem; align-items: center; gap: 0.4rem; padding: 0 0.65rem; color: var(--text-secondary); background: transparent; border: 0; font-size: 0.7rem; text-align: left; }
.root-name svg { width: 0.9rem; color: var(--accent); }
.root-document { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 1.7rem; align-items: center; padding-left: 1.45rem; }
.root-document.active { background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent); }
.root-document button { color: var(--text-secondary); background: transparent; border: 0; }
.root-document button:first-child { display: flex; min-width: 0; height: 1.9rem; align-items: center; gap: 0.4rem; text-align: left; }
.root-document button:last-child { display: grid; width: 1.7rem; height: 1.7rem; place-items: center; opacity: 0; }
.root-document:hover button:last-child, .root-document:focus-within button:last-child { opacity: 1; }
.root-document svg { width: 0.85rem; color: var(--accent); }
.root-document span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.73rem; }
.root-document small { margin-left: auto; color: var(--accent); }
.root-move-menu { position: absolute; z-index: 8; top: 1.8rem; right: 0.3rem; display: grid; min-width: 9rem; padding: 0.25rem; background: var(--bg-elevated); border: 1px solid var(--border-muted); border-radius: 0.4rem; box-shadow: var(--shadow-float); }
.root-move-menu button { padding: 0.45rem 0.55rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.25rem; font-size: 0.72rem; }
.root-move-menu button:hover { color: var(--text-primary); background: var(--accent-soft); }
.tree-empty { padding: 1rem; color: var(--text-tertiary); font-size: 0.72rem; text-align: center; }
button:focus-visible, label:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
</style>
