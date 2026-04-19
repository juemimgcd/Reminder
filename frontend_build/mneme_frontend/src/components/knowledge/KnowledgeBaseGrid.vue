<script setup lang="ts">
import type { KnowledgeBase } from '@/lib/types';

defineProps<{
  items: KnowledgeBase[];
  activeId: string;
}>();

const emit = defineEmits<{
  (event: 'select', id: string): void;
}>();
</script>

<template>
  <div class="knowledge-grid">
    <button
      v-for="item in items"
      :key="item.id"
      class="knowledge-card"
      type="button"
      :data-active="item.id === activeId"
      @click="emit('select', item.id)"
    >
      <div class="knowledge-card__header">
        <strong>{{ item.name }}</strong>
        <span class="status-pill" :data-status="item.status">{{ item.status }}</span>
      </div>
      <p>{{ item.description }}</p>
      <dl class="knowledge-card__meta">
        <div>
          <dt>文档</dt>
          <dd>{{ item.document_count }}</dd>
        </div>
        <div>
          <dt>记忆条目</dt>
          <dd>{{ item.memory_count }}</dd>
        </div>
      </dl>
    </button>
  </div>
</template>
