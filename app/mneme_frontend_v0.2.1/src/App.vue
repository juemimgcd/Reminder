<script setup lang="ts">
import type { Component } from "vue";
import { computed } from "vue";
import {
  BookOpen,
  BrainCircuit,
  FlaskConical,
  GitBranch,
  LifeBuoy,
  LogOut,
  Network,
  Plus,
  RefreshCw,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
  FolderOpen,
} from "@lucide/vue";
import ActivityBar from "./components/shell/ActivityBar.vue";
import MobileNavigation from "./components/shell/MobileNavigation.vue";
import ResourceSidebar from "./components/shell/ResourceSidebar.vue";
import StatusBar from "./components/shell/StatusBar.vue";
import UiIconButton from "./components/ui/UiIconButton.vue";
import UiSkeleton from "./components/ui/UiSkeleton.vue";
import UiStatusPanel from "./components/ui/UiStatusPanel.vue";
import { useI18n } from "./composables/useI18n";
import { useMnemeWorkspace } from "./composables/useMnemeWorkspace";
import { useResponsiveShell } from "./composables/useResponsiveShell";
import type { WorkspaceView } from "./types";
import AiLabView from "./views/AiLabView.vue";
import DashboardView from "./views/DashboardView.vue";
import GraphView from "./views/GraphView.vue";
import SettingsView from "./views/SettingsView.vue";
import VaultView from "./views/VaultView.vue";

type ViewItem = { id: WorkspaceView; label: string; shortLabel: string; icon: Component; hint: string };

const workspace = useMnemeWorkspace();
const shell = useResponsiveShell();
const { formatDate, t } = useI18n();

const VIEW_ITEMS = computed<ViewItem[]>(() => [
  { id: "dashboard", label: t("nav.map"), shortLabel: t("nav.short.map"), icon: Network, hint: t("nav.hint.map") },
  { id: "notes", label: t("nav.vault"), shortLabel: t("nav.short.vault"), icon: FolderOpen, hint: t("nav.hint.vault") },
  { id: "graph", label: t("nav.graph"), shortLabel: t("nav.short.graph"), icon: GitBranch, hint: t("nav.hint.graph") },
  { id: "ai", label: t("nav.ai"), shortLabel: t("nav.short.ai"), icon: FlaskConical, hint: t("nav.hint.ai") },
  { id: "settings", label: t("nav.settings"), shortLabel: t("nav.short.settings"), icon: SlidersHorizontal, hint: t("nav.hint.settings") },
]);

const currentViewItem = computed(() => VIEW_ITEMS.value.find((item) => item.id === workspace.view.value) ?? VIEW_ITEMS.value[0]);
const activeHealthLabel = computed(() => workspace.readiness.value?.overall_status ?? workspace.serviceHealth.value?.status ?? "preview");
const activeViewLoadState = computed(() => workspace.viewLoadStates[workspace.view.value]);
const activeViewLoading = computed(() => activeViewLoadState.value.phase.value === "loading");

function navigate(id: string) {
  workspace.view.value = id as WorkspaceView;
  shell.closeOverlays();
}

function openCreateCommand() {
  workspace.workspaceCommandTab.value = "create";
  workspace.view.value = "dashboard";
  shell.closeOverlays();
}
</script>

