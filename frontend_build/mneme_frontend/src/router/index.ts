import { createRouter, createWebHistory } from 'vue-router';
import { useSessionStore } from '@/stores/session';
import LandingView from '@/views/LandingView.vue';
import LoginView from '@/views/LoginView.vue';
import RegisterView from '@/views/RegisterView.vue';
import WorkspaceDashboardView from '@/views/WorkspaceDashboardView.vue';
import KnowledgeBasesView from '@/views/KnowledgeBasesView.vue';
import DocumentsView from '@/views/DocumentsView.vue';
import ChatView from '@/views/ChatView.vue';
import MemoryView from '@/views/MemoryView.vue';
import InsightsView from '@/views/InsightsView.vue';
import AppShell from '@/components/app/AppShell.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
    },
    {
      path: '/app',
      component: AppShell,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: WorkspaceDashboardView,
        },
        {
          path: 'knowledge-bases',
          name: 'knowledge-bases',
          component: KnowledgeBasesView,
        },
        {
          path: 'documents',
          name: 'documents',
          component: DocumentsView,
        },
        {
          path: 'chat',
          name: 'chat',
          component: ChatView,
        },
        {
          path: 'memory',
          name: 'memory',
          component: MemoryView,
        },
        {
          path: 'insights',
          name: 'insights',
          component: InsightsView,
        },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const session = useSessionStore();

  if (session.token && !session.user) {
    await session.bootstrap();
  }

  if (to.meta.requiresAuth && !session.isAuthenticated) {
    return { name: 'login' };
  }

  if ((to.name === 'login' || to.name === 'register') && session.isAuthenticated) {
    return { name: 'dashboard' };
  }

  return true;
});

export default router;
