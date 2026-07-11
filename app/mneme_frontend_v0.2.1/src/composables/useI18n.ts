import { messages } from "../i18n/messages";
import { usePreferences } from "./usePreferences";

type TranslationParams = Record<string, string | number>;

export function useI18n() {
  const { locale } = usePreferences();

  function t(key: string, params: TranslationParams = {}) {
    const template = messages[locale.value][key] ?? messages["en-US"][key] ?? key;
    return Object.entries(params).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
      template,
    );
  }

  function formatDate(value: string | number | Date) {
    return new Intl.DateTimeFormat(locale.value, { dateStyle: "medium" }).format(new Date(value));
  }

  function formatNumber(value: number) {
    return new Intl.NumberFormat(locale.value).format(value);
  }

  return { locale, t, formatDate, formatNumber };
}
