<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue';

defineProps<{
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__icon">
      <AppIcon name="spark" />
    </div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
  </div>
</template>
