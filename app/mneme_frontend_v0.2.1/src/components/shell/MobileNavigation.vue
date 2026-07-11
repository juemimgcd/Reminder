<script setup lang="ts">
import type { Component } from "vue";
import { Menu } from "@lucide/vue";

type NavigationItem = { id: string; label: string; icon: Component };
defineProps<{ items: NavigationItem[]; activeId: string }>();
const emit = defineEmits<{ navigate: [id: string]; toggleResources: [] }>();
</script>

<template>
  <nav data-testid="mobile-navigation" class="mobile-navigation" aria-label="Mobile workspace">
    <button type="button" aria-label="Open resources" @click="emit('toggleResources')"><Menu class="size-[18px]" /><span>Files</span></button>
    <button
      v-for="item in items.filter((entry) => entry.id !== 'dashboard')"
      :key="item.id"
      type="button"
      :class="{ 'mobile-navigation__active': activeId === item.id }"
      :aria-label="item.label"
      :aria-pressed="activeId === item.id"
      @click="emit('navigate', item.id)"
    >
      <component :is="item.icon" class="size-[18px]" />
      <span>{{ item.label.replace('Knowledge ', '').replace('System ', '').replace('Research ', '') }}</span>
    </button>
  </nav>
</template>

<style scoped>
.mobile-navigation { position: fixed; inset: auto 0 0; z-index: 35; display: none; min-height: 3.7rem; grid-template-columns: repeat(5, minmax(0, 1fr)); padding: 0.3rem max(0.35rem, env(safe-area-inset-right)) max(0.35rem, env(safe-area-inset-bottom)); background: color-mix(in srgb, var(--bg-sidebar) 96%, transparent); border-top: 1px solid var(--border-muted); }
.mobile-navigation button { display: grid; min-width: 0; place-items: center; gap: 0.12rem; padding: 0.3rem 0.15rem; color: var(--text-tertiary); background: transparent; border: 0; border-radius: 0.4rem; font-size: 0.6rem; }
.mobile-navigation button:hover, .mobile-navigation__active { color: var(--accent); background: var(--accent-soft); }
.mobile-navigation span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 767px) { .mobile-navigation { display: grid; } }
</style>
