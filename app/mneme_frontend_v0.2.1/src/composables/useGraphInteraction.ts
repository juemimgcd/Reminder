import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3";
import { computed, onBeforeUnmount, ref, watch, type ComputedRef } from "vue";
import type { GraphEdgeData, GraphNodeData } from "../types";

export type GraphFilter = "all" | "tags" | "orphans";
export type PositionedGraphNode = GraphNodeData & { x: number; y: number };
type SimulationPhase = "idle" | "running" | "settled" | "reduced";
type SimulationGraphNode = GraphNodeData & SimulationNodeDatum & {
  x: number;
  y: number;
  fx: number | null;
  fy: number | null;
};
type SimulationGraphLink = SimulationLinkDatum<SimulationGraphNode> & GraphEdgeData;

export function useGraphInteraction(
  nodes: ComputedRef<GraphNodeData[]>,
  edges: ComputedRef<GraphEdgeData[]>,
) {
  const activeFilter = ref<GraphFilter>("all");
  const enabledNodeTypes = ref(new Set<string>());
  const selectedNode = ref<GraphNodeData | null>(null);
  const positionOverrides = ref(new Map<string, { x: number; y: number }>());
  const simulationPhase = ref<SimulationPhase>("idle");
  const publishedPositions = ref(new Map<string, { x: number; y: number }>());
  let simulation: Simulation<SimulationGraphNode, SimulationGraphLink> | null = null;
  let simulationNodes: SimulationGraphNode[] = [];
  let frameId: number | null = null;
  let pausedForVisibility = false;

  function publishPositions() {
    if (frameId !== null) return;
    frameId = window.requestAnimationFrame(() => {
      frameId = null;
      publishedPositions.value = new Map(
        simulationNodes.map((node) => [node.id, { x: node.x, y: node.y }]),
      );
    });
  }

  function stopSimulation() {
    simulation?.stop();
    simulation = null;
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      pausedForVisibility = simulationPhase.value === "running";
      if (pausedForVisibility) simulation?.stop();
      return;
    }
    if (pausedForVisibility && simulation) {
      pausedForVisibility = false;
      simulation.restart();
    }
  }

  function startingPosition(node: GraphNodeData, index: number, total: number) {
    if (node.depth === 0) return { x: 380, y: 300 };
    const angle = (Math.PI * 2 * Math.max(index - 1, 0)) / Math.max(total - 1, 1) - Math.PI / 2;
    const radius = 135 + Math.min(node.depth, 3) * 42;
    return { x: 380 + Math.cos(angle) * radius, y: 340 + Math.sin(angle) * radius };
  }

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
    return visibleNodes.value.map((node) => {
      const overridden = positionOverrides.value.get(node.id);
      if (overridden) return { ...node, ...overridden };
      const published = publishedPositions.value.get(node.id);
      if (published) return { ...node, ...published };
      const sourceIndex = nodes.value.findIndex((item) => item.id === node.id);
      return { ...node, ...startingPosition(node, sourceIndex, nodes.value.length) };
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
    positionOverrides.value = new Map();
    rebuildSimulation();
  }

  const graphSignature = computed(() => [
    ...nodes.value.map((node) => `n:${node.id}:${node.parent_id ?? ""}`),
    ...edges.value.map((edge) => `e:${edge.id}:${edge.source}:${edge.target}`),
  ].join("|"));

  function rebuildSimulation() {
    stopSimulation();
    if (!nodes.value.length) {
      simulationNodes = [];
      publishedPositions.value = new Map();
      simulationPhase.value = "idle";
      return;
    }

    simulationNodes = nodes.value.map((node, index) => ({
      ...node,
      ...startingPosition(node, index, nodes.value.length),
      vx: 0,
      vy: 0,
      fx: null,
      fy: null,
    }));
    const links: SimulationGraphLink[] = edges.value.map((edge) => ({ ...edge, source: edge.source, target: edge.target }));
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    simulation = forceSimulation<SimulationGraphNode>(simulationNodes)
      .alpha(1)
      .alphaMin(0.015)
      .alphaDecay(0.045)
      .velocityDecay(0.36)
      .force("link", forceLink<SimulationGraphNode, SimulationGraphLink>(links).id((node) => node.id).distance(118).strength(0.42))
      .force("charge", forceManyBody<SimulationGraphNode>().strength((node) => node.depth === 0 ? -360 : -245).distanceMax(540))
      .force("collision", forceCollide<SimulationGraphNode>().radius((node) => node.depth === 0 ? 54 : 38).strength(0.9))
      .force("center", forceCenter(380, 340).strength(0.12))
      .force("x", forceX<SimulationGraphNode>(380).strength((node) => node.depth === 0 ? 0.1 : 0.025))
      .force("y", forceY<SimulationGraphNode>(340).strength((node) => node.depth === 0 ? 0.1 : 0.025))
      .on("tick", publishPositions)
      .on("end", () => {
        publishPositions();
        simulationPhase.value = "settled";
      });

    if (reducedMotion) {
      simulation.stop();
      for (let index = 0; index < 120; index += 1) simulation.tick();
      publishedPositions.value = new Map(simulationNodes.map((node) => [node.id, { x: node.x, y: node.y }]));
      simulationPhase.value = "reduced";
    } else {
      simulationPhase.value = "running";
    }
  }

  document.addEventListener("visibilitychange", handleVisibilityChange);
  watch(graphSignature, rebuildSimulation, { immediate: true });
  onBeforeUnmount(() => {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    stopSimulation();
  });

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
    simulationPhase,
    toggleNodeType,
    visibleEdges,
    visibleNodes,
  };
}
