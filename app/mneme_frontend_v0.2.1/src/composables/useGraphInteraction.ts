import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type ForceCollide,
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

export function createGraphSignature(
  nodes: Pick<GraphNodeData, "id" | "parent_id">[],
  edges: Pick<GraphEdgeData, "id" | "source" | "target">[],
) {
  const nodeIdentities = nodes
    .map((node) => [node.id, node.parent_id] as const)
    .sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right)));
  const edgeIdentities = edges
    .map((edge) => [edge.id, edge.source, edge.target] as const)
    .sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right)));
  return JSON.stringify({ nodes: nodeIdentities, edges: edgeIdentities });
}

export function useGraphInteraction(
  nodes: ComputedRef<GraphNodeData[]>,
  edges: ComputedRef<GraphEdgeData[]>,
) {
  const activeFilter = ref<GraphFilter>("all");
  const enabledNodeTypes = ref(new Set<string>());
  const selectedNode = ref<GraphNodeData | null>(null);
  const layoutSeed = ref(0);
  const simulationPhase = ref<SimulationPhase>("idle");
  const publishedPositions = ref(new Map<string, { x: number; y: number }>());
  let simulation: Simulation<SimulationGraphNode, SimulationGraphLink> | null = null;
  let simulationNodes: SimulationGraphNode[] = [];
  let frameId: number | null = null;
  let pausedForVisibility = false;
  let reducedMotionActive = false;
  let collisionForce: ForceCollide<SimulationGraphNode> | null = null;
  let visibleLabelIds = new Set<string>();

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
    pausedForVisibility = false;
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
  }

  function publishPositionsImmediately() {
    if (frameId !== null) window.cancelAnimationFrame(frameId);
    frameId = null;
    publishedPositions.value = new Map(
      simulationNodes.map((node) => [node.id, { x: node.x, y: node.y }]),
    );
  }

  function settleReducedMotion(alpha: number) {
    if (!simulation) return;
    simulation.stop().alphaTarget(0).alpha(alpha);
    for (let index = 0; index < 120; index += 1) simulation.tick();
    publishPositionsImmediately();
    simulationPhase.value = "reduced";
    pausedForVisibility = false;
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      pausedForVisibility = simulationPhase.value === "running" && simulation !== null;
      if (pausedForVisibility) simulation?.stop();
      return;
    }
    const shouldRestart = pausedForVisibility && simulation !== null && simulationPhase.value === "running";
    pausedForVisibility = false;
    if (shouldRestart && simulation) {
      simulation.restart();
    }
  }

  function startingPosition(node: GraphNodeData, index: number, total: number) {
    if (node.depth === 0) return { x: 380, y: 300 };
    const identitySeed = Array.from(node.id).reduce((sum, character) => sum + character.charCodeAt(0), 0);
    const angle = (Math.PI * 2 * Math.max(index - 1, 0)) / Math.max(total - 1, 1)
      - Math.PI / 2 + Math.sin(identitySeed * 0.73) * 0.12;
    const radius = 135 + Math.min(node.depth, 3) * 42 + Math.cos(identitySeed * 0.41) * 16;
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
  const neighborIds = computed(() => {
    const selectedId = selectedNode.value?.id;
    if (!selectedId) return new Set<string>();
    return new Set(visibleEdges.value.flatMap((edge) => {
      if (edge.source === selectedId) return [edge.target];
      if (edge.target === selectedId) return [edge.source];
      return [];
    }));
  });
  const positionedNodes = computed<PositionedGraphNode[]>(() => {
    return visibleNodes.value.map((node) => {
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

  function focusState(nodeId: string): "selected" | "neighbor" | "dimmed" | "normal" {
    if (!selectedNode.value) return "normal";
    if (selectedNode.value.id === nodeId) return "selected";
    return neighborIds.value.has(nodeId) ? "neighbor" : "dimmed";
  }

  function edgeFocusState(source: string, target: string): "connected" | "dimmed" | "normal" {
    const selectedId = selectedNode.value?.id;
    if (!selectedId) return "normal";
    return source === selectedId || target === selectedId ? "connected" : "dimmed";
  }

  function nodeRadius(node: GraphNodeData) {
    const degree = degreeByNode.value.get(node.id) ?? 0;
    return Math.min(28, 9 + Math.sqrt(degree) * 4 + (node.depth === 0 ? 7 : 0));
  }

  function priorityLabelIds(zoom: number) {
    const limit = zoom >= 1.44 ? 14 : zoom >= 1.1 ? 5 : 4;
    return new Set(
      [...visibleNodes.value]
        .sort((left, right) => (
          (degreeByNode.value.get(right.id) ?? 0) - (degreeByNode.value.get(left.id) ?? 0)
          || left.id.localeCompare(right.id)
        ))
        .slice(0, limit)
        .map((node) => node.id),
    );
  }

  function labelVisible(nodeId: string, zoom: number, hoveredId: string | null) {
    const node = visibleNodes.value.find((item) => item.id === nodeId);
    if (!node) return false;
    if (node.depth === 0 || nodeId === hoveredId || nodeId === selectedNode.value?.id) return true;
    return priorityLabelIds(zoom).has(nodeId);
  }

  function setVisibleLabelIds(next: Set<string>) {
    if (next.size === visibleLabelIds.size && [...next].every((id) => visibleLabelIds.has(id))) return;
    visibleLabelIds = new Set(next);
    collisionForce?.radius((node) => {
      const labelAllowance = visibleLabelIds.has(node.id) ? Math.min(44, node.label.length * 2.4) : 0;
      return nodeRadius(node) + 9 + labelAllowance;
    });
    if (!simulation || simulationPhase.value === "settled" || simulationPhase.value === "reduced") return;
    if (reducedMotionActive) {
      settleReducedMotion(0.12);
      return;
    }
    simulation.alpha(Math.max(simulation.alpha(), 0.12)).restart();
    simulationPhase.value = "running";
  }

  function simulationNode(nodeId: string) {
    return simulationNodes.find((node) => node.id === nodeId) ?? null;
  }

  function startDrag(nodeId: string) {
    const node = simulationNode(nodeId);
    if (!node || !simulation) return;
    node.fx = node.x;
    node.fy = node.y;
    if (reducedMotionActive) {
      simulation.stop();
      simulationPhase.value = "reduced";
      return;
    }
    simulation.alphaTarget(0.22).restart();
    simulationPhase.value = "running";
  }

  function dragNode(nodeId: string, x: number, y: number) {
    const node = simulationNode(nodeId);
    if (!node) return;
    node.fx = x;
    node.fy = y;
    node.x = x;
    node.y = y;
    publishPositions();
  }

  function endDrag(nodeId: string) {
    const node = simulationNode(nodeId);
    if (!node || !simulation) return;
    node.fx = null;
    node.fy = null;
    if (reducedMotionActive) {
      settleReducedMotion(0.32);
      return;
    }
    simulation.alphaTarget(0).alpha(Math.max(simulation.alpha(), 0.32)).restart();
    simulationPhase.value = "running";
  }

  function restartLayout() {
    if (!simulation) return;
    layoutSeed.value += 1;
    simulationNodes.forEach((node, index) => {
      node.fx = null;
      node.fy = null;
      if (node.depth === 0) return;
      const angle = (index + 1) * 1.618 + layoutSeed.value * 0.43;
      node.x += Math.cos(angle) * 26;
      node.y += Math.sin(angle) * 26;
      node.vx = 0;
      node.vy = 0;
    });
    if (reducedMotionActive) {
      settleReducedMotion(1);
      return;
    }
    simulation.alphaTarget(0).alpha(1);
    simulationPhase.value = "running";
    publishPositions();
    if (document.hidden) {
      pausedForVisibility = true;
      simulation.stop();
    } else {
      simulation.restart();
    }
  }

  const graphSignature = computed(() => createGraphSignature(nodes.value, edges.value));

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
    reducedMotionActive = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    collisionForce = forceCollide<SimulationGraphNode>().radius((node) => {
      const labelAllowance = visibleLabelIds.has(node.id) ? Math.min(44, node.label.length * 2.4) : 0;
      return nodeRadius(node) + 9 + labelAllowance;
    }).strength(0.88);

    simulation = forceSimulation<SimulationGraphNode>(simulationNodes)
      .alpha(1)
      .alphaMin(0.015)
      .alphaDecay(0.045)
      .velocityDecay(0.36)
      .force("link", forceLink<SimulationGraphNode, SimulationGraphLink>(links).id((node) => node.id).distance((link) => {
        const source = link.source as string | SimulationGraphNode;
        const target = link.target as string | SimulationGraphNode;
        const sourceId = typeof source === "string" ? source : source.id;
        const targetId = typeof target === "string" ? target : target.id;
        const degreeAllowance = Math.min(36, ((degreeByNode.value.get(sourceId) ?? 0) + (degreeByNode.value.get(targetId) ?? 0)) * 4);
        return (link.edge_type === "contains" ? 125 : 150) + degreeAllowance;
      }).strength(0.32))
      .force("charge", forceManyBody<SimulationGraphNode>().strength((node) => -150 - Math.min(240, (degreeByNode.value.get(node.id) ?? 0) * 28)).distanceMax(560))
      .force("collision", collisionForce)
      .force("center", forceCenter(380, 340).strength(0.065))
      .force("x", forceX<SimulationGraphNode>(380).strength((node) => node.depth === 0 ? 0.065 : 0.015))
      .force("y", forceY<SimulationGraphNode>(340).strength((node) => node.depth === 0 ? 0.065 : 0.015))
      .on("tick", publishPositions)
      .on("end", () => {
        publishPositions();
        simulationPhase.value = "settled";
      });

    if (reducedMotionActive) {
      settleReducedMotion(1);
    } else {
      simulationPhase.value = "running";
      if (document.hidden) {
        pausedForVisibility = true;
        simulation.stop();
      }
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
    startDrag,
    endDrag,
    edgeFocusState,
    focusState,
    labelVisible,
    nodeRadius,
    setVisibleLabelIds,
    toggleNodeType,
    visibleEdges,
    visibleNodes,
  };
}
