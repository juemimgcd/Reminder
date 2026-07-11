<script setup lang="ts">
withDefaults(
  defineProps<{ label: string; active?: boolean; disabled?: boolean; size?: "sm" | "md" }>(),
  { active: false, disabled: false, size: "md" },
);
</script>

<template>
  <button
    type="button"
    class="ui-icon-button"
    :class="[`ui-icon-button--${size}`, { 'ui-icon-button--active': active }]"
    :aria-label="label"
    :aria-pressed="active"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped>
.ui-icon-button { display: inline-grid; place-items: center; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 0.4rem; transition: 140ms ease; }
.ui-icon-button--sm { width: 2rem; height: 2rem; }
.ui-icon-button--md { width: 2.5rem; height: 2.5rem; }
.ui-icon-button:hover:not(:disabled) { color: var(--text-primary); background: var(--bg-elevated); border-color: var(--border-muted); }
.ui-icon-button--active { color: var(--accent); background: var(--accent-soft); }
.ui-icon-button:disabled { cursor: not-allowed; opacity: 0.4; }
</style>
