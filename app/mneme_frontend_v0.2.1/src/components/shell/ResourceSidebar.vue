<script setup lang="ts">
defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <div v-if="open" class="resource-sidebar__scrim" aria-hidden="true" @click="emit('close')" />
  <aside data-testid="resource-sidebar" class="resource-sidebar stitch-sidebar" :class="{ 'resource-sidebar--open': open }" :aria-hidden="!open">
    <slot />
  </aside>
</template>

<style scoped>
.resource-sidebar { display: flex; width: 256px; min-width: 0; height: 100vh; flex-direction: column; overflow: hidden; border-right: 1px solid var(--border-muted); }
.resource-sidebar__scrim { display: none; }
@media (min-width: 1024px) { .resource-sidebar[aria-hidden="true"] { width: 0; visibility: hidden; border: 0; } }
@media (max-width: 1023px) {
  .resource-sidebar { position: fixed; inset: 0 auto 0 0; z-index: 50; width: min(84vw, 300px); box-shadow: var(--shadow-float); transform: translateX(-102%); transition: transform 180ms ease; }
  .resource-sidebar--open { transform: translateX(0); }
  .resource-sidebar__scrim { position: fixed; inset: 0; z-index: 40; display: block; background: rgba(0, 0, 0, 0.35); }
}
</style>
