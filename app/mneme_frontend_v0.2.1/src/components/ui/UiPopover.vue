<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from "vue";

type PopoverPlacement = "top" | "right" | "bottom" | "left";
type PopoverAlign = "start" | "center" | "end";
type PopoverRole = "dialog" | "menu" | "listbox";

const props = withDefaults(defineProps<{
  placement?: PopoverPlacement;
  align?: PopoverAlign;
  role?: PopoverRole;
  ariaLabel?: string;
  autofocus?: boolean;
  disabled?: boolean;
}>(), { placement: "bottom", align: "start", role: "dialog", ariaLabel: "", autofocus: true, disabled: false });

const open = defineModel<boolean>({ default: false });
const emit = defineEmits<{ open: []; close: [] }>();
const contentId = useId();
const triggerId = useId();
const triggerRoot = ref<HTMLElement | null>(null);
const panel = ref<HTMLElement | null>(null);
const panelStyle = ref<Record<string, string>>({});
let previousFocus: HTMLElement | null = null;
let restoreOnClose = true;

const triggerProps = computed(() => ({
  id: triggerId,
  "aria-controls": contentId,
  "aria-expanded": open.value,
  "aria-haspopup": props.role,
  disabled: props.disabled,
  onClick: toggle,
}));

function triggerElement() {
  return triggerRoot.value?.querySelector<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])') ?? triggerRoot.value;
}

function toggle() {
  if (props.disabled) return;
  if (open.value) close(true);
  else open.value = true;
}

function close(restoreFocus = true) {
  restoreOnClose = restoreFocus;
  open.value = false;
}

function onDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node;
  if (triggerRoot.value?.contains(target) || panel.value?.contains(target)) return;
  close(false);
}

function onDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  event.preventDefault();
  close(true);
}

function updatePosition() {
  const trigger = triggerElement();
  if (!trigger || !panel.value) return;
  const triggerRect = trigger.getBoundingClientRect();
  const panelRect = panel.value.getBoundingClientRect();
  const gap = 8;
  const edge = 8;
  let top = triggerRect.bottom + gap;
  let left = triggerRect.left;

  if (props.placement === "top") top = triggerRect.top - panelRect.height - gap;
  if (props.placement === "right") left = triggerRect.right + gap;
  if (props.placement === "left") left = triggerRect.left - panelRect.width - gap;

  if (props.placement === "top" || props.placement === "bottom") {
    if (props.align === "center") left = triggerRect.left + (triggerRect.width - panelRect.width) / 2;
    if (props.align === "end") left = triggerRect.right - panelRect.width;
  } else {
    top = triggerRect.top;
    if (props.align === "center") top = triggerRect.top + (triggerRect.height - panelRect.height) / 2;
    if (props.align === "end") top = triggerRect.bottom - panelRect.height;
  }

  top = Math.min(Math.max(edge, top), window.innerHeight - panelRect.height - edge);
  left = Math.min(Math.max(edge, left), window.innerWidth - panelRect.width - edge);
  panelStyle.value = {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    "--popover-origin": originForPlacement(props.placement, props.align),
  };
}

function originForPlacement(placement: PopoverPlacement, align: PopoverAlign) {
  if (placement === "top" || placement === "bottom") {
    const horizontal = align === "start" ? "left" : align === "end" ? "right" : "center";
    return `${horizontal} ${placement === "top" ? "bottom" : "top"}`;
  }
  const vertical = align === "start" ? "top" : align === "end" ? "bottom" : "center";
  return `${placement === "left" ? "right" : "left"} ${vertical}`;
}

function addListeners() {
  document.addEventListener("pointerdown", onDocumentPointerDown);
  document.addEventListener("keydown", onDocumentKeyDown);
  window.addEventListener("resize", updatePosition);
  window.addEventListener("scroll", updatePosition, true);
}

function removeListeners() {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
  document.removeEventListener("keydown", onDocumentKeyDown);
  window.removeEventListener("resize", updatePosition);
  window.removeEventListener("scroll", updatePosition, true);
}

watch(open, async (isOpen) => {
  if (isOpen) {
    previousFocus = document.activeElement as HTMLElement | null;
    restoreOnClose = true;
    addListeners();
    emit("open");
    await nextTick();
    updatePosition();
    if (props.autofocus) {
      const autofocusTarget = panel.value?.querySelector<HTMLElement>('[autofocus], button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      (autofocusTarget ?? panel.value)?.focus();
    }
    return;
  }

  removeListeners();
  emit("close");
  if (restoreOnClose) (previousFocus ?? triggerElement())?.focus();
  previousFocus = null;
});

onBeforeUnmount(removeListeners);
</script>

<template>
  <span ref="triggerRoot" class="ui-popover__trigger">
    <slot name="trigger" :open="open" :props="triggerProps" :close="() => close(true)" />
  </span>
  <Teleport to="body">
    <Transition name="ui-popover">
      <div
        v-if="open"
        :id="contentId"
        ref="panel"
        class="ui-popover"
        :role="role"
        :aria-label="ariaLabel || undefined"
        :aria-labelledby="ariaLabel ? undefined : triggerId"
        :style="panelStyle"
        tabindex="-1"
      ><slot :close="() => close(true)" /></div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ui-popover__trigger { display: inline-flex; }
.ui-popover { position: fixed; z-index: var(--z-popover); min-width: 10rem; max-width: min(24rem, calc(100vw - 1rem)); max-height: calc(100vh - 1rem); overflow: auto; padding: var(--space-2); color: var(--content-primary); background: var(--surface-panel); border: 1px solid var(--stroke-subtle); border-radius: var(--radius-popover); box-shadow: var(--shadow-popover); transform-origin: var(--popover-origin); }
.ui-popover-enter-active { transition: opacity 180ms var(--ease-out-ui), transform 180ms var(--ease-out-ui); }
.ui-popover-leave-active { transition: opacity 120ms var(--ease-out-ui), transform 120ms var(--ease-out-ui); }
.ui-popover-enter-from, .ui-popover-leave-to { opacity: 0; transform: scale(0.97); }
@media (prefers-reduced-motion: reduce) { .ui-popover-enter-active, .ui-popover-leave-active { transition-property: opacity; } .ui-popover-enter-from, .ui-popover-leave-to { transform: none; } }
</style>
