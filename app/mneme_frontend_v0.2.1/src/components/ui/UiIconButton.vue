<script setup lang="ts">
import { computed, useSlots } from "vue";

type TooltipSide = "top" | "right" | "bottom" | "left";

const props = withDefaults(
  defineProps<{
    label: string;
    active?: boolean;
    disabled?: boolean;
    size?: "sm" | "md";
    tooltip?: string;
    tooltipSide?: TooltipSide;
  }>(),
  { disabled: false, size: "md", tooltip: "", tooltipSide: "bottom" },
);

const slots = useSlots();
const ariaPressed = computed(() => props.active === undefined ? undefined : props.active);
const hasTooltip = computed(() => Boolean(props.tooltip || slots.tooltip));
</script>

<template>
  <button
    type="button"
    class="ui-icon-button"
    :class="[`ui-icon-button--${size}`, { 'ui-icon-button--active': active }]"
    :aria-label="label"
    :aria-pressed="ariaPressed"
    :disabled="disabled"
  >
    <slot />
    <span v-if="active" class="ui-icon-button__indicator" aria-hidden="true" />
    <span
      v-if="hasTooltip"
      class="ui-icon-button__tooltip"
      :class="`ui-icon-button__tooltip--${tooltipSide}`"
      role="tooltip"
    ><slot name="tooltip">{{ tooltip }}</slot></span>
  </button>
</template>

<style scoped>
.ui-icon-button {
  position: relative;
  display: inline-grid;
  flex: 0 0 auto;
  place-items: center;
  color: var(--content-secondary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  transition:
    color var(--duration-fast) ease,
    background-color var(--duration-fast) ease,
    border-color var(--duration-fast) ease,
    transform var(--duration-press) var(--ease-out-ui);
}

.ui-icon-button--sm { width: 2rem; height: 2rem; }
.ui-icon-button--md { width: 2.5rem; height: 2.5rem; }
.ui-icon-button--active { color: var(--accent-primary); background: var(--accent-subtle); }
.ui-icon-button:active:not(:disabled):not(:focus-visible) { transform: scale(0.97); }
.ui-icon-button:disabled { opacity: 0.4; }
.ui-icon-button__indicator { position: absolute; bottom: 0.2rem; left: 50%; width: 0.25rem; height: 0.25rem; background: currentColor; border-radius: 50%; transform: translateX(-50%); }

@media (hover: hover) and (pointer: fine) {
  .ui-icon-button:hover:not(:disabled) { color: var(--content-primary); background: var(--surface-raised); border-color: var(--stroke-subtle); }
  .ui-icon-button--active:hover:not(:disabled) { color: var(--accent-primary); background: var(--accent-subtle); }
}

.ui-icon-button__tooltip {
  position: absolute;
  z-index: var(--z-popover);
  width: max-content;
  max-width: 14rem;
  padding: 0.35rem 0.5rem;
  color: var(--content-primary);
  background: var(--surface-raised);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
  box-shadow: var(--shadow-popover);
  font-size: var(--font-size-xs);
  font-weight: 500;
  line-height: 1.35;
  opacity: 0;
  pointer-events: none;
  transform: scale(0.97);
  transition: opacity 150ms var(--ease-out-ui), transform 150ms var(--ease-out-ui);
}

.ui-icon-button__tooltip--top { bottom: calc(100% + var(--space-2)); left: 50%; transform-origin: bottom center; translate: -50% 0; }
.ui-icon-button__tooltip--right { top: 50%; left: calc(100% + var(--space-2)); transform-origin: left center; translate: 0 -50%; }
.ui-icon-button__tooltip--bottom { top: calc(100% + var(--space-2)); left: 50%; transform-origin: top center; translate: -50% 0; }
.ui-icon-button__tooltip--left { top: 50%; right: calc(100% + var(--space-2)); transform-origin: right center; translate: 0 -50%; }

@media (hover: hover) and (pointer: fine) {
  .ui-icon-button:hover .ui-icon-button__tooltip,
  .ui-icon-button:focus-visible .ui-icon-button__tooltip { opacity: 1; transform: scale(1); }
  .ui-icon-button:hover .ui-icon-button__tooltip { transition-delay: 400ms; }
  .ui-icon-button:focus-visible .ui-icon-button__tooltip { transition: none; }
}

@media (prefers-reduced-motion: reduce) {
  .ui-icon-button { transition-property: color, background-color, border-color; }
  .ui-icon-button__tooltip { transform: none; transition-property: opacity; }
}
</style>
