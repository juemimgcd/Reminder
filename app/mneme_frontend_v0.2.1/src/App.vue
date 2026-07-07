<script setup lang="ts">
import {
  Bell,
  BookOpen,
  Bot,
  Boxes,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Copy,
  Database,
  File,
  FilePlus2,
  FlaskConical,
  FolderGit2,
  FolderOpen,
  FolderPlus,
  GitBranch,
  Grid3X3,
  HardDrive,
  KeyRound,
  LifeBuoy,
  ListFilter,
  LogOut,
  Menu,
  MessageSquare,
  MoreVertical,
  Network,
  Pencil,
  Pin,
  Play,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Tag,
  Upload,
  UserRound,
  Workflow,
  X,
  ZoomIn,
  ZoomOut,
} from "@lucide/vue";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type Simulation } from "d3";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useMnemeWorkspace, type WorkspaceCommandTab } from "./composables/useMnemeWorkspace";
import type { WorkspaceView } from "./types";

const workspace = useMnemeWorkspace();

const VIEW_ITEMS: Array<{ id: WorkspaceView; label: string; icon: unknown; hint: string }> = [
  { id: "dashboard", label: "Semantic Map", icon: Network, hint: "Workspace overview and semantic health" },
  { id: "notes", label: "Research Vault", icon: FolderOpen, hint: "Documents and durable memory" },
  { id: "graph", label: "Knowledge Graph", icon: GitBranch, hint: "GraphRAG node structure" },
  { id: "ai", label: "AI Laboratory", icon: FlaskConical, hint: "Ask and companion replies" },
  { id: "settings", label: "System Settings", icon: SlidersHorizontal, hint: "Health, profile, and analytics" },
];

const WORKSPACE_COMMANDS: Array<{ id: WorkspaceCommandTab; label: string; hint: string; icon: unknown }> = [
  { id: "create", label: "Create Vault", hint: "Start a research space", icon: FolderPlus },
  { id: "upload", label: "Upload File", hint: "Attach to active vault", icon: Upload },
  { id: "ask", label: "Ask Vault", hint: "Query indexed context", icon: Search },
  { id: "companion", label: "Companion", hint: "Reflective answer", icon: Bot },
];

const SETTINGS_TABS = ["General", "AI Models", "Security", "Data Sync"];

type ForceGraphNode = {
  id: string;
  label: string;
  nodeType: string;
  depth: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
};

type ForceGraphLink = {
  id: string;
  source: string | ForceGraphNode;
  target: string | ForceGraphNode;
};

const graphFileRailCollapsed = ref(false);
const graphSimulationNodes = ref<ForceGraphNode[]>([]);
const graphSimulationLinks = ref<ForceGraphLink[]>([]);
const draggingGraphNode = ref<ForceGraphNode | null>(null);
let graphSimulation: Simulation<ForceGraphNode, ForceGraphLink> | null = null;

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
const graphSelectedNode = computed(() => graphNodePositions.value.find((node) => node.depth === 1) ?? graphNodePositions.value[0] ?? null);
const graphSummary = computed(() => {
  const graph = workspace.graphData.value;
  if (!graph) {
    return "Graph data is loading.";
  }
  return `${graph.scope} graph with ${graph.nodes.length} nodes, ${graph.edges.length} edges, and ${graph.relationship_scope ?? "local"} relationships.`;
});
const memoryGovernanceSummary = computed(() => {
  const governance = workspace.memoryGovernance.value;
  if (!governance) {
    return "Memory governance is loading.";
  }
  return `${governance.canonical_memory_count} canonical memories consolidated from ${governance.raw_entry_count} raw entries.`;
});
const activeHealthLabel = computed(() => workspace.serviceHealth.value?.status ?? "loading");
const chatTranscript = computed(() => [
  {
    role: "user",
    text: workspace.chatQuestion.value || "Ask this vault about its strongest evidence.",
  },
  {
    role: "assistant",
    text:
      workspace.chatResult.value?.answer ??
      workspace.companionResult.value?.direct_answer ??
      "Ask a question to generate an evidence-backed response from the active vault.",
  },
]);

watch(
  () => workspace.graphData.value,
  (graph) => {
    graphSimulation?.stop();

    if (!graph) {
      graphSimulationNodes.value = [];
      graphSimulationLinks.value = [];
      return;
    }

    const previousPositions = new Map(graphSimulationNodes.value.map((node) => [node.id, { x: node.x, y: node.y }]));
    const nodes: ForceGraphNode[] = graph.nodes.map((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(graph.nodes.length, 1) - Math.PI / 2;
      const previous = previousPositions.get(node.id);
      return {
        id: node.id,
        label: node.label,
        nodeType: node.node_type,
        depth: node.depth,
        x: previous?.x ?? 380 + Math.cos(angle) * (node.depth === 0 ? 0 : 165 - node.depth * 24),
        y: previous?.y ?? 340 + Math.sin(angle) * (node.depth === 0 ? 0 : 165 - node.depth * 24),
      };
    });
    const links: ForceGraphLink[] = graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
    }));

    graphSimulationNodes.value = nodes;
    graphSimulationLinks.value = links;
    graphSimulation = forceSimulation<ForceGraphNode>(nodes)
      .force(
        "link",
        forceLink<ForceGraphNode, ForceGraphLink>(links)
          .id((node) => node.id)
          .distance(125)
          .strength(0.42),
      )
      .force("charge", forceManyBody<ForceGraphNode>().strength(-520))
      .force("center", forceCenter<ForceGraphNode>(380, 340))
      .force("collide", forceCollide<ForceGraphNode>().radius((node) => (node.depth === 0 ? 50 : 34)).strength(0.9))
      .alpha(0.95)
      .on("tick", () => {
        graphSimulationNodes.value = [...nodes];
        graphSimulationLinks.value = [...links];
      });
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  graphSimulation?.stop();
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

