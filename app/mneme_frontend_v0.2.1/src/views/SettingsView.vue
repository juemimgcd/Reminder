<script setup lang="ts">
import { BrainCircuit, Database, Globe2, Moon, RefreshCw, Sun, Workflow } from "@lucide/vue";
import { ref } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import { useI18n } from "../composables/useI18n";
import { usePreferences, type Locale, type ThemeMode } from "../composables/usePreferences";

defineProps<{ workspace: MnemeWorkspace; healthLabel: string }>();
const preferences = usePreferences();
const { t } = useI18n();
const contextWindow = ref(32);
const themes: Array<{ value: ThemeMode; icon: unknown }> = [{ value: "system", icon: Globe2 }, { value: "light", icon: Sun }, { value: "dark", icon: Moon }];
const locales: Array<{ value: Locale; label: string }> = [{ value: "en-US", label: "English" }, { value: "zh-CN", label: "简体中文" }];
</script>

<template>
  <div data-testid="stitch-settings-layout" class="settings-layout">
    <aside class="settings-section-nav"><small>{{ t("settings.preferences") }}</small><nav><a href="#appearance">{{ t("settings.appearance") }}</a><a href="#models">{{ t("settings.models") }}</a><a href="#sync">{{ t("settings.sync") }}</a><a href="#health">{{ t("settings.health") }}</a></nav></aside>
    <section>
      <article id="appearance">
        <header><div><small>{{ t("settings.appearance") }}</small><h2>{{ t("settings.appearanceDescription") }}</h2></div></header>
        <fieldset><legend>{{ t("settings.theme") }}</legend><div class="choice-grid"><button v-for="theme in themes" :key="theme.value" :class="{ active: preferences.themeMode.value === theme.value }" :aria-label="t(`settings.theme.${theme.value}Label`)" :aria-pressed="preferences.themeMode.value === theme.value" @click="preferences.setThemeMode(theme.value)"><component :is="theme.icon" /><span>{{ t(`settings.theme.${theme.value}`) }}</span></button></div></fieldset>
        <fieldset><legend>{{ t("settings.language") }}</legend><div class="choice-grid locale-grid"><button v-for="locale in locales" :key="locale.value" :class="{ active: preferences.locale.value === locale.value }" :aria-pressed="preferences.locale.value === locale.value" @click="preferences.setLocale(locale.value)">{{ locale.label }}</button></div></fieldset>
      </article>

      <article id="models">
        <header><div><small>Intelligence</small><h2>AI Models Configuration</h2></div><BrainCircuit /></header>
        <div class="model-grid"><section v-for="config in workspace.aiModelConfigs.value" :key="config.id" :class="{ selected: config.is_default }"><div><strong>{{ config.label }}</strong><span v-if="config.is_default">Default</span></div><p>{{ config.provider }} / {{ config.model_name }}</p><small>{{ config.base_url }}</small><footer><button :aria-label="`Test ${config.label}`" @click="workspace.testAiModelConfig(config.id)">Test</button><button v-if="!config.is_default" :aria-label="`Set ${config.label} default`" @click="workspace.setDefaultAiModelConfig(config.id)">Set default</button></footer></section></div>
        <p v-if="workspace.aiModelActionStatus.value" class="status-note">{{ workspace.aiModelActionStatus.value }}</p>
        <label class="range"><span>Context window <strong>{{ (contextWindow * 1000).toLocaleString() }}</strong></span><input v-model.number="contextWindow" type="range" min="8" max="128" /><button @click="workspace.updateActiveModelContextWindow(contextWindow * 1000)">Save context window</button></label>
      </article>

      <article id="sync">
        <header><div><small>Storage</small><h2>Vault synchronization</h2></div><Workflow /></header>
        <div class="sync-actions"><button :disabled="!!workspace.syncBusyTarget.value" @click="workspace.rebuildActiveGraph"><RefreshCw :class="{ spin: workspace.syncBusyTarget.value === 'graph' }" />Rebuild Graph</button><button :disabled="!!workspace.syncBusyTarget.value" @click="workspace.rebuildActiveMemory"><Database />Rebuild Memory</button></div>
        <p v-if="workspace.syncStatus.value" class="status-note">{{ workspace.syncStatus.value }}</p>
      </article>

      <article id="health" data-testid="insights-function-grid">
        <header><div><small>System</small><h2>Knowledge Graph Health</h2></div><span class="health">{{ healthLabel }}</span></header>
        <div data-testid="insights-output-workspace" class="health-grid"><section><span>Nodes</span><strong>{{ workspace.graphData.value?.nodes.length ?? 0 }}</strong></section><section><span>Edges</span><strong>{{ workspace.graphData.value?.edges.length ?? 0 }}</strong></section><section><span>Backend</span><strong>{{ workspace.neo4jHealth.value?.backend ?? "pending" }}</strong></section><section><span>Readiness</span><strong>{{ workspace.readiness.value?.overall_status ?? "loading" }}</strong></section></div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.settings-layout { display: grid; width: min(100%, 1100px); min-width: 0; margin: 0 auto; padding: 2rem; grid-template-columns: 190px minmax(0, 1fr); gap: 2.5rem; font-family: var(--font-sans); }
