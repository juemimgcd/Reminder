<script setup lang="ts">
withDefaults(defineProps<{ width?: string; height?: string; rounded?: boolean }>(), { width: "100%", height: "1rem", rounded: false });
</script>

<template>
  <span class="ui-skeleton" :class="{ 'ui-skeleton--rounded': rounded }" :style="{ width, height }" aria-hidden="true" />
</template>

<style scoped>
.ui-skeleton { display: block; overflow: hidden; background: var(--bg-elevated); border-radius: 0.3rem; }
.ui-skeleton::after { display: block; width: 36%; height: 100%; content: ""; background: color-mix(in srgb, var(--text-secondary) 10%, transparent); animation: ui-skeleton 1.4s ease-in-out infinite; transform: translateX(-120%); }
.ui-skeleton--rounded { border-radius: 999px; }
@keyframes ui-skeleton { to { transform: translateX(320%); } }
</style>
