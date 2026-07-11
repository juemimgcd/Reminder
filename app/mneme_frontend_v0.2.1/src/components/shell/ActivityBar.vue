<script setup lang="ts">
import type { Component } from "vue";
import { BrainCircuit, PanelLeft, Plus } from "@lucide/vue";
import UiIconButton from "../ui/UiIconButton.vue";

export type ActivityItem = { id: string; label: string; icon: Component };

defineProps<{ items: ActivityItem[]; activeId: string }>();
const emit = defineEmits<{ navigate: [id: string]; create: []; toggleResource: [] }>();
</script>

<template>
  <aside data-testid="activity-bar" class="activity-bar" aria-label="Primary workspace">
    <div class="activity-bar__brand" aria-label="Mneme"><BrainCircuit class="size-5" /></div>
    <nav class="activity-bar__nav">
      <UiIconButton label="Toggle resources" @click="emit('toggleResource')"><PanelLeft class="size-4" /></UiIconButton>
      <UiIconButton
        v-for="item in items"
        :key="item.id"
        :label="item.label"
        :active="activeId === item.id"
        @click="emit('navigate', item.id)"
      >
        <component :is="item.icon" class="size-[18px]" />
      </UiIconButton>
    </nav>
    <UiIconButton label="New research space" @click="emit('create')"><Plus class="size-4" /></UiIconButton>
  </aside>
</template>

<style scoped>
.activity-bar { display: flex; flex-direction: column; align-items: center; gap: 0.6rem; min-height: 100vh; padding: 0.7rem 0.45rem; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.activity-bar__brand { display: grid; place-items: center; width: 2.35rem; height: 2.35rem; margin-bottom: 0.45rem; color: var(--accent); background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent) 32%, var(--border-muted)); border-radius: 0.55rem; }
.activity-bar__nav { display: grid; flex: 1; align-content: start; gap: 0.3rem; }
</style>
