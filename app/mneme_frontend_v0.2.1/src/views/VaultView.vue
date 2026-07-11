<script setup lang="ts">
import { File, FilePlus2, FolderOpen, LayoutGrid, List, Plus } from "@lucide/vue";
import { computed, ref } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import { useI18n } from "../composables/useI18n";
import UiEmptyState from "../components/ui/UiEmptyState.vue";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const { t } = useI18n();
const emit = defineEmits<{ create: [] }>();
const statusFilter = ref<"all" | "indexed">("all");
const compact = ref(false);
const visibleDocuments = computed(() => props.workspace.selectedDocuments.value.filter((doc) => statusFilter.value === "all" || doc.status === "indexed"));
</script>

<template>
  <div data-testid="stitch-research-vault-layout" class="vault-layout">
    <aside>
      <header><div><small>{{ t("vault.spaces") }}</small><h2>{{ t("vault.title") }}</h2></div><button aria-label="Create vault" @click="emit('create')"><Plus class="size-4" /></button></header>
      <nav>
        <button v-for="vault in workspace.knowledgeBases.value" :key="vault.id" :class="{ active: workspace.selectedKnowledgeBaseId.value === vault.id }" @click="workspace.selectKnowledgeBase(vault.id)">
          <FolderOpen class="size-4" /><span><strong>{{ vault.name }}</strong><small>{{ vault.description || "No description" }}</small></span>
        </button>
      </nav>
      <section><small>{{ t("vault.savedTags") }}</small><div><span>#research</span><span>#memory</span><span>#graph</span></div></section>
    </aside>

    <section class="vault-content">
      <header class="vault-heading">
        <div><small>{{ workspace.selectedKnowledgeBase.value?.description || t("vault.active") }}</small><h1>{{ workspace.selectedKnowledgeBase.value?.name ?? t("vault.title") }}</h1></div>
        <div class="vault-actions">
          <input :key="workspace.uploadInputKey.value" data-testid="workspace-upload-input" class="sr-only" type="file" @change="workspace.uploadFile(($event.target as HTMLInputElement).files?.[0])" />
          <button :aria-label="statusFilter === 'all' ? 'Show indexed files' : 'Show all files'" @click="statusFilter = statusFilter === 'all' ? 'indexed' : 'all'"><List class="size-4" /></button>
          <button aria-label="Toggle document density" @click="compact = !compact"><component :is="compact ? LayoutGrid : List" class="size-4" /></button>
          <label class="upload-button"><FilePlus2 class="size-4" />{{ t("vault.upload") }}<input class="sr-only" type="file" @change="workspace.uploadFile(($event.target as HTMLInputElement).files?.[0])" /></label>
        </div>
      </header>

      <div class="document-list" :class="{ compact }">
        <article v-for="doc in visibleDocuments" :key="doc.id" data-testid="document-card">
          <File class="document-icon" />
          <div class="document-copy"><strong>{{ doc.file_name }}</strong><small>{{ doc.file_type || "document" }} · {{ doc.status }}</small></div>
          <div class="document-actions">
            <button :disabled="doc.status === 'indexed'" @click="workspace.indexDocument(doc.id)">{{ t("vault.index") }}</button>
            <button class="danger" @click="workspace.deleteDocument(doc.id)">{{ t("vault.delete") }}</button>
          </div>
        </article>
        <UiEmptyState v-if="!visibleDocuments.length" :title="t('vault.emptyTitle')" :description="t('vault.emptyDescription')">
          <template #icon><File class="size-5" /></template>
        </UiEmptyState>
      </div>

      <section data-testid="memory-function-grid" class="memory-strip">
        <header><div><small>Memory Output Workspace</small><h2>{{ t("vault.memory") }}</h2></div><span>{{ workspace.memoryLibrary.value?.timeline.length ?? 0 }} entries</span></header>
        <div data-testid="memory-output-workspace">
          <article v-for="entry in (workspace.memoryLibrary.value?.timeline ?? []).slice(0, 4)" :key="entry.entry_id"><strong>{{ entry.entry_name }}</strong><p>{{ entry.summary }}</p></article>
          <p v-if="!(workspace.memoryLibrary.value?.timeline ?? []).length">No synthesized memory events yet.</p>
        </div>
      </section>
    </section>
  </div>
