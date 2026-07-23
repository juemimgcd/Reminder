<script setup lang="ts">
import { computed } from "vue";

export type UiButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type UiButtonSize = "sm" | "md";

const props = withDefaults(
  defineProps<{
    variant?: UiButtonVariant;
    size?: UiButtonSize;
    disabled?: boolean;
    loading?: boolean;
    type?: "button" | "submit" | "reset";
  }>(),
  { variant: "secondary", size: "md", disabled: false, loading: false, type: "button" },
);

const classes = computed(() => [
  `ui-button--${props.variant}`,
  `ui-button--${props.size}`,
]);
</script>

<template>
  <button
    :type="type"
    class="ui-button"
    :class="classes"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <span v-if="loading" class="ui-button__spinner" aria-hidden="true" />
    <span v-else-if="$slots.icon" class="ui-button__icon" aria-hidden="true"><slot name="icon" /></span>
    <span class="ui-button__label"><slot /></span>
  </button>
</template>

<style scoped>
.ui-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  font-weight: 600;
  line-height: 1;
  transition:
    color var(--duration-fast) ease,
    background-color var(--duration-fast) ease,
    border-color var(--duration-fast) ease,
    box-shadow var(--duration-fast) ease,
    transform var(--duration-press) var(--ease-out-ui);
}

.ui-button--sm { min-height: 2rem; padding: 0.35rem 0.65rem; font-size: 0.78rem; }
.ui-button--md { min-height: 2.5rem; padding: 0.55rem 0.9rem; font-size: var(--font-size-sm); }
.ui-button--primary { color: var(--accent-on-primary); background: var(--accent-primary); }
.ui-button--secondary { color: var(--content-primary); background: var(--surface-panel); border-color: var(--stroke-subtle); }
.ui-button--ghost { color: var(--content-secondary); background: transparent; }
.ui-button--danger { color: var(--status-danger); background: transparent; border-color: color-mix(in srgb, var(--status-danger) 42%, var(--stroke-subtle)); }

@media (hover: hover) and (pointer: fine) {
  .ui-button--primary:hover:not(:disabled) { color: #fff; background: var(--accent-hover); }
  .ui-button--secondary:hover:not(:disabled) { background: var(--surface-raised); border-color: var(--stroke-default); }
  .ui-button--ghost:hover:not(:disabled) { color: var(--content-primary); background: var(--surface-raised); }
  .ui-button--danger:hover:not(:disabled) { background: color-mix(in srgb, var(--status-danger) 10%, transparent); }
}

.ui-button:active:not(:disabled):not(:focus-visible) { transform: scale(0.97); }
.ui-button:disabled { opacity: 0.48; }
.ui-button__icon { display: inline-grid; place-items: center; }
.ui-button__icon :deep(svg) { width: 1rem; height: 1rem; }
.ui-button__label { min-width: 0; }
.ui-button__spinner { width: 0.9rem; height: 0.9rem; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: ui-spin 700ms linear infinite; }

@keyframes ui-spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .ui-button { transition-property: color, background-color, border-color, box-shadow; }
  .ui-button__spinner { animation: ui-spinner-pulse 1.2s ease-in-out infinite; border-right-color: currentColor; }
}

@keyframes ui-spinner-pulse { 50% { opacity: 0.35; } }
</style>
