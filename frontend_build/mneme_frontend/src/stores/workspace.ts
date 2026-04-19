import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { api } from '@/lib/api';
import { activityFeed, dashboardMetrics } from '@/mocks/data';
import type {
  ChatExchange,
  DocumentItem,
  GrowthAdvice,
  GrowthReport,
  IndexSubmission,
  KnowledgeBase,
  MemoryLibrary,
  PersonalProfile,
} from '@/lib/types';

const RUNNING_DOCUMENT_STATUSES = ['queued', 'indexing', 'parsing', 'chunking', 'embedding', 'vector_upserting'];

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const currentUserId = ref<number | null>(null);
  const knowledgeBases = ref<KnowledgeBase[]>([]);
  const documents = ref<DocumentItem[]>([]);
  const chats = ref<ChatExchange[]>([]);
  const memoryLibrary = ref<MemoryLibrary | null>(null);
  const profile = ref<PersonalProfile | null>(null);
  const growth = ref<GrowthReport | null>(null);
  const advice = ref<GrowthAdvice | null>(null);
  const activeKnowledgeBaseId = ref<string>('');
  const loading = ref(false);
  const insightsLoading = ref(false);
  const adviceLoading = ref(false);

  const currentKnowledgeBase = computed(
    () => knowledgeBases.value.find((item) => item.id === activeKnowledgeBaseId.value) ?? null,
  );

  const filteredDocuments = computed(() =>
    activeKnowledgeBaseId.value
      ? documents.value.filter((item) => item.knowledge_base_id === activeKnowledgeBaseId.value)
      : documents.value,
  );

  function decorateKnowledgeBases(baseItems: KnowledgeBase[], documentItems: DocumentItem[]) {
    return baseItems.map((item) => {
      const relatedDocuments = documentItems.filter((doc) => doc.knowledge_base_id === item.id);
      const hasRunningTask = relatedDocuments.some((doc) => RUNNING_DOCUMENT_STATUSES.includes(doc.status));
      return {
        ...item,
        document_count: relatedDocuments.length || item.document_count,
        memory_count:
          item.id === activeKnowledgeBaseId.value && memoryLibrary.value
            ? memoryLibrary.value.timeline.length
            : item.memory_count,
        updated_at:
          relatedDocuments[0]?.created_at ?? item.updated_at ?? item.created_at ?? new Date().toISOString(),
        status: hasRunningTask ? 'indexing' : item.is_default ? 'ready' : item.status,
      };
    });
  }

  async function refreshInsights(token: string, options?: { keepAdvice?: boolean }) {
    if (!activeKnowledgeBaseId.value || !currentUserId.value) {
      throw new Error('请先选择知识库');
    }

    insightsLoading.value = true;
    try {
      const nextMemory = await api.memoryLibrary(token, activeKnowledgeBaseId.value, currentUserId.value);
      memoryLibrary.value = nextMemory;

      if (!nextMemory.timeline.length) {
        profile.value = null;
        growth.value = null;
        if (!options?.keepAdvice) {
          advice.value = null;
        }
        knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
        return;
      }

      const [nextProfile, nextGrowth] = await Promise.all([
        api.profile(token, activeKnowledgeBaseId.value),
        api.growth(token, activeKnowledgeBaseId.value),
      ]);
      profile.value = nextProfile;
      growth.value = nextGrowth;
      if (!options?.keepAdvice) {
        advice.value = null;
      }
      knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
    } finally {
      insightsLoading.value = false;
    }
  }

  async function waitForDocumentCompletion(token: string, documentId: string) {
    const targetDocument = documents.value.find((item) => item.id === documentId);
    const taskId = targetDocument?.task_id;
    if (!taskId) {
      return;
    }

    for (let attempt = 0; attempt < 20; attempt += 1) {
      await delay(3000);
      const task = await api.taskStatus(token, taskId);
      documents.value = documents.value.map((item) =>
        item.id === documentId
          ? {
              ...item,
              status:
                task.status === 'completed'
                  ? 'indexed'
                  : task.status === 'canceled'
                    ? 'uploaded'
                    : task.status,
            }
          : item,
      );
      knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);

      if (task.status === 'completed') {
        await refreshDocuments(token);
        await refreshInsights(token);
        return;
      }
      if (task.status === 'failed') {
        await refreshDocuments(token);
        return;
      }
    }
  }

  async function initialize(userId: number, token: string) {
    loading.value = true;
    try {
      currentUserId.value = userId;
      const baseItems = await api.knowledgeBases(userId, token);
      activeKnowledgeBaseId.value = activeKnowledgeBaseId.value || baseItems[0]?.id || '';
      documents.value = await api.documents(token);
      chats.value = await api.chatHistory();
      knowledgeBases.value = decorateKnowledgeBases(baseItems, documents.value);
      activeKnowledgeBaseId.value = activeKnowledgeBaseId.value || knowledgeBases.value[0]?.id || '';
      if (activeKnowledgeBaseId.value) {
        await refreshInsights(token);
      }
    } finally {
      loading.value = false;
    }
  }

  async function selectKnowledgeBase(knowledgeBaseId: string, token: string) {
    if (!currentUserId.value) {
      throw new Error('缺少当前用户上下文');
    }
    activeKnowledgeBaseId.value = knowledgeBaseId;
    await refreshInsights(token);
  }

  async function createKnowledgeBase(
    payload: { name: string; description: string },
    userId: number,
    token: string,
  ) {
    const created = await api.createKnowledgeBase(userId, payload, token);
    currentUserId.value = userId;
    knowledgeBases.value.unshift(created);
    activeKnowledgeBaseId.value = created.id;
    memoryLibrary.value = null;
    profile.value = null;
    growth.value = null;
    advice.value = null;
    return created;
  }

  async function refreshDocuments(token: string) {
    if (!currentUserId.value) {
      return;
    }
    documents.value = await api.documents(token, activeKnowledgeBaseId.value || undefined);
    knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
  }

  async function uploadDocuments(token: string, files: File[]) {
    if (!activeKnowledgeBaseId.value || !currentUserId.value) {
      throw new Error('请先选择知识库');
    }
    const uploaded = await api.uploadDocuments(token, activeKnowledgeBaseId.value, files);
    documents.value = [...uploaded, ...documents.value];
    knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
  }

  async function indexDocument(token: string, documentId: string) {
    const updated = (await api.indexDocument(token, documentId)) as IndexSubmission | DocumentItem;
    documents.value = documents.value.map((item) =>
      item.id === documentId
        ? {
            ...item,
            status: updated.status,
            task_id: 'task_id' in updated ? updated.task_id : item.task_id,
          }
        : item,
    );
    knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
    if (updated.status === 'indexed') {
      await refreshInsights(token);
      return;
    }
    void waitForDocumentCompletion(token, documentId);
  }

  async function rebuildMemory(token: string) {
    if (!activeKnowledgeBaseId.value) {
      throw new Error('请先选择知识库');
    }
    await api.rebuildMemory(token, activeKnowledgeBaseId.value);
    await refreshInsights(token);
  }

  async function generateAdvice(token: string, focusGoal?: string) {
    if (!activeKnowledgeBaseId.value) {
      throw new Error('请先选择知识库');
    }
    adviceLoading.value = true;
    try {
      advice.value = await api.advice(token, activeKnowledgeBaseId.value, focusGoal);
      return advice.value;
    } finally {
      adviceLoading.value = false;
    }
  }

  async function ask(token: string, payload: { question: string; topK: number }) {
    if (!activeKnowledgeBaseId.value || !currentUserId.value) {
      throw new Error('请先选择知识库');
    }
    const exchange = await api.chatQuery(token, {
      knowledgeBaseId: activeKnowledgeBaseId.value,
      question: payload.question,
      topK: payload.topK,
    });
    chats.value = [exchange, ...chats.value];
  }

  return {
    knowledgeBases,
    documents,
    chats,
    memoryLibrary,
    profile,
    growth,
    advice,
    activeKnowledgeBaseId,
    loading,
    insightsLoading,
    adviceLoading,
    currentKnowledgeBase,
    filteredDocuments,
    dashboardMetrics,
    activityFeed,
    initialize,
    selectKnowledgeBase,
    createKnowledgeBase,
    refreshDocuments,
    refreshInsights,
    uploadDocuments,
    indexDocument,
    rebuildMemory,
    generateAdvice,
    ask,
  };
});
