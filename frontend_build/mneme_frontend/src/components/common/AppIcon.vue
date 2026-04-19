<script setup lang="ts">
const props = defineProps<{
  name:
    | 'vault'
    | 'spark'
    | 'upload'
    | 'chat'
    | 'memory'
    | 'insight'
    | 'sun'
    | 'moon'
    | 'arrow'
    | 'check'
    | 'alert';
}>();

const iconPaths: Record<string, string[]> = {
  vault: [
    'M5 10.5 12 6l7 4.5v7L12 22l-7-4.5Z',
    'M12 6v16',
    'M5 10.5 12 15l7-4.5',
  ],
  spark: ['M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8L12 2Z'],
  upload: ['M12 17V7', 'M8 11l4-4 4 4', 'M5 20h14'],
  chat: ['M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v6A2.5 2.5 0 0 1 16.5 15H12l-4 4v-4H7.5A2.5 2.5 0 0 1 5 12.5Z'],
  memory: ['M7 5h10', 'M7 12h10', 'M7 19h7', 'M4 5h.01', 'M4 12h.01', 'M4 19h.01'],
  insight: ['M6 18 10 12l3 3 5-7', 'M4 20h16', 'M4 4h16v16H4z'],
  sun: ['M12 4V2', 'M12 22v-2', 'M4.93 4.93 6.34 6.34', 'M17.66 17.66l1.41 1.41', 'M2 12h2', 'M20 12h2', 'M4.93 19.07l1.41-1.41', 'M17.66 6.34l1.41-1.41', 'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z'],
  moon: ['M20 14.5A7.5 7.5 0 1 1 9.5 4 6 6 0 0 0 20 14.5Z'],
  arrow: ['M5 12h14', 'M13 6l6 6-6 6'],
  check: ['M5.5 12.5 10 17l8.5-10'],
  alert: ['M12 8v5', 'M12 17h.01', 'M10.28 3.86 1.82 18a2 2 0 0 0 1.72 3h16.36a2 2 0 0 0 1.72-3L13.72 3.86a2 2 0 0 0-3.44 0Z'],
};
</script>

<template>
  <svg class="app-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path
      v-for="(path, index) in iconPaths[props.name]"
      :key="`${props.name}-${index}`"
      :d="path"
      stroke="currentColor"
      stroke-linecap="round"
      stroke-linejoin="round"
      stroke-width="1.75"
    />
  </svg>
</template>
