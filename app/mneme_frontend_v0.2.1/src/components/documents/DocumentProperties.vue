<script setup lang="ts">
import { BookOpen, FileClock, Link2, Tag } from "@lucide/vue";
import type { DocumentPreviewData, DocumentVersionData } from "../../types";
import { useI18n } from "../../composables/useI18n";

const { formatDate, t } = useI18n();

defineProps<{
  preview: DocumentPreviewData | null;
  versions: DocumentVersionData[];
  activeDocumentId: string;
}>();
const emit = defineEmits<{ selectVersion: [documentId: string] }>();
</script>

<template>
  <aside id="document-properties-pane" data-testid="document-properties" class="properties" :aria-label="t('reader.properties')" tabindex="-1">
    <header><small>{{ t("reader.inspector") }}</small><h2>{{ t("reader.properties") }}</h2></header>
    <div v-if="preview" class="properties-scroll">
      <section>
        <h3><BookOpen /> {{ t("reader.source") }}</h3>
        <dl>
          <div><dt>{{ t("reader.type") }}</dt><dd>{{ preview.file_type }}</dd></div>
          <div><dt>{{ t("reader.status") }}</dt><dd><span class="status-dot" />{{ preview.status }}</dd></div>
          <div><dt>{{ t("reader.version") }}</dt><dd>v{{ preview.version_number ?? 1 }}</dd></div>
        </dl>
      </section>

      <section v-if="preview.summary">
        <h3><Tag /> {{ t("reader.summary") }}</h3>
        <p>{{ preview.summary }}</p>
      </section>

      <section data-testid="document-version-history">
        <h3><FileClock /> {{ t("reader.versionHistory") }}</h3>
        <div class="version-list">
          <button
            v-for="version in versions"
            :key="version.document_id"
            type="button"
            :class="{ active: version.document_id === activeDocumentId }"
            @click="emit('selectVersion', version.document_id)"
          >
            <span>v{{ version.version_number }}</span>
            <small>{{ formatDate(version.created_at) }}</small>
          </button>
          <p v-if="!versions.length">{{ t("reader.noVersions") }}</p>
        </div>
      </section>

      <section>
        <h3><Link2 /> {{ t("reader.backlinks") }}</h3>
        <p>{{ t("reader.linkedMemories", { count: preview.memory_entries.length }) }}</p>
        <ul v-if="preview.memory_entries.length">
          <li v-for="memory in preview.memory_entries" :key="memory.entry_id">{{ memory.entry_name }}</li>
        </ul>
      </section>
    </div>
    <p v-else class="properties-empty">{{ t("reader.propertiesEmpty") }}</p>
  </aside>
</template>

<style scoped>
.properties { min-width: 0; min-height: 0; overflow: hidden; background: var(--bg-sidebar); border-left: 1px solid var(--border-muted); }
.properties > header { padding: 0.9rem 1rem 0.75rem; border-bottom: 1px solid var(--border-muted); }
.properties small { color: var(--text-tertiary); font: 0.6rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.08em; }
.properties h2 { margin: 0.15rem 0 0; font: 600 1rem var(--font-serif); }
.properties-scroll { height: calc(100% - 3.9rem); overflow: auto; padding: 0 1rem 2rem; }
.properties section { padding: 1rem 0; border-bottom: 1px solid var(--border-muted); }
.properties h3 { display: flex; align-items: center; gap: 0.45rem; margin: 0 0 0.7rem; color: var(--text-secondary); font: 600 0.68rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.06em; }
.properties h3 svg { width: 0.85rem; color: var(--accent); }
.properties dl { display: grid; gap: 0.5rem; margin: 0; }
.properties dl div { display: flex; align-items: center; justify-content: space-between; gap: 0.8rem; }
.properties dt, .properties p, .properties li { color: var(--text-secondary); font-size: 0.75rem; line-height: 1.55; }
.properties dd { display: flex; align-items: center; gap: 0.35rem; margin: 0; color: var(--text-primary); font: 0.68rem var(--font-mono); }
.status-dot { width: 0.42rem; height: 0.42rem; background: var(--success); border-radius: 50%; }
.version-list { display: grid; gap: 0.25rem; }
.version-list button { display: flex; min-height: 2.2rem; align-items: center; justify-content: space-between; padding: 0 0.55rem; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 0.35rem; }
.version-list button:hover { background: var(--bg-elevated); }
.version-list button.active { color: var(--text-primary); background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 32%, transparent); }
.version-list small { text-transform: none; letter-spacing: 0; }
.properties ul { margin: 0.5rem 0 0; padding-left: 1rem; }
.properties-empty { margin: 0; padding: 1.2rem 1rem; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
</style>
