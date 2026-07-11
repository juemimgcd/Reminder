<script setup lang="ts">
import { ChevronLeft, File, FolderOpen, FolderPlus, Network, Play, Search, Send, SlidersHorizontal, Target, Workflow, X, ZoomIn, ZoomOut } from "@lucide/vue";
import { computed, onBeforeUnmount, ref } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import type { GraphNodeData } from "../types";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const railCollapsed = ref(window.matchMedia("(max-width: 1023px)").matches);
const previewNode = ref<GraphNodeData | null>(null);
const zoom = ref(1);
const graphViewBox = ref("0 0 760 680");
let previewTimer: number | undefined;

const positionedNodes = computed(() => {
  const nodes = props.workspace.graphData.value?.nodes ?? [];
  return nodes.map((node, index) => {
    if (node.depth === 0) return { ...node, x: 380, y: 250 };
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length - 1, 1) - Math.PI / 2;
    const radius = 180 + Math.min(node.depth, 2) * 42;
    return { ...node, x: 380 + Math.cos(angle) * radius, y: 340 + Math.sin(angle) * radius };
  });
});

const nodeMap = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])));
const positionedEdges = computed(() => (props.workspace.graphData.value?.edges ?? []).map((edge) => ({ ...edge, sourceNode: nodeMap.value.get(edge.source), targetNode: nodeMap.value.get(edge.target) })).filter((edge) => edge.sourceNode && edge.targetNode));

function nodeRadius(node: GraphNodeData) { return node.depth === 0 ? 24 : Math.max(8, 15 - node.depth * 2); }
function nodeFill(node: GraphNodeData) { return node.depth === 0 ? "var(--accent-strong)" : node.node_type === "memory" ? "var(--accent)" : "var(--text-tertiary)"; }

function startGraphNodeDrag(node: GraphNodeData) {
  window.clearTimeout(previewTimer);
  previewTimer = window.setTimeout(async () => {
    previewNode.value = node;
    await props.workspace.loadDocumentPreview(node.entity_id);
  }, 420);
}

function moveGraphNodeDrag() {}
function endGraphNodeDrag() { window.clearTimeout(previewTimer); }
function hideGraphDocumentPreview() { previewNode.value = null; props.workspace.clearDocumentPreview(); }
function setZoom(value: number) {
  zoom.value = Math.min(1.8, Math.max(0.65, value));
  const width = 760 / zoom.value;
  const height = 680 / zoom.value;
  graphViewBox.value = `${(760 - width) / 2} ${(680 - height) / 2} ${width} ${height}`;
}
function centerGraph() { zoom.value = 1; graphViewBox.value = "0 0 760 680"; }
function restartGraphLayout() { centerGraph(); }
onBeforeUnmount(() => window.clearTimeout(previewTimer));
</script>

