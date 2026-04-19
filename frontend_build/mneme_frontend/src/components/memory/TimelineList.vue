<script setup lang="ts">
import type { MemoryLibrary } from '@/lib/types';

defineProps<{
  library: MemoryLibrary;
}>();
</script>

<template>
  <div class="timeline-layout">
    <ol class="timeline-list">
      <li v-for="entry in library.timeline" :key="entry.entry_id">
        <time>{{ new Date(entry.created_at).toLocaleDateString('zh-CN') }}</time>
        <div>
          <strong>{{ entry.entry_name }}</strong>
          <p>{{ entry.summary }}</p>
          <span class="inline-badge">{{ entry.entry_type }}</span>
        </div>
      </li>
    </ol>

    <div class="memory-sidegrid">
      <section class="memory-group">
        <h3>按类型归档</h3>
        <div class="chip-wrap">
          <span v-for="(entries, type) in library.by_type" :key="type" class="memory-chip">
            {{ type }} · {{ entries.length }}
          </span>
        </div>
      </section>

      <section class="memory-group">
        <h3>主题簇</h3>
        <article v-for="theme in library.by_theme" :key="theme.theme_name" class="theme-card">
          <strong>{{ theme.theme_name }}</strong>
          <p>{{ theme.entries.join(' / ') }}</p>
        </article>
      </section>
    </div>
  </div>
</template>
