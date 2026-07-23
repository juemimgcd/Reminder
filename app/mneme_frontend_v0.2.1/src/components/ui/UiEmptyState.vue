<script setup lang="ts">
withDefaults(defineProps<{ title: string; description: string; compact?: boolean }>(), { compact: false });
</script>

<template>
  <section class="ui-empty-state" :class="{ 'ui-empty-state--compact': compact }">
    <div v-if="$slots.icon" class="ui-empty-state__icon" aria-hidden="true"><slot name="icon" /></div>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <div v-if="$slots.action" class="ui-empty-state__action"><slot name="action" /></div>
  </section>
</template>

<style scoped>
.ui-empty-state { display: grid; min-height: 16rem; align-content: center; justify-items: center; padding: 2.5rem 1.5rem; color: var(--content-secondary); text-align: center; }
.ui-empty-state--compact { min-height: 10rem; padding: var(--space-6) var(--space-4); }
.ui-empty-state__icon { display: grid; width: 2.75rem; height: 2.75rem; place-items: center; margin-bottom: var(--space-4); color: var(--accent-primary); background: var(--accent-subtle); border-radius: var(--radius-panel); }
.ui-empty-state__icon :deep(svg) { width: 1.25rem; height: 1.25rem; }
h2 { margin: 0; color: var(--content-primary); font-size: var(--font-size-md); font-weight: 650; }
p { max-width: 28rem; margin: 0.45rem 0 0; font-size: var(--font-size-sm); line-height: 1.6; }
.ui-empty-state__action { margin-top: var(--space-5); }
</style>
