import { computed, ref } from "vue";
import { api } from "../lib/api";
import type { CanonicalMemory, MemoryCandidate, MemoryDetail } from "../types";

type BusyKind = "loading" | "pending";

export function useMemoryCenter(
  token: { value: string },
  knowledgeBaseId: { value: string },
  sharedPendingCount: { value: number },
) {
  const memories = ref<CanonicalMemory[]>([]);
  const candidates = ref<MemoryCandidate[]>([]);
  const detail = ref<MemoryDetail | null>(null);
  const loading = ref(false);
  const pending = ref(false);
  const error = ref("");
  const automaticConversationMemory = ref(false);
  const scope = computed(() => knowledgeBaseId.value || null);

  async function execute<T>(
    kind: BusyKind,
    operation: () => Promise<T>,
  ): Promise<T | undefined> {
    if (loading.value || pending.value) return;
    const busy = kind === "loading" ? loading : pending;
    busy.value = true;
    error.value = "";
    try {
      return await operation();
    } catch (cause) {
      error.value =
        cause instanceof Error ? cause.message : "Memory request failed.";
      return undefined;
    } finally {
      busy.value = false;
    }
  }

  async function refresh() {
    const [memoryPage, candidatePage, settings] = await Promise.all([
      api.listMemories(token.value, scope.value),
      api.listMemoryCandidates(token.value, scope.value),
      api.getMemorySettings(token.value),
    ]);
    memories.value = memoryPage.items;
    candidates.value = candidatePage.items;
    sharedPendingCount.value =
      candidatePage.pending_count ?? candidatePage.total;
    automaticConversationMemory.value = settings.automatic_conversation_memory;
    if (
      detail.value &&
      !memories.value.some(
        (item) => item.memory_id === detail.value?.memory.memory_id,
      )
    )
      detail.value = null;
  }

  async function load() {
    if (!token.value) return;
    await execute("loading", refresh);
  }

  async function select(memory: CanonicalMemory) {
    await execute("loading", async () => {
      detail.value = await api.getMemoryDetail(
        token.value,
        memory.memory_id,
        memory.knowledge_base_id,
      );
    });
  }

  async function confirm(
    action: string,
    targetId: string | null,
    knowledgeBaseId: string | null,
  ) {
    return api.issueMemoryConfirmation(token.value, {
      action,
      target_id: targetId,
      knowledge_base_id: knowledgeBaseId,
    });
  }

  async function candidateAction(
    item: MemoryCandidate,
    action: "confirm" | "reject",
  ) {
    await execute("pending", async () => {
      const confirmation = await confirm(
        `${action}_candidate`,
        item.candidate_id,
        item.knowledge_base_id,
      );
      await api.candidateCommand(
        token.value,
        item.candidate_id,
        action,
        item.knowledge_base_id,
        confirmation.confirmation_token,
      );
      await refresh();
    });
  }

  async function revise(memory: CanonicalMemory, value: string) {
    await execute("pending", async () => {
      const confirmation = await confirm(
        "revise_memory",
        memory.memory_id,
        memory.knowledge_base_id,
      );
      await api.reviseMemory(
        token.value,
        memory,
        value,
        confirmation.confirmation_token,
      );
      await refresh();
      detail.value = await api.getMemoryDetail(
        token.value,
        memory.memory_id,
        memory.knowledge_base_id,
      );
    });
  }

  async function invalidate(memory: CanonicalMemory) {
    await execute("pending", async () => {
      const confirmation = await confirm(
        "invalidate_memory",
        memory.memory_id,
        memory.knowledge_base_id,
      );
      await api.memoryCommand(
        token.value,
        memory,
        "invalidate",
        confirmation.confirmation_token,
      );
      detail.value = null;
      await refresh();
    });
  }

  async function remove(memory: CanonicalMemory) {
    await execute("pending", async () => {
      const confirmation = await confirm(
        "hard_delete_memory",
        memory.memory_id,
        memory.knowledge_base_id,
      );
      await api.deleteMemory(
        token.value,
        memory,
        confirmation.confirmation_token,
      );
      detail.value = null;
      await refresh();
    });
  }

  async function toggleSettings() {
    await execute("pending", async () => {
      const result = await api.updateMemorySettings(
        token.value,
        !automaticConversationMemory.value,
      );
      automaticConversationMemory.value = result.automatic_conversation_memory;
    });
  }

  async function purge(
    kind: "source" | "knowledge_base" | "account",
    targetId?: string,
  ) {
    await execute("pending", async () => {
      const knowledgeBase = kind === "account" ? null : scope.value;
      const target = kind === "account" ? null : (targetId ?? knowledgeBase);
      const confirmation = await confirm(
        `purge_${kind}`,
        target,
        knowledgeBase,
      );
      const payload: Record<string, unknown> = {
        reason: `user_purge_${kind}`,
        confirmation_token: confirmation.confirmation_token,
      };
      if (kind === "source") {
        payload.source_id = target;
        payload.scope_knowledge_base_id = knowledgeBase;
      } else if (kind === "knowledge_base")
        payload.knowledge_base_id = knowledgeBase;
      else payload.purge_account = true;
      await api.purgeMemory(token.value, payload);
      detail.value = null;
      await refresh();
    });
  }

  return {
    memories,
    candidates,
    detail,
    loading,
    pending,
    error,
    pendingCount: sharedPendingCount,
    automaticConversationMemory,
    load,
    select,
    candidateAction,
    revise,
    invalidate,
    remove,
    toggleSettings,
    purge,
  };
}
