<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import AppIcon from '@/components/common/AppIcon.vue';
import { useSessionStore } from '@/stores/session';
import { useWorkspaceStore } from '@/stores/workspace';
import { useTheme } from '@/composables/useTheme';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const workspace = useWorkspaceStore();
const { theme, toggleTheme } = useTheme();

const navigation = [
  { name: 'dashboard', label: '总览', icon: 'vault' as const },
  { name: 'knowledge-bases', label: '知识库', icon: 'spark' as const },
  { name: 'documents', label: '文档', icon: 'upload' as const },
  { name: 'chat', label: '问答', icon: 'chat' as const },
  { name: 'memory', label: '记忆库', icon: 'memory' as const },
  { name: 'insights', label: '洞察', icon: 'insight' as const },
];

const routeTitle = computed(() => {
  const current = navigation.find((item) => item.name === route.name);
  return current?.label ?? '工作台';
});

onMounted(async () => {
  if (session.user && session.token && !workspace.knowledgeBases.length) {
    await workspace.initialize(session.user.id, session.token);
  }
});

async function handleKnowledgeBaseChange(event: Event) {
  const nextId = (event.target as HTMLSelectElement).value;
  if (session.token) {
    await workspace.selectKnowledgeBase(nextId, session.token);
  }
}

function logout() {
  session.logout();
  router.push({ name: 'login' });
}
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar" aria-label="主导航">
      <RouterLink class="brandmark" :to="{ name: 'dashboard' }">
        <span class="brandmark__glyph">M</span>
        <span>
          <strong>Mneme</strong>
          <small>Memory Workspace</small>
        </span>
      </RouterLink>

      <nav class="app-nav">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          class="app-nav__link"
          :to="{ name: item.name }"
        >
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="app-sidebar__footer">
        <p class="app-sidebar__caption">当前产品前端默认启用 Mock 演示，接入后端时可在 `.env` 关闭。</p>
      </div>
    </aside>

    <div class="app-shell__content">
      <header class="app-topbar">
        <div>
          <p class="app-topbar__eyebrow">Mneme Workspace</p>
          <h1 class="app-topbar__title">{{ routeTitle }}</h1>
        </div>

        <div class="app-topbar__actions">
          <label class="kb-switcher">
            <span>知识库上下文</span>
            <select
              :value="workspace.activeKnowledgeBaseId"
              aria-label="切换知识库"
              @change="handleKnowledgeBaseChange"
            >
              <option
                v-for="item in workspace.knowledgeBases"
                :key="item.id"
                :value="item.id"
              >
                {{ item.name }}
              </option>
            </select>
          </label>

          <button class="ghost-button" type="button" @click="toggleTheme">
            <AppIcon :name="theme === 'dark' ? 'sun' : 'moon'" />
            <span>{{ theme === 'dark' ? '浅色' : '深色' }}</span>
          </button>

          <button class="ghost-button" type="button" @click="logout">
            <span>{{ session.user?.username }}</span>
          </button>
        </div>
      </header>

      <main id="app-main" class="app-main">
        <RouterView />
      </main>
    </div>
  </div>
</template>
