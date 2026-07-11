<script setup lang="ts">
defineProps<{ title: string; hint?: string }>();
</script>

<template>
  <header class="workspace-header">
    <div class="workspace-header__titles">
      <p v-if="hint">{{ hint }}</p>
      <h1>{{ title }}</h1>
    </div>
    <div class="workspace-header__actions"><slot name="actions" /></div>
  </header>
</template>

<style scoped>
.workspace-header { display: flex; min-height: 3.4rem; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.6rem 1rem; background: color-mix(in srgb, var(--bg-canvas) 94%, transparent); border-bottom: 1px solid var(--border-muted); }
.workspace-header__titles { min-width: 0; }
.workspace-header p { overflow: hidden; margin: 0 0 0.1rem; color: var(--text-tertiary); font-family: var(--font-mono); font-size: 0.66rem; text-overflow: ellipsis; white-space: nowrap; }
.workspace-header h1 { overflow: hidden; margin: 0; font-size: 0.96rem; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.workspace-header__actions { display: flex; align-items: center; gap: 0.35rem; }
</style>
