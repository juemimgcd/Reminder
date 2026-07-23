<script setup lang="ts">
import { computed, useId } from "vue";

const props = withDefaults(defineProps<{
  label: string;
  description?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
}>(), { description: "", error: "", required: false, disabled: false });

const inputId = useId();
const descriptionId = useId();
const errorId = useId();
const describedBy = computed(() => [props.description ? descriptionId : "", props.error ? errorId : ""].filter(Boolean).join(" ") || undefined);
const inputProps = computed(() => ({
  id: inputId,
  disabled: props.disabled,
  required: props.required,
  "aria-describedby": describedBy.value,
  "aria-invalid": props.error ? true : undefined,
}));
</script>

<template>
  <div class="ui-field" :class="{ 'ui-field--disabled': disabled, 'ui-field--error': error }">
    <label :for="inputId">{{ label }}<span v-if="required" aria-hidden="true">*</span></label>
    <slot :id="inputId" :props="inputProps" />
    <p v-if="description" :id="descriptionId" class="ui-field__description">{{ description }}</p>
    <p v-if="error" :id="errorId" class="ui-field__error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.ui-field { display: grid; gap: 0.35rem; min-width: 0; }
.ui-field label { color: var(--content-secondary); font-size: var(--font-size-xs); font-weight: 600; }
.ui-field label span { margin-left: 0.2rem; color: var(--status-danger); }
.ui-field :deep(input), .ui-field :deep(textarea), .ui-field :deep(select) { width: 100%; min-height: 2.5rem; padding: 0.55rem 0.7rem; color: var(--content-primary); background: var(--surface-canvas); border: 1px solid var(--stroke-subtle); border-radius: var(--radius-control); transition: border-color var(--duration-fast) ease, box-shadow var(--duration-fast) ease, background-color var(--duration-fast) ease; }
.ui-field :deep(textarea) { min-height: 6rem; resize: vertical; }
.ui-field :deep(input:focus), .ui-field :deep(textarea:focus), .ui-field :deep(select:focus) { border-color: var(--accent-primary); box-shadow: 0 0 0 3px var(--accent-subtle); outline: none; }
.ui-field--error :deep(input), .ui-field--error :deep(textarea), .ui-field--error :deep(select) { border-color: var(--status-danger); }
.ui-field--disabled { opacity: 0.58; }
.ui-field__description, .ui-field__error { margin: 0; font-size: var(--font-size-xs); line-height: 1.45; }
.ui-field__description { color: var(--content-tertiary); }
.ui-field__error { color: var(--status-danger); }
</style>
