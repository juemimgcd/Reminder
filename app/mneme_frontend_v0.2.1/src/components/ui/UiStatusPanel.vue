<script setup lang="ts">
withDefaults(defineProps<{ title: string; description?: string; tone?: "info" | "success" | "warning" | "error" }>(), { description: "", tone: "info" });
</script>

<template>
  <section class="ui-status" :class="`ui-status--${tone}`" :role="tone === 'error' ? 'alert' : 'status'">
    <div class="ui-status__mark" aria-hidden="true" />
    <div>
      <p class="ui-status__title">{{ title }}</p>
      <p v-if="description" class="ui-status__description">{{ description }}</p>
      <div v-if="$slots.action" class="ui-status__action"><slot name="action" /></div>
    </div>
  </section>
</template>

<style scoped>
.ui-status { display: grid; grid-template-columns: auto 1fr; gap: 0.75rem; padding: 0.9rem 1rem; color: var(--text-secondary); background: var(--bg-sidebar); border: 1px solid var(--border-muted); border-radius: 0.45rem; }
.ui-status__mark { width: 0.45rem; height: 0.45rem; margin-top: 0.35rem; background: var(--accent); border-radius: 50%; }
.ui-status--success .ui-status__mark { background: var(--success); }
.ui-status--warning .ui-status__mark { background: var(--warning); }
.ui-status--error .ui-status__mark { background: var(--danger); }
.ui-status__title { margin: 0; color: var(--text-primary); font-size: 0.85rem; font-weight: 600; }
.ui-status__description { margin: 0.2rem 0 0; font-size: 0.8rem; line-height: 1.5; }
.ui-status__action { margin-top: 0.75rem; }
</style>
