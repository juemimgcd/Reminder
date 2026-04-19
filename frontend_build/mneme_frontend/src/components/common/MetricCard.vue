<script setup lang="ts">
defineProps<{
  label: string;
  value: string;
  change: string;
  tone: 'teal' | 'amber' | 'indigo' | 'coral';
}>();
</script>

<template>
  <article class="metric-card" :data-tone="tone">
    <p class="metric-card__label">{{ label }}</p>
    <strong class="metric-card__value">{{ value }}</strong>
    <span class="metric-card__change">{{ change }}</span>
  </article>
</template>
