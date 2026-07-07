import { computed, onMounted, ref } from "vue";
import { api, API_BASE_URL, IS_PREVIEW_MODE, PREVIEW_TOKEN } from "../lib/api";
import type {
  AiModelConfigData,
  AiModelProviderPreset,
  ChatQueryData,
  ChatMessageData,
  ChatSessionData,
  CompanionAnswerResult,
  DocumentListItem,
  EvidenceProfileData,
  GraphData,
  GrowthAdviceResult,
  GrowthReportResult,
  KnowledgeBaseAnalyticsReportData,
  KnowledgeBaseData,
  MemoryGovernanceData,
  MemoryLibraryData,
  Neo4jHealthData,
  PersonalProfileResult,
  ProductionReadinessReportData,
  ServiceHealthData,
  UserPublic,
  WorkspaceView,
} from "../types";

const TOKEN_KEY = "mneme.access_token";
const SELECTED_KB_KEY = "mneme.selected_knowledge_base_id";

export type AuthStatus = "checking" | "guest" | "authenticated";
export type WorkspaceCommandTab = "create" | "upload" | "ask" | "companion";

function storageGet(key: string) {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(key) ?? "";
}

function storageSet(key: string, value: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(key, value);
  }
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function useMnemeWorkspace() {
  const token = ref(IS_PREVIEW_MODE ? PREVIEW_TOKEN : storageGet(TOKEN_KEY));
  const authStatus = ref<AuthStatus>(IS_PREVIEW_MODE || token.value ? "checking" : "guest");
  const authError = ref("");
  const banner = ref("");
  const isLoading = ref(false);

  const view = ref<WorkspaceView>("graph");
  const workspaceCommandTab = ref<WorkspaceCommandTab>("ask");
  const user = ref<UserPublic | null>(null);
  const knowledgeBases = ref<KnowledgeBaseData[]>([]);
  const selectedKnowledgeBaseId = ref(storageGet(SELECTED_KB_KEY));
  const documents = ref<DocumentListItem[]>([]);

  const serviceHealth = ref<ServiceHealthData | null>(null);
  const neo4jHealth = ref<Neo4jHealthData | null>(null);
  const readiness = ref<ProductionReadinessReportData | null>(null);
  const graphData = ref<GraphData | null>(null);
  const memoryLibrary = ref<MemoryLibraryData | null>(null);
  const memoryGovernance = ref<MemoryGovernanceData | null>(null);
  const profile = ref<PersonalProfileResult | null>(null);
  const profileEvidence = ref<EvidenceProfileData | null>(null);
  const growth = ref<GrowthReportResult | null>(null);
  const analytics = ref<KnowledgeBaseAnalyticsReportData | null>(null);
  const advice = ref<GrowthAdviceResult | null>(null);
  const chatResult = ref<ChatQueryData | null>(null);
  const companionResult = ref<CompanionAnswerResult | null>(null);
  const chatSessions = ref<ChatSessionData[]>([]);
  const activeChatSessionId = ref("");
  const chatMessages = ref<ChatMessageData[]>([]);
  const aiModelConfigs = ref<AiModelConfigData[]>([]);
  const aiModelProviderPresets = ref<AiModelProviderPreset[]>([]);
  const activeAiModelConfigId = ref("");

  const loginForm = ref({ username: "", password: "" });
  const knowledgeBaseForm = ref({ name: "", description: "" });
  const chatQuestion = ref("How should I review this vault?");
  const companionQuestion = ref("What should I focus on next?");
  const adviceGoal = ref("Improve retrieval quality");

  const selectedKnowledgeBase = computed(
    () => knowledgeBases.value.find((item) => item.id === selectedKnowledgeBaseId.value) ?? knowledgeBases.value[0] ?? null,
  );
  const selectedDocuments = computed(() =>
    documents.value.filter((item) => !selectedKnowledgeBase.value || item.knowledge_base_id === selectedKnowledgeBase.value.id),
  );
  const indexedDocumentCount = computed(() => selectedDocuments.value.filter((item) => item.status === "indexed").length);
  const activeKnowledgeBaseId = computed(() => selectedKnowledgeBase.value?.id ?? "");
  const isAuthenticated = computed(() => authStatus.value === "authenticated");

  async function loadWorkspace() {
    if (!token.value || !user.value) {
      return;
    }

    isLoading.value = true;
    try {
      const [healthData, neo4jData, readinessData, kbData] = await Promise.all([
        api.health(),
        api.neo4jHealth(),
        api.readiness(),
        api.listKnowledgeBases(user.value.id, token.value),
      ]);

      serviceHealth.value = healthData;
      neo4jHealth.value = neo4jData;
      readiness.value = readinessData;
      knowledgeBases.value = kbData.items;

      if (!selectedKnowledgeBaseId.value || !kbData.items.some((item) => item.id === selectedKnowledgeBaseId.value)) {
        selectedKnowledgeBaseId.value = kbData.items[0]?.id ?? "";
      }

      if (selectedKnowledgeBaseId.value) {
        storageSet(SELECTED_KB_KEY, selectedKnowledgeBaseId.value);
      }

      await loadKnowledgeBasePanels();
      await loadAiModelConfigs();
    } catch (error) {
      banner.value = errorMessage(error, "Unable to load workspace.");
    } finally {
      isLoading.value = false;
    }
  }

  async function loadKnowledgeBasePanels() {
    if (!token.value || !activeKnowledgeBaseId.value) {
      return;
    }

    const kbId = activeKnowledgeBaseId.value;
    const [documentData, graph, memory, governance, profileData, evidenceData, growthData, analyticsData, adviceData] =
      await Promise.all([
        api.listDocuments(token.value, { userId: user.value?.id ?? null, knowledgeBaseId: kbId }),
        api.getKnowledgeBaseGraph(token.value, kbId, { include_memory: true, include_relationships: true }),
        api.memoryLibrary(token.value, kbId),
        api.memoryGovernance(token.value, kbId),
        api.profile(token.value, kbId),
        api.profileEvidence(token.value, kbId, 30),
        api.growth(token.value, kbId, 30),
        api.analytics(token.value, kbId),
        api.advice(token.value, kbId, adviceGoal.value),
      ]);

    documents.value = documentData.items;
    graphData.value = graph;
    memoryLibrary.value = memory;
    memoryGovernance.value = governance;
    profile.value = profileData;
    profileEvidence.value = evidenceData;
    growth.value = growthData;
    analytics.value = analyticsData;
    advice.value = adviceData;
    await loadChatSessions();
  }

  async function authenticateWithToken() {
    if (!token.value) {
      authStatus.value = "guest";
      return;
    }

    authStatus.value = "checking";
    try {
      user.value = await api.me(token.value);
      authStatus.value = "authenticated";
      await loadWorkspace();
    } catch (error) {
      authStatus.value = "guest";
      authError.value = errorMessage(error, "Session expired. Please sign in again.");
      token.value = "";
    }
  }

  async function login() {
    authError.value = "";
    isLoading.value = true;
    try {
      const auth = await api.login(loginForm.value);
      token.value = auth.access_token;
      storageSet(TOKEN_KEY, token.value);
      await authenticateWithToken();
    } catch (error) {
      authError.value = errorMessage(error, "Unable to sign in.");
    } finally {
      isLoading.value = false;
    }
  }

  async function createKnowledgeBase() {
    if (!user.value || !token.value || !knowledgeBaseForm.value.name.trim()) {
      return;
    }

    const created = await api.createKnowledgeBase(user.value.id, token.value, {
      name: knowledgeBaseForm.value.name.trim(),
      description: knowledgeBaseForm.value.description.trim() || null,
    });
    knowledgeBases.value = [...knowledgeBases.value, created];
    selectedKnowledgeBaseId.value = created.id;
    knowledgeBaseForm.value = { name: "", description: "" };
    banner.value = `Created ${created.name}`;
    await loadKnowledgeBasePanels();
  }

  async function askVault() {
    if (!token.value || !activeKnowledgeBaseId.value || !chatQuestion.value.trim()) {
      return;
    }

    chatResult.value = await api.chatQuery(token.value, {
      question: chatQuestion.value.trim(),
      knowledge_base_id: activeKnowledgeBaseId.value,
      top_k: 4,
    });
  }

  async function loadChatSessions() {
    if (!token.value || !activeKnowledgeBaseId.value) {
      chatSessions.value = [];
      chatMessages.value = [];
      activeChatSessionId.value = "";
      return;
    }
    const data = await api.listChatSessions(token.value, activeKnowledgeBaseId.value);
    chatSessions.value = data.items;
    if (!data.items.length) {
      chatMessages.value = [];
      activeChatSessionId.value = "";
      return;
    }
    if (!activeChatSessionId.value || !data.items.some((item) => item.id === activeChatSessionId.value)) {
      activeChatSessionId.value = data.items[0].id;
    }
    await selectChatSession(activeChatSessionId.value);
  }

  async function selectChatSession(sessionId: string) {
    if (!token.value || !sessionId) {
      return;
    }
    activeChatSessionId.value = sessionId;
    const detail = await api.getChatSession(token.value, sessionId);
    chatMessages.value = detail.messages;
  }

  async function createChatSession() {
    if (!token.value || !activeKnowledgeBaseId.value) {
      return;
    }
    const session = await api.createChatSession(token.value, {
      knowledge_base_id: activeKnowledgeBaseId.value,
      title: "New Chat",
    });
    chatSessions.value = [session, ...chatSessions.value];
    activeChatSessionId.value = session.id;
    chatMessages.value = [];
  }

  async function sendChatMessage() {
    if (!token.value || !activeKnowledgeBaseId.value || !chatQuestion.value.trim()) {
      return;
    }
    if (!activeChatSessionId.value) {
      await createChatSession();
    }
    if (!activeChatSessionId.value) {
      return;
    }
    const question = chatQuestion.value.trim();
    chatQuestion.value = "";
    const detail = await api.sendChatSessionMessage(token.value, activeChatSessionId.value, {
      question,
      top_k: 4,
    });
    chatMessages.value = [...chatMessages.value, ...detail.messages];
    chatSessions.value = chatSessions.value.map((session) => (session.id === detail.session.id ? detail.session : session));
  }

  async function loadAiModelConfigs() {
    if (!token.value) {
      return;
    }
    const data = await api.listAiModelConfigs(token.value);
    aiModelProviderPresets.value = data.provider_presets;
    aiModelConfigs.value = data.items;
    activeAiModelConfigId.value = data.default_config_id ?? data.items[0]?.id ?? "";
  }

  async function askCompanion() {
    if (!token.value || !activeKnowledgeBaseId.value || !companionQuestion.value.trim()) {
      return;
    }

    companionResult.value = await api.companionReply(token.value, activeKnowledgeBaseId.value, {
      question: companionQuestion.value.trim(),
      top_k: 4,
    });
  }

  async function refreshAdvice() {
    if (!token.value || !activeKnowledgeBaseId.value) {
      return;
    }
    advice.value = await api.advice(token.value, activeKnowledgeBaseId.value, adviceGoal.value);
  }

  function selectKnowledgeBase(id: string) {
    selectedKnowledgeBaseId.value = id;
    storageSet(SELECTED_KB_KEY, id);
    void loadKnowledgeBasePanels();
  }

  function logout() {
    token.value = "";
    user.value = null;
    authStatus.value = "guest";
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(TOKEN_KEY);
    }
  }

  onMounted(() => {
    void authenticateWithToken();
  });

  return {
    API_BASE_URL,
    IS_PREVIEW_MODE,
    activeKnowledgeBaseId,
    activeAiModelConfigId,
    activeChatSessionId,
    advice,
    adviceGoal,
    analytics,
    aiModelConfigs,
    aiModelProviderPresets,
    askCompanion,
    askVault,
    authError,
    authStatus,
    banner,
    chatQuestion,
    chatResult,
    chatMessages,
    chatSessions,
    companionQuestion,
    companionResult,
    createChatSession,
    createKnowledgeBase,
    documents,
    graphData,
    indexedDocumentCount,
    isAuthenticated,
    isLoading,
    knowledgeBaseForm,
    knowledgeBases,
    loadKnowledgeBasePanels,
    loadAiModelConfigs,
    loadChatSessions,
    login,
    loginForm,
    logout,
    memoryGovernance,
    memoryLibrary,
    neo4jHealth,
    profile,
    profileEvidence,
    readiness,
    refreshAdvice,
    selectedDocuments,
    selectedKnowledgeBase,
    selectedKnowledgeBaseId,
    selectKnowledgeBase,
    selectChatSession,
    sendChatMessage,
    serviceHealth,
    user,
    view,
    workspaceCommandTab,
    growth,
  };
}
