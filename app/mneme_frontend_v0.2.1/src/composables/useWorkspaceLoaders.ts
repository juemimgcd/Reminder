import { ref } from "vue";
import type { WorkspaceView } from "../types";
import { createLoadState } from "./loadState";

export interface ViewLoadResult {
  empty?: boolean;
  message?: string;
}

type ViewLoader = (generation: number) => Promise<ViewLoadResult | void>;

export function useWorkspaceLoaders(loaders: Record<WorkspaceView, ViewLoader>) {
  const generation = ref(0);
  const loadedGenerations = new Map<WorkspaceView, number>();
  const viewLoadStates = {
    dashboard: createLoadState(),
    notes: createLoadState(),
    graph: createLoadState(),
    ai: createLoadState(),
    settings: createLoadState(),
  } satisfies Record<WorkspaceView, ReturnType<typeof createLoadState>>;

  function isCurrent(capturedGeneration: number) {
    return capturedGeneration === generation.value;
  }

  function invalidate() {
    generation.value += 1;
    loadedGenerations.clear();
    Object.values(viewLoadStates).forEach((state) => {
      state.phase.value = "idle";
      state.message.value = "";
    });
  }

  async function ensureViewLoaded(view: WorkspaceView, force = false) {
    const state = viewLoadStates[view];
    const capturedGeneration = generation.value;
    if (!force && loadedGenerations.get(view) === capturedGeneration) return;
    if (!force && state.phase.value === "loading") return;

    state.phase.value = "loading";
    state.message.value = "";
    try {
      const result = ((await loaders[view](capturedGeneration)) ?? {}) as ViewLoadResult;
      if (!isCurrent(capturedGeneration)) return;
      state.message.value = result?.message ?? "";
      state.phase.value = result?.empty ? "empty" : "ready";
      loadedGenerations.set(view, capturedGeneration);
    } catch {
      if (!isCurrent(capturedGeneration)) return;
      state.phase.value = "error";
      state.message.value = "This feature is temporarily unavailable. Please try again later.";
    }
  }

  return { ensureViewLoaded, generation, invalidate, isCurrent, viewLoadStates };
}
