<script setup lang="ts">
defineProps<{
  title?: string;
  eyebrow?: string;
}>();
</script>

<template>
  <section class="surface-panel">
    <header v-if="title || eyebrow" class="surface-panel__header">
      <p v-if="eyebrow" class="surface-panel__eyebrow">{{ eyebrow }}</p>
      <h2 v-if="title" class="surface-panel__title">{{ title }}</h2>
    </header>
    <div class="surface-panel__body">
      <slot />
    </div>
  </section>
</template>