<template>
  <main v-if="!workspace.isAuthenticated.value" class="auth-screen">
    <section class="auth-card">
      <header><div class="auth-mark"><BrainCircuit /></div><div><h1>Mneme</h1><p>Personal knowledge, kept close.</p></div></header>
      <div class="auth-mode" role="group" aria-label="Authentication mode">
        <button type="button" :class="{ active: workspace.authMode.value === 'login' }" @click="workspace.setAuthMode('login')">{{ t("auth.login") }}</button>
        <button type="button" :class="{ active: workspace.authMode.value === 'register' }" @click="workspace.setAuthMode('register')">{{ t("auth.register") }}</button>
      </div>
      <form v-if="workspace.authMode.value === 'login'" @submit.prevent="workspace.login">
        <label><span>{{ t("auth.username") }}</span><input v-model="workspace.loginForm.value.username" autocomplete="username" required /></label>
        <label><span>{{ t("auth.password") }}</span><input v-model="workspace.loginForm.value.password" type="password" autocomplete="current-password" required /></label>
        <p v-if="workspace.authError.value" class="auth-error" aria-live="polite">{{ workspace.authError.value }}</p>
        <button :disabled="workspace.authPending.value"><ShieldCheck />{{ workspace.authPending.value ? t("auth.signingIn") : t("auth.login") }}</button>
      </form>
      <form v-else @submit.prevent="workspace.register">
        <label><span>{{ t("auth.username") }}</span><input v-model="workspace.registerForm.value.username" autocomplete="username" minlength="3" required /></label>
        <label><span>{{ t("auth.displayName") }}</span><input v-model="workspace.registerForm.value.displayName" autocomplete="name" /></label>
        <label><span>{{ t("auth.password") }}</span><input v-model="workspace.registerForm.value.password" type="password" autocomplete="new-password" minlength="8" required /></label>
        <label><span>{{ t("auth.confirmPassword") }}</span><input v-model="workspace.registerForm.value.confirmPassword" type="password" autocomplete="new-password" minlength="8" required /></label>
        <p v-if="workspace.authError.value" class="auth-error" aria-live="polite">{{ workspace.authError.value }}</p>
        <button :disabled="workspace.authPending.value"><ShieldCheck />{{ workspace.authPending.value ? t("auth.creatingAccount") : t("auth.createAccount") }}</button>
      </form>
    </section>
  </main>

  <main v-else data-testid="obsidian-shell" class="mneme-workbench">
    <input
      :key="workspace.uploadInputKey.value"
      class="sr-only"
      type="file"
      aria-label="Upload document"
      @change="workspace.uploadFile(($event.target as HTMLInputElement).files?.[0])"
    />
    <div class="mneme-shell" :class="{ 'mneme-shell--resource-closed': !shell.resourceOpen.value }">
      <ActivityBar :items="VIEW_ITEMS" :active-id="workspace.view.value" @create="openCreateCommand" @toggle-resource="shell.toggleResource" @navigate="navigate" />

      <ResourceSidebar :open="shell.resourceOpen.value" @close="shell.closeOverlays">
        <aside data-testid="sanctuary-sidebar" class="explorer">
          <header class="explorer-brand">
            <div class="brand-mark"><BrainCircuit /></div>
            <div><h1>Mneme</h1><p>Cognitive Sanctuary</p></div>
          </header>
          <button class="new-research" @click="openCreateCommand"><Plus />{{ t("shell.newResearch") }}</button>

          <nav class="explorer-scroll">
            <section data-testid="sidebar-group-vaults">
              <header><span>{{ t("shell.researchSpaces") }}</span><UiIconButton label="Create vault" size="sm" @click="openCreateCommand"><Plus /></UiIconButton></header>
              <button v-for="vault in workspace.knowledgeBases.value" :key="vault.id" :class="{ active: workspace.selectedKnowledgeBaseId.value === vault.id }" @click="workspace.selectKnowledgeBase(vault.id)">
                <strong>{{ vault.name }}</strong><small>{{ vault.description || t("shell.noDescription") }}</small>
              </button>
            </section>
            <section data-testid="sidebar-group-files">
              <header><span>{{ t("shell.recentFiles") }}</span></header>
              <button v-for="doc in workspace.selectedDocuments.value.slice(0, 6)" :key="doc.id" @click="workspace.openDocument(doc.id)"><strong>{{ doc.file_name }}</strong><small>{{ doc.status }} · {{ formatDate(doc.created_at) }}</small></button>
            </section>
          </nav>

          <footer>
            <button @click="workspace.showDocumentationStatus"><BookOpen />{{ t("shell.documentation") }}</button>
            <button @click="workspace.showSupportStatus"><LifeBuoy />{{ t("shell.support") }}</button>
            <div class="user-card"><div><UserRound /></div><span><strong>{{ workspace.user.value?.display_name || t("shell.previewUser") }}</strong><small>{{ workspace.user.value?.username }}</small></span></div>
          </footer>
        </aside>
      </ResourceSidebar>

      <section class="mneme-shell__main">
        <header v-if="workspace.view.value !== 'graph' && workspace.view.value !== 'ai'" data-testid="sanctuary-topbar" class="workspace-topbar">
          <div data-testid="sanctuary-active-view"><small>{{ currentViewItem.hint }}</small><h2>{{ currentViewItem.label }}</h2></div>
          <div><span>{{ activeHealthLabel }}</span><UiIconButton label="Refresh panels" @click="workspace.loadKnowledgeBasePanels"><RefreshCw /></UiIconButton><UiIconButton label="Log out" @click="workspace.logout"><LogOut /></UiIconButton></div>
        </header>
        <UiStatusPanel v-if="workspace.banner.value" class="workspace-banner" :title="workspace.banner.value" dismissible @dismiss="workspace.dismissBanner" />
        <UiStatusPanel v-if="workspace.authNotice.value" class="workspace-banner" :title="workspace.authNotice.value" />
        <UiStatusPanel v-if="workspace.documentActionStatus.value" class="workspace-banner" :title="workspace.documentActionStatus.value" />
        <UiStatusPanel v-if="activeViewLoadState.message.value" class="workspace-banner" :title="activeViewLoadState.message.value" variant="warning" />
        <UiStatusPanel
          v-if="workspace.duplicateUpload.value"
          data-testid="duplicate-upload-notice"
          class="workspace-banner"
          :title="`${workspace.duplicateUpload.value.file_name} already exists`"
        >
          <template #action><button type="button" @click="workspace.openDuplicateUpload">Open existing file</button></template>
        </UiStatusPanel>

        <section data-testid="obsidian-editor-pane" class="workspace-content">
          <div v-if="workspace.isLoading.value || activeViewLoading" class="workspace-loading" aria-label="Loading workspace">
            <UiSkeleton width="38%" height="1.8rem" />
            <UiSkeleton width="72%" height="0.8rem" />
            <UiSkeleton width="100%" height="13rem" />
          </div>
          <DashboardView v-else-if="workspace.view.value === 'dashboard'" :workspace="workspace" />
          <div v-else-if="workspace.view.value === 'notes'">
            <section v-if="workspace.activeDocumentId.value" data-testid="document-reader" class="workspace-banner" aria-live="polite">
              <strong data-testid="document-reader-title">{{ workspace.documentContent.value?.file_name }}</strong>
            </section>
            <VaultView :workspace="workspace" @create="openCreateCommand" />
          </div>
          <GraphView v-else-if="workspace.view.value === 'graph'" :workspace="workspace" />
          <AiLabView v-else-if="workspace.view.value === 'ai'" :workspace="workspace" :format-date="formatDate" />
          <SettingsView v-else :workspace="workspace" :health-label="activeHealthLabel" />
        </section>

        <StatusBar :status="activeHealthLabel" :detail="workspace.selectedKnowledgeBase.value?.name" />
      </section>

      <MobileNavigation :items="VIEW_ITEMS" :active-id="workspace.view.value" @toggle-resources="shell.toggleResource" @navigate="navigate" />
    </div>
  </main>
