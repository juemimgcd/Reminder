import { onBeforeUnmount, ref } from "vue";

const mobileQuery = window.matchMedia("(max-width: 767px)");
const tabletQuery = window.matchMedia("(min-width: 768px) and (max-width: 1023px)");

export function useResponsiveShell() {
  type ShellMode = "desktop" | "tablet" | "mobile";
  const currentMode = (): ShellMode => mobileQuery.matches ? "mobile" : tabletQuery.matches ? "tablet" : "desktop";
  let lastMode = currentMode();
  const isMobile = ref(mobileQuery.matches);
  const isTablet = ref(tabletQuery.matches);
  const resourceOpen = ref(!(mobileQuery.matches || tabletQuery.matches));
  const contextOpen = ref(false);

  function syncBreakpoints() {
    const nextMode = currentMode();
    isMobile.value = mobileQuery.matches;
    isTablet.value = tabletQuery.matches;
    if (nextMode !== lastMode) resourceOpen.value = nextMode === "desktop";
    lastMode = nextMode;
    if (isMobile.value) contextOpen.value = false;
  }

  function toggleResource() {
    resourceOpen.value = !resourceOpen.value;
  }

  function toggleContext() {
    contextOpen.value = !contextOpen.value;
  }

  function closeOverlays() {
    if (isMobile.value || isTablet.value) {
      resourceOpen.value = false;
      contextOpen.value = false;
    }
  }

  mobileQuery.addEventListener("change", syncBreakpoints);
  tabletQuery.addEventListener("change", syncBreakpoints);
  onBeforeUnmount(() => {
    mobileQuery.removeEventListener("change", syncBreakpoints);
    tabletQuery.removeEventListener("change", syncBreakpoints);
  });

  return {
    isMobile,
    isTablet,
    resourceOpen,
    contextOpen,
    toggleResource,
    toggleContext,
    closeOverlays,
  };
}
