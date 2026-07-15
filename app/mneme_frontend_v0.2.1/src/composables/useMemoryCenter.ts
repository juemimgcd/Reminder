import { computed, ref } from "vue";
import { api } from "../lib/api";
import type { CanonicalMemory, MemoryCandidate, MemoryDetail } from "../types";

export function useMemoryCenter(token: { value: string }, knowledgeBaseId: { value: string }) {
  const memories = ref<CanonicalMemory[]>([]);
  const candidates = ref<MemoryCandidate[]>([]);
  const detail = ref<MemoryDetail | null>(null);
  const loading = ref(false);
  const pending = ref(false);
  const error = ref("");
  const pendingCount = ref(0);
  const automaticConversationMemory = ref(false);
  const scope = computed(() => knowledgeBaseId.value || null);

  async function load() {
    if (!token.value) return;
    loading.value = true; error.value = "";
    try {
      const [memoryPage, candidatePage, settings] = await Promise.all([api.listMemories(token.value, scope.value), api.listMemoryCandidates(token.value, scope.value), api.getMemorySettings(token.value)]);
      memories.value = memoryPage.items; candidates.value = candidatePage.items; pendingCount.value = candidatePage.pending_count ?? candidatePage.total; automaticConversationMemory.value = settings.automatic_conversation_memory;
      if (detail.value && !memories.value.some((m) => m.memory_id === detail.value?.memory.memory_id)) detail.value = null;
    } catch (cause) { error.value = cause instanceof Error ? cause.message : "Unable to load memory."; }
    finally { loading.value = false; }
  }

  async function select(memory: CanonicalMemory) { detail.value = await api.getMemoryDetail(token.value, memory.memory_id, memory.knowledge_base_id); }
  async function confirm(action: string, targetId: string | null, knowledgeBaseId: string | null) { return api.issueMemoryConfirmation(token.value, { action, target_id: targetId, knowledge_base_id: knowledgeBaseId }); }
  async function candidateAction(item: MemoryCandidate, action: "confirm" | "reject") { if (pending.value) return; pending.value = true; try { const c = await confirm(`${action}_candidate`, item.candidate_id, item.knowledge_base_id); await api.candidateCommand(token.value, item.candidate_id, action, item.knowledge_base_id, c.confirmation_token); await load(); } finally { pending.value = false; } }
  async function revise(memory: CanonicalMemory, value: string) { const c = await confirm("revise_memory", memory.memory_id, memory.knowledge_base_id); await api.reviseMemory(token.value, memory, value, c.confirmation_token); await load(); await select(memory); }
  async function invalidate(memory: CanonicalMemory) { const c = await confirm("invalidate_memory", memory.memory_id, memory.knowledge_base_id); await api.memoryCommand(token.value, memory, "invalidate", c.confirmation_token); await load(); }
  async function remove(memory: CanonicalMemory) { const c = await confirm("hard_delete_memory", memory.memory_id, memory.knowledge_base_id); await api.deleteMemory(token.value, memory, c.confirmation_token); detail.value = null; await load(); }
  async function toggleSettings() { const result = await api.updateMemorySettings(token.value, !automaticConversationMemory.value); automaticConversationMemory.value = result.automatic_conversation_memory; }
  async function purge(kind: "source" | "knowledge_base" | "account", targetId?: string) {
    if (pending.value) return; pending.value = true;
    try {
      const action = `purge_${kind}`; const kb = kind === "account" ? null : scope.value; const target = kind === "account" ? null : targetId ?? kb;
      const c = await confirm(action, target, kb);
      const payload: Record<string, unknown> = { reason: `user_purge_${kind}`, confirmation_token: c.confirmation_token };
      if (kind === "source") { payload.source_id = target; payload.scope_knowledge_base_id = kb; }
      else if (kind === "knowledge_base") payload.knowledge_base_id = kb;
      else payload.purge_account = true;
      await api.purgeMemory(token.value, payload); detail.value = null; await load();
    } finally { pending.value = false; }
  }
  return { memories, candidates, detail, loading, pending, error, pendingCount, automaticConversationMemory, load, select, candidateAction, revise, invalidate, remove, toggleSettings, purge };
}