</template>

<style scoped>
.vault-layout { display: grid; height: 100%; min-height: 0; grid-template-columns: 250px minmax(0, 1fr); background: var(--bg-canvas); }
.vault-layout > aside { min-width: 0; overflow: auto; padding: 1rem; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.vault-layout aside header, .vault-heading, .memory-strip header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
small { color: var(--text-tertiary); font: 500 0.66rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.07em; }
h1, h2 { margin: 0.2rem 0 0; font-weight: 600; }
.vault-layout aside button, .vault-actions button { color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 0.4rem; }
.vault-layout aside header button { display: grid; width: 2rem; height: 2rem; place-items: center; }
.vault-layout aside nav { display: grid; gap: 0.2rem; margin-top: 1rem; }
.vault-layout aside nav button { display: flex; min-width: 0; gap: 0.6rem; padding: 0.65rem; text-align: left; }
.vault-layout aside nav button.active { color: var(--text-primary); background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent); }
.vault-layout aside nav span, .vault-layout aside nav strong, .vault-layout aside nav small { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vault-layout aside nav span { flex: 1; }
.vault-layout aside section { margin-top: 2rem; }
.vault-layout aside section div { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.6rem; }
.vault-layout aside section span { padding: 0.25rem 0.45rem; color: var(--text-secondary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.3rem; font-size: 0.7rem; }
.vault-content { min-width: 0; overflow: auto; padding: 1.5rem 2rem; }
.vault-heading h1 { font: 600 clamp(1.6rem, 4vw, 2.4rem) var(--font-serif); }
.vault-actions { display: flex; gap: 0.35rem; }
.vault-actions button, .upload-button { display: inline-flex; min-height: 2.3rem; align-items: center; justify-content: center; gap: 0.4rem; padding: 0.45rem 0.65rem; color: var(--text-secondary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.4rem; font-size: 0.78rem; }
.document-list { display: grid; gap: 0; margin-top: 1.5rem; border-top: 1px solid var(--border-muted); }
.document-list article { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.8rem; padding: 0.9rem 0.4rem; border-bottom: 1px solid var(--border-muted); }
.document-list.compact article { padding-block: 0.55rem; }
.document-icon { color: var(--accent); }
.document-copy strong, .document-copy small { display: block; }
.document-copy small { margin-top: 0.2rem; text-transform: none; }
.document-actions { display: flex; gap: 0.3rem; }
.document-actions button { padding: 0.35rem 0.55rem; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-muted); border-radius: 0.35rem; font-size: 0.72rem; }
.document-actions .danger { color: var(--danger); }
.document-actions button:disabled { opacity: 0.4; }
.memory-strip { margin-top: 2.5rem; padding-top: 1.2rem; border-top: 1px solid var(--border-muted); }
.memory-strip header > span { color: var(--text-tertiary); font: 0.7rem var(--font-mono); }
.memory-strip > div { display: grid; gap: 0.75rem; margin-top: 1rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.memory-strip article { padding-left: 0.8rem; border-left: 2px solid var(--accent); }
.memory-strip p { margin: 0.25rem 0 0; color: var(--text-secondary); font-size: 0.82rem; line-height: 1.55; }
@media (max-width: 767px) { .vault-layout { grid-template-columns: 1fr; } .vault-layout > aside { display: none; } .vault-content { padding: 1rem; } .vault-heading { align-items: flex-start; } .vault-actions button { display: none; } .document-list article { grid-template-columns: auto minmax(0, 1fr); } .document-actions { grid-column: 2; } .memory-strip > div { grid-template-columns: 1fr; } }
</style>
