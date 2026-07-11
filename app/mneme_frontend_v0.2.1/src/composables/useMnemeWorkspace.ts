import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "./useI18n";
import { useWorkspaceLoaders, type ViewLoadResult } from "./useWorkspaceLoaders";
import { api, API_BASE_URL, IS_PREVIEW_MODE, PREVIEW_TOKEN } from "../lib/api";
import { safeStorageGet, safeStorageRemove, safeStorageSet } from "../lib/safeStorage";
import type {
  AiModelConfigData,
  AiModelProviderPreset,
  AuthMode,
  ChatQueryData,
  ChatMessageData,
  ChatSessionData,
  CompanionAnswerResult,
  DocumentListItem,
  DocumentPreviewData,
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

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function useMnemeWorkspace() {
  const { t } = useI18n();
  const token = ref(IS_PREVIEW_MODE ? PREVIEW_TOKEN : safeStorageGet(TOKEN_KEY));
  const authStatus = ref<AuthStatus>(IS_PREVIEW_MODE || token.value ? "checking" : "guest");
  const authError = ref("");
  const authMode = ref<AuthMode>("login");
  const authPending = ref(false);
  const authNotice = ref("");
  const banner = ref("");
  const isLoading = ref(false);

  const view = ref<WorkspaceView>(IS_PREVIEW_MODE ? "graph" : "dashboard");
  const workspaceCommandTab = ref<WorkspaceCommandTab>("ask");
  const user = ref<UserPublic | null>(null);
  const knowledgeBases = ref<KnowledgeBaseData[]>([]);
  const selectedKnowledgeBaseId = ref(safeStorageGet(SELECTED_KB_KEY));
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
  const documentPreview = ref<DocumentPreviewData | null>(null);
  const syncStatus = ref("");
  const syncBusyTarget = ref<"graph" | "memory" | "">("");
  const uploadInputKey = ref(0);
  const documentActionStatus = ref("");
  const graphRagQuestion = ref("");
  const graphRagStatus = ref("");
  const aiModelActionStatus = ref("");
  const chatSessionFilter = ref("");

  const loginForm = ref({ username: "", password: "" });
  const registerForm = ref({ username: "", displayName: "", password: "", confirmPassword: "" });
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
  const filteredChatSessions = computed(() => {
    const query = chatSessionFilter.value.trim().toLowerCase();
    if (!query) {
      return chatSessions.value;
    }
    return chatSessions.value.filter((session) => (session.title || "Untitled Chat").toLowerCase().includes(query));
  });

  const workspaceLoaders = useWorkspaceLoaders({
    dashboard: loadDashboardView,
    notes: loadNotesView,
    graph: loadGraphView,
    ai: loadAiView,
    settings: loadSettingsView,
  });
  const { ensureViewLoaded, viewLoadStates } = workspaceLoaders;

  async function applyRequest<T>(generation: number, request: Promise<T>, apply: (value: T) => void): Promise<boolean> {
    try {
      const value = await request;
      if (workspaceLoaders.isCurrent(generation)) apply(value);
      return true;
    } catch {
      return false;
    }
  }

  function loadResult(outcomes: boolean[], empty = false): ViewLoadResult {
    return {
      empty,
      message: outcomes.every(Boolean) ? "" : t("load.temporarilyUnavailable"),
    };
  }

  async function loadDashboardView(): Promise<ViewLoadResult> {
    return { empty: false };
  }

  async function loadNotesView(generation: number): Promise<ViewLoadResult> {
    if (!token.value || !activeKnowledgeBaseId.value) return { empty: true };
    const kbId = activeKnowledgeBaseId.value;
    const documentsRequest = applyRequest(generation, api.listDocuments(token.value, { userId: user.value?.id ?? null, knowledgeBaseId: kbId }), (data) => { documents.value = data.items; });
    const memoryRequest = applyRequest(generation, api.memoryLibrary(token.value, kbId), (data) => { memoryLibrary.value = data; });
    const outcomes = [await documentsRequest, await memoryRequest];
    return loadResult(outcomes, !selectedDocuments.value.length);
  }

  async function loadGraphView(generation: number): Promise<ViewLoadResult> {
    if (!token.value || !activeKnowledgeBaseId.value) return { empty: true };
    const kbId = activeKnowledgeBaseId.value;
    const documentsRequest = applyRequest(generation, api.listDocuments(token.value, { userId: user.value?.id ?? null, knowledgeBaseId: kbId }), (data) => { documents.value = data.items; });
    const graphRequest = applyRequest(generation, api.getKnowledgeBaseGraph(token.value, kbId, { include_memory: true, include_relationships: true }), (data) => { graphData.value = data; });
    const outcomes = [await documentsRequest, await graphRequest];
    return loadResult(outcomes, !graphData.value?.nodes.length);
  }

  async function loadAiView(generation: number): Promise<ViewLoadResult> {
    if (!token.value || !activeKnowledgeBaseId.value) return { empty: true };
    const sessionsRequest = (async () => {
      try {
        const data = await api.listChatSessions(token.value, activeKnowledgeBaseId.value);
        const sessionId = data.items[0]?.id ?? "";
        const detail = sessionId ? await api.getChatSession(token.value, sessionId) : null;
        if (workspaceLoaders.isCurrent(generation)) {
          chatSessions.value = data.items;
          activeChatSessionId.value = sessionId;
          chatMessages.value = detail?.messages ?? [];
        }
        return true;
      } catch {
        return false;
      }
    })();
    const modelsRequest = applyRequest(generation, api.listAiModelConfigs(token.value), (data) => {
      aiModelProviderPresets.value = data.provider_presets;
      aiModelConfigs.value = data.items;
      activeAiModelConfigId.value = data.default_config_id ?? data.items[0]?.id ?? "";
    });
    const outcomes = [await sessionsRequest, await modelsRequest];
    return loadResult(outcomes, !chatSessions.value.length);
  }

  async function loadSettingsView(generation: number): Promise<ViewLoadResult> {
    if (!token.value) return { empty: true };
    const modelRequest = applyRequest(generation, api.listAiModelConfigs(token.value), (data) => {
      aiModelProviderPresets.value = data.provider_presets;
      aiModelConfigs.value = data.items;
      activeAiModelConfigId.value = data.default_config_id ?? data.items[0]?.id ?? "";
    });
    const neo4jRequest = applyRequest(generation, api.neo4jHealth(), (data) => { neo4jHealth.value = data; });
    const graphRequest = activeKnowledgeBaseId.value
      ? applyRequest(generation, api.getKnowledgeBaseGraph(token.value, activeKnowledgeBaseId.value, { include_memory: true, include_relationships: true }), (data) => { graphData.value = data; })
      : Promise.resolve(true);
    const outcomes = [await modelRequest, await neo4jRequest, await graphRequest];
    return loadResult(outcomes);
  }

  async function loadWorkspace() {
    if (!token.value || !user.value) {
      return;
    }

    isLoading.value = true;
    const healthRequest = api.health().then((data) => { serviceHealth.value = data; }).catch(() => undefined);
    const readinessRequest = api.readiness().then((data) => { readiness.value = data; }).catch(() => undefined);
    try {
      const kbData = await api.listKnowledgeBases(user.value.id, token.value);
      knowledgeBases.value = kbData.items;

      if (!selectedKnowledgeBaseId.value || !kbData.items.some((item) => item.id === selectedKnowledgeBaseId.value)) {
        selectedKnowledgeBaseId.value = kbData.items[0]?.id ?? "";
      }

      if (selectedKnowledgeBaseId.value) {
        safeStorageSet(SELECTED_KB_KEY, selectedKnowledgeBaseId.value);
      }

      void ensureViewLoaded(view.value, true);

      void healthRequest;
      void readinessRequest;
    } catch {
      banner.value = t("load.temporarilyUnavailable");
    } finally {
      isLoading.value = false;
    }
  }

  async function loadKnowledgeBasePanels() {
    await ensureViewLoaded(view.value, true);
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
      void loadWorkspace();
    } catch (error) {
      authStatus.value = "guest";
      authError.value = errorMessage(error, "Session expired. Please sign in again.");
      token.value = "";
      safeStorageRemove(TOKEN_KEY);
    }
  }

  async function establishSession(accessToken: string) {
    token.value = accessToken;
    if (!safeStorageSet(TOKEN_KEY, accessToken)) {
      authNotice.value = t("auth.sessionOnly");
    }
    await authenticateWithToken();
  }

  function setAuthMode(mode: AuthMode) {
    authMode.value = mode;
    authError.value = "";
  }

  async function login() {
    authError.value = "";
    authPending.value = true;
    try {
      const auth = await api.login(loginForm.value);
      await establishSession(auth.access_token);
    } catch (error) {
      authError.value = errorMessage(error, t("auth.loginFailed"));
    } finally {
      authPending.value = false;
    }
  }

  async function register() {
    authError.value = "";
    if (registerForm.value.password !== registerForm.value.confirmPassword) {
      authError.value = t("auth.passwordMismatch");
      return;
    }

    authPending.value = true;
    try {
      await api.register({
        username: registerForm.value.username,
        display_name: registerForm.value.displayName.trim() || null,
        password: registerForm.value.password,
      });
      const auth = await api.login({
        username: registerForm.value.username,
        password: registerForm.value.password,
      });
      await establishSession(auth.access_token);
    } catch (error) {
      authError.value = errorMessage(error, t("auth.registerFailed"));
    } finally {
      authPending.value = false;
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

  async function showDocumentationStatus() {
    const result = await api.documentationStatus();
    banner.value = result.message;
  }

  async function showSupportStatus() {
    const result = await api.supportStatus();
    banner.value = result.message;
  }

  async function uploadFile(file: File | null | undefined) {
    if (!file || !token.value || !activeKnowledgeBaseId.value) {
      return;
    }

    const result = await api.uploadDocument(token.value, {
      file,
      userId: user.value?.id ?? null,
      knowledgeBaseId: activeKnowledgeBaseId.value,
    });
    banner.value = `Uploaded ${result.file_name}`;
    uploadInputKey.value += 1;
    await loadKnowledgeBasePanels();
  }

  async function indexDocument(documentId: string) {
    if (!token.value) {
      return;
    }

    const result = await api.indexDocument(documentId, token.value);
    documentActionStatus.value = result.message;
    await loadKnowledgeBasePanels();
  }

  async function deleteDocument(documentId: string) {
    if (!token.value) {
      return;
    }

    const result = await api.deleteDocument(documentId, token.value);
    documentActionStatus.value = `Deleted ${result.document_id}`;
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

  async function runGraphRag() {
    if (!token.value || !activeKnowledgeBaseId.value || !graphRagQuestion.value.trim()) {
      return;
    }

    const result = await api.graphRag(token.value, activeKnowledgeBaseId.value, {
      query: graphRagQuestion.value.trim(),
      top_k: 6,
      max_expansions: 8,
    });
    graphRagStatus.value = result.summary;
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

  async function deleteActiveChatSession() {
    if (!token.value || !activeChatSessionId.value) {
      return;
    }

    await api.deleteChatSession(token.value, activeChatSessionId.value);
    banner.value = "Chat session deleted";
    await loadChatSessions();
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

  async function testAiModelConfig(configId: string) {
    if (!token.value) {
      return;
    }

    const result = await api.testAiModelConfig(token.value, configId);
    aiModelActionStatus.value = result.message;
  }

  async function setDefaultAiModelConfig(configId: string) {
    if (!token.value) {
      return;
    }

    const updated = await api.setDefaultAiModelConfig(token.value, configId);
    aiModelConfigs.value = aiModelConfigs.value.map((config) => ({ ...config, is_default: config.id === updated.id }));
    activeAiModelConfigId.value = updated.id;
    aiModelActionStatus.value = `${updated.label} is now default`;
  }

  async function updateActiveModelContextWindow(value: number) {
    if (!token.value || !activeAiModelConfigId.value) {
      return;
    }

    const updated = await api.updateAiModelConfig(token.value, activeAiModelConfigId.value, {
      context_window: value,
    });
    aiModelConfigs.value = aiModelConfigs.value.map((config) => (config.id === updated.id ? updated : config));
    aiModelActionStatus.value = `Context window updated to ${updated.context_window.toLocaleString()}`;
  }

  async function loadDocumentPreview(documentId: string) {
    if (!token.value || !documentId) {
      documentPreview.value = null;
      return;
    }
    documentPreview.value = await api.documentPreview(token.value, documentId);
  }

  function clearDocumentPreview() {
    documentPreview.value = null;
  }

  async function rebuildActiveGraph() {
    if (!token.value || !activeKnowledgeBaseId.value) {
      return;
    }
    syncBusyTarget.value = "graph";
    try {
      const result = await api.rebuildKnowledgeBaseGraph(token.value, activeKnowledgeBaseId.value);
      syncStatus.value = `Graph rebuild ${result.status} for ${selectedKnowledgeBase.value?.name ?? activeKnowledgeBaseId.value}`;
      graphData.value = await api.getKnowledgeBaseGraph(token.value, activeKnowledgeBaseId.value, {
        include_memory: true,
        include_relationships: true,
      });
    } finally {
      syncBusyTarget.value = "";
    }
  }

  async function rebuildActiveMemory() {
    if (!token.value || !activeKnowledgeBaseId.value) {
      return;
    }
    syncBusyTarget.value = "memory";
    try {
      const result = await api.rebuildMemory(token.value, activeKnowledgeBaseId.value);
      syncStatus.value = `Memory rebuild processed ${result.processed_document_count} documents and ${result.entry_count} entries`;
      memoryLibrary.value = await api.memoryLibrary(token.value, activeKnowledgeBaseId.value);
      memoryGovernance.value = await api.memoryGovernance(token.value, activeKnowledgeBaseId.value);
    } finally {
      syncBusyTarget.value = "";
    }
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
    safeStorageSet(SELECTED_KB_KEY, id);
    workspaceLoaders.invalidate();
    void ensureViewLoaded(view.value);
  }

  function dismissBanner() {
    banner.value = "";
  }

  function logout() {
    token.value = "";
    user.value = null;
    authStatus.value = "guest";
    safeStorageRemove(TOKEN_KEY);
  }

  onMounted(() => {
    void authenticateWithToken();
  });

  watch([isAuthenticated, view, activeKnowledgeBaseId], ([authenticated]) => {
    if (authenticated) void ensureViewLoaded(view.value);
  }, { immediate: true });

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
    aiModelActionStatus,
    aiModelProviderPresets,
    askCompanion,
    askVault,
    authError,
    authMode,
    authNotice,
    authPending,
    authStatus,
    banner,
    chatQuestion,
    chatResult,
    chatMessages,
    chatSessionFilter,
    chatSessions,
    companionQuestion,
    companionResult,
    createChatSession,
    createKnowledgeBase,
    clearDocumentPreview,
    deleteActiveChatSession,
    deleteDocument,
    dismissBanner,
    documentActionStatus,
    documentPreview,
    documents,
    filteredChatSessions,
    graphData,
    graphRagQuestion,
    graphRagStatus,
    indexedDocumentCount,
    indexDocument,
    isAuthenticated,
    isLoading,
    knowledgeBaseForm,
    knowledgeBases,
    loadKnowledgeBasePanels,
    loadAiModelConfigs,
    loadChatSessions,
    loadDocumentPreview,
    login,
    loginForm,
    logout,
    memoryGovernance,
    memoryLibrary,
    neo4jHealth,
    profile,
    profileEvidence,
    readiness,
    register,
    registerForm,
    rebuildActiveGraph,
    rebuildActiveMemory,
    refreshAdvice,
    runGraphRag,
    selectedDocuments,
    selectedKnowledgeBase,
    selectedKnowledgeBaseId,
    selectKnowledgeBase,
    selectChatSession,
    sendChatMessage,
    serviceHealth,
    setAuthMode,
    setDefaultAiModelConfig,
    showDocumentationStatus,
    showSupportStatus,
    syncBusyTarget,
    syncStatus,
    testAiModelConfig,
    updateActiveModelContextWindow,
    uploadFile,
    uploadInputKey,
    user,
    view,
    viewLoadStates,
    workspaceCommandTab,
    growth,
  };
}

export type MnemeWorkspace = ReturnType<typeof useMnemeWorkspace>;
