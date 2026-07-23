<script setup lang="ts">
withDefaults(defineProps<{ width?: string; height?: string; rounded?: boolean }>(), { width: "100%", height: "1rem", rounded: false });
</script>

<template>
  <span class="ui-skeleton" :class="{ 'ui-skeleton--rounded': rounded }" :style="{ width, height }" aria-hidden="true" />
</template>

<style scoped>
.ui-skeleton { display: block; overflow: hidden; background: var(--surface-raised); border-radius: calc(var(--radius-control) - 1px); }
.ui-skeleton::after { display: block; width: 36%; height: 100%; content: ""; background: color-mix(in srgb, var(--content-secondary) 10%, transparent); animation: ui-skeleton 1.4s linear infinite; transform: translateX(-120%); }
.ui-skeleton--rounded { border-radius: var(--radius-round); }
@keyframes ui-skeleton { to { transform: translateX(320%); } }
@media (prefers-reduced-motion: reduce) { .ui-skeleton::after { width: 100%; animation: none; opacity: 0.35; transform: none; } }
</style>
