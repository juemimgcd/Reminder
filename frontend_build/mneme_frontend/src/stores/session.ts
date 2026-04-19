import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { api } from '@/lib/api';
import type { AuthPayload, User } from '@/lib/types';

const TOKEN_KEY = 'mneme-token';

export const useSessionStore = defineStore('session', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY));
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref('');

  const isAuthenticated = computed(() => Boolean(token.value));

  async function bootstrap() {
    if (!token.value || user.value) {
      return;
    }

    try {
      user.value = await api.me(token.value);
    } catch (err) {
      console.warn('Unable to load current user:', err);
      logout();
    }
  }

  async function login(payload: AuthPayload) {
    loading.value = true;
    error.value = '';
    try {
      const auth = await api.login(payload);
      token.value = auth.access_token;
      localStorage.setItem(TOKEN_KEY, auth.access_token);
      user.value = await api.me(auth.access_token);
    } catch (err) {
      error.value = err instanceof Error ? err.message : '登录失败';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function register(payload: AuthPayload) {
    loading.value = true;
    error.value = '';
    try {
      await api.register(payload);
      await login(payload);
    } catch (err) {
      error.value = err instanceof Error ? err.message : '注册失败';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem(TOKEN_KEY);
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    bootstrap,
    login,
    register,
    logout,
  };
});
