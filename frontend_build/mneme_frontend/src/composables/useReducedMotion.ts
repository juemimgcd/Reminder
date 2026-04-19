import { onMounted, onUnmounted, ref } from 'vue';

export function useReducedMotion() {
  const reducedMotion = ref(false);
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  const sync = () => {
    reducedMotion.value = mediaQuery.matches;
    document.documentElement.classList.toggle('reduced-motion', mediaQuery.matches);
  };

  onMounted(() => {
    sync();
    mediaQuery.addEventListener('change', sync);
  });

  onUnmounted(() => {
    mediaQuery.removeEventListener('change', sync);
  });

  return { reducedMotion };
}
