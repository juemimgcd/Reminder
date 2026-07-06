import * as d3 from "d3";
import { useEffect, useMemo, useRef } from "react";

import type { GraphData, GraphEdgeData, GraphNodeData } from "../types";

interface KnowledgeGraphCanvasProps {
  data: GraphData | null;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNodeData) => void;
}

type SimulationGraphNode = GraphNodeData & d3.SimulationNodeDatum;
type SimulationGraphLink = GraphEdgeData & d3.SimulationLinkDatum<SimulationGraphNode>;

const NODE_COLORS: Record<string, string> = {
  user: "#c6c6c7",
  knowledge_base: "#7c3aed",
  document: "#d2bbff",
  memory_entry: "#958da1",
};

export default function KnowledgeGraphCanvas({
  data,
  selectedNodeId,
  onSelectNode,
}: KnowledgeGraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<SimulationGraphNode, undefined> | null>(null);
  const outerRingRef = useRef<d3.Selection<SVGCircleElement, SimulationGraphNode, SVGGElement, unknown> | null>(null);

  const counts = useMemo(() => {
    if (!data) {
      return [];
    }

    return Object.entries(data.node_type_counts);
  }, [data]);

  useEffect(() => {
    if (!svgRef.current) {
      return;
    }

    const svg = d3.select(svgRef.current);
    simulationRef.current?.stop();
    svg.selectAll("*").remove();
    outerRingRef.current = null;

    if (!data) {
      simulationRef.current = null;
      return;
    }

    const width = svgRef.current.clientWidth || 960;
    const height = svgRef.current.clientHeight || 720;
    const root = svg.append("g");

    const zoom = d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.35, 2.5]).on("zoom", (event) => {
      root.attr("transform", event.transform.toString());
    });
    svg.call(zoom);

    const nodes: SimulationGraphNode[] = data.nodes.map((node) => ({ ...node }));
    const edges: SimulationGraphLink[] = data.edges.map((edge) => ({ ...edge }));

    const simulation = d3
      .forceSimulation<SimulationGraphNode>(nodes)
      .force(
        "link",
        d3
          .forceLink<SimulationGraphNode, SimulationGraphLink>(edges)
          .id((d) => d.id)
          .distance((edge) => (edge.edge_type === "contains" ? 150 : 230))
          .strength((edge) => (edge.edge_type === "contains" ? 0.72 : 0.28)),
      )
      .force("charge", d3.forceManyBody().strength(-520))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide<SimulationGraphNode>().radius((node) => {
        return node.node_type === "document" ? 42 : node.node_type === "memory_entry" ? 28 : 34;
      }));

    const link = root
      .append("g")
      .attr("stroke", "#3f3f46")
      .attr("stroke-opacity", 0.72)
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke-width", (edge) => (edge.edge_type === "related" ? 1.2 : 1.6))
      .attr("stroke-dasharray", (edge) => (edge.edge_type === "related" ? "6 5" : null));

    const node = root
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, SimulationGraphNode>()
          .on("start", (event) => {
            if (!event.active) {
              simulation.alphaTarget(0.25).restart();
            }
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
          })
          .on("drag", (event) => {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
          })
          .on("end", (event) => {
            if (!event.active) {
              simulation.alphaTarget(0);
            }
            event.subject.fx = null;
            event.subject.fy = null;
          }),
      )
      .on("click", (_, datum) => {
        onSelectNode(datum);
      });

    node
      .append("circle")
      .attr("r", (datum) => {
        if (datum.id === data.root_node_id) {
          return 20;
        }
        return datum.node_type === "document" ? 13 : datum.node_type === "memory_entry" ? 9 : 11;
      })
      .attr("fill", "#18181b")
      .attr("stroke", (datum) => (datum.id === selectedNodeId ? "#e5e1e4" : NODE_COLORS[datum.node_type] ?? "#b8b8b8"))
      .attr("stroke-width", (datum) => (datum.id === selectedNodeId ? 3.2 : datum.id === data.root_node_id ? 2.8 : 2));

    node
      .append("circle")
      .attr("r", (datum) => {
        if (datum.id === data.root_node_id) {
          return 7;
        }
        return datum.node_type === "document" ? 4.5 : 3.5;
      })
      .attr("fill", (datum) => NODE_COLORS[datum.node_type] ?? "#b8b8b8");

    const labels = root
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((datum) => datum.label)
      .attr("font-size", 14)
      .attr("font-weight", 500)
      .attr("font-family", "Inter, Microsoft YaHei UI, ui-sans-serif, system-ui, sans-serif")
      .attr("fill", "#e5e1e4")
      .attr("paint-order", "stroke")
      .attr("stroke", "#09090b")
      .attr("stroke-width", 4)
      .attr("dx", 20)
      .attr("dy", 5);

    outerRingRef.current = node.select<SVGCircleElement>("circle");

    simulation.on("tick", () => {
      link
        .attr("x1", (edge) => (edge.source as SimulationGraphNode).x ?? 0)
        .attr("y1", (edge) => (edge.source as SimulationGraphNode).y ?? 0)
        .attr("x2", (edge) => (edge.target as SimulationGraphNode).x ?? 0)
        .attr("y2", (edge) => (edge.target as SimulationGraphNode).y ?? 0);

      node.attr("transform", (datum) => `translate(${datum.x ?? 0},${datum.y ?? 0})`);
      labels
        .attr("x", (datum) => datum.x ?? 0)
        .attr("y", (datum) => datum.y ?? 0);
    });

    simulationRef.current = simulation;

    return () => {
      simulation.stop();
      simulationRef.current = null;
      outerRingRef.current = null;
    };
  }, [data, onSelectNode]);

  useEffect(() => {
    if (!data || !outerRingRef.current) {
      return;
    }

    outerRingRef.current
      .attr("stroke", (datum) => (datum.id === selectedNodeId ? "#e5e1e4" : NODE_COLORS[datum.node_type] ?? "#b8b8b8"))
      .attr("stroke-width", (datum) => (datum.id === selectedNodeId ? 3.2 : datum.id === data.root_node_id ? 2.8 : 2));
  }, [data, selectedNodeId]);

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0a0a0c] text-sm text-text-muted">
        当前没有图数据，请先选择范围并加载。
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-[#0a0a0c]">
      <div className="glass-panel absolute left-4 right-4 top-4 z-10 flex items-center justify-between rounded-xl px-4 py-3 text-xs text-text-muted">
        <div className="flex flex-wrap gap-4">
          <span>Nodes {data.node_count}</span>
          <span>Edges {data.edge_count}</span>
          <span>Scope {data.scope}</span>
        </div>
        <div className="flex flex-wrap gap-3">
          {counts.map(([type, count]) => (
            <span key={type} className="inline-flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS[type] ?? "#9f9688" }} />
              {type} {count}
            </span>
          ))}
        </div>
      </div>
      <div className="relative flex-1 bg-[radial-gradient(#18181b_1px,transparent_1px)] [background-size:24px_24px]">
        <svg ref={svgRef} className="h-full w-full" />
      </div>
    </div>
  );
}
