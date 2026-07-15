<script setup lang="ts">
import { onMounted, watch } from "vue";
import { Brain, RefreshCw } from "@lucide/vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import { useMemoryCenter } from "../composables/useMemoryCenter";
import CandidateInbox from "../components/memory/CandidateInbox.vue";
import MemoryDetail from "../components/memory/MemoryDetail.vue";
import MemoryList from "../components/memory/MemoryList.vue";
import UiEmptyState from "../components/ui/UiEmptyState.vue";
import UiSkeleton from "../components/ui/UiSkeleton.vue";
import UiStatusPanel from "../components/ui/UiStatusPanel.vue";
const props = defineProps<{ workspace: MnemeWorkspace }>();
const center = useMemoryCenter(
  props.workspace.token,
  props.workspace.activeKnowledgeBaseId,
  props.workspace.memoryPendingCount,
);
watch(props.workspace.activeKnowledgeBaseId, () => center.load());
onMounted(() => center.load());
async function confirmed(message: string, action: () => Promise<void>) {
  if (window.confirm(message)) await action();
}
</script>
<template>
  <div class="memory-center">
    <header>
      <div>
        <small>Governed long-term memory</small>
        <h1>
          Memory Center
          <span v-if="center.pendingCount.value"
            >{{ center.pendingCount.value }} pending</span
          >
        </h1>
      </div>
      <button
        :disabled="center.loading.value || center.pending.value"
        @click="center.load"
      >
        <RefreshCw />Refresh
      </button>
    </header>
    <UiStatusPanel
      v-if="center.error.value"
      :title="center.error.value"
      variant="warning"
    />
    <div v-if="center.loading.value" class="loading">
      <UiSkeleton v-for="n in 3" :key="n" height="4rem" />
    </div>
    <template v-else
      ><section class="settings">
        <label
          ><input
            type="checkbox"
            :disabled="center.pending.value || center.loading.value"
            :checked="center.automaticConversationMemory.value"
            @change="center.toggleSettings"
          />
          Automatically learn from conversations</label
        >
        <div>
          <button
            :disabled="
              center.pending.value || !workspace.activeKnowledgeBaseId.value
            "
            @click="
              confirmed(
                'Clear every governed memory in this knowledge base? This cannot be undone.',
                () => center.purge('knowledge_base'),
              )
            "
          >
            Clear this knowledge base</button
          ><button
            :disabled="center.pending.value"
            class="danger"
            @click="
              confirmed(
                'FINAL WARNING: clear all long-term memory for your account across every knowledge base? This cannot be undone.',
                () => center.purge('account'),
              )
            "
          >
            Clear all my memory
          </button>
        </div>
      </section>
      <CandidateInbox
        :items="center.candidates.value"
        :pending="center.loading.value || center.pending.value"
        @action="center.candidateAction" />
      <div class="body">
        <section>
          <h2>Active memories</h2>
          <MemoryList
            v-if="center.memories.value.length"
            :items="center.memories.value"
            :pending="center.pending.value || center.loading.value"
            :selected-id="center.detail.value?.memory.memory_id"
            @select="center.select"
          /><UiEmptyState
            v-else
            title="No active memories"
            description="Confirmed long-term memories will appear here."
            ><template #icon><Brain /></template
          ></UiEmptyState>
        </section>
        <MemoryDetail
          v-if="center.detail.value"
          :detail="center.detail.value"
          :pending="center.loading.value || center.pending.value"
          @revise="(value) => center.revise(center.detail.value!.memory, value)"
          @invalidate="
            confirmed(
              'Invalidate this memory while retaining its audit history?',
              () => center.invalidate(center.detail.value!.memory),
            )
          "
          @remove="
            confirmed(
              'Hard delete this memory and all revisions? This cannot be undone.',
              () => center.remove(center.detail.value!.memory),
            )
          "
          @purge-source="
            (id) =>
              confirmed(
                'Clear memories backed by this owned source? This cannot be undone.',
                () => center.purge('source', id),
              )
          "
        /></div
    ></template>
  </div>
</template>
<style scoped>
.memory-center {
  display: grid;
  gap: 1rem;
  max-width: 1200px;
  margin: auto;
  padding: 1.25rem;
}
.memory-center > header,
.settings {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.memory-center h1 {
  margin: 0.15rem 0;
  font: 600 1.35rem var(--font-serif);
}
h1 span {
  color: var(--accent);
  font: 0.65rem var(--font-mono);
}
small {
  color: var(--text-tertiary);
}
button {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.6rem;
  color: var(--text-secondary);
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.35rem;
}
button svg {
  width: 1rem;
}
.danger {
  color: var(--danger);
}
.settings {
  padding: 0.7rem;
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.45rem;
}
.settings div {
  display: flex;
  gap: 0.4rem;
}
.body {
  display: grid;
  grid-template-columns: minmax(250px, 0.8fr) minmax(350px, 1.2fr);
  gap: 1rem;
}
.body h2 {
  font-size: 0.85rem;
}
.loading {
  display: grid;
  gap: 0.6rem;
}
@media (max-width: 800px) {
  .body {
    grid-template-columns: 1fr;
  }
  .settings {
    align-items: flex-start;
    flex-direction: column;
  }
  .settings div {
    flex-wrap: wrap;
  }
}
</style>
