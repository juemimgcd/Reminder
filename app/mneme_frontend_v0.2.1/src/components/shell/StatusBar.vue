<script setup lang="ts">
defineProps<{ status: string; detail?: string }>();
</script>

<template>
  <footer class="status-bar">
    <span class="status-bar__dot" aria-hidden="true" />
    <span>{{ status }}</span>
    <span v-if="detail" class="status-bar__detail">{{ detail }}</span>
  </footer>
</template>

<style scoped>
.status-bar { display: flex; min-height: 1.55rem; align-items: center; gap: 0.45rem; padding: 0.2rem 0.75rem; color: var(--text-tertiary); background: var(--bg-sidebar); border-top: 1px solid var(--border-muted); font-family: var(--font-mono); font-size: 0.64rem; }
.status-bar__dot { width: 0.38rem; height: 0.38rem; background: var(--success); border-radius: 50%; }
.status-bar__detail { margin-left: auto; }
@media (max-width: 767px) { .status-bar { display: none; } }
</style>