function openCreateCommand() {
  workspace.workspaceCommandTab.value = "create";
  workspace.view.value = "dashboard";
}

function endpointNode(endpoint: string | ForceGraphNode) {
  if (typeof endpoint !== "string") {
    return endpoint;
  }
  return graphSimulationNodes.value.find((node) => node.id === endpoint) ?? null;
}

function endpointX(endpoint: string | ForceGraphNode) {
  return endpointNode(endpoint)?.x ?? 380;
}

function endpointY(endpoint: string | ForceGraphNode) {
  return endpointNode(endpoint)?.y ?? 340;
}

function graphNodeRadius(node: ForceGraphNode) {
  return node.depth === 0 ? 22 : node.depth === 1 ? 15 : 9;
}

function graphNodeFill(node: ForceGraphNode) {
  return node.depth === 0 ? "#7c3aed" : "#c6c6c7";
}

function graphPointerPoint(event: PointerEvent) {
  const svg = (event.currentTarget as SVGElement).ownerSVGElement ?? (event.currentTarget as SVGSVGElement);
  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const matrix = svg.getScreenCTM();
  if (!matrix) {
    return { x: event.offsetX, y: event.offsetY };
  }
  return point.matrixTransform(matrix.inverse());
}

function startGraphNodeDrag(node: ForceGraphNode, event: PointerEvent) {
  draggingGraphNode.value = node;
  const point = graphPointerPoint(event);
  node.fx = point.x;
  node.fy = point.y;
  node.x = point.x;
  node.y = point.y;
  graphSimulation?.alphaTarget(0.28).restart();
  (event.currentTarget as Element).setPointerCapture?.(event.pointerId);
}

function moveGraphNodeDrag(event: PointerEvent) {
  if (!draggingGraphNode.value) {
    return;
  }
  const point = graphPointerPoint(event);
  draggingGraphNode.value.fx = point.x;
  draggingGraphNode.value.fy = point.y;
  draggingGraphNode.value.x = point.x;
  draggingGraphNode.value.y = point.y;
  graphSimulationNodes.value = [...graphSimulationNodes.value];
}

function endGraphNodeDrag() {
  if (!draggingGraphNode.value) {
    return;
  }
  draggingGraphNode.value.fx = null;
  draggingGraphNode.value.fy = null;
  draggingGraphNode.value = null;
  graphSimulation?.alphaTarget(0);
}
</script>

