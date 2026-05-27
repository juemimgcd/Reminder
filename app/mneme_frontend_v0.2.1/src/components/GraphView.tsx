import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import { ZoomIn, ZoomOut, RotateCcw, Maximize } from "lucide-react";
import { GraphNode, GraphLink } from "@/src/types";

export default function GraphView() {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const nodes: GraphNode[] = [
      { id: "1", label: "Design System", type: "concept" },
      { id: "2", label: "Tokens", type: "document" },
      { id: "3", label: "Typography", type: "document" },
      { id: "4", label: "Color Palette", type: "concept" },
      { id: "5", label: "Elevation", type: "document" },
      { id: "6", label: "Layouts", type: "document" },
    ];

    const links: GraphLink[] = [
      { source: "1", target: "2" },
      { source: "1", target: "3" },
      { source: "1", target: "4" },
      { source: "2", target: "4" },
      { source: "4", target: "5" },
      { source: "1", target: "6" },
    ];

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    const simulation = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(150))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#e5e5e5")
      .attr("stroke-width", 1);

    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(drag(simulation as any) as any);

    // Outer ring (Black stroke + White fill)
    node.append("circle")
      .attr("r", (d) => d.id === "1" ? 14 : 7)
      .attr("fill", "#ffffff")
      .attr("stroke", "#000000")
      .attr("stroke-width", 1.5);

    // Inner center (Solid black)
    node.append("circle")
      .attr("r", (d) => d.id === "1" ? 6 : 3)
      .attr("fill", "#000000");

    const label = g.append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.label)
      .attr("font-size", "11px")
      .attr("dx", 16)
      .attr("dy", 4)
      .attr("fill", (d) => d.id === "1" ? "#0f172a" : "#64748b")
      .attr("font-weight", (d) => d.id === "1" ? "600" : "500");

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("transform", (d: any) => `translate(${d.x},${d.y})`);

      label
        .attr("x", (d: any) => d.x)
        .attr("y", (d: any) => d.y);
    });

    const zoomHandler = d3.zoom()
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoomHandler as any);

    function drag(simulation: any) {
      function dragstarted(event: any) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      function dragged(event: any) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      function dragended(event: any) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }
  }, []);

  return (
    <div className="flex-1 flex flex-col relative h-full bg-surface overflow-hidden">
      <svg ref={svgRef} className="w-full h-full" />
      
      <div className="absolute bottom-6 right-6 bg-surface-container-lowest/80 backdrop-blur border border-outline-variant p-2 rounded font-label-mono text-[10px] text-text-muted z-20">
        Nodes: 243 | Edges: 512
      </div>

      <div className="absolute bottom-6 left-6 flex flex-col gap-1 z-20 bg-surface-container-lowest/80 backdrop-blur border border-outline-variant rounded p-1">
        <button className="p-1.5 text-text-muted hover:text-primary rounded transition-colors">
          <ZoomIn size={18} />
        </button>
        <button className="p-1.5 text-text-muted hover:text-primary rounded transition-colors">
          <ZoomOut size={18} />
        </button>
        <button className="p-1.5 text-text-muted hover:text-primary rounded transition-colors">
          <RotateCcw size={18} />
        </button>
        <button className="p-1.5 text-text-muted hover:text-primary rounded transition-colors">
          <Maximize size={18} />
        </button>
      </div>
    </div>
  );
}