</template>

<style scoped>
.auth-screen { display: grid; min-height: 100vh; place-items: center; padding: 1rem; background: var(--bg-canvas); color: var(--text-primary); }
.auth-card { width: min(100%, 390px); padding: 1.5rem; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.65rem; box-shadow: var(--shadow-float); }
.auth-card header { display: flex; align-items: center; gap: 0.8rem; }
.auth-mark, .brand-mark { display: grid; width: 2.4rem; height: 2.4rem; place-items: center; color: var(--accent); background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--border-muted)); border-radius: 0.5rem; }
.auth-mark svg, .brand-mark svg { width: 1.1rem; }
.auth-card h1, .auth-card p { margin: 0; }
.auth-card h1 { font: 600 1.35rem var(--font-serif); }
.auth-card p { margin-top: 0.15rem; color: var(--text-secondary); font-size: 0.78rem; }
.auth-card form { display: grid; gap: 0.8rem; margin-top: 1.3rem; }
.auth-mode { display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; margin-top: 1.3rem; padding: 0.2rem; background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.5rem; }
.auth-mode button { min-height: 2.1rem; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.35rem; font-weight: 600; }
.auth-mode button.active { color: var(--text-primary); background: var(--accent-soft); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 42%, transparent); }
.auth-card label { display: grid; gap: 0.3rem; color: var(--text-secondary); font-size: 0.75rem; }
.auth-card input { height: 2.5rem; padding: 0 0.7rem; color: var(--text-primary); background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.auth-card form > button { display: flex; height: 2.5rem; align-items: center; justify-content: center; gap: 0.45rem; color: var(--accent-contrast); background: var(--accent); border: 0; border-radius: 0.4rem; }
.auth-card form > button:disabled { cursor: wait; opacity: 0.58; }
.auth-card form > button svg { width: 1rem; }
.auth-error { color: var(--danger) !important; }
.explorer { display: flex; min-height: 0; flex: 1; flex-direction: column; }
.explorer-brand { display: flex; align-items: center; gap: 0.7rem; padding: 1rem; }
.explorer-brand h1 { margin: 0; font: 600 1.15rem var(--font-serif); }
.explorer-brand p { margin: 0.15rem 0 0; color: var(--text-tertiary); font: 0.6rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.08em; }
.new-research { display: flex; min-height: 2.4rem; align-items: center; justify-content: center; gap: 0.45rem; margin: 0 0.8rem 0.6rem; color: var(--accent-contrast); background: var(--accent); border: 0; border-radius: 0.4rem; font-size: 0.75rem; font-weight: 500; }
.new-research svg { width: 0.9rem; }
.explorer-scroll { flex: 1; overflow: auto; padding: 0.5rem 0.65rem; }
.explorer-scroll section + section { margin-top: 1.25rem; }
.explorer-scroll section > header { display: flex; min-height: 1.8rem; align-items: center; justify-content: space-between; padding: 0 0.35rem; color: var(--text-tertiary); font: 0.62rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.06em; }
.explorer-scroll section > button { display: block; width: 100%; padding: 0.55rem 0.65rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.35rem; }
.explorer-scroll section > button:hover { background: var(--bg-elevated); }
.explorer-scroll section > button.active { color: var(--text-primary); background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent); }
.explorer-scroll strong, .explorer-scroll small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.explorer-scroll strong { font-size: 0.78rem; font-weight: 500; }
.explorer-scroll small { margin-top: 0.18rem; color: var(--text-tertiary); font-size: 0.65rem; }
.explorer > footer { display: grid; gap: 0.2rem; padding: 0.65rem; border-top: 1px solid var(--border-muted); }
.explorer > footer > button { display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.35rem; font-size: 0.75rem; }
.explorer > footer > button:hover { color: var(--text-primary); background: var(--bg-elevated); }
.explorer > footer svg { width: 0.95rem; }
.user-card { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.35rem; padding: 0.6rem; background: var(--bg-panel); border-radius: 0.4rem; }
.user-card > div { display: grid; width: 1.8rem; height: 1.8rem; place-items: center; color: var(--accent); background: var(--accent-soft); border-radius: 50%; }
.user-card strong, .user-card small { display: block; }
.user-card strong { font-size: 0.75rem; }
.user-card small { color: var(--text-tertiary); font-size: 0.64rem; }
.workspace-topbar { display: flex; min-height: 3.5rem; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.55rem 1rem; background: var(--bg-canvas); border-bottom: 1px solid var(--border-muted); }
.workspace-topbar small { color: var(--text-tertiary); font: 0.62rem var(--font-mono); }
.workspace-topbar h2 { margin: 0.12rem 0 0; font-size: 0.92rem; }
.workspace-topbar > div:last-child { display: flex; align-items: center; gap: 0.3rem; }
.workspace-topbar > div:last-child > span { padding: 0.25rem 0.4rem; color: var(--text-tertiary); border: 1px solid var(--border-muted); border-radius: 0.3rem; font: 0.62rem var(--font-mono); }
.workspace-banner { width: 100%; min-width: 0; flex: 0 0 auto; margin: 0; padding: 0.55rem 1rem; color: var(--text-secondary); background: var(--accent-soft); border-width: 0 0 1px; border-radius: 0; font-size: 0.72rem; }
.workspace-content { min-width: 0; min-height: 0; flex: 1; overflow: auto; }
.workspace-loading { display: grid; width: min(100%, 900px); gap: 0.9rem; margin: 0 auto; padding: 2rem; }
@media (max-width: 767px) { .workspace-topbar { padding-inline: 0.75rem; } .workspace-topbar > div:last-child > span { display: none; } }
</style>
