<script setup lang="ts">
import { Bot, Database, File, FolderPlus, Network, Search, Upload } from "@lucide/vue";
import type { MnemeWorkspace, WorkspaceCommandTab } from "../composables/useMnemeWorkspace";
import { useI18n } from "../composables/useI18n";

defineProps<{ workspace: MnemeWorkspace }>();
const { t } = useI18n();

const commands: Array<{ id: WorkspaceCommandTab; label: string; hint: string; icon: unknown }> = [
  { id: "create", label: "Create vault", hint: "Start a research space", icon: FolderPlus },
  { id: "upload", label: "Upload file", hint: "Attach source material", icon: Upload },
  { id: "ask", label: "Ask vault", hint: "Query indexed context", icon: Search },
  { id: "companion", label: "Companion", hint: "Generate a reflective answer", icon: Bot },
];
</script>

<template>
  <section data-testid="dashboard-overview" class="view-page">
    <header class="view-heading">
      <p>{{ t("dashboard.kicker") }}</p>
      <h1>{{ workspace.selectedKnowledgeBase.value?.name ?? t("dashboard.title") }}</h1>
      <span>{{ t("dashboard.description") }}</span>
    </header>

    <div data-testid="stitch-dashboard-grid" class="dashboard-stats">
      <article><File /><span>Documents</span><strong>{{ workspace.selectedDocuments.value.length }}</strong><small>{{ workspace.indexedDocumentCount.value }} indexed</small></article>
      <article><Database /><span>Memories</span><strong>{{ workspace.memoryLibrary.value?.timeline.length ?? 0 }}</strong><small>{{ workspace.memoryGovernance.value?.canonical_memory_count ?? 0 }} canonical</small></article>
      <article><Network /><span>Graph</span><strong>{{ workspace.graphData.value?.nodes.length ?? 0 }}</strong><small>{{ workspace.graphData.value?.edges.length ?? 0 }} relations</small></article>
    </div>

    <section data-testid="unified-command-module" class="command-module">
      <nav data-testid="workspace-command-tabs">
        <button v-for="command in commands" :key="command.id" :class="{ active: workspace.workspaceCommandTab.value === command.id }" @click="workspace.workspaceCommandTab.value = command.id">
          <component :is="command.icon" class="size-4" />
          <span><strong>{{ command.label }}</strong><small>{{ command.hint }}</small></span>
        </button>
      </nav>
      <div data-testid="workspace-command-panel" class="command-panel">
        <form v-if="workspace.workspaceCommandTab.value === 'create'" data-testid="workspace-create-kb-command" @submit.prevent="workspace.createKnowledgeBase">
          <input v-model="workspace.knowledgeBaseForm.value.name" class="premium-input" placeholder="Vault name" />
          <textarea v-model="workspace.knowledgeBaseForm.value.description" class="premium-input" placeholder="What will live here?" />
          <button class="primary-action"><FolderPlus class="size-4" />Create vault</button>
        </form>
        <div v-else-if="workspace.workspaceCommandTab.value === 'upload'" data-testid="workspace-upload-command">
          <label class="drop-zone"><Upload class="size-5" /><span>Choose a document for the active vault</span><input :key="workspace.uploadInputKey.value" type="file" @change="workspace.uploadFile(($event.target as HTMLInputElement).files?.[0])" /></label>
        </div>
        <form v-else-if="workspace.workspaceCommandTab.value === 'ask'" data-testid="workspace-chat-command" @submit.prevent="workspace.askVault">
          <textarea v-model="workspace.chatQuestion.value" class="premium-input" placeholder="Ask a question grounded in this vault" />
          <button class="primary-action"><Search class="size-4" />Ask vault</button>
          <p v-if="workspace.chatResult.value" class="answer">{{ workspace.chatResult.value.answer }}</p>
        </form>
        <form v-else @submit.prevent="workspace.askCompanion">
          <textarea v-model="workspace.companionQuestion.value" class="premium-input" placeholder="What should Mneme reflect on?" />
          <button class="primary-action"><Bot class="size-4" />Ask companion</button>
          <p v-if="workspace.companionResult.value" class="answer">{{ workspace.companionResult.value.direct_answer }}</p>
        </form>
      </div>
    </section>
  </section>
</template>

<style scoped>
.view-page { width: min(100%, 1120px); margin: 0 auto; padding: 2rem; }
.view-heading p { margin: 0; color: var(--accent); font: 500 0.7rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.09em; }
.view-heading h1 { margin: 0.55rem 0 0; font: 600 clamp(1.8rem, 4vw, 2.8rem) var(--font-serif); }
.view-heading > span { display: block; max-width: 38rem; margin-top: 0.55rem; color: var(--text-secondary); line-height: 1.65; }
.dashboard-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 2rem; border-block: 1px solid var(--border-muted); }
.dashboard-stats article { display: grid; grid-template-columns: auto 1fr; gap: 0.25rem 0.65rem; padding: 1.2rem; border-right: 1px solid var(--border-muted); }
.dashboard-stats article:last-child { border-right: 0; }
.dashboard-stats svg { width: 1rem; color: var(--accent); }
.dashboard-stats span, .dashboard-stats small { color: var(--text-secondary); font-size: 0.76rem; }
.dashboard-stats strong { grid-column: 2; font-size: 1.6rem; }
.dashboard-stats small { grid-column: 2; }
.command-module { display: grid; grid-template-columns: 220px minmax(0, 1fr); margin-top: 2rem; overflow: hidden; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.55rem; }
.command-module nav { display: grid; align-content: start; gap: 0.2rem; padding: 0.55rem; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.command-module nav button { display: flex; gap: 0.65rem; padding: 0.75rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.4rem; }
.command-module nav button.active { color: var(--text-primary); background: var(--accent-soft); }
.command-module nav strong, .command-module nav small { display: block; }
.command-module nav small { margin-top: 0.15rem; color: var(--text-tertiary); font-size: 0.68rem; }
.command-panel { min-height: 260px; padding: 1.5rem; }
.command-panel form { display: grid; gap: 0.8rem; }
.command-panel input, .command-panel textarea { width: 100%; padding: 0.75rem; border: 1px solid var(--border-muted); }
.command-panel textarea { min-height: 7rem; resize: vertical; }
.primary-action { display: inline-flex; width: fit-content; align-items: center; gap: 0.45rem; padding: 0.65rem 0.9rem; color: var(--accent-contrast); background: var(--accent); border: 0; border-radius: 0.4rem; }
.drop-zone { display: grid; min-height: 12rem; place-items: center; align-content: center; gap: 0.7rem; color: var(--text-secondary); border: 1px dashed var(--border-strong); border-radius: 0.5rem; }
.answer { padding: 1rem; color: var(--text-secondary); background: var(--bg-sidebar); border-left: 2px solid var(--accent); }
@media (max-width: 767px) { .view-page { padding: 1.2rem; } .dashboard-stats { grid-template-columns: 1fr; } .dashboard-stats article { border-right: 0; border-bottom: 1px solid var(--border-muted); } .command-module { grid-template-columns: 1fr; } .command-module nav { grid-template-columns: repeat(4, 1fr); border-right: 0; border-bottom: 1px solid var(--border-muted); } .command-module nav button { justify-content: center; padding: 0.65rem 0.2rem; } .command-module nav span { display: none; } }
</style>
