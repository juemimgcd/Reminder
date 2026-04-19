<script setup lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useSessionStore } from '@/stores/session';

const router = useRouter();
const session = useSessionStore();
const form = reactive({
  username: '',
  password: '',
});

async function submit() {
  await session.register(form);
  router.push({ name: 'dashboard' });
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-panel">
      <div class="auth-panel__intro">
        <p class="section-header__eyebrow">开始沉淀</p>
        <h1>创建你的记忆型知识库入口</h1>
        <p>注册后，后端会自动创建默认知识库。前端会立即把你带到工作台视图。</p>
      </div>

      <form class="auth-form" @submit.prevent="submit">
        <label>
          <span>用户名</span>
          <input v-model="form.username" autocomplete="username" minlength="3" required />
        </label>
        <label>
          <span>密码</span>
          <input
            v-model="form.password"
            autocomplete="new-password"
            minlength="8"
            required
            type="password"
          />
        </label>
        <p v-if="session.error" class="form-error" role="alert">{{ session.error }}</p>
        <button class="primary-button" type="submit" :disabled="session.loading">
          {{ session.loading ? '创建中...' : '创建账号' }}
        </button>
        <RouterLink class="text-link" :to="{ name: 'login' }">已有账号？去登录</RouterLink>
      </form>
    </section>
  </main>
</template>