<template>
  <main v-if="!workspace.isAuthenticated.value" class="mneme-workbench grid min-h-screen place-items-center bg-surface-base px-4 text-on-surface">
    <section class="glass-panel w-full max-w-[440px] rounded-lg p-6">
      <div class="mb-6 flex items-center gap-3">
        <div class="grid size-10 place-items-center rounded-lg bg-primary-container text-on-primary-container">
          <BrainCircuit class="size-5" />
        </div>
        <div>
          <h1 class="text-xl font-semibold">Mneme Intelligence</h1>
          <p class="text-sm text-text-muted">Cognitive Sanctuary</p>
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
      <aside data-testid="sanctuary-sidebar" class="stitch-sidebar flex w-64 flex-col" style="width: 256px">
        <div class="px-5 pb-5 pt-7">
          <div class="mb-7 flex items-center gap-3">
            <div class="grid size-10 place-items-center rounded-lg border border-primary/30 bg-primary-container/20 text-primary">
              <BrainCircuit class="size-5" />
            </div>
            <div class="min-w-0">
              <h1 class="text-[22px] font-bold leading-7 text-primary">{{ workspace.view.value === "ai" ? "Cognitive Sanctuary" : "Mneme Intelligence" }}</h1>
              <p class="font-mono text-[11px] uppercase text-on-surface-variant">{{ workspace.view.value === "ai" ? "Deep Thought Mode" : "Cognitive Sanctuary" }}</p>
            </div>
          </div>

          <button class="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-primary-container px-4 font-mono text-sm font-semibold text-on-primary-container transition hover:brightness-110" @click="openCreateCommand">
            <Plus class="size-4" />
            {{ workspace.view.value === "ai" ? "New Memory" : "New Research" }}
          </button>
        </div>

        <nav class="flex-1 overflow-y-auto px-4 py-2">
          <div class="grid gap-1 border-b border-outline-variant/20 pb-4">
            <button
              v-for="item in VIEW_ITEMS"
              :key="item.id"
              class="flex h-11 items-center gap-3 rounded-md px-3 text-left text-sm transition"
              :class="workspace.view.value === item.id ? 'bg-primary/10 text-primary ring-1 ring-primary/20' : 'text-on-surface-variant hover:bg-surface-container-high/50 hover:text-on-surface'"
              :aria-pressed="workspace.view.value === item.id"
              @click="workspace.view.value = item.id"
            >
              <component :is="item.icon" class="size-4 shrink-0" />
              <span class="font-medium">{{ item.label }}</span>
            </button>
          </div>

          <section data-testid="sidebar-group-vaults" class="mt-5 grid gap-2">
            <div class="flex items-center justify-between px-2 font-mono text-[11px] uppercase text-text-muted">
              <span>Research Spaces</span>
              <button class="premium-action-btn grid size-7 place-items-center rounded-md" title="Create vault" @click="openCreateCommand">
                <FolderPlus class="size-3.5" />
              </button>
            </div>
            <button
              v-for="vault in workspace.knowledgeBases.value"
              :key="vault.id"
              class="rounded-md px-3 py-2 text-left text-sm"
              :class="workspace.selectedKnowledgeBaseId.value === vault.id ? 'bg-surface-container-high text-primary ring-1 ring-primary/30' : 'text-text-dim hover:bg-surface-container'"
              @click="workspace.selectKnowledgeBase(vault.id)"
            >
              <span class="block truncate font-semibold">{{ vault.name }}</span>
              <span class="block truncate text-xs text-text-muted">{{ vault.description || "No description" }}</span>
            </button>
          </section>

          <section data-testid="sidebar-group-files" class="mt-5 grid gap-2">
            <div class="px-2 font-mono text-[11px] uppercase text-text-muted">Recent Files</div>
            <button v-for="doc in workspace.selectedDocuments.value" :key="doc.id" class="rounded-md px-3 py-2 text-left text-sm text-text-dim hover:bg-surface-container">
              <span class="block truncate font-medium">{{ doc.file_name }}</span>
              <span class="block text-xs text-text-muted">{{ doc.status }} - {{ formatDate(doc.created_at) }}</span>
            </button>
          </section>
        </nav>

        <footer class="border-t border-outline-variant/20 p-4">
          <div class="mb-3 grid gap-1">
            <a class="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-on-surface-variant hover:text-primary" href="#">
              <BookOpen class="size-4" />
              Documentation
            </a>
            <a class="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-on-surface-variant hover:text-primary" href="#">
              <LifeBuoy class="size-4" />
              Support
            </a>
          </div>
          <div class="flex items-center gap-3 rounded-md bg-surface-container-low p-3">
            <div class="grid size-8 place-items-center rounded-full bg-primary-container/30 text-primary">
              <UserRound class="size-4" />
            </div>
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold">{{ workspace.user.value?.display_name || workspace.user.value?.username }}</p>
              <p class="truncate text-xs text-text-muted">{{ workspace.user.value?.username }}</p>
            </div>
          </div>
        </footer>
      </aside>

      <section class="flex min-w-0 flex-col">
        <header v-if="workspace.view.value !== 'graph' && workspace.view.value !== 'ai'" data-testid="sanctuary-topbar" class="flex h-16 items-center justify-between border-b border-white/5 bg-surface/65 px-5 backdrop-blur-xl lg:px-8">
          <div data-testid="sanctuary-active-view" class="min-w-0">
            <p class="truncate font-mono text-xs text-primary">{{ currentViewItem.hint }}</p>
            <h2 class="truncate text-xl font-semibold">{{ currentViewItem.label }}</h2>
          </div>
          <div class="flex items-center gap-2">
            <span class="hidden rounded-md border border-outline-variant/30 px-3 py-1 font-mono text-xs text-text-muted sm:inline-flex">{{ activeHealthLabel }}</span>
            <button class="premium-action-btn grid size-9 place-items-center rounded-md" title="Refresh panels" @click="workspace.loadKnowledgeBasePanels">
              <RefreshCw class="size-4" />
            </button>
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
            <div v-if="workspace.view.value !== 'graph' && workspace.view.value !== 'notes' && workspace.view.value !== 'ai'" class="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p class="font-mono text-xs text-primary">{{ workspace.selectedKnowledgeBase.value?.name ?? "No vault selected" }}</p>
                <h1 class="mt-2 text-3xl font-semibold">{{ currentViewItem.label }}</h1>
              </div>
              <p class="max-w-2xl text-sm leading-6 text-text-muted">{{ workspace.banner.value || graphSummary }}</p>
            </div>

            <div v-if="workspace.view.value === 'dashboard'" data-testid="dashboard-overview">
              <div data-testid="stitch-dashboard-grid" class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <section class="stitch-card rounded-lg p-5">
                  <File class="mb-4 size-5 text-primary" />
                  <p class="text-sm text-text-muted">Documents</p>
                  <p class="mt-2 text-3xl font-semibold">{{ workspace.selectedDocuments.value.length }}</p>
                  <p class="mt-2 text-xs text-text-muted">{{ workspace.indexedDocumentCount.value }} indexed</p>
                </section>
                <section class="stitch-card rounded-lg p-5">
                  <Database class="mb-4 size-5 text-primary" />
                  <p class="text-sm text-text-muted">Memory</p>
                  <p class="mt-2 text-3xl font-semibold">{{ workspace.memoryLibrary.value?.timeline.length ?? 0 }}</p>
                  <p class="mt-2 text-xs text-text-muted">{{ workspace.memoryGovernance.value?.canonical_memory_count ?? 0 }} canonical</p>
                </section>
                <section class="stitch-card rounded-lg p-5">
                  <Network class="mb-4 size-5 text-primary" />
                  <p class="text-sm text-text-muted">Graph Nodes</p>
                  <p class="mt-2 text-3xl font-semibold">{{ workspace.graphData.value?.nodes.length ?? 0 }}</p>
                  <p class="mt-2 text-xs text-text-muted">{{ workspace.graphData.value?.edges.length ?? 0 }} relations</p>
                </section>
                <section class="stitch-card rounded-lg p-5">
                  <CheckCircle2 class="mb-4 size-5 text-primary" />
                  <p class="text-sm text-text-muted">Readiness</p>
                  <p class="mt-2 text-3xl font-semibold">{{ workspace.readiness.value?.overall_status ?? "..." }}</p>
                  <p class="mt-2 text-xs text-text-muted">{{ workspace.neo4jHealth.value?.backend ?? "graph backend" }}</p>
                </section>

                <section data-testid="unified-command-module" class="glass-panel rounded-lg md:col-span-2 xl:col-span-4">
                  <div class="grid xl:grid-cols-[240px_minmax(0,1fr)]">
                    <nav data-testid="workspace-command-tabs" class="border-b border-white/10 p-2 xl:border-b-0 xl:border-r xl:border-white/10">
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

                    <div data-testid="workspace-command-panel" class="min-w-0 p-5">
                      <form v-if="workspace.workspaceCommandTab.value === 'create'" data-testid="workspace-create-kb-command" class="mx-auto grid max-w-3xl gap-3" @submit.prevent="workspace.createKnowledgeBase">
                        <input v-model="workspace.knowledgeBaseForm.value.name" class="premium-input h-10 px-3" placeholder="Vault name" />
                        <textarea v-model="workspace.knowledgeBaseForm.value.description" class="premium-input min-h-24 p-3" placeholder="Description"></textarea>
                        <button class="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                          <FolderPlus class="size-4" />
                          Create
                        </button>
                      </form>

                      <div v-else-if="workspace.workspaceCommandTab.value === 'upload'" data-testid="workspace-upload-command" class="mx-auto grid max-w-3xl gap-3">
                        <div class="rounded-lg border border-dashed border-outline-variant/40 p-6 text-sm text-text-muted">
                          <FilePlus2 class="mb-3 size-5 text-primary" />
                          Upload is connected to the backend API surface; preview mode keeps files local for layout review.
                        </div>
                      </div>

                      <form v-else-if="workspace.workspaceCommandTab.value === 'ask'" data-testid="workspace-chat-command" class="grid gap-3" @submit.prevent="workspace.askVault">
                        <textarea v-model="workspace.chatQuestion.value" class="premium-input min-h-28 p-3" />
                        <button class="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                          <Search class="size-4" />
                          Ask vault
                        </button>
                        <p v-if="workspace.chatResult.value" class="rounded-lg border border-outline-variant/30 bg-surface-container-low p-4 text-sm leading-6 text-on-surface">
                          {{ workspace.chatResult.value.answer }}
                        </p>
                      </form>

                      <form v-else class="grid gap-3" @submit.prevent="workspace.askCompanion">
                        <textarea v-model="workspace.companionQuestion.value" class="premium-input min-h-28 p-3" />
                        <button class="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-primary-container px-4 text-sm font-semibold text-on-primary-container">
                          <Bot class="size-4" />
                          Ask companion
                        </button>
                        <p v-if="workspace.companionResult.value" class="rounded-lg border border-outline-variant/30 bg-surface-container-low p-4 text-sm leading-6 text-on-surface">
                          {{ workspace.companionResult.value.direct_answer }}
                        </p>
                      </form>
                    </div>
                  </div>
                </section>
              </div>
            </div>

            <div v-else-if="workspace.view.value === 'notes'" data-testid="stitch-research-vault-layout" class="grid h-[calc(100vh-64px)] min-h-0 grid-cols-1 bg-surface-base lg:grid-cols-[360px_minmax(0,1fr)]">
              <aside class="stitch-panel border-r border-outline-variant/30 p-5">
                <div class="mb-5 flex items-center justify-between">
                  <div>
                    <p class="font-mono text-xs uppercase text-text-muted">Directories</p>
                    <h2 class="mt-1 text-lg font-semibold">Research Vault</h2>
                  </div>
                  <button class="premium-action-btn grid size-8 place-items-center rounded-md" @click="openCreateCommand">
                    <Plus class="size-4" />
                  </button>
                </div>
                <div class="grid gap-2">
                  <button
                    v-for="vault in workspace.knowledgeBases.value"
                    :key="vault.id"
                    class="flex items-start gap-3 rounded-md px-3 py-3 text-left"
                    :class="workspace.selectedKnowledgeBaseId.value === vault.id ? 'bg-surface-container-high text-primary ring-1 ring-primary/30' : 'text-on-surface-variant hover:bg-surface-container'"
                    @click="workspace.selectKnowledgeBase(vault.id)"
                  >
                    <FolderOpen class="mt-0.5 size-4 shrink-0" />
                    <span class="min-w-0">
                      <span class="block truncate text-sm font-semibold">{{ vault.name }}</span>
                      <span class="block truncate text-xs text-text-muted">{{ vault.description || "No description" }}</span>
                    </span>
                  </button>
                </div>
                <div class="mt-8">
                  <p class="mb-3 font-mono text-xs uppercase text-text-muted">Saved Tags</p>
                  <div class="flex flex-wrap gap-2">
                    <span class="premium-tag rounded-full px-3 py-1 font-mono text-xs text-on-surface-variant">#research</span>
                    <span class="premium-tag rounded-full px-3 py-1 font-mono text-xs text-on-surface-variant">#memory</span>
                    <span class="premium-tag rounded-full px-3 py-1 font-mono text-xs text-on-surface-variant">#graph</span>
                  </div>
                </div>
              </aside>

              <section class="min-w-0 overflow-auto p-6 lg:p-8">
                <div class="mb-7 flex items-center justify-between gap-4">
                  <div>
                    <p class="font-mono text-xs text-primary">{{ workspace.selectedKnowledgeBase.value?.description || "Active research space" }}</p>
                    <h2 class="mt-2 text-3xl font-semibold">{{ workspace.selectedKnowledgeBase.value?.name ?? "No vault selected" }}</h2>
                  </div>
                  <div class="hidden items-center gap-2 sm:flex">
                    <button class="premium-action-btn grid size-9 place-items-center rounded-md"><ListFilter class="size-4" /></button>
                    <button class="premium-action-btn grid size-9 place-items-center rounded-md"><Grid3X3 class="size-4" /></button>
                  </div>
                </div>

                <div v-if="workspace.selectedDocuments.value.length" data-testid="memory-function-grid" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <article v-for="doc in workspace.selectedDocuments.value" :key="doc.id" class="stitch-card rounded-lg p-4">
                    <div class="mb-14 flex items-center justify-between">
                      <File class="size-8 text-primary/80" />
                      <span class="rounded-full border px-2 py-0.5 text-[11px]" :class="statusClass(doc.status)">{{ doc.status }}</span>
                    </div>
                    <h3 class="truncate text-base font-semibold">{{ doc.file_name }}</h3>
                    <p class="mt-2 font-mono text-xs text-primary">#{{ doc.file_type || "document" }} #research</p>
                    <div class="mt-4 flex items-center justify-between border-t border-outline-variant/20 pt-3 font-mono text-xs text-text-muted">
                      <span class="inline-flex items-center gap-1"><Clock3 class="size-3.5" /> {{ formatDate(doc.created_at) }}</span>
                      <span>{{ doc.file_type }}</span>
                    </div>
                  </article>
                </div>
                <div v-else class="stitch-panel rounded-lg p-8 text-sm text-text-muted">No documents in this vault yet.</div>

                <section data-testid="memory-output-workspace" class="mt-6 grid gap-3">
                  <article v-for="entry in workspace.memoryLibrary.value?.timeline ?? []" :key="entry.entry_id" class="rounded-lg border border-outline-variant/30 bg-surface-container-low/40 p-4">
                    <p class="text-sm font-semibold">{{ entry.entry_name }}</p>
                    <p class="mt-1 text-sm leading-6 text-text-muted">{{ entry.summary }}</p>
                  </article>
                </section>
              </section>
            </div>

            <div v-else-if="workspace.view.value === 'graph'" data-testid="stitch-graph-layout" class="relative min-h-screen overflow-hidden bg-[#08080a]" title="Graph Workspace">
              <div
                data-testid="graph-function-grid"
                class="grid h-screen min-h-screen grid-cols-1 transition-[grid-template-columns] duration-200"
                :class="graphFileRailCollapsed ? 'xl:grid-cols-[0_minmax(0,1fr)_376px]' : 'xl:grid-cols-[320px_minmax(0,1fr)_376px]'"
              >
                <aside
                  data-testid="graph-file-rail"
                  class="stitch-panel border-r border-outline-variant/30"
                  :class="graphFileRailCollapsed ? 'invisible pointer-events-none overflow-hidden border-r-0' : ''"
                  :aria-hidden="graphFileRailCollapsed"
                >
                  <div class="flex h-[68px] items-center gap-4 border-b border-outline-variant/20 px-5">
                    <Menu class="size-5 text-text-muted" />
                    <h2 class="text-base font-medium">Files</h2>
                    <div class="ml-auto flex gap-3 text-text-muted">
                      <FilePlus2 class="size-5" />
                      <FolderPlus class="size-5" />
                    </div>
                  </div>
                  <div class="space-y-4 p-5">
                    <div>
                      <div class="mb-3 flex items-center gap-3 text-on-surface">
                        <FolderOpen class="size-5 text-on-surface-variant" />
                        <span class="text-base">Machine Learning</span>
                      </div>
                      <div class="ml-8 grid gap-1">
                        <button class="flex h-10 items-center gap-3 rounded bg-surface-container-high px-3 text-left text-primary">
                          <File class="size-5" />
                          <span>Neural Networks</span>
                        </button>
                        <button class="flex h-10 items-center gap-3 rounded px-3 text-left text-on-surface-variant hover:bg-surface-container">
                          <File class="size-5" />
                          <span>Gradient Descent</span>
                        </button>
                        <button class="flex h-10 items-center gap-3 rounded px-3 text-left text-on-surface-variant hover:bg-surface-container">
                          <File class="size-5" />
                          <span>Optimization</span>
                        </button>
                      </div>
                    </div>
                    <button class="flex h-10 items-center gap-3 rounded px-3 text-left text-on-surface-variant hover:bg-surface-container">
                      <FolderOpen class="size-5" />
                      <span>Architecture</span>
                    </button>
                    <button class="flex h-10 items-center gap-3 rounded px-3 text-left text-on-surface-variant hover:bg-surface-container">
                      <FolderOpen class="size-5" />
                      <span>Research Papers</span>
                    </button>
                    <button v-for="doc in workspace.selectedDocuments.value" :key="doc.id" class="flex h-10 items-center gap-3 rounded px-3 text-left text-on-surface-variant hover:bg-surface-container">
                      <File class="size-5" />
                      <span class="truncate">{{ doc.file_name }}</span>
                    </button>
                  </div>
                </aside>

                <section data-testid="graph-output-workspace" class="relative min-h-[640px] overflow-hidden bg-[#070708]">
                  <div class="absolute left-5 top-5 z-10 flex gap-10">
                    <button class="glass-panel flex h-16 items-center gap-3 rounded-md px-5 text-base text-on-surface">
                      <Network class="size-7 text-primary" />
                      Graph View
                    </button>
                    <div class="grid gap-3">
                      <div class="glass-panel flex h-12 w-[328px] items-center gap-3 rounded-lg px-5 text-text-muted">
                        <Search class="size-5" />
                        Search knowledge base...
                      </div>
                      <div class="glass-panel flex h-16 items-center gap-5 rounded-lg px-3">
                        <button class="rounded border border-primary/40 bg-primary/10 px-3 py-2 text-sm text-primary">All Nodes</button>
                        <button class="px-3 py-2 text-sm text-on-surface-variant">Tags</button>
                        <button class="px-3 py-2 text-sm text-on-surface-variant">Orphans</button>
                        <button class="border-l border-outline-variant/30 pl-5 text-on-surface-variant"><SlidersHorizontal class="size-5" /></button>
                      </div>
                    </div>
                  </div>

                  <svg
                    class="h-full min-h-[640px] w-full touch-none select-none"
                    viewBox="0 0 760 680"
                    role="img"
                    aria-label="Knowledge graph"
                    @pointermove="moveGraphNodeDrag"
                    @pointerup="endGraphNodeDrag"
                    @pointerleave="endGraphNodeDrag"
                  >
                    <g stroke="#3f3f46" stroke-width="2">
                      <line
                        v-for="edge in graphSimulationLinks"
                        :key="edge.id"
                        :x1="endpointX(edge.source)"
                        :y1="endpointY(edge.source)"
                        :x2="endpointX(edge.target)"
                        :y2="endpointY(edge.target)"
                      />
                    </g>
                    <g
                      v-for="node in graphSimulationNodes"
                      :key="node.id"
                      data-testid="force-node"
                      :data-node-id="node.id"
                      class="cursor-grab active:cursor-grabbing"
                      @pointerdown="startGraphNodeDrag(node, $event)"
                    >
                      <circle
                        :cx="node.x ?? 380"
                        :cy="node.y ?? 340"
                        :r="graphNodeRadius(node)"
                        :fill="graphNodeFill(node)"
                        :stroke="node.depth === 0 ? '#d2bbff' : 'transparent'"
                        :stroke-width="node.depth === 0 ? 4 : 0"
                      />
                      <text
                        :x="node.x ?? 380"
                        :y="(node.y ?? 340) + graphNodeRadius(node) + 24"
                        fill="#fafafa"
                        :font-size="node.depth === 0 ? 20 : 15"
                        :font-weight="node.depth === 0 ? 700 : 500"
                        text-anchor="middle"
                      >
                        {{ node.label }}
                      </text>
                    </g>
                  </svg>

                  <div class="glass-panel absolute left-[58%] top-[47%] hidden items-center gap-3 rounded px-4 py-3 text-sm text-on-surface-variant xl:flex">
                    <Workflow class="size-7 text-primary" />
                    <span>Long press to preview</span>
                  </div>

                  <button
                    data-testid="graph-file-rail-toggle"
                    class="glass-panel absolute top-1/2 z-50 grid size-12 place-items-center rounded-full text-text-muted"
                    :class="graphFileRailCollapsed ? 'left-4' : 'left-[-16px]'"
                    :title="graphFileRailCollapsed ? 'Expand file list' : 'Collapse file list'"
                    @click="graphFileRailCollapsed = !graphFileRailCollapsed"
                  >
                    <ChevronDown class="size-5" :class="graphFileRailCollapsed ? '-rotate-90' : 'rotate-90'" />
                  </button>

                  <div class="glass-panel absolute bottom-7 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-lg p-2">
                    <button class="premium-action-btn grid size-12 place-items-center rounded-md"><ZoomIn class="size-5" /></button>
                    <button class="premium-action-btn grid size-12 place-items-center rounded-md"><ZoomOut class="size-5" /></button>
                    <button class="premium-action-btn grid size-12 place-items-center rounded-md"><Target class="size-5" /></button>
                    <button class="premium-action-btn grid size-12 place-items-center rounded-md"><Play class="size-5" /></button>
                  </div>
                </section>

                <aside class="stitch-panel border-l border-outline-variant/30">
                  <div class="flex h-[68px] items-center justify-between border-b border-outline-variant/20 px-5">
                    <p class="font-semibold">Properties</p>
                    <div class="flex gap-5 text-text-muted">
                      <Pencil class="size-5" />
                      <X class="size-5" />
                    </div>
                  </div>
                  <div class="p-5">
                    <h2 class="text-3xl font-semibold">Neural Networks</h2>
                    <div class="mt-4 flex flex-wrap gap-2">
                      <span class="premium-tag rounded px-2 py-1 font-mono text-xs text-on-surface-variant">#ai</span>
                      <span class="premium-tag rounded px-2 py-1 font-mono text-xs text-on-surface-variant">#machine-learning</span>
                      <span class="premium-tag rounded px-2 py-1 font-mono text-xs text-on-surface-variant">#core</span>
                      <span class="premium-tag rounded border-dashed px-2 py-1 font-mono text-xs text-on-surface-variant">+ Add tag</span>
                    </div>
                    <div class="mt-8">
                      <p class="mb-4 font-mono text-xs uppercase tracking-wide text-text-muted">Summary</p>
                      <p class="text-base leading-7 text-on-surface-variant">A computing system inspired by the biological neural networks that constitute animal brains. Neural networks are composed of node layers, containing an input layer, one or more hidden layers, and an output layer.</p>
                      <a class="mt-4 inline-flex items-center gap-2 text-primary" href="#">Read full note <ChevronDown class="size-4 -rotate-90" /></a>
                    </div>
                    <div class="mt-9 grid gap-4 text-sm">
                      <p class="font-mono text-xs uppercase tracking-wide text-text-muted">Metadata</p>
                      <div class="flex justify-between"><span class="text-text-muted">Created</span><span>Oct 12, 2023</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">Modified</span><span>2 days ago</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">Connections</span><span>{{ workspace.graphData.value?.edges.length ?? 8 }} nodes</span></div>
                      <div class="flex justify-between"><span class="text-text-muted">Status</span><span class="text-emerald-300">Evergreen</span></div>
                    </div>
                    <div class="mt-9">
                      <p class="mb-4 font-mono text-xs uppercase tracking-wide text-text-muted">Backlinks (5)</p>
                      <article class="border border-outline-variant/30 bg-surface-container-low p-3">
                        <p class="font-semibold">Deep Learning</p>
                        <p class="mt-1 text-sm text-text-muted">...subset of machine learning based on artificial neural networks.</p>
                      </article>
                    </div>
                  </div>
                </aside>
              </div>
            </div>

            <div v-else-if="workspace.view.value === 'ai'" data-testid="stitch-ai-laboratory-layout" class="grid h-screen min-h-0 grid-cols-1 bg-[#070708] lg:grid-cols-[320px_minmax(0,1fr)]">
              <aside class="stitch-panel border-r border-outline-variant/30 p-5">
                <div class="premium-input mb-5 flex h-10 items-center gap-3 rounded px-3 text-text-muted">
                  <Search class="size-4" />
                  Search history...
                </div>
                <button class="mb-6 flex h-12 w-full items-center justify-center gap-3 rounded bg-surface-container-high text-base font-semibold">
                  <MessageSquare class="size-5" />
                  New Chat
                </button>
                <div class="grid gap-2">
                  <button class="rounded border border-primary/40 bg-surface-container-high px-4 py-3 text-left">
                    <span class="block truncate text-sm font-semibold text-primary">Project Mnemosyne: Synthesis</span>
                    <span class="text-xs text-text-muted">Today, 14:03</span>
                  </button>
                  <button class="rounded px-4 py-3 text-left text-on-surface-variant hover:bg-surface-container">
                    <span class="block truncate text-sm font-semibold">Quantum Entanglement Analysis</span>
                    <span class="text-xs text-text-muted">Yesterday, 09:45</span>
                  </button>
                  <button class="rounded px-4 py-3 text-left text-on-surface-variant hover:bg-surface-container">
                    <span class="block truncate text-sm font-semibold">Neural Network Synthesis</span>
                    <span class="text-xs text-text-muted">Oct 24, 2023</span>
                  </button>
                  <button class="rounded px-4 py-3 text-left text-on-surface-variant hover:bg-surface-container">
                    <span class="block truncate text-sm font-semibold">Project Mnemosyne Plan</span>
                    <span class="text-xs text-text-muted">Oct 22, 2023</span>
                  </button>
                </div>
                <button class="glass-panel absolute right-[-18px] top-1/2 hidden size-12 place-items-center rounded-full text-text-muted lg:grid">
                  <ChevronDown class="size-5 rotate-90" />
                </button>
              </aside>

              <section data-testid="chat-function-grid" class="relative flex min-w-0 flex-col">
                <header class="flex h-20 items-center justify-between border-b border-outline-variant/10 px-8">
                  <div>
                    <h2 class="text-3xl font-semibold leading-none">Project Mnemosyne: Synthesis</h2>
                    <p class="mt-2 font-mono text-xs text-text-muted">
                      <span class="text-primary">●</span> Model: M-Cognitive v4.2 - Context: 128k Tokens
                    </p>
                  </div>
                  <div class="flex gap-6 text-on-surface-variant">
                    <Search class="size-5" />
                    <MoreVertical class="size-5" />
                  </div>
                </header>

                <div class="flex-1 overflow-auto px-8 pb-8 pt-16">
                  <div class="mx-auto max-w-[900px]">
                    <div class="mb-12 flex justify-center">
                      <span class="rounded-full bg-surface-container-high px-4 py-1 font-mono text-xs text-on-surface-variant">Today, 14:03</span>
                    </div>

                    <div class="mb-8 flex justify-end">
                      <div class="max-w-[675px] rounded bg-surface-container-high px-6 py-5 text-base leading-7">
                        Analyze the latest research nodes connected to "Quantum Entanglement in Biological Systems". Summarize the core contradictions in the recent methodologies.
                      </div>
                    </div>

                    <div class="mb-8 grid grid-cols-[44px_minmax(0,1fr)] gap-5">
                      <div class="grid size-10 place-items-center rounded-lg border border-primary/40 bg-primary/10 text-primary">
                        <Bot class="size-5" />
                      </div>
                      <article class="rounded border border-outline-variant/30 border-l-4 border-l-primary bg-[#0c0c0e] p-6 text-base leading-8">
                        <p>Based on the current knowledge graph traversal, there are 3 primary nodes referencing "Quantum Entanglement in Biological Systems" updated in the last 72 hours.</p>
                        <p class="mt-5">The core contradictions arise from the environmental decoherence models used:</p>
                        <ul class="mt-4 list-disc space-y-3 pl-6">
                          <li><span class="text-primary">Node A (Dr. Chen, 2024):</span> Posits that macromolecular shielding extends coherence times up to 100fs.</li>
                          <li><span class="text-primary">Node B (Symposium proceedings):</span> Argues thermal noise disrupts entanglement within 10fs, challenging the shielding hypothesis entirely.</li>
                        </ul>
                        <div class="mt-8 flex flex-wrap gap-3 border-t border-outline-variant/20 pt-4">
                          <span class="premium-tag rounded px-3 py-1 font-mono text-xs text-on-surface-variant">doc_ref_492.pdf</span>
                          <span class="premium-tag rounded px-3 py-1 font-mono text-xs text-on-surface-variant">Graph Node: Bio-Q</span>
                        </div>
                      </article>
                    </div>

                    <div class="mb-8 flex justify-end">
                      <div class="max-w-[520px] rounded bg-surface-container-high px-6 py-4 text-base">Can you generate a visual map of these contradictions?</div>
                    </div>

                    <div class="mb-24 grid grid-cols-[44px_minmax(0,1fr)] gap-5">
                      <div class="grid size-10 place-items-center rounded-lg border border-primary/40 bg-primary/10 text-primary">
                        <Bot class="size-5" />
                      </div>
                      <div class="inline-flex w-fit items-center gap-2 rounded border border-outline-variant/30 border-l-4 border-l-primary bg-[#0c0c0e] px-5 py-4">
                        <span class="size-2 rounded-full bg-primary"></span>
                        <span class="size-2 rounded-full bg-primary"></span>
                        <span class="size-2 rounded-full bg-primary"></span>
                      </div>
                    </div>
                  </div>
                </div>

                <form data-testid="workspace-chat-command" class="sticky bottom-0 border-t border-outline-variant/10 bg-[#070708]/95 px-8 pb-7 pt-4 backdrop-blur" @submit.prevent="workspace.askVault">
                  <div class="mx-auto max-w-[900px]">
                    <div class="rounded-lg border border-outline-variant/30 bg-surface-container-low p-4">
                      <div class="mb-3 flex w-fit items-center gap-2 rounded-full bg-surface-container-high px-3 py-1 font-mono text-xs text-on-surface-variant">
                        Context: Node B
                        <X class="size-3" />
                      </div>
                      <div class="flex items-center gap-4">
                        <Upload class="size-5 text-on-surface-variant" />
                        <Workflow class="size-5 text-on-surface-variant" />
                        <textarea v-model="workspace.chatQuestion.value" class="premium-input min-h-12 flex-1 resize-none border-0 bg-transparent p-3" placeholder="Message Cognitive Sanctuary... (/ for commands, @ for nodes)" />
                        <button class="grid size-12 place-items-center rounded bg-primary-container text-on-primary-container">
                          <Send class="size-6" />
                        </button>
                      </div>
                    </div>
                    <p class="mt-3 text-center font-mono text-xs text-text-muted">AI responses may be structurally imperfect. Verify critical data against original research nodes.</p>
                  </div>
                </form>
              </section>
            </div>

            <div v-else data-testid="stitch-settings-layout" class="mx-auto grid w-full max-w-[1200px] gap-6 md:grid-cols-[280px_minmax(0,1fr)]">
              <aside class="grid h-fit gap-2">
                <h2 class="mb-6 text-3xl font-semibold">Settings</h2>
                <button v-for="tab in SETTINGS_TABS" :key="tab" class="rounded-md px-5 py-3 text-left font-mono text-sm" :class="tab === 'AI Models' ? 'bg-surface-container-high text-primary ring-1 ring-primary/30' : 'text-on-surface-variant hover:bg-surface-container'">
                  {{ tab }}
                </button>
              </aside>

              <section class="grid gap-6">
                <article class="stitch-card rounded-lg p-6">
                  <div class="mb-6 flex items-center gap-3">
                    <BrainCircuit class="size-6 text-primary" />
                    <h2 class="text-2xl font-semibold">Cognitive Engine Selection</h2>
                  </div>
                  <div class="grid gap-4 md:grid-cols-2">
                    <div class="rounded-lg border border-primary/60 bg-surface-container/60 p-5">
                      <h3 class="font-mono text-base font-semibold">M-Cognitive v4.2</h3>
                      <p class="mt-3 text-sm leading-6 text-on-surface-variant">Local semantic mapping engine tuned for graph queries and vault synthesis.</p>
                    </div>
                    <div class="rounded-lg border border-outline-variant/20 bg-surface-container-low p-5">
                      <h3 class="font-mono text-base font-semibold">Configured Provider</h3>
                      <p class="mt-3 text-sm leading-6 text-on-surface-variant">{{ workspace.neo4jHealth.value?.backend ?? "Backend configuration pending" }}</p>
                    </div>
                  </div>
                  <div class="mt-6">
                    <div class="mb-2 flex justify-between font-mono text-sm">
                      <span>Context Window Size</span>
                      <span class="text-primary">64,000</span>
                    </div>
                    <input class="premium-range w-full" type="range" min="8" max="128" value="64" />
                  </div>
                </article>

                <article class="stitch-card rounded-lg p-6">
                  <div class="mb-6 flex items-center gap-3">
                    <KeyRound class="size-6 text-primary" />
                    <h2 class="text-2xl font-semibold">API Access & Security</h2>
                  </div>
                  <label class="grid gap-2">
                    <span class="font-mono text-sm">Primary Access Token</span>
                    <span class="flex items-center gap-3">
                      <input class="premium-input h-11 flex-1 px-3 font-mono" value="••••••••••••••••••••••••••••••••" readonly />
                      <button class="premium-action-btn inline-flex h-11 items-center gap-2 rounded-md px-4 font-mono text-sm">
                        <Copy class="size-4" />
                        Copy
                      </button>
                    </span>
                  </label>
                  <p class="mt-3 text-sm text-text-muted">Never share this key. It provides full access to your semantic vault.</p>
                </article>

                <article class="stitch-card rounded-lg p-6">
                  <div class="mb-6 flex items-center gap-3">
                    <Workflow class="size-6 text-primary" />
                    <h2 class="text-2xl font-semibold">Vault Synchronization</h2>
                  </div>
                  <div class="flex items-center justify-between rounded-lg bg-surface-container-high p-4">
                    <div>
                      <p class="font-mono text-sm font-semibold">Auto-Sync Graph Data</p>
                      <p class="mt-1 text-sm text-text-muted">Continuously backup semantic nodes to secure cloud.</p>
                    </div>
                    <div class="flex h-7 w-12 items-center justify-end rounded-full bg-primary-container p-1">
                      <span class="size-5 rounded-full bg-white"></span>
                    </div>
                  </div>
                </article>

                <article data-testid="insights-function-grid" class="glass-panel rounded-lg p-6">
                  <div class="mb-5 flex items-center gap-3">
                    <Sparkles class="size-5 text-primary" />
                    <h2 class="text-xl font-semibold">Insights</h2>
                  </div>
                  <div data-testid="insights-output-workspace" class="grid gap-4 md:grid-cols-2">
                    <section class="rounded-lg border border-outline-variant/30 p-4">
                      <p class="text-sm font-semibold">Growth</p>
                      <p class="mt-2 text-sm leading-6 text-text-muted">{{ workspace.growth.value?.stage_summary }}</p>
                    </section>
                    <section class="rounded-lg border border-outline-variant/30 p-4">
                      <p class="text-sm font-semibold">Advice</p>
                      <p class="mt-2 text-sm leading-6 text-text-muted">{{ workspace.advice.value?.advice_summary }}</p>
                    </section>
                    <section class="rounded-lg border border-outline-variant/30 p-4">
                      <Boxes class="mb-3 size-5 text-primary" />
                      <p class="text-sm text-text-muted">Analytics</p>
                      <p class="mt-1 font-semibold">{{ workspace.analytics.value?.documents.document_count ?? 0 }} docs</p>
                    </section>
                    <section class="rounded-lg border border-outline-variant/30 p-4">
                      <Bell class="mb-3 size-5 text-primary" />
                      <p class="text-sm text-text-muted">Readiness</p>
                      <p class="mt-1 font-semibold">{{ workspace.readiness.value?.overall_status ?? "loading" }}</p>
                    </section>
                  </div>
                </article>
              </section>
            </div>
          </div>
        </section>
      </section>
    </div>
  </main>
</template>
