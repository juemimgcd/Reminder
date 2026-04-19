<script setup lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useSessionStore } from '@/stores/session';

const router = useRouter();
const session = useSessionStore();
const form = reactive({
  username: 'mneme_demo',
  password: '12345678',
});

async function submit() {
  await session.login(form);
  router.push({ name: 'dashboard' });
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-panel">
      <div class="auth-panel__intro">
        <p class="section-header__eyebrow">欢迎回来</p>
        <h1>登录 Mneme 工作台</h1>
        <p>默认已经为演示模式填充一组账号。若接入真实后端，可直接使用真实注册流程。</p>
      </div>

      <form class="auth-form" @submit.prevent="submit">
        <label>
          <span>用户名</span>
          <input v-model="form.username" autocomplete="username" required />
        </label>
        <label>
          <span>密码</span>
          <input
            v-model="form.password"
            autocomplete="current-password"
            required
            type="password"
          />
        </label>
        <p v-if="session.error" class="form-error" role="alert">{{ session.error }}</p>
        <button class="primary-button" type="submit" :disabled="session.loading">
          {{ session.loading ? '登录中...' : '登录' }}
        </button>
        <RouterLink class="text-link" :to="{ name: 'register' }">没有账号？去注册</RouterLink>
      </form>
    </section>
  </main>
</template>