.settings-layout > aside { position: sticky; top: 1rem; min-width: 0; height: fit-content; }
small { color: var(--text-tertiary); font: 0.66rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.07em; }
h2 { margin: 0.25rem 0 0; font-family: var(--font-sans); font-size: 1rem; font-weight: 650; line-height: 1.45; }
.settings-layout > aside nav { display: grid; gap: 0.15rem; margin-top: 0.75rem; }
.settings-layout > aside a { padding: 0.55rem 0.65rem; color: var(--text-secondary); border-radius: 0.35rem; text-decoration: none; }
.settings-layout > aside a:hover { color: var(--text-primary); background: var(--bg-elevated); }
.settings-layout > section { display: grid; min-width: 0; gap: 1rem; }
article { min-width: 0; scroll-margin-top: 1rem; padding: 1.25rem; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.5rem; }
article > header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-muted); }
article > header > svg { width: 1.1rem; color: var(--accent); }
fieldset { margin: 1rem 0 0; padding: 0; border: 0; }
legend { margin-bottom: 0.55rem; color: var(--text-secondary); font-size: 0.76rem; }
.choice-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.45rem; }
.choice-grid button { display: flex; min-height: 3.2rem; align-items: center; justify-content: center; gap: 0.45rem; color: var(--text-secondary); background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.choice-grid button.active { color: var(--accent); background: var(--accent-soft); border-color: var(--accent); }
.choice-grid svg { width: 1rem; }
.locale-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.model-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.65rem; margin-top: 1rem; }
.model-grid section { min-width: 0; padding: 0.9rem; background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.model-grid section.selected { border-color: var(--accent); }
.model-grid section > div { display: flex; justify-content: space-between; gap: 0.5rem; }
.model-grid section > div span { color: var(--accent); font-size: 0.7rem; }
.model-grid p, .model-grid small { overflow-wrap: anywhere; }
.model-grid p { margin: 0.6rem 0 0.15rem; color: var(--text-secondary); font-size: 0.78rem; }
.model-grid footer { display: flex; gap: 0.35rem; margin-top: 0.8rem; }
.model-grid button, .range button, .sync-actions button { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; padding: 0.45rem 0.65rem; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-muted); border-radius: 0.35rem; font-size: 0.72rem; }
.range { display: grid; gap: 0.65rem; margin-top: 1rem; }
.range span { display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 0.78rem; }
.range input { accent-color: var(--accent); }
.range button { width: fit-content; }
.sync-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.sync-actions svg { width: 1rem; }
.spin { animation: spin 800ms linear infinite; }
.status-note { margin: 0.8rem 0 0; padding: 0.7rem; color: var(--text-secondary); background: var(--bg-sidebar); border-left: 2px solid var(--accent); font-size: 0.78rem; }
.health { padding: 0.25rem 0.45rem; color: var(--success); background: color-mix(in srgb, var(--success) 10%, transparent); border-radius: 0.3rem; font-size: 0.7rem; }
.health-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 1rem; border: 1px solid var(--border-muted); }
.health-grid section { display: grid; gap: 0.35rem; padding: 0.8rem; border-right: 1px solid var(--border-muted); }
.health-grid section:last-child { border-right: 0; }
.health-grid span { color: var(--text-tertiary); font-size: 0.68rem; }
.health-grid strong { overflow: hidden; font-size: 0.85rem; text-overflow: ellipsis; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 900px) { .settings-layout { grid-template-columns: minmax(0, 1fr); gap: 1rem; padding: 1rem; } .settings-layout > aside { position: sticky; top: 0; z-index: 8; padding: 0.65rem; background: color-mix(in srgb, var(--bg-canvas) 94%, transparent); border-bottom: 1px solid var(--border-muted); backdrop-filter: blur(12px); } .settings-layout > aside > small { display: none; } .settings-layout > aside nav { display: flex; gap: 0.25rem; margin: 0; overflow-x: auto; } .settings-layout > aside a { flex: 0 0 auto; white-space: nowrap; } }
@media (max-width: 560px) { .model-grid, .health-grid, .choice-grid { grid-template-columns: 1fr; } .locale-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .health-grid section { border-right: 0; border-bottom: 1px solid var(--border-muted); } .sync-actions { flex-direction: column; } }
</style>
