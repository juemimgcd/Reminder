<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from "vue";
import UiButton, { type UiButtonVariant } from "./UiButton.vue";

const props = withDefaults(defineProps<{
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmVariant?: UiButtonVariant;
  busy?: boolean;
  dismissible?: boolean;
  initialFocus?: "cancel" | "confirm" | "dialog";
}>(), {
  description: "",
  confirmLabel: "Confirm",
  cancelLabel: "Cancel",
  confirmVariant: "primary",
  busy: false,
  dismissible: true,
  initialFocus: "cancel",
});

const open = defineModel<boolean>({ default: false });
const emit = defineEmits<{ confirm: []; cancel: [] }>();
const titleId = useId();
const descriptionId = useId();
const dialog = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
let previousOverflow = "";

function focusableElements() {
  return Array.from(dialog.value?.querySelectorAll<HTMLElement>('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])') ?? []);
}

function cancel() {
  if (props.busy) return;
  open.value = false;
  emit("cancel");
}

function dismiss() {
  if (!props.dismissible) return;
  cancel();
}

function onBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) dismiss();
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    dismiss();
    return;
  }
  if (event.key !== "Tab") return;
  const elements = focusableElements();
  if (!elements.length) {
    event.preventDefault();
    dialog.value?.focus();
    return;
  }
  const first = elements[0];
  const last = elements[elements.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

watch(open, async (isOpen) => {
  if (isOpen) {
    previousFocus = document.activeElement as HTMLElement | null;
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    await nextTick();
    const selector = props.initialFocus === "cancel" ? '[data-dialog-cancel]' : props.initialFocus === "confirm" ? '[data-dialog-confirm]' : "";
    const target = selector ? dialog.value?.querySelector<HTMLElement>(selector) : dialog.value;
    (target ?? dialog.value)?.focus();
    return;
  }
  document.body.style.overflow = previousOverflow;
  previousFocus?.focus();
  previousFocus = null;
});

onBeforeUnmount(() => {
  if (open.value) document.body.style.overflow = previousOverflow;
});
</script>

<template>
  <Teleport to="body">
    <Transition name="ui-dialog">
      <div v-if="open" class="ui-dialog__backdrop" @mousedown="onBackdropClick">
        <section
          ref="dialog"
          class="ui-dialog"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="description ? descriptionId : undefined"
          tabindex="-1"
          @keydown="onKeyDown"
        >
          <header>
            <div>
              <h2 :id="titleId">{{ title }}</h2>
              <p v-if="description" :id="descriptionId">{{ description }}</p>
            </div>
          </header>
          <div v-if="$slots.default" class="ui-dialog__content"><slot /></div>
          <footer>
            <slot name="actions" :cancel="cancel">
              <UiButton data-dialog-cancel variant="secondary" :disabled="busy" @click="cancel">{{ cancelLabel }}</UiButton>
              <UiButton data-dialog-confirm :variant="confirmVariant" :loading="busy" @click="emit('confirm')">{{ confirmLabel }}</UiButton>
            </slot>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ui-dialog__backdrop { position: fixed; inset: 0; z-index: var(--z-dialog); display: grid; place-items: center; padding: var(--space-4); background: rgb(0 0 0 / 48%); }
.ui-dialog { width: min(30rem, 100%); max-height: calc(100dvh - 2rem); overflow: auto; padding: var(--space-5); color: var(--content-primary); background: var(--surface-panel); border: 1px solid var(--stroke-subtle); border-radius: var(--radius-popover); box-shadow: var(--shadow-dialog); transform-origin: center; }
.ui-dialog:focus { outline: none; }
.ui-dialog header h2 { margin: 0; font-size: var(--font-size-lg); line-height: var(--line-height-tight); }
.ui-dialog header p { margin: var(--space-2) 0 0; color: var(--content-secondary); font-size: var(--font-size-sm); line-height: var(--line-height-body); }
.ui-dialog__content { margin-top: var(--space-4); }
.ui-dialog footer { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-5); }
.ui-dialog-enter-active { transition: opacity 200ms var(--ease-out-ui); }
.ui-dialog-leave-active { transition: opacity 140ms var(--ease-out-ui); }
.ui-dialog-enter-active .ui-dialog { transition: transform 200ms var(--ease-out-ui); }
.ui-dialog-leave-active .ui-dialog { transition: transform 140ms var(--ease-out-ui); }
.ui-dialog-enter-from, .ui-dialog-leave-to { opacity: 0; }
.ui-dialog-enter-from .ui-dialog, .ui-dialog-leave-to .ui-dialog { transform: scale(0.96); }
@media (prefers-reduced-motion: reduce) { .ui-dialog-enter-active .ui-dialog, .ui-dialog-leave-active .ui-dialog { transition: none; } .ui-dialog-enter-from .ui-dialog, .ui-dialog-leave-to .ui-dialog { transform: none; } }
</style>
