import { computed, ref, watch } from "vue";

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = Exclude<ThemeMode, "system">;
export type Locale = "zh-CN" | "en-US";

const THEME_STORAGE_KEY = "mneme.theme";
const LOCALE_STORAGE_KEY = "mneme.locale";
const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");

function readTheme(): ThemeMode {
  const value = localStorage.getItem(THEME_STORAGE_KEY);
  return value === "light" || value === "dark" || value === "system" ? value : "system";
}

function readLocale(): Locale {
  const value = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (value === "zh-CN" || value === "en-US") return value;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

const themeMode = ref<ThemeMode>(readTheme());
const systemTheme = ref<ResolvedTheme>(colorScheme.matches ? "dark" : "light");
const locale = ref<Locale>(readLocale());
const resolvedTheme = computed<ResolvedTheme>(() =>
  themeMode.value === "system" ? systemTheme.value : themeMode.value,
);

function applyPreferences() {
  document.documentElement.dataset.theme = resolvedTheme.value;
  document.documentElement.lang = locale.value;
  document.documentElement.style.colorScheme = resolvedTheme.value;
}

function setThemeMode(value: ThemeMode) {
  themeMode.value = value;
}

function setLocale(value: Locale) {
  locale.value = value;
}

colorScheme.addEventListener("change", (event) => {
  systemTheme.value = event.matches ? "dark" : "light";
});

watch(themeMode, (value) => {
  localStorage.setItem(THEME_STORAGE_KEY, value);
  applyPreferences();
});

watch(locale, (value) => {
  localStorage.setItem(LOCALE_STORAGE_KEY, value);
  applyPreferences();
});

watch(resolvedTheme, applyPreferences);

export function initializePreferences() {
  applyPreferences();
}

export function usePreferences() {
  return {
    themeMode,
    resolvedTheme,
    locale,
    setThemeMode,
    setLocale,
  };
}
