<script setup lang="ts">
defineProps<{ title: string; description: string }>();
</script>

<template>
  <section class="ui-empty-state">
    <div v-if="$slots.icon" class="ui-empty-state__icon"><slot name="icon" /></div>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <div v-if="$slots.action" class="ui-empty-state__action"><slot name="action" /></div>
  </section>
</template>

<style scoped>
.ui-empty-state { display: grid; justify-items: center; align-content: center; min-height: 16rem; padding: 2.5rem 1.5rem; text-align: center; color: var(--text-secondary); }
.ui-empty-state__icon { display: grid; place-items: center; width: 2.75rem; height: 2.75rem; margin-bottom: 1rem; color: var(--accent); background: var(--accent-soft); border-radius: 0.6rem; }
h2 { margin: 0; color: var(--text-primary); font-size: 1rem; font-weight: 600; }
p { max-width: 28rem; margin: 0.45rem 0 0; font-size: 0.875rem; line-height: 1.6; }
.ui-empty-state__action { margin-top: 1.25rem; }
</style>
