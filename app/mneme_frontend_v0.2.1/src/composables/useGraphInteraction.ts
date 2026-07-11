import { computed, ref, type ComputedRef } from "vue";
import type { GraphEdgeData, GraphNodeData } from "../types";

export type GraphFilter = "all" | "tags" | "orphans";
export type PositionedGraphNode = GraphNodeData & { x: number; y: number };

export function useGraphInteraction(
  nodes: ComputedRef<GraphNodeData[]>,
  edges: ComputedRef<GraphEdgeData[]>,
) {
  const activeFilter = ref<GraphFilter>("all");
  const enabledNodeTypes = ref(new Set<string>());
  const selectedNode = ref<GraphNodeData | null>(null);
  const positionOverrides = ref(new Map<string, { x: number; y: number }>());
  const layoutSeed = ref(0);

  const nodeTypes = computed(() => Array.from(new Set(nodes.value.map((node) => node.node_type))).sort());
  const degreeByNode = computed(() => {
    const degree = new Map(nodes.value.map((node) => [node.id, 0]));
    edges.value.forEach((edge) => {
      degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
      degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
    });
    return degree;
  });

  const visibleNodes = computed(() => nodes.value.filter((node) => {
    if (enabledNodeTypes.value.size && !enabledNodeTypes.value.has(node.node_type)) return false;
    if (activeFilter.value === "tags") return node.node_type.includes("tag");
    if (activeFilter.value === "orphans") return (degreeByNode.value.get(node.id) ?? 0) === 0;
    return true;
  }));

  const visibleNodeIds = computed(() => new Set(visibleNodes.value.map((node) => node.id)));
  const visibleEdges = computed(() => edges.value.filter((edge) => visibleNodeIds.value.has(edge.source) && visibleNodeIds.value.has(edge.target)));
  const positionedNodes = computed<PositionedGraphNode[]>(() => {
    const total = Math.max(nodes.value.length - 1, 1);
    return visibleNodes.value.map((node) => {
      const overridden = positionOverrides.value.get(node.id);
      if (overridden) return { ...node, ...overridden };
      if (node.depth === 0) return { ...node, x: 380, y: 260 };
      const sourceIndex = Math.max(nodes.value.findIndex((item) => item.id === node.id), 1);
      const angle = (Math.PI * 2 * (sourceIndex - 1)) / total - Math.PI / 2 + layoutSeed.value * 0.43;
      const radius = 178 + Math.min(node.depth, 2) * 44;
      return { ...node, x: 380 + Math.cos(angle) * radius, y: 340 + Math.sin(angle) * radius };
    });
  });

  const positionedNodeMap = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])));
  const positionedEdges = computed(() => visibleEdges.value
    .map((edge) => ({ ...edge, sourceNode: positionedNodeMap.value.get(edge.source), targetNode: positionedNodeMap.value.get(edge.target) }))
    .filter((edge) => edge.sourceNode && edge.targetNode));

  function setActiveFilter(filter: GraphFilter) {
    activeFilter.value = filter;
    if (selectedNode.value && !visibleNodeIds.value.has(selectedNode.value.id)) selectedNode.value = null;
  }

  function toggleNodeType(nodeType: string) {
    const next = new Set(enabledNodeTypes.value.size ? enabledNodeTypes.value : nodeTypes.value);
    if (next.has(nodeType)) next.delete(nodeType);
    else next.add(nodeType);
    enabledNodeTypes.value = next.size === nodeTypes.value.length ? new Set() : next;
  }

  function isNodeTypeEnabled(nodeType: string) {
    return !enabledNodeTypes.value.size || enabledNodeTypes.value.has(nodeType);
  }

  function selectNode(node: GraphNodeData | null) {
    selectedNode.value = node;
  }

  function dragNode(nodeId: string, x: number, y: number) {
    const next = new Map(positionOverrides.value);
    next.set(nodeId, { x, y });
    positionOverrides.value = next;
  }

  function restartLayout() {
    layoutSeed.value += 1;
    positionOverrides.value = new Map();
  }

  return {
    activeFilter,
    dragNode,
    enabledNodeTypes,
    isNodeTypeEnabled,
    nodeTypes,
    positionedEdges,
    positionedNodes,
    restartLayout,
    selectedNode,
    selectNode,
    setActiveFilter,
    toggleNodeType,
    visibleEdges,
    visibleNodes,
  };
}