<template>
  <div data-testid="stitch-graph-layout" class="graph-layout" title="Graph Workspace">
    <div data-testid="graph-function-grid" class="graph-grid">
      <aside data-testid="graph-file-rail" class="graph-file-panel" :aria-hidden="railCollapsed">
        <header><div><small>Active vault</small><h2>Files</h2></div><FolderPlus class="size-4" /></header>
        <nav>
          <section><h3><FolderOpen />Machine Learning</h3><button class="active"><File />Neural Networks</button><button><File />Gradient Descent</button><button><File />Optimization</button></section>
          <button><FolderOpen />Architecture</button><button><FolderOpen />Research Papers</button>
          <button v-for="doc in workspace.selectedDocuments.value" :key="doc.id"><File /><span>{{ doc.file_name }}</span></button>
        </nav>
      </aside>

      <section data-testid="graph-output-workspace" class="graph-canvas">
        <div class="graph-toolbar">
          <div class="graph-title"><Network /><span>Graph View</span></div>
          <div class="graph-toolbar-controls">
            <form @submit.prevent="workspace.runGraphRag"><Search /><input v-model="workspace.graphRagQuestion.value" placeholder="Search knowledge base..." /><button aria-label="Run GraphRAG"><Send /></button></form>
            <div class="graph-tabs"><button class="active">All Nodes</button><button>Tags</button><button>Orphans</button><button aria-label="Graph filters"><SlidersHorizontal /></button></div>
          </div>
        </div>
        <p v-if="workspace.graphRagStatus.value" class="graph-status">{{ workspace.graphRagStatus.value }}</p>

        <svg :viewBox="graphViewBox" role="img" aria-label="Knowledge graph" @pointermove="moveGraphNodeDrag" @pointerup="endGraphNodeDrag" @pointerleave="endGraphNodeDrag">
          <g stroke="var(--border-strong)" stroke-width="2">
            <line v-for="edge in positionedEdges" :key="edge.id" :x1="edge.sourceNode!.x" :y1="edge.sourceNode!.y" :x2="edge.targetNode!.x" :y2="edge.targetNode!.y" />
          </g>
          <g v-for="node in positionedNodes" :key="node.id" data-testid="force-node" :data-node-id="node.id" class="graph-node" @pointerdown="startGraphNodeDrag(node)">
            <circle :cx="node.x" :cy="node.y" :r="nodeRadius(node)" :fill="nodeFill(node)" :stroke="node.depth === 0 ? 'color-mix(in srgb, var(--accent) 55%, white)' : 'transparent'" :stroke-width="node.depth === 0 ? 4 : 0" />
            <text :x="node.x" :y="node.y + nodeRadius(node) + 22" fill="var(--text-primary)" :font-size="node.depth === 0 ? 18 : 14" :font-weight="node.depth === 0 ? 600 : 500" text-anchor="middle">{{ node.label }}</text>
          </g>
        </svg>

        <div class="graph-hint"><Workflow /><span>Long press to preview</span></div>
        <aside v-if="previewNode" data-testid="graph-document-preview-panel" class="graph-preview">
          <header><small>Properties</small><button title="Close preview" @click="hideGraphDocumentPreview"><X /></button></header>
          <h2>{{ workspace.documentPreview.value?.file_name ?? previewNode.label }}</h2>
          <div class="tags"><span>#{{ previewNode.node_type }}</span><span>#{{ workspace.documentPreview.value?.file_type ?? "graph" }}</span></div>
          <section><small>Summary</small><p>{{ workspace.documentPreview.value?.summary ?? `${previewNode.label} is linked inside the active knowledge graph.` }}</p><a href="#document">Read full note</a></section>
          <section v-if="workspace.documentPreview.value?.memory_entries.length"><small>Backlinks</small><article v-for="entry in workspace.documentPreview.value.memory_entries" :key="entry.entry_id"><strong>{{ entry.entry_name }}</strong><p>{{ entry.summary }}</p></article></section>
        </aside>

        <button data-testid="graph-file-rail-toggle" class="rail-toggle" :title="railCollapsed ? 'Expand file list' : 'Collapse file list'" @click="railCollapsed = !railCollapsed"><ChevronLeft :class="{ rotate: railCollapsed }" /></button>
        <div class="zoom-controls"><button aria-label="Zoom in graph" @click="setZoom(zoom + 0.15)"><ZoomIn /></button><button aria-label="Zoom out graph" @click="setZoom(zoom - 0.15)"><ZoomOut /></button><button aria-label="Center graph" @click="centerGraph"><Target /></button><button aria-label="Restart graph layout" @click="restartGraphLayout"><Play /></button></div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.graph-layout, .graph-grid { height: 100%; min-height: 0; overflow: hidden; background: var(--bg-canvas); }
