<script setup lang="ts">
import { onMounted } from 'vue';
import { useSessionStore } from '@/stores/session';
import { useTheme } from '@/composables/useTheme';
import { useReducedMotion } from '@/composables/useReducedMotion';

const session = useSessionStore();

useTheme();
useReducedMotion();

onMounted(() => {
  session.bootstrap();
});
</script>

<template>
  <a class="skip-link" href="#app-main">跳到主要内容</a>
  <RouterView />
</template>
