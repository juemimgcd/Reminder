<script setup lang="ts">
import type { Component } from "vue";
import { nextTick } from "vue";

export type UiSegmentedOption = {
  value: string;
  label: string;
  icon?: Component;
  disabled?: boolean;
};

const props = withDefaults(defineProps<{
  options: UiSegmentedOption[];
  ariaLabel: string;
  disabled?: boolean;
  size?: "sm" | "md";
}>(), { disabled: false, size: "md" });

const model = defineModel<string>({ required: true });

function tabIndexFor(option: UiSegmentedOption, index: number) {
  if (model.value === option.value) return 0;
  const hasSelectedOption = props.options.some((item) => item.value === model.value && !item.disabled);
  if (!hasSelectedOption && props.options.findIndex((item) => !item.disabled) === index) return 0;
  return -1;
}

function select(option: UiSegmentedOption) {
  if (props.disabled || option.disabled) return;
  model.value = option.value;
}

async function moveSelection(event: KeyboardEvent, currentIndex: number) {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const available = props.options
    .map((option, index) => ({ option, index }))
    .filter(({ option }) => !option.disabled);
  if (!available.length) return;

  const currentPosition = available.findIndex(({ index }) => index === currentIndex);
  let nextPosition = currentPosition;
  if (event.key === 'Home') nextPosition = 0;
  else if (event.key === 'End') nextPosition = available.length - 1;
  else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') nextPosition = currentPosition < 0 ? 0 : (currentPosition + 1) % available.length;
  else nextPosition = currentPosition < 0 ? available.length - 1 : (currentPosition - 1 + available.length) % available.length;

  const next = available[nextPosition];
  select(next.option);
  await nextTick();
  const group = (event.currentTarget as HTMLElement).closest('[role="radiogroup"]');
  group?.querySelectorAll<HTMLButtonElement>('[role="radio"]')[next.index]?.focus();
}
</script>

<template>
  <div class="ui-segmented" :class="`ui-segmented--${size}`" role="radiogroup" :aria-label="ariaLabel" :aria-disabled="disabled || undefined">
    <button
      v-for="(option, index) in options"
      :key="option.value"
      type="button"
      role="radio"
      class="ui-segmented__option"
      :class="{ 'ui-segmented__option--active': model === option.value }"
      :aria-checked="model === option.value"
      :tabindex="tabIndexFor(option, index)"
      :disabled="disabled || option.disabled"
      @click="select(option)"
      @keydown="moveSelection($event, index)"
    >
      <component :is="option.icon" v-if="option.icon" aria-hidden="true" />
      <span>{{ option.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.ui-segmented { display: inline-flex; min-width: 0; gap: 2px; padding: 3px; background: var(--surface-sidebar); border: 1px solid var(--stroke-subtle); border-radius: calc(var(--radius-control) + 2px); }
.ui-segmented__option { display: inline-flex; min-width: 0; align-items: center; justify-content: center; gap: 0.4rem; color: var(--content-secondary); background: transparent; border: 0; border-radius: var(--radius-control); font-weight: 600; line-height: 1; transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease, box-shadow var(--duration-fast) ease; }
.ui-segmented--sm .ui-segmented__option { min-height: 1.8rem; padding: 0.35rem 0.55rem; font-size: var(--font-size-xs); }
.ui-segmented--md .ui-segmented__option { min-height: 2.2rem; padding: 0.5rem 0.75rem; font-size: 0.8rem; }
.ui-segmented__option svg { width: 0.95rem; height: 0.95rem; }
.ui-segmented__option--active { color: var(--content-primary); background: var(--surface-panel); box-shadow: inset 0 0 0 1px var(--stroke-subtle); }
.ui-segmented__option:disabled { opacity: 0.45; }
@media (hover: hover) and (pointer: fine) { .ui-segmented__option:hover:not(:disabled):not(.ui-segmented__option--active) { color: var(--content-primary); background: var(--surface-raised); } }
</style>
