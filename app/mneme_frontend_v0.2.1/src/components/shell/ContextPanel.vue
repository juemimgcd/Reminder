<script setup lang="ts">
defineProps<{ open: boolean; label: string }>();
</script>

<template>
  <aside v-if="open" class="context-panel" :aria-label="label"><slot /></aside>
</template>

<style scoped>
.context-panel { width: 280px; min-width: 0; height: 100%; overflow: auto; background: var(--bg-panel); border-left: 1px solid var(--border-muted); }
@media (max-width: 1023px) { .context-panel { position: fixed; inset: 0 0 0 auto; z-index: 55; width: min(88vw, 340px); box-shadow: var(--shadow-float); } }
</style>