.graph-grid { position: relative; display: grid; grid-template-columns: 280px minmax(0, 1fr); }
.graph-file-panel { min-width: 0; overflow: auto; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.graph-file-panel[aria-hidden="true"] { visibility: hidden; overflow: hidden; pointer-events: none; }
.graph-file-panel header { display: flex; height: 3.5rem; align-items: center; justify-content: space-between; padding: 0 1rem; border-bottom: 1px solid var(--border-muted); }
.graph-file-panel small { color: var(--text-tertiary); font: 0.62rem var(--font-mono); text-transform: uppercase; }
.graph-file-panel h2 { margin: 0.1rem 0 0; font-size: 0.9rem; }
.graph-file-panel nav { display: grid; gap: 0.2rem; padding: 0.8rem; }
.graph-file-panel nav section { display: grid; gap: 0.18rem; }
.graph-file-panel h3, .graph-file-panel nav button { display: flex; min-width: 0; align-items: center; gap: 0.55rem; margin: 0; padding: 0.55rem; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.35rem; font-size: 0.78rem; text-align: left; }
.graph-file-panel h3 { color: var(--text-primary); font-weight: 500; }
.graph-file-panel nav section button { padding-left: 1.9rem; }
.graph-file-panel nav button.active { color: var(--accent); background: var(--accent-soft); }
.graph-file-panel svg { width: 1rem; flex: 0 0 auto; }
.graph-file-panel nav span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.graph-canvas { position: relative; min-width: 0; overflow: hidden; background: var(--bg-canvas); }
.graph-canvas > svg { width: 100%; height: 100%; min-height: 620px; touch-action: none; user-select: none; }
.graph-node { cursor: grab; }
.graph-toolbar { position: absolute; top: 1rem; left: 1rem; z-index: 10; display: flex; gap: 0.7rem; }
.graph-title, .graph-toolbar form, .graph-tabs, .zoom-controls { display: flex; align-items: center; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.45rem; box-shadow: var(--shadow-float); }
.graph-title { height: 3rem; gap: 0.5rem; padding: 0 0.8rem; font-size: 0.8rem; }
.graph-title svg { width: 1rem; color: var(--accent); }
.graph-toolbar-controls { display: grid; gap: 0.35rem; }
.graph-toolbar form { width: 320px; height: 2.7rem; gap: 0.45rem; padding: 0 0.7rem; box-shadow: none; }
.graph-toolbar form > svg { width: 1rem; color: var(--text-tertiary); }
.graph-toolbar input { min-width: 0; flex: 1; background: transparent; border: 0; outline: 0; }
.graph-toolbar form button, .graph-tabs button, .zoom-controls button, .graph-preview button { display: grid; place-items: center; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.3rem; }
.graph-toolbar form button svg { width: 0.95rem; color: var(--accent); }
.graph-tabs { height: 2.5rem; gap: 0.15rem; padding: 0.25rem; box-shadow: none; }
.graph-tabs button { height: 2rem; padding: 0 0.65rem; font-size: 0.72rem; }
.graph-tabs button.active { color: var(--accent); background: var(--accent-soft); }
.graph-tabs svg { width: 1rem; }
.graph-status { position: absolute; top: 6.7rem; left: 1rem; z-index: 12; max-width: min(28rem, calc(100% - 2rem)); padding: 0.65rem 0.8rem; color: var(--text-secondary); background: var(--bg-panel); border-left: 2px solid var(--accent); font-size: 0.75rem; }
.graph-hint { position: absolute; top: 50%; right: 1rem; display: flex; align-items: center; gap: 0.45rem; padding: 0.5rem 0.65rem; color: var(--text-tertiary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.35rem; font-size: 0.7rem; }
.graph-hint svg { width: 1rem; }
.graph-preview { position: absolute; top: 1rem; right: 1rem; z-index: 25; width: min(350px, calc(100% - 2rem)); max-height: calc(100% - 2rem); overflow: auto; padding: 1rem; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.5rem; box-shadow: var(--shadow-float); }
.graph-preview header { display: flex; justify-content: space-between; }
.graph-preview header small, .graph-preview section small { color: var(--text-tertiary); font: 0.64rem var(--font-mono); text-transform: uppercase; }
.graph-preview button svg { width: 1rem; }
.graph-preview h2 { margin: 0.9rem 0 0; font: 600 1.6rem var(--font-serif); }
.graph-preview .tags { display: flex; gap: 0.35rem; margin-top: 0.7rem; }
.graph-preview .tags span { padding: 0.2rem 0.35rem; color: var(--accent); background: var(--accent-soft); border-radius: 0.25rem; font-size: 0.65rem; }
.graph-preview section { margin-top: 1.2rem; }
.graph-preview p { color: var(--text-secondary); font-size: 0.8rem; line-height: 1.6; }
.graph-preview a { display: inline-block; margin-top: 0.3rem; color: var(--accent); font-size: 0.75rem; text-decoration: none; }
.graph-preview article { margin-top: 0.6rem; padding-left: 0.7rem; border-left: 2px solid var(--accent); }
.rail-toggle { position: absolute; top: 50%; left: 0.4rem; z-index: 35; display: grid; width: 2.2rem; height: 2.6rem; place-items: center; color: var(--text-secondary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.rail-toggle svg { width: 1rem; }
.rail-toggle svg.rotate { transform: rotate(180deg); }
.zoom-controls { position: absolute; bottom: 1rem; left: 50%; gap: 0.25rem; padding: 0.25rem; transform: translateX(-50%); }
.zoom-controls button { width: 2.3rem; height: 2.3rem; }
.zoom-controls button:hover { color: var(--accent); background: var(--accent-soft); }
.zoom-controls svg { width: 1rem; }
@media (max-width: 1023px) { .graph-grid { grid-template-columns: minmax(0, 1fr); } .graph-file-panel { position: absolute; inset: 0 auto 0 0; z-index: 30; width: min(84vw, 320px); box-shadow: var(--shadow-float); } .graph-file-panel[aria-hidden="true"] { display: none; } .graph-hint { display: none; } }
@media (max-width: 767px) { .graph-toolbar { right: 0.6rem; left: 0.6rem; display: grid; grid-template-columns: 2.7rem minmax(0, 1fr); } .graph-title { width: 2.7rem; padding: 0; justify-content: center; } .graph-title span { display: none; } .graph-toolbar form { width: 100%; } .graph-tabs { overflow-x: auto; } .graph-canvas > svg { min-height: 560px; } .zoom-controls { bottom: 0.75rem; } }
</style>
