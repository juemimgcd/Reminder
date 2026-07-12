<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{
  title: string;
  description?: string;
  detail?: string;
  tone?: "info" | "success" | "warning" | "error";
  variant?: "info" | "success" | "warning" | "error";
  dismissible?: boolean;
}>(), { description: "", detail: "", tone: "info", variant: undefined, dismissible: false });
const emit = defineEmits<{ dismiss: [] }>();
const resolvedTone = computed(() => props.variant ?? props.tone);
const resolvedDetail = computed(() => props.detail || props.description);
</script>

<template>
  <section class="ui-status" :class="`ui-status--${resolvedTone}`" :role="resolvedTone === 'error' ? 'alert' : 'status'">
    <div class="ui-status__mark" aria-hidden="true" />
    <div>
      <p class="ui-status__title">{{ title }}</p>
      <p v-if="resolvedDetail" class="ui-status__description">{{ resolvedDetail }}</p>
      <div v-if="$slots.action" class="ui-status__action"><slot name="action" /></div>
    </div>
    <button v-if="dismissible" class="ui-status__dismiss" type="button" aria-label="Dismiss notification" @click="emit('dismiss')">×</button>
  </section>
</template>

<style scoped>
.ui-status { display: grid; min-width: 0; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.75rem; padding: 0.9rem 1rem; color: var(--text-secondary); background: var(--bg-sidebar); border: 1px solid var(--border-muted); border-radius: 0.45rem; }
.ui-status__mark { width: 0.45rem; height: 0.45rem; margin-top: 0.35rem; background: var(--accent); border-radius: 50%; }
.ui-status--success .ui-status__mark { background: var(--success); }
.ui-status--warning .ui-status__mark { background: var(--warning); }
.ui-status--error .ui-status__mark { background: var(--danger); }
.ui-status__title { margin: 0; color: var(--text-primary); font-family: var(--font-sans); font-size: 0.85rem; font-weight: 600; line-height: 1.45; overflow-wrap: anywhere; }
.ui-status__description { margin: 0.2rem 0 0; font-size: 0.8rem; line-height: 1.5; }
.ui-status__action { margin-top: 0.75rem; }
.ui-status__dismiss { align-self: start; color: var(--text-tertiary); background: transparent; border: 0; font-size: 1rem; }
</style>
