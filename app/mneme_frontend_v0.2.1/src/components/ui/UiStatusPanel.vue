<script setup lang="ts">
import { AlertTriangle, CheckCircle2, CircleAlert, Info, X } from "@lucide/vue";
import { computed } from "vue";

type StatusTone = "info" | "success" | "warning" | "error" | "danger";

const props = withDefaults(defineProps<{
  title: string;
  description?: string;
  detail?: string;
  tone?: StatusTone;
  variant?: StatusTone;
  dismissible?: boolean;
  dismissLabel?: string;
}>(), { description: "", detail: "", tone: "info", variant: undefined, dismissible: false, dismissLabel: "Dismiss notification" });

const emit = defineEmits<{ dismiss: [] }>();
const resolvedTone = computed(() => props.variant ?? props.tone);
const visualTone = computed(() => resolvedTone.value === "danger" ? "error" : resolvedTone.value);
const resolvedDetail = computed(() => props.detail || props.description);
const icon = computed(() => ({ info: Info, success: CheckCircle2, warning: AlertTriangle, error: CircleAlert }[visualTone.value]));
</script>

<template>
  <section
    class="ui-status"
    :class="`ui-status--${visualTone}`"
    :role="visualTone === 'error' ? 'alert' : 'status'"
    :aria-live="visualTone === 'error' ? 'assertive' : 'polite'"
  >
    <component :is="icon" class="ui-status__icon" aria-hidden="true" />
    <div class="ui-status__content">
      <p class="ui-status__title">{{ title }}</p>
      <p v-if="resolvedDetail" class="ui-status__description">{{ resolvedDetail }}</p>
      <div v-if="$slots.action" class="ui-status__action"><slot name="action" /></div>
    </div>
    <button v-if="dismissible" class="ui-status__dismiss" type="button" :aria-label="dismissLabel" @click="emit('dismiss')"><X /></button>
  </section>
</template>

<style scoped>
.ui-status { --status-color: var(--status-info); display: grid; min-width: 0; grid-template-columns: auto minmax(0, 1fr) auto; gap: var(--space-3); padding: 0.9rem var(--space-4); color: var(--content-secondary); background: color-mix(in srgb, var(--status-color) 7%, var(--surface-sidebar)); border: 1px solid color-mix(in srgb, var(--status-color) 24%, var(--stroke-subtle)); border-radius: var(--radius-control); }
.ui-status--success { --status-color: var(--status-success); }
.ui-status--warning { --status-color: var(--status-warning); }
.ui-status--error { --status-color: var(--status-danger); }
.ui-status__icon { width: 1rem; height: 1rem; margin-top: 0.15rem; color: var(--status-color); }
.ui-status__content { min-width: 0; }
.ui-status__title { margin: 0; overflow-wrap: anywhere; color: var(--content-primary); font-size: var(--font-size-sm); font-weight: 600; line-height: 1.45; }
.ui-status__description { margin: 0.2rem 0 0; font-size: 0.8rem; line-height: 1.5; }
.ui-status__action { margin-top: var(--space-3); }
.ui-status__dismiss { display: grid; width: 2rem; height: 2rem; place-items: center; align-self: start; margin: -0.35rem -0.45rem 0 0; color: var(--content-tertiary); background: transparent; border: 0; border-radius: var(--radius-control); transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease; }
.ui-status__dismiss svg { width: 0.95rem; height: 0.95rem; }
@media (hover: hover) and (pointer: fine) { .ui-status__dismiss:hover { color: var(--content-primary); background: var(--surface-raised); } }
</style>
