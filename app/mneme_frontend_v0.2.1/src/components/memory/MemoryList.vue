<script setup lang="ts">
import type { CanonicalMemory } from "../../types";
defineProps<{
  items: CanonicalMemory[];
  selectedId?: string;
  pending: boolean;
}>();
defineEmits<{ select: [memory: CanonicalMemory] }>();
</script>
<template>
  <div class="memory-list">
    <button
      v-for="item in items"
      :key="item.memory_id"
      :class="{ active: item.memory_id === selectedId }"
      :disabled="pending"
      @click="$emit('select', item)"
    >
      <small
        >{{ item.memory_type }} ·
        {{ Math.round(item.confidence * 100) }}%</small
      ><strong>{{ item.subject }} {{ item.predicate }}</strong
      ><span>{{ item.value }}</span>
    </button>
  </div>
</template>
<style scoped>
.memory-list {
  display: grid;
  gap: 0.45rem;
}
.memory-list button {
  display: grid;
  gap: 0.25rem;
  padding: 0.75rem;
  text-align: left;
  color: var(--text-primary);
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.45rem;
}
.memory-list button.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}
small,
span {
  color: var(--text-secondary);
}
strong {
  font-size: 0.82rem;
}
span {
  font-size: 0.74rem;
}
</style>
