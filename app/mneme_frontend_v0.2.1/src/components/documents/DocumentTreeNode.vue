<script setup lang="ts">
import { ChevronRight, FileText, Folder, FolderOpen, MoreHorizontal } from "@lucide/vue";
import { computed, ref } from "vue";
import type { DocumentFolderData, DocumentListItem } from "../../types";

const props = defineProps<{
  folder: DocumentFolderData;
  folders: DocumentFolderData[];
  documents: DocumentListItem[];
  activeDocumentId: string;
  depth: number;
}>();
const emit = defineEmits<{
  openDocument: [documentId: string];
  selectFolder: [folderId: string];
  moveDocument: [documentId: string, folderId: string];
}>();
const expanded = ref(true);
const movingDocumentId = ref("");
const childFolders = computed(() => props.folders.filter((folder) => !folder.is_root && folder.parent_id === props.folder.id));
const folderDocuments = computed(() => props.documents.filter((document) => document.folder_id === props.folder.id));

function startDrag(event: DragEvent, documentId: string) {
  event.dataTransfer?.setData("application/x-mneme-document", documentId);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
}

function dropDocument(event: DragEvent) {
  const documentId = event.dataTransfer?.getData("application/x-mneme-document");
  if (documentId) emit("moveDocument", documentId, props.folder.id);
}
</script>

<template>
  <li
    role="treeitem"
    :aria-expanded="expanded"
    :data-testid="`folder-${folder.name}`"
    class="folder-node"
    @dragover.prevent
    @drop.prevent="dropDocument"
  >
    <div class="folder-row" :style="{ '--tree-depth': depth }">
      <button type="button" class="folder-toggle" :aria-label="`${expanded ? 'Collapse' : 'Expand'} ${folder.name}`" @click="expanded = !expanded">
        <ChevronRight :class="{ expanded }" />
      </button>
      <button type="button" class="folder-name" @click="emit('selectFolder', folder.id)">
        <FolderOpen v-if="expanded" /><Folder v-else />
        <span>{{ folder.name }}</span>
      </button>
    </div>

    <ul v-show="expanded" role="group">
      <li v-for="document in folderDocuments" :key="document.id" class="document-row" :class="{ active: activeDocumentId === document.id }" :style="{ '--tree-depth': depth + 1 }">
        <button type="button" draggable="true" @dragstart="startDrag($event, document.id)" @dblclick="emit('openDocument', document.id)" @click="emit('openDocument', document.id)">
          <FileText /><span>{{ document.file_name }}</span><small v-if="document.version_number > 1">v{{ document.version_number }}</small>
        </button>
        <button type="button" :aria-label="`Move ${document.file_name}`" @click="movingDocumentId = movingDocumentId === document.id ? '' : document.id"><MoreHorizontal /></button>
        <div v-if="movingDocumentId === document.id" class="move-menu" role="listbox" aria-label="Move document">
          <button
            v-for="target in folders.filter((item) => item.id !== folder.id)"
            :key="target.id"
            type="button"
            role="option"
            :aria-selected="false"
            @click="emit('moveDocument', document.id, target.id); movingDocumentId = ''"
          >{{ target.is_root ? "Vault root" : target.name }}</button>
        </div>
      </li>
      <DocumentTreeNode
        v-for="child in childFolders"
        :key="child.id"
        :folder="child"
        :folders="folders"
        :documents="documents"
        :active-document-id="activeDocumentId"
        :depth="depth + 1"
        @open-document="emit('openDocument', $event)"
        @select-folder="emit('selectFolder', $event)"
        @move-document="(documentId, folderId) => emit('moveDocument', documentId, folderId)"
      />
    </ul>
  </li>
</template>

<style scoped>
ul { margin: 0; padding: 0; list-style: none; }
.folder-row { display: grid; grid-template-columns: 1.45rem minmax(0, 1fr); align-items: center; padding-left: calc(var(--tree-depth) * 0.72rem); }
.folder-row button, .document-row > button { color: var(--text-secondary); background: transparent; border: 0; }
.folder-toggle { display: grid; width: 1.45rem; height: 1.9rem; place-items: center; }
.folder-toggle svg { width: 0.78rem; transition: transform 140ms ease; }
.folder-toggle svg.expanded { transform: rotate(90deg); }
.folder-name { display: flex; min-width: 0; height: 1.9rem; align-items: center; gap: 0.4rem; padding: 0 0.3rem; text-align: left; }
.folder-name svg, .document-row svg { width: 0.9rem; flex: 0 0 auto; color: var(--accent); }
.folder-name span, .document-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.document-row { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 1.7rem; align-items: center; padding-left: calc(var(--tree-depth) * 0.72rem + 1.45rem); }
.document-row.active { background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent); }
.document-row > button:first-child { display: flex; min-width: 0; height: 1.9rem; align-items: center; gap: 0.4rem; padding: 0 0.3rem; text-align: left; font-size: 0.73rem; }
.document-row > button:last-of-type { display: grid; width: 1.7rem; height: 1.7rem; place-items: center; opacity: 0; }
.document-row:hover > button:last-of-type, .document-row:focus-within > button:last-of-type { opacity: 1; }
.document-row small { margin-left: auto; color: var(--accent); font: 0.58rem var(--font-mono); }
.move-menu { position: absolute; z-index: 8; top: 1.8rem; right: 0.3rem; display: grid; min-width: 9rem; padding: 0.25rem; background: var(--bg-elevated); border: 1px solid var(--border-muted); border-radius: 0.4rem; box-shadow: var(--shadow-float); }
.move-menu button { padding: 0.45rem 0.55rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.25rem; font-size: 0.72rem; }
.move-menu button:hover { color: var(--text-primary); background: var(--accent-soft); }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
</style>
