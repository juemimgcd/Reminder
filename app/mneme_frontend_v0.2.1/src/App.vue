<script setup lang="ts">
import {
  Bell,
  Bot,
  CheckCircle2,
  CircleDot,
  Database,
  FileText,
  FolderGit2,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Palette,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  UserRound,
} from "@lucide/vue";
import { computed } from "vue";
import { useMnemeWorkspace, type WorkspaceCommandTab } from "./composables/useMnemeWorkspace";
import type { WorkspaceView } from "./types";

const workspace = useMnemeWorkspace();

const VIEW_ITEMS: Array<{ id: WorkspaceView; label: string; icon: unknown; hint: string }> = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, hint: "Knowledge base at a glance" },
  { id: "notes", label: "Notes", icon: FileText, hint: "Documents and durable memory" },
  { id: "graph", label: "Graph", icon: GitBranch, hint: "GraphRAG structure" },
  { id: "ai", label: "AI Chat", icon: Bot, hint: "Ask and companion replies" },
  { id: "settings", label: "Settings", icon: Settings, hint: "Health, profile, and analytics" },
];

const WORKSPACE_COMMANDS: Array<{ id: WorkspaceCommandTab; label: string; hint: string; icon: unknown }> = [
  { id: "create", label: "Create Vault", hint: "新建知识库", icon: Plus },
  { id: "upload", label: "Upload File", hint: "加入当前 vault", icon: Upload },
  { id: "ask", label: "Ask Vault", hint: "检索问答", icon: Search },
  { id: "companion", label: "Companion", hint: "陪伴式回复", icon: Bot },
];

const currentViewItem = computed(() => VIEW_ITEMS.find((item) => item.id === workspace.view.value) ?? VIEW_ITEMS[0]);
const graphNodePositions = computed(() => {
  const nodes = workspace.graphData.value?.nodes ?? [];
  const radius = 190;
  return nodes.map((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1) - Math.PI / 2;
    return {
      ...node,
      x: 260 + Math.cos(angle) * (node.depth === 0 ? 0 : radius - node.depth * 28),
      y: 235 + Math.sin(angle) * (node.depth === 0 ? 0 : radius - node.depth * 28),
    };
  });
});
const graphSummary = computed(() => {
  const graph = workspace.graphData.value;
  if (!graph) {
    return "Graph data is loading.";
  }
  return `${graph.scope} graph with ${graph.nodes.length} nodes, ${graph.edges.length} edges, and ${graph.relationship_scope} relationships.`;
});
const memoryGovernanceSummary = computed(() => {
  const governance = workspace.memoryGovernance.value;
  if (!governance) {
    return "Memory governance is loading.";
  }
  return `${governance.canonical_memory_count} canonical memories consolidated from ${governance.raw_entry_count} raw entries.`;
});

function formatDate(value?: string | null) {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(new Date(value));
}

function statusClass(status?: string | null) {
  if (status === "indexed" || status === "ok" || status === "preview" || status === "completed") {
    return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
  }
  if (status === "failed" || status === "error") {
    return "border-rose-400/30 bg-rose-400/10 text-rose-200";
  }
  return "border-sky-400/30 bg-sky-400/10 text-sky-200";
}
</script>

