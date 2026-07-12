<script setup lang="ts">
import { FileText, X } from "@lucide/vue";
import type { DocumentContentData, DocumentTab } from "../../types";
import DocumentContent from "./DocumentContent.vue";
import UiEmptyState from "../ui/UiEmptyState.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import { useI18n } from "../../composables/useI18n";

const { t } = useI18n();

defineProps<{
  tabs: DocumentTab[];
  activeDocumentId: string;
  content: DocumentContentData | null;
  phase: "idle" | "loading" | "ready" | "empty" | "error";
  error: string;
  blobUrl: string | null;
  blobPhase: "idle" | "loading" | "ready" | "error";
  blobError: string;
}>();
const emit = defineEmits<{
  selectTab: [documentId: string];
  closeTab: [documentId: string];
  download: [];
  retry: [];
}>();
</script>

<template>
  <main data-testid="document-reader" class="reader" tabindex="-1" :aria-label="t('reader.landmark')">
    <div v-if="tabs.length" class="reader-tabs" role="tablist" :aria-label="t('reader.openDocuments')">
      <div v-for="tab in tabs" :key="tab.documentId" class="reader-tab" :class="{ active: activeDocumentId === tab.documentId }">
        <button type="button" role="tab" :aria-selected="activeDocumentId === tab.documentId" @click="emit('selectTab', tab.documentId)">
          <FileText />
          <span>{{ tab.title }}</span>
        </button>
        <button type="button" :aria-label="t('reader.closeDocument', { name: tab.title })" @click.stop="emit('closeTab', tab.documentId)"><X /></button>
      </div>
    </div>

    <section class="reader-body">
      <div v-if="phase === 'loading'" class="reader-loading" :aria-label="t('reader.loadingDocument')">
        <UiSkeleton width="42%" height="2.4rem" />
        <UiSkeleton width="90%" height="0.85rem" />
        <UiSkeleton width="76%" height="0.85rem" />
        <UiSkeleton width="100%" height="12rem" />
      </div>
      <UiEmptyState v-else-if="phase === 'idle'" :title="t('reader.openSource')" :description="t('reader.openSourceDescription')">
        <template #icon><FileText /></template>
      </UiEmptyState>
      <UiEmptyState v-else-if="phase === 'empty'" :title="t('reader.empty')" :description="t('reader.emptyDescription')" />
      <UiEmptyState v-else-if="phase === 'error'" :title="t('reader.unavailable')" :description="error || t('reader.unavailableDescription')">
        <template #action><button type="button" @click="emit('download')">{{ t("reader.downloadOriginal") }}</button></template>
      </UiEmptyState>
      <DocumentContent v-else-if="content" :content="content" :blob-url="blobUrl" :blob-phase="blobPhase" :blob-error="blobError" @download="emit('download')" @retry="emit('retry')" />
    </section>

    <footer v-if="content" class="reader-status">
      <span data-testid="document-reader-title">{{ content.file_name }}</span>
      <span>{{ content.render_mode }} · {{ content.mime_type }}</span>
    </footer>
  </main>
</template>

<style scoped>
.reader { display: grid; min-width: 0; min-height: 0; grid-template-rows: auto minmax(0, 1fr) auto; background: var(--bg-canvas); }
.reader-tabs { display: flex; min-height: 2.45rem; overflow-x: auto; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-muted); scrollbar-width: thin; }
.reader-tab { display: flex; min-width: 0; align-items: center; border-right: 1px solid var(--border-muted); }
.reader-tab.active { background: var(--bg-canvas); box-shadow: inset 0 -2px var(--accent); }
.reader-tab > button:first-child { display: flex; min-width: 7rem; max-width: 13rem; height: 100%; align-items: center; gap: 0.45rem; padding: 0 0.55rem 0 0.75rem; color: var(--text-secondary); background: transparent; border: 0; }
.reader-tab.active > button:first-child { color: var(--text-primary); }
.reader-tab span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.72rem; }
.reader-tab svg { width: 0.85rem; flex: 0 0 auto; }
.reader-tab > button:last-child { display: grid; width: 1.8rem; height: 100%; place-items: center; color: var(--text-tertiary); background: transparent; border: 0; }
.reader-tab > button:last-child:hover { color: var(--text-primary); background: var(--bg-elevated); }
.reader-body { min-height: 0; overflow: auto; }
.reader-loading { display: grid; width: min(100%, 760px); gap: 1rem; margin: 0 auto; padding: clamp(2rem, 6vw, 5rem); }
.reader-status { display: flex; min-height: 1.75rem; align-items: center; justify-content: space-between; gap: 1rem; padding: 0 0.7rem; color: var(--text-tertiary); background: var(--bg-sidebar); border-top: 1px solid var(--border-muted); font: 0.62rem var(--font-mono); }
.reader-status span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.reader button:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
@media (max-width: 767px) { .reader-tabs { min-height: 2.25rem; } .reader-tab > button:first-child { max-width: 10rem; } .reader-status span:last-child { display: none; } }
</style>
