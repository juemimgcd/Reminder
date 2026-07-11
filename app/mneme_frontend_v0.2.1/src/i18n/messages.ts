import type { Locale } from "../composables/usePreferences";

export const messages: Record<Locale, Record<string, string>> = {
  "en-US": {
    "settings.appearance": "Appearance & language",
    "settings.appearanceDescription": "Choose how Mneme looks and speaks on this device.",
    "settings.theme": "Theme",
    "settings.theme.system": "System",
    "settings.theme.light": "Light",
    "settings.theme.dark": "Dark",
    "settings.theme.systemLabel": "System theme",
    "settings.theme.lightLabel": "Light theme",
    "settings.theme.darkLabel": "Dark theme",
    "settings.language": "Language",
    "settings.language.english": "English",
    "settings.language.chinese": "简体中文",
  },
  "zh-CN": {
    "settings.appearance": "外观与语言",
    "settings.appearanceDescription": "选择 Mneme 在此设备上的显示方式和界面语言。",
    "settings.theme": "主题",
    "settings.theme.system": "跟随系统",
    "settings.theme.light": "浅色",
    "settings.theme.dark": "深色",
    "settings.theme.systemLabel": "跟随系统主题",
    "settings.theme.lightLabel": "浅色主题",
    "settings.theme.darkLabel": "深色主题",
    "settings.language": "语言",
    "settings.language.english": "English",
    "settings.language.chinese": "简体中文",
  },
};
