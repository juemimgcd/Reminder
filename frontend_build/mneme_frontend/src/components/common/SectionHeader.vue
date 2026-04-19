<script setup lang="ts">
defineProps<{
  eyebrow: string;
  title: string;
  description: string;
}>();
</script>

<template>
  <header class="section-header">
    <p class="section-header__eyebrow">{{ eyebrow }}</p>
    <div>
      <h1 class="section-header__title">{{ title }}</h1>
      <p class="section-header__description">{{ description }}</p>
    </div>
  </header>
</template>
