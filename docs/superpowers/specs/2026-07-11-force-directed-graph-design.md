# Force-Directed Knowledge Graph Design

## Goal

Upgrade Mneme's graph from deterministic static coordinates to an Obsidian-style force-directed workspace that visibly settles into equilibrium, responds physically to drag operations, and stops consuming animation resources after convergence.

## User Experience

When the graph becomes visible, nodes begin from stable seeded positions and move under link, charge, collision, and centering forces. Motion is strongest at entry, then decays smoothly until the layout is visually stable. The graph must feel alive without drifting forever.

Dragging a node temporarily fixes it beneath the pointer and reheats the simulation so neighboring nodes respond immediately. Releasing the pointer removes the temporary fixation and allows the graph to settle again. The existing Restart Graph Layout control adds a small deterministic perturbation, restores simulation energy, and produces a visibly different settling pass.

Filters only affect rendering. Switching between All Nodes, Tags, Orphans, or node-type filters must not recreate the physics model or make unrelated nodes jump. Existing preview, zoom, GraphRAG, file-rail, and responsive behaviors remain intact.

## Recommended Implementation

Use the project's existing `d3` dependency rather than adding a new physics package. `useGraphInteraction.ts` remains the public interaction boundary and gains a focused force-simulation lifecycle. `GraphView.vue` renders the reactive simulation positions and translates pointer actions into drag lifecycle calls.

The simulation uses:

- `forceLink` to keep related nodes together, with link distance adjusted by node depth and relationship type.
- `forceManyBody` with negative strength to separate unrelated nodes.
- `forceCollide` with a radius derived from the rendered circle and label allowance.
- `forceCenter` plus weak `forceX` and `forceY` constraints to keep the working set within the main canvas.
- D3 alpha decay to stop naturally after convergence instead of running indefinitely.

Initial coordinates remain deterministically seeded so reloads do not begin from a random pile. D3 owns mutable simulation copies, never the API response objects. Rendered positions are published through Vue refs in a batched animation-frame update, avoiding one component update for every internal D3 tick.

## Simulation Lifecycle

The force simulation is created when non-empty graph data becomes available and rebuilt only when the graph's node or edge identity set changes. A knowledge-base change therefore creates a new simulation, while a filter change does not.

The lifecycle is:

1. Convert API nodes into simulation nodes with deterministic starting coordinates.
2. Resolve graph edges to simulation-node identifiers.
3. Start with alpha `1` and a decay tuned to produce a visible but short convergence.
4. Publish positions on animation frames while alpha remains above the minimum threshold.
5. Stop automatically when the simulation converges.
6. Stop and cancel pending animation frames when GraphView unmounts or the graph dataset changes.

The target is a perceptible convergence of roughly 1.5 to 3 seconds for the current graph sizes. Exact duration is governed by alpha rather than an arbitrary timeout.

## Drag and Restart Behavior

Pointer down selects the node, sets `fx` and `fy` to its current position, raises `alphaTarget`, and restarts the simulation. Pointer movement converts screen coordinates into SVG coordinates and updates the fixed position. Pointer up or pointer cancellation clears `fx` and `fy`, resets `alphaTarget` to zero, and lets the graph settle.

Restart Layout clears stale drag fixation, applies a small seeded offset to non-root nodes, restores alpha to `1`, and restarts. The knowledge-base root receives a weaker central force rather than a hard lock, so it moves naturally while remaining visually central.

## Motion and Accessibility

For users whose system reports `prefers-reduced-motion: reduce`, the simulation performs a bounded number of synchronous ticks, publishes the stable result once, and stops. No continuous settling animation is shown.

Motion remains functional on touch devices. Pointer capture prevents a drag from being lost when the pointer moves outside the original node. Pointer cancellation follows the same release path as pointer up.

The implementation must avoid perpetual timers, hidden-tab animation work, and a new visual language. Existing graph colors, typography, controls, and design tokens remain unchanged.

## Performance Boundaries

- Only one simulation may exist for a mounted GraphView.
- Vue position publication is limited to one update per animation frame.
- Filtering does not recreate or reheat the simulation.
- Unmounting always stops the D3 timer and cancels queued animation frames.
- Converged simulations remain stopped until drag, restart, or a new graph dataset reheats them.

## Testing and Acceptance

Automated tests must first fail against the current static layout, then verify:

- Node coordinates change across multiple animation frames after graph entry.
- Displacement becomes materially smaller as alpha decays, demonstrating convergence rather than endless drift.
- Dragging fixes the selected node under the pointer and causes connected nodes to respond.
- Releasing the node allows another settling pass.
- Restart Layout produces renewed movement and a changed layout.
- Filters do not reset the positions of nodes that remain visible.
- Reduced-motion mode publishes a stable layout without continuous movement.
- Existing graph preview, zoom, filters, rail collapse, desktop, and mobile tests continue to pass.
- Type checking, production build, and the complete Playwright suite pass before deployment.

After local validation, deploy the same branch to the existing Compose stack without deleting named volumes. Production acceptance must verify the deployed asset shows coordinate movement followed by convergence, drag/release behavior, restart reheating, healthy services, and no new frontend or backend errors.
