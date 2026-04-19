import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { api } from '@/lib/api';
import { activityFeed, dashboardMetrics } from '@/mocks/data';
import type {
  ChatExchange,
  DocumentItem,
  GrowthReport,
  IndexSubmission,
  KnowledgeBase,
  MemoryLibrary,
  PersonalProfile,
} from '@/lib/types';

export const useWorkspaceStore = defineStore('workspace', () => {
  const currentUserId = ref<number | null>(null);
  const knowledgeBases = ref<KnowledgeBase[]>([]);
  const documents = ref<DocumentItem[]>([]);
  const chats = ref<ChatExchange[]>([]);
  const memoryLibrary = ref<MemoryLibrary | null>(null);
  const profile = ref<PersonalProfile | null>(null);
  const growth = ref<GrowthReport | null>(null);
  const activeKnowledgeBaseId = ref<string>('');
  const loading = ref(false);

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
      const hasRunningTask = relatedDocuments.some((doc) =>
        ['queued', 'indexing', 'parsing', 'chunking', 'embedding', 'vector_upserting'].includes(doc.status),
      );
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

  async function initialize(userId: number, token: string) {
    loading.value = true;
    try {
      currentUserId.value = userId;
      const baseItems = await api.knowledgeBases(userId, token);
      activeKnowledgeBaseId.value = activeKnowledgeBaseId.value || baseItems[0]?.id || '';
      documents.value = await api.documents(userId, token);
      chats.value = await api.chatHistory();
      knowledgeBases.value = decorateKnowledgeBases(baseItems, documents.value);
      activeKnowledgeBaseId.value = activeKnowledgeBaseId.value || knowledgeBases.value[0]?.id || '';
      if (activeKnowledgeBaseId.value) {
        memoryLibrary.value = await api.memoryLibrary(token, activeKnowledgeBaseId.value, userId);
        profile.value = await api.profile(token, activeKnowledgeBaseId.value);
        growth.value = await api.growth(token, activeKnowledgeBaseId.value);
        knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
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
    memoryLibrary.value = await api.memoryLibrary(token, knowledgeBaseId, currentUserId.value);
    profile.value = await api.profile(token, knowledgeBaseId);
    growth.value = await api.growth(token, knowledgeBaseId);
    knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
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
    return created;
  }

  async function refreshDocuments(token: string) {
    if (!currentUserId.value) {
      return;
    }
    documents.value = await api.documents(currentUserId.value, token, activeKnowledgeBaseId.value || undefined);
    knowledgeBases.value = decorateKnowledgeBases(knowledgeBases.value, documents.value);
  }

  async function uploadDocuments(token: string, files: File[]) {
    if (!activeKnowledgeBaseId.value || !currentUserId.value) {
      throw new Error('请先选择知识库');
    }
    const uploaded = await api.uploadDocuments(token, currentUserId.value, activeKnowledgeBaseId.value, files);
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
  }

  async function ask(token: string, payload: { question: string; topK: number }) {
    if (!activeKnowledgeBaseId.value || !currentUserId.value) {
      throw new Error('请先选择知识库');
    }
    const exchange = await api.chatQuery(token, {
      userId: currentUserId.value,
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
    activeKnowledgeBaseId,
    loading,
    currentKnowledgeBase,
    filteredDocuments,
    dashboardMetrics,
    activityFeed,
    initialize,
    selectKnowledgeBase,
    createKnowledgeBase,
    refreshDocuments,
    uploadDocuments,
    indexDocument,
    ask,
  };
});
