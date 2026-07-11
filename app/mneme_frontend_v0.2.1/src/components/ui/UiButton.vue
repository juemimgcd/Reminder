<script setup lang="ts">
import { computed } from "vue";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant;
    size?: ButtonSize;
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
    :aria-busy="loading"
  >
    <span v-if="loading" class="ui-button__spinner" aria-hidden="true" />
    <slot name="icon" />
    <slot />
  </button>
</template>

<style scoped>
.ui-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 1px solid transparent;
  border-radius: 0.4rem;
  font-weight: 500;
  transition: color 140ms ease, background-color 140ms ease, border-color 140ms ease;
}
.ui-button--sm { min-height: 2rem; padding: 0.35rem 0.65rem; font-size: 0.78rem; }
.ui-button--md { min-height: 2.5rem; padding: 0.55rem 0.9rem; font-size: 0.875rem; }
.ui-button--primary { color: var(--accent-contrast); background: var(--accent); }
.ui-button--primary:hover:not(:disabled) { background: var(--accent-strong); color: #fff; }
.ui-button--secondary { color: var(--text-primary); background: var(--bg-panel); border-color: var(--border-muted); }
.ui-button--secondary:hover:not(:disabled) { background: var(--bg-elevated); border-color: var(--border-strong); }
.ui-button--ghost { color: var(--text-secondary); background: transparent; }
.ui-button--ghost:hover:not(:disabled) { color: var(--text-primary); background: var(--bg-elevated); }
.ui-button--danger { color: var(--danger); background: transparent; border-color: color-mix(in srgb, var(--danger) 42%, var(--border-muted)); }
.ui-button--danger:hover:not(:disabled) { background: color-mix(in srgb, var(--danger) 10%, transparent); }
.ui-button:disabled { cursor: not-allowed; opacity: 0.48; }
.ui-button__spinner { width: 0.9rem; height: 0.9rem; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: ui-spin 700ms linear infinite; }
@keyframes ui-spin { to { transform: rotate(360deg); } }
</style>
