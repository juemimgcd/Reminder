import { ref, watchEffect } from 'vue';

const STORAGE_KEY = 'mneme-theme';
const preferred = window.matchMedia('(prefers-color-scheme: dark)');
const theme = ref<'light' | 'dark'>(
  (localStorage.getItem(STORAGE_KEY) as 'light' | 'dark' | null) ??
    (preferred.matches ? 'dark' : 'light'),
);

export function useTheme() {
  watchEffect(() => {
    document.documentElement.dataset.theme = theme.value;
  });

  const setTheme = (value: 'light' | 'dark') => {
    localStorage.setItem(STORAGE_KEY, value);
    theme.value = value;
  };

  const toggleTheme = () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
  };

  return {
    theme,
    setTheme,
    toggleTheme,
  };
}
