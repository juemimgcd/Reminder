<script setup lang="ts">
import type { ChatSource } from '@/lib/types';

defineProps<{
  source: ChatSource;
}>();
</script>

<template>
  <article class="source-card">
    <header>
      <strong>{{ source.document_id }}</strong>
      <span>{{ source.source_page_nos.join(' / ') || '页码未知' }}</span>
    </header>
    <p>{{ source.text }}</p>
    <small>来源 chunk: {{ source.chunk_id }}</small>
  </article>
</template>