<template>
  <main v-if="!workspace.isAuthenticated.value" class="mneme-workbench grid min-h-screen place-items-center bg-surface-base px-4 text-on-surface">
    <section class="glass-panel w-full max-w-[440px] rounded-lg p-6">
      <div class="mb-6 flex items-center gap-3">
        <div class="grid size-10 place-items-center rounded-md bg-primary-container text-on-primary-container">
          <FolderGit2 class="size-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold">Mneme Workspace</h1>
          <p class="text-sm text-text-muted">Backend endpoint {{ workspace.API_BASE_URL }}</p>
        </div>
      </div>

      <form class="grid gap-3" @submit.prevent="workspace.login">
        <label class="grid gap-1 text-sm">
          <span class="text-text-muted">Username</span>
          <input v-model="workspace.loginForm.value.username" class="premium-input h-10 px-3" autocomplete="username" />
        </label>
        <label class="grid gap-1 text-sm">
          <span class="text-text-muted">Password</span>
          <input v-model="workspace.loginForm.value.password" class="premium-input h-10 px-3" type="password" autocomplete="current-password" />
        </label>
        <p v-if="workspace.authError.value" class="text-sm text-rose-300">{{ workspace.authError.value }}</p>
        <button class="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container" type="submit">
          <ShieldCheck class="size-4" />
          Sign in
        </button>
      </form>
    </section>
  </main>

  <main v-else data-testid="obsidian-shell" class="mneme-workbench min-h-screen text-on-surface" style="background-color: #09090b">
    <div class="grid min-h-screen grid-cols-[256px_minmax(0,1fr)]">
      <aside data-testid="sanctuary-sidebar" class="flex w-64 flex-col border-r border-border-subtle bg-surface-base/95" style="width: 256px">
        <div class="flex h-16 items-center gap-3 border-b border-border-subtle px-4">
          <div class="grid size-9 place-items-center rounded-md bg-primary-container text-on-primary-container">
            <FolderGit2 class="size-5" />
          </div>
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold">{{ workspace.IS_PREVIEW_MODE ? "Preview" : "Mneme" }}</p>
            <p class="truncate text-xs text-text-muted">{{ workspace.user.value?.username }}</p>
          </div>
        </div>

        <nav class="flex-1 overflow-y-auto px-3 py-4">
          <div class="grid gap-1">
            <button
              v-for="item in VIEW_ITEMS"
              :key="item.id"
              class="flex h-10 items-center gap-3 rounded-md px-3 text-left text-sm transition"
              :class="workspace.view.value === item.id ? 'bg-primary-container text-on-primary-container' : 'text-text-dim hover:bg-surface-container'"
              :aria-pressed="workspace.view.value === item.id"
              @click="workspace.view.value = item.id"
            >
              <component :is="item.icon" class="size-4 shrink-0" />
              <span>{{ item.label }}</span>
            </button>
          </div>

          <section data-testid="sidebar-group-vaults" class="mt-6 flex flex-col gap-2">
            <div class="flex items-center justify-between px-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
              <span>Vaults</span>
              <button class="premium-action-btn grid size-7 place-items-center rounded-md" title="Create vault" @click="workspace.workspaceCommandTab.value = 'create'; workspace.view.value = 'dashboard'">
                <Plus class="size-3.5" />
              </button>
            </div>
            <button
              v-for="vault in workspace.knowledgeBases.value"
              :key="vault.id"
              class="rounded-md px-3 py-2 text-left text-sm"
              :class="workspace.selectedKnowledgeBaseId.value === vault.id ? 'bg-accent-soft text-primary' : 'text-text-dim hover:bg-surface-container'"
              @click="workspace.selectKnowledgeBase(vault.id)"
            >
              <span class="block truncate font-medium">{{ vault.name }}</span>
              <span class="block truncate text-xs text-text-muted">{{ vault.description || "No description" }}</span>
            </button>
          </section>

          <section data-testid="sidebar-group-files" class="mt-6 flex flex-col gap-2">
            <div class="px-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Files</div>
            <button v-for="doc in workspace.selectedDocuments.value" :key="doc.id" class="rounded-md px-3 py-2 text-left text-sm text-text-dim hover:bg-surface-container">
              <span class="block truncate font-medium">{{ doc.file_name }}</span>
              <span class="block text-xs text-text-muted">{{ doc.status }} · {{ formatDate(doc.created_at) }}</span>
            </button>
          </section>
        </nav>
      </aside>

      <section class="flex min-w-0 flex-col">
        <header data-testid="sanctuary-topbar" class="flex h-16 items-center justify-between border-b border-border-subtle bg-surface-base/80 px-4 backdrop-blur-md lg:h-16 lg:px-6">
          <div class="min-w-0">
            <p class="truncate text-sm text-text-muted">{{ workspace.selectedKnowledgeBase.value?.name ?? "No vault selected" }}</p>
            <h2 class="truncate text-lg font-semibold">{{ currentViewItem.label }}</h2>
          </div>
          <div class="flex items-center gap-2">
            <span class="hidden rounded-md border border-border-subtle px-2.5 py-1 text-xs text-text-muted sm:inline-flex">{{ workspace.serviceHealth.value?.status ?? "loading" }}</span>
            <button class="premium-action-btn grid size-9 place-items-center rounded-md" title="Log out" @click="workspace.logout">
              <LogOut class="size-4" />
            </button>
          </div>
        </header>

        <section
          data-testid="obsidian-editor-pane"
          class="min-h-0 flex-1 overflow-auto"
          :class="workspace.view.value === 'graph' || workspace.view.value === 'notes' || workspace.view.value === 'ai' ? 'p-0' : 'px-4 py-7 sm:px-6 lg:px-8 lg:py-8'"
        >
          <div :class="workspace.view.value === 'graph' || workspace.view.value === 'notes' || workspace.view.value === 'ai' ? 'h-full max-w-none' : 'mx-auto w-full max-w-[1200px]'">
            <div v-if="workspace.view.value !== 'graph' && workspace.view.value !== 'notes' && workspace.view.value !== 'ai'" data-testid="sanctuary-active-view" class="mb-10 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p class="text-sm font-medium text-primary">{{ currentViewItem.hint }}</p>
                <h1 class="mt-2 text-3xl font-semibold">{{ currentViewItem.label }}</h1>
              </div>
              <p class="max-w-2xl text-sm leading-6 text-text-muted">{{ workspace.banner.value || "A Vue TypeScript workbench backed by the same Mneme API contract." }}</p>
            </div>

            <div v-if="workspace.view.value === 'dashboard'" data-testid="dashboard-overview">
              <div data-testid="stitch-dashboard-grid" class="mx-auto grid w-full max-w-[1200px] gap-4 px-0 py-0 md:grid-cols-3">
                <section class="premium-card rounded-lg p-5">
                  <div class="premium-card-content">
                    <p class="text-sm text-text-muted">Documents</p>
                    <p class="mt-2 text-3xl font-semibold">{{ workspace.selectedDocuments.value.length }}</p>
                    <p class="mt-2 text-xs text-text-muted">{{ workspace.indexedDocumentCount.value }} indexed</p>
                  </div>
                </section>
                <section class="premium-card rounded-lg p-5">
                  <div class="premium-card-content">
                    <p class="text-sm text-text-muted">Memory</p>
                    <p class="mt-2 text-3xl font-semibold">{{ workspace.memoryLibrary.value?.timeline.length ?? 0 }}</p>
                    <p class="mt-2 text-xs text-text-muted">canonical {{ workspace.memoryGovernance.value?.canonical_memory_count ?? 0 }}</p>
                  </div>
                </section>
                <section class="premium-card rounded-lg p-5">
                  <div class="premium-card-content">
                    <p class="text-sm text-text-muted">Graph</p>
                    <p class="mt-2 text-3xl font-semibold">{{ workspace.graphData.value?.nodes.length ?? 0 }}</p>
                    <p class="mt-2 text-xs text-text-muted">{{ workspace.graphData.value?.edges.length ?? 0 }} relations</p>
                  </div>
                </section>

                <section data-testid="unified-command-module" class="premium-card rounded-lg md:col-span-3">
                  <div class="grid xl:grid-cols-[220px_minmax(0,1fr)]">
                    <nav data-testid="workspace-command-tabs" class="border-b border-white/10 bg-surface-container-low/20 p-2 xl:border-b-0 xl:border-r">
                      <button
                        v-for="command in WORKSPACE_COMMANDS"
                        :key="command.id"
                        class="flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm"
                        :class="workspace.workspaceCommandTab.value === command.id ? 'bg-primary-container text-on-primary-container' : 'text-text-dim hover:bg-surface-container'"
                        @click="workspace.workspaceCommandTab.value = command.id"
                      >
                        <component :is="command.icon" class="size-4" />
                        <span>
                          <span class="block font-medium">{{ command.label }}</span>
                          <span class="block text-xs opacity-70">{{ command.hint }}</span>
                        </span>
                      </button>
                    </nav>

                    <div data-testid="workspace-command-panel" class="min-w-0 p-4">
                      <form v-if="workspace.workspaceCommandTab.value === 'create'" data-testid="workspace-create-kb-command" class="mx-auto grid max-w-3xl gap-3" @submit.prevent="workspace.createKnowledgeBase">
                        <input v-model="workspace.knowledgeBaseForm.value.name" class="premium-input h-10 px-3" placeholder="Vault name" />
                        <textarea v-model="workspace.knowledgeBaseForm.value.description" class="premium-input min-h-24 p-3" placeholder="Description"></textarea>
                        <button class="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                          <Plus class="size-4" />
                          Create
                        </button>
                      </form>

                      <div v-else-if="workspace.workspaceCommandTab.value === 'upload'" data-testid="workspace-upload-command" class="mx-auto grid max-w-3xl gap-3">
                        <div class="rounded-lg border border-dashed border-border-subtle p-6 text-sm text-text-muted">
                          <Upload class="mb-3 size-5 text-primary" />
                          Upload is wired to the backend API surface; preview mode keeps files local for layout review.
                        </div>
                      </div>

                      <form v-else-if="workspace.workspaceCommandTab.value === 'ask'" data-testid="workspace-chat-command" class="grid gap-3" @submit.prevent="workspace.askVault">
                        <textarea v-model="workspace.chatQuestion.value" class="premium-input min-h-28 p-3" />
                        <button class="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                          <Search class="size-4" />
                          Ask vault
                        </button>
                        <p v-if="workspace.chatResult.value" class="rounded-lg border border-border-subtle bg-surface-container-low p-4 text-sm leading-6 text-on-surface">
                          {{ workspace.chatResult.value.answer }}
                        </p>
                      </form>

                      <form v-else class="grid gap-3" @submit.prevent="workspace.askCompanion">
                        <textarea v-model="workspace.companionQuestion.value" class="premium-input min-h-28 p-3" />
                        <button class="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                          <Bot class="size-4" />
                          Ask companion
                        </button>
                        <p v-if="workspace.companionResult.value" class="rounded-lg border border-border-subtle bg-surface-container-low p-4 text-sm leading-6 text-on-surface">
                          {{ workspace.companionResult.value.direct_answer }}
                        </p>
                      </form>
                    </div>
                  </div>
                </section>
              </div>
            </div>

            <div v-else-if="workspace.view.value === 'notes'" data-testid="stitch-notes-layout" class="grid h-[calc(100vh-64px)] min-h-0 grid-cols-1 bg-surface-base lg:grid-cols-[400px_minmax(0,1fr)]">
              <aside class="border-r border-border-subtle p-4">
                <h2 class="mb-4 text-lg font-semibold">Notes</h2>
                <div class="grid gap-2">
                  <article v-for="doc in workspace.selectedDocuments.value" :key="doc.id" class="premium-card rounded-lg p-4">
                    <div class="premium-card-content">
                      <div class="flex items-start justify-between gap-3">
                        <h3 class="truncate text-sm font-semibold">{{ doc.file_name }}</h3>
                        <span class="rounded-full border px-2 py-0.5 text-[11px]" :class="statusClass(doc.status)">{{ doc.status }}</span>
                      </div>
                      <p class="mt-2 text-xs text-text-muted">{{ doc.file_type }} · {{ formatDate(doc.created_at) }}</p>
                    </div>
                  </article>
                </div>
              </aside>
              <section class="p-6">
                <div class="glass-panel h-full rounded-lg p-6">
                  <p class="text-sm text-primary">Memory Library</p>
                  <h2 class="mt-2 text-2xl font-semibold">{{ workspace.selectedKnowledgeBase.value?.name }}</h2>
                  <div data-testid="memory-function-grid" class="mt-6 grid gap-3 xl:grid-cols-[0.72fr_1.28fr]">
                    <div class="rounded-lg border border-border-subtle p-4">
                      <p class="mb-3 text-sm font-semibold">Canonical memory</p>
                      <p class="text-sm leading-6 text-text-muted">{{ memoryGovernanceSummary }}</p>
                    </div>
                    <div testId="memory-output-workspace" class="grid gap-2">
                      <div v-for="entry in workspace.memoryLibrary.value?.timeline ?? []" :key="entry.entry_id" class="rounded-lg border border-border-subtle p-3">
                        <p class="text-sm font-medium">{{ entry.entry_name }}</p>
                        <p class="mt-1 text-xs leading-5 text-text-muted">{{ entry.summary }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <div v-else-if="workspace.view.value === 'graph'" data-testid="stitch-graph-canvas" class="relative min-h-[calc(100vh-164px)] overflow-hidden bg-[#0a0a0c]" title="Graph Workspace">
              <div data-testid="graph-function-grid" class="grid h-full min-h-[calc(100vh-164px)] gap-0 xl:grid-cols-[320px_minmax(0,1fr)]">
                <aside class="border-r border-border-subtle bg-surface-base/80 p-5">
                  <h2 class="text-lg font-semibold">Graph Workspace</h2>
                  <p class="mt-2 text-sm leading-6 text-text-muted">{{ graphSummary }}</p>
                  <div class="mt-6 grid gap-3">
                    <div class="rounded-lg border border-border-subtle p-3 text-sm">
                      <span class="text-text-muted">Nodes</span>
                      <strong class="ml-2">{{ workspace.graphData.value?.nodes.length ?? 0 }}</strong>
                    </div>
                    <div class="rounded-lg border border-border-subtle p-3 text-sm">
                      <span class="text-text-muted">Edges</span>
                      <strong class="ml-2">{{ workspace.graphData.value?.edges.length ?? 0 }}</strong>
                    </div>
                  </div>
                </aside>
                <div testId="graph-output-workspace" class="relative min-h-[520px]">
                  <svg class="h-full min-h-[520px] w-full" viewBox="0 0 520 470" role="img" aria-label="Knowledge graph">
                    <line
                      v-for="edge in workspace.graphData.value?.edges ?? []"
                      :key="edge.id"
                      :x1="graphNodePositions.find((node) => node.id === edge.source)?.x ?? 260"
                      :y1="graphNodePositions.find((node) => node.id === edge.source)?.y ?? 235"
                      :x2="graphNodePositions.find((node) => node.id === edge.target)?.x ?? 260"
                      :y2="graphNodePositions.find((node) => node.id === edge.target)?.y ?? 235"
                      stroke="#3f3f46"
                      stroke-width="2"
                    />
                    <g v-for="node in graphNodePositions" :key="node.id">
                      <circle :cx="node.x" :cy="node.y" :r="node.depth === 0 ? 30 : 20" fill="#7c3aed" opacity="0.88" />
                      <text :x="node.x" :y="node.y + 42" fill="#e5e1e4" font-size="13" text-anchor="middle">{{ node.label }}</text>
                    </g>
                  </svg>
                </div>
              </div>
            </div>

            <div v-else-if="workspace.view.value === 'ai'" data-testid="stitch-ai-layout" class="grid h-[calc(100vh-64px)] min-h-0 grid-cols-1 bg-surface-base lg:grid-cols-[280px_minmax(0,1fr)]">
              <aside class="border-r border-border-subtle p-5">
                <h2 class="text-lg font-semibold">AI Chat</h2>
                <p class="mt-2 text-sm leading-6 text-text-muted">{{ workspace.profile.value?.profile_summary }}</p>
              </aside>
              <section class="overflow-auto p-6">
                <div data-testid="chat-function-grid" class="grid gap-3 xl:grid-cols-2">
                  <form class="glass-panel rounded-lg p-5" @submit.prevent="workspace.askVault">
                    <h3 class="mb-3 text-base font-semibold">Ask Vault</h3>
                    <textarea v-model="workspace.chatQuestion.value" class="premium-input min-h-36 w-full p-3" />
                    <button class="mt-3 inline-flex h-10 items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                      <Search class="size-4" />
                      Ask
                    </button>
                    <p v-if="workspace.chatResult.value" class="mt-4 text-sm leading-6 text-text-muted">{{ workspace.chatResult.value.answer }}</p>
                  </form>
                  <form class="glass-panel rounded-lg p-5" @submit.prevent="workspace.askCompanion">
                    <h3 class="mb-3 text-base font-semibold">Companion</h3>
                    <textarea v-model="workspace.companionQuestion.value" class="premium-input min-h-36 w-full p-3" />
                    <button class="mt-3 inline-flex h-10 items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                      <Bot class="size-4" />
                      Reply
                    </button>
                    <p v-if="workspace.companionResult.value" class="mt-4 text-sm leading-6 text-text-muted">{{ workspace.companionResult.value.direct_answer }}</p>
                  </form>
                </div>
              </section>
            </div>

            <div v-else data-testid="stitch-settings-layout" class="mx-auto grid w-full max-w-[1200px] gap-4 px-0 py-0 md:grid-cols-[260px_minmax(0,1fr)]">
              <aside class="glass-panel rounded-lg p-4">
                <button v-for="tab in [
                  { icon: UserRound, label: 'Profile' },
                  { icon: Palette, label: 'Appearance' },
                  { icon: Bell, label: 'Notifications' },
                  { icon: SlidersHorizontal, label: 'Advanced' },
                ]" :key="tab.label" class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-text-dim hover:bg-surface-container">
                  <component :is="tab.icon" class="size-4" />
                  {{ tab.label }}
                </button>
              </aside>
              <section class="grid gap-4">
                <div data-testid="insights-function-grid" class="glass-panel rounded-lg p-5">
                  <div class="mb-4 flex items-center gap-2">
                    <Sparkles class="size-5 text-primary" />
                    <h2 class="text-lg font-semibold">Insights</h2>
                  </div>
                  <div testId="insights-output-workspace" class="grid gap-3 md:grid-cols-2">
                    <article class="rounded-lg border border-border-subtle p-4">
                      <p class="text-sm font-semibold">Growth</p>
                      <p class="mt-2 text-sm leading-6 text-text-muted">{{ workspace.growth.value?.stage_summary }}</p>
                    </article>
                    <article class="rounded-lg border border-border-subtle p-4">
                      <p class="text-sm font-semibold">Advice</p>
                      <p class="mt-2 text-sm leading-6 text-text-muted">{{ workspace.advice.value?.advice_summary }}</p>
                    </article>
                  </div>
                </div>

                <div class="grid gap-3 md:grid-cols-3">
                  <article class="premium-card rounded-lg p-4">
                    <div class="premium-card-content">
                      <Database class="mb-3 size-5 text-primary" />
                      <p class="text-sm text-text-muted">Neo4j</p>
                      <p class="mt-1 font-semibold">{{ workspace.neo4jHealth.value?.backend ?? "unknown" }}</p>
                    </div>
                  </article>
                  <article class="premium-card rounded-lg p-4">
                    <div class="premium-card-content">
                      <CheckCircle2 class="mb-3 size-5 text-primary" />
                      <p class="text-sm text-text-muted">Readiness</p>
                      <p class="mt-1 font-semibold">{{ workspace.readiness.value?.overall_status ?? "loading" }}</p>
                    </div>
                  </article>
                  <article class="premium-card rounded-lg p-4">
                    <div class="premium-card-content">
                      <CircleDot class="mb-3 size-5 text-primary" />
                      <p class="text-sm text-text-muted">Analytics</p>
                      <p class="mt-1 font-semibold">{{ workspace.analytics.value?.documents.document_count ?? 0 }} docs</p>
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </div>
        </section>
      </section>
    </div>
  </main>
</template>
