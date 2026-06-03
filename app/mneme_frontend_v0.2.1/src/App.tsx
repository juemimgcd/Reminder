import {
  AlertCircle,
  Bot,
  Brain,
  Database,
  FolderGit2,
  GitBranch,
  Loader2,
  LogOut,
  MessageSquareText,
  Plus,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  UserRound,
} from "lucide-react";
import { Suspense, lazy, type FormEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";

import AuthScreen from "./components/AuthScreen";
import { ApiError, api, API_BASE_URL } from "./lib/api";
import { cn } from "./lib/utils";
import type {
  CompanionAnswerResult,
  DocumentListItem,
  EvidenceProfileData,
  GraphData,
  GraphNodeData,
  GraphProjectionRebuildData,
  GraphRagDecisionData,
  GrowthAdviceResult,
  GrowthReportResult,
  KnowledgeBaseAnalyticsReportData,
  KnowledgeBaseData,
  MemoryGovernanceData,
  MemoryLibraryData,
  MemoryRebuildData,
  Neo4jHealthData,
  PersonalProfileResult,
  ProductionReadinessReportData,
  TaskRecordData,
  UserPublic,
  WorkspaceView,
  ChatQueryData,
} from "./types";

type AuthStatus = "checking" | "guest" | "authed";
type BannerTone = "success" | "error" | "info";
type GraphScope = "user" | "knowledge_base" | "document";

interface BannerState {
  tone: BannerTone;
  text: string;
}

const TOKEN_KEY = "mneme.access_token";
const SELECTED_KB_KEY = "mneme.selected_kb";
const ACTIVE_TASK_STATUSES = new Set(["queued", "running", "pending", "created", "retrying"]);
const VIEW_CACHE_TARGETS = ["graph", "memory", "insights"] as const;

const VIEW_ITEMS: Array<{ id: WorkspaceView; label: string; icon: typeof FolderGit2; hint: string }> = [
  { id: "workspace", label: "Workspace", icon: FolderGit2, hint: "知识库与文档" },
  { id: "chat", label: "Chat", icon: MessageSquareText, hint: "问答与陪伴" },
  { id: "graph", label: "Graph", icon: GitBranch, hint: "结构与 GraphRAG" },
  { id: "memory", label: "Memory", icon: Database, hint: "记忆库与治理" },
  { id: "insights", label: "Insights", icon: Brain, hint: "画像、成长、分析" },
];

const KnowledgeGraphCanvas = lazy(() => import("./components/KnowledgeGraphCanvas"));
const ReactMarkdown = lazy(() => import("react-markdown"));

function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatBytes(bytes?: number | null) {
  if (!bytes || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();
  if (["indexed", "completed", "success", "healthy", "running", "pass", "ok"].includes(normalized)) {
    return "border-emerald-400/30 bg-emerald-500/10 text-emerald-300";
  }
  if (["failed", "error", "dead", "fail"].includes(normalized)) {
    return "border-red-400/30 bg-red-500/10 text-red-300";
  }
  if (["queued", "pending", "running", "indexing", "parsing", "chunking", "embedding", "vector_upserting", "warn"].includes(normalized)) {
    return "border-secondary/30 bg-secondary/10 text-secondary";
  }
  return "border-outline-variant bg-surface-container text-text-muted";
}

function getErrorMessage(error: unknown, fallback = "请求失败，请稍后再试。") {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}

function CardSection({
  title,
  description,
  actions,
  children,
  compact = false,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  compact?: boolean;
}) {
  return (
    <section className="overflow-hidden rounded-md border border-outline-variant bg-surface shadow-[0_22px_70px_rgba(0,0,0,0.2)]">
      <div
        className={cn(
          "flex items-start justify-between gap-4 border-b border-outline-variant bg-surface-container-low",
          compact ? "px-4 py-3.5" : "px-5 py-4",
        )}
      >
        <div>
          <h2 className="text-sm font-semibold text-on-surface">{title}</h2>
          {description ? <p className="mt-1 text-xs leading-6 text-text-muted">{description}</p> : null}
        </div>
        {actions}
      </div>
      <div className={compact ? "px-4 py-4" : "px-5 py-5"}>{children}</div>
    </section>
  );
}

function MetricCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-md border border-outline-variant bg-surface-container-low px-4 py-4">
      <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">{label}</div>
      <div className="mt-3 text-2xl font-semibold text-on-surface">{value}</div>
      {hint ? <div className="mt-2 text-xs text-text-muted">{hint}</div> : null}
    </div>
  );
}

function StatusPill({ text }: { text: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider",
        statusClass(text),
      )}
    >
      {text}
    </span>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-md border border-dashed border-outline-variant bg-surface-container-low px-6 py-10 text-center">
      <div className="text-sm font-medium text-on-surface">{title}</div>
      <div className="mx-auto mt-2 max-w-xl text-xs leading-6 text-text-muted">{text}</div>
    </div>
  );
}

function PanelSkeleton({ text = "正在加载面板" }: { text?: string }) {
  return (
    <div className="flex min-h-[220px] items-center justify-center rounded-md border border-dashed border-outline-variant bg-surface-container-low text-sm text-text-muted">
      <div className="inline-flex items-center gap-3">
        <Loader2 className="h-4 w-4 animate-spin" />
        {text}
      </div>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) ?? "");
  const [authStatus, setAuthStatus] = useState<AuthStatus>(() => (localStorage.getItem(TOKEN_KEY) ? "checking" : "guest"));
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [busyKeys, setBusyKeys] = useState<Record<string, boolean>>({});

  const [view, setView] = useState<WorkspaceView>("workspace");
  const [user, setUser] = useState<UserPublic | null>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseData[]>([]);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState(() => localStorage.getItem(SELECTED_KB_KEY) ?? "");
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [taskMap, setTaskMap] = useState<Record<string, TaskRecordData>>({});

  const [serviceHealth, setServiceHealth] = useState<{ service: string; status: string } | null>(null);
  const [neo4jHealth, setNeo4jHealth] = useState<Neo4jHealthData | null>(null);
  const [readiness, setReadiness] = useState<ProductionReadinessReportData | null>(null);

  const [knowledgeBaseForm, setKnowledgeBaseForm] = useState({ name: "", description: "" });
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const [chatQuestion, setChatQuestion] = useState("");
  const [chatTopK, setChatTopK] = useState(4);
  const [chatResult, setChatResult] = useState<ChatQueryData | null>(null);

  const [companionQuestion, setCompanionQuestion] = useState("");
  const [companionTopK, setCompanionTopK] = useState(4);
  const [companionResult, setCompanionResult] = useState<CompanionAnswerResult | null>(null);

  const [graphScope, setGraphScope] = useState<GraphScope>("knowledge_base");
  const [graphIncludeMemory, setGraphIncludeMemory] = useState(true);
  const [graphIncludeRelationships, setGraphIncludeRelationships] = useState(true);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedGraphNode, setSelectedGraphNode] = useState<GraphNodeData | null>(null);
  const [graphRebuildResult, setGraphRebuildResult] = useState<GraphProjectionRebuildData | null>(null);
  const [graphPlannerQuery, setGraphPlannerQuery] = useState("");
  const [graphPlannerResult, setGraphPlannerResult] = useState<GraphRagDecisionData | null>(null);

  const [memoryLibrary, setMemoryLibrary] = useState<MemoryLibraryData | null>(null);
  const [memoryGovernance, setMemoryGovernance] = useState<MemoryGovernanceData | null>(null);
  const [documentMemoryLibrary, setDocumentMemoryLibrary] = useState<MemoryLibraryData | null>(null);
  const [memoryRebuildResult, setMemoryRebuildResult] = useState<MemoryRebuildData | null>(null);

  const [recentDays, setRecentDays] = useState(30);
  const [profile, setProfile] = useState<PersonalProfileResult | null>(null);
  const [profileEvidence, setProfileEvidence] = useState<EvidenceProfileData | null>(null);
  const [growth, setGrowth] = useState<GrowthReportResult | null>(null);
  const [analytics, setAnalytics] = useState<KnowledgeBaseAnalyticsReportData | null>(null);
  const [adviceGoal, setAdviceGoal] = useState("");
  const [advice, setAdvice] = useState<GrowthAdviceResult | null>(null);

  const selectedKnowledgeBase = useMemo(
    () => knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId) ?? null,
    [knowledgeBases, selectedKnowledgeBaseId],
  );
  const selectedDocument = useMemo(
    () => documents.find((item) => item.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId],
  );

  const activeTaskIds = useMemo(
    () => Object.values(taskMap).filter((task) => ACTIVE_TASK_STATUSES.has(task.status.toLowerCase())).map((task) => task.id),
    [taskMap],
  );
  const indexedDocumentCount = useMemo(
    () => documents.filter((item) => item.status.toLowerCase() === "indexed").length,
    [documents],
  );
  const currentViewItem = useMemo(() => VIEW_ITEMS.find((item) => item.id === view) ?? VIEW_ITEMS[0], [view]);
  const CurrentViewIcon = currentViewItem.icon;

  const documentTaskMap = useMemo(() => {
    const entries: Record<string, TaskRecordData> = {};
    Object.values(taskMap).forEach((task) => {
      entries[task.target_id] = task;
    });
    return entries;
  }, [taskMap]);

  const graphLoadKey = useMemo(
    () =>
      [
        token || "-",
        graphScope,
        selectedKnowledgeBaseId || "-",
        selectedDocumentId || "-",
        graphIncludeMemory ? "memory" : "no-memory",
        graphIncludeRelationships ? "relationships" : "no-relationships",
      ].join("|"),
    [graphIncludeMemory, graphIncludeRelationships, graphScope, selectedDocumentId, selectedKnowledgeBaseId, token],
  );
  const memoryLoadKey = useMemo(
    () => [token || "-", selectedKnowledgeBaseId || "-", selectedDocumentId || "-"].join("|"),
    [selectedDocumentId, selectedKnowledgeBaseId, token],
  );
  const insightsLoadKey = useMemo(
    () => [token || "-", selectedKnowledgeBaseId || "-", recentDays].join("|"),
    [recentDays, selectedKnowledgeBaseId, token],
  );

  const graphLoadKeyRef = useRef("");
  const memoryLoadKeyRef = useRef("");
  const insightsLoadKeyRef = useRef("");

  const setBusy = useCallback((key: string, next: boolean) => {
    setBusyKeys((current) => ({ ...current, [key]: next }));
  }, []);

  const isBusy = useCallback((key: string) => Boolean(busyKeys[key]), [busyKeys]);

  const showBanner = useCallback((tone: BannerTone, text: string) => {
    setBanner({ tone, text });
  }, []);

  const invalidateViewCache = useCallback((targets: Array<(typeof VIEW_CACHE_TARGETS)[number]> = [...VIEW_CACHE_TARGETS]) => {
    if (targets.includes("graph")) {
      graphLoadKeyRef.current = "";
    }
    if (targets.includes("memory")) {
      memoryLoadKeyRef.current = "";
    }
    if (targets.includes("insights")) {
      insightsLoadKeyRef.current = "";
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    invalidateViewCache();
    setToken("");
    setAuthStatus("guest");
    setUser(null);
    setKnowledgeBases([]);
    setDocuments([]);
    setTaskMap({});
    setSelectedKnowledgeBaseId("");
    setSelectedDocumentId("");
    setChatResult(null);
    setCompanionResult(null);
    setGraphData(null);
    setMemoryLibrary(null);
    setMemoryGovernance(null);
    setProfile(null);
    setProfileEvidence(null);
    setGrowth(null);
    setAnalytics(null);
    setAdvice(null);
  }, [invalidateViewCache]);

  const handleRequestError = useCallback(
    (error: unknown, fallback: string) => {
      if (error instanceof ApiError && error.status === 401) {
        logout();
        showBanner("error", "登录状态已失效，请重新登录。");
        return;
      }
      showBanner("error", getErrorMessage(error, fallback));
    },
    [logout, showBanner],
  );

  const refreshOperationalHealth = useCallback(async () => {
    try {
      const [healthData, neo4jData, readinessData] = await Promise.all([
        api.health(),
        api.neo4jHealth(),
        api.readiness(),
      ]);
      setServiceHealth(healthData);
      setNeo4jHealth(neo4jData);
      setReadiness(readinessData);
    } catch (error) {
      showBanner("error", getErrorMessage(error, "健康检查加载失败。"));
    }
  }, [showBanner]);

  const refreshDocuments = useCallback(
    async (nextToken: string, currentUser: UserPublic, knowledgeBaseId: string) => {
      const list = await api.listDocuments(nextToken, {
        userId: currentUser.id,
        knowledgeBaseId,
      });
      setDocuments(list.items);
      setSelectedDocumentId((current) => {
        if (current && list.items.some((item) => item.id === current)) {
          return current;
        }
        return list.items[0]?.id ?? "";
      });
      return list.items;
    },
    [],
  );

  const loadSession = useCallback(
    async (nextToken: string) => {
      try {
        const currentUser = await api.me(nextToken);
        const knowledgeBaseList = await api.listKnowledgeBases(currentUser.id, nextToken);
        const items = knowledgeBaseList.items;
        const persistedId = localStorage.getItem(SELECTED_KB_KEY) ?? "";
        const resolvedKnowledgeBaseId =
          items.find((item) => item.id === persistedId)?.id ||
          items[0]?.id ||
          "";

        setUser(currentUser);
        setKnowledgeBases(items);
        setSelectedKnowledgeBaseId(resolvedKnowledgeBaseId);

        if (!resolvedKnowledgeBaseId) {
          setDocuments([]);
          setSelectedDocumentId("");
        }

        setAuthStatus("authed");
      } catch (error) {
        logout();
        handleRequestError(error, "加载会话失败。");
      }
    },
    [handleRequestError, logout],
  );

  useEffect(() => {
    if (authStatus !== "authed") {
      return;
    }
    void refreshOperationalHealth();
  }, [authStatus, refreshOperationalHealth]);

  useEffect(() => {
    if (token) {
      setAuthStatus("checking");
      void loadSession(token);
    }
  }, [loadSession, token]);

  useEffect(() => {
    if (selectedKnowledgeBaseId) {
      localStorage.setItem(SELECTED_KB_KEY, selectedKnowledgeBaseId);
    } else {
      localStorage.removeItem(SELECTED_KB_KEY);
    }
  }, [selectedKnowledgeBaseId]);

  useEffect(() => {
    if (authStatus !== "authed" || !token || !user || !selectedKnowledgeBaseId) {
      return;
    }

    void refreshDocuments(token, user, selectedKnowledgeBaseId).catch((error) => {
      handleRequestError(error, "文档列表刷新失败。");
    });
  }, [authStatus, token, user, selectedKnowledgeBaseId, refreshDocuments, handleRequestError]);

  useEffect(() => {
    if (!activeTaskIds.length || !token) {
      return;
    }

    const tick = async () => {
      try {
        const updates = await Promise.all(activeTaskIds.map((taskId) => api.getTask(taskId, token)));
        setTaskMap((current) => {
          const next = { ...current };
          updates.forEach((task) => {
            next[task.id] = task;
          });
          return next;
        });

        if (user && selectedKnowledgeBaseId) {
          const finished = updates.some((task) => !ACTIVE_TASK_STATUSES.has(task.status.toLowerCase()));
          if (finished) {
            invalidateViewCache();
            await refreshDocuments(token, user, selectedKnowledgeBaseId);
          }
        }
      } catch (error) {
        handleRequestError(error, "任务状态刷新失败。");
      }
    };

    void tick();
    const timer = window.setInterval(() => {
      void tick();
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [activeTaskIds, handleRequestError, invalidateViewCache, refreshDocuments, selectedKnowledgeBaseId, token, user]);

  useEffect(() => {
    if (!graphData) {
      setSelectedGraphNode(null);
      return;
    }

    const node =
      graphData.nodes.find((item) => item.id === selectedGraphNode?.id) ||
      graphData.nodes.find((item) => item.id === graphData.root_node_id) ||
      graphData.nodes[0] ||
      null;
    setSelectedGraphNode(node);
  }, [graphData, selectedGraphNode?.id]);

  const loadGraph = useCallback(async (options?: { force?: boolean }) => {
    if (!token) {
      return;
    }
    if (!options?.force && graphData && graphLoadKeyRef.current === graphLoadKey) {
      return;
    }

    setBusy("graph", true);
    try {
      const baseParams = {
        include_memory: graphIncludeMemory,
        include_relationships: graphIncludeRelationships,
        min_shared_memory_count: 2,
        min_relationship_score: 0.35,
        max_related_edges: graphScope === "document" ? 24 : 80,
      };

      const nextGraph =
        graphScope === "user"
          ? await api.getUserGraph(token, baseParams)
          : graphScope === "document"
            ? selectedDocumentId
              ? await api.getDocumentGraph(token, selectedDocumentId, {
                  ...baseParams,
                  relationship_scope: "knowledge_base",
                })
              : null
            : selectedKnowledgeBaseId
              ? await api.getKnowledgeBaseGraph(token, selectedKnowledgeBaseId, baseParams)
              : null;

      setGraphData(nextGraph);
      graphLoadKeyRef.current = graphLoadKey;
    } catch (error) {
      handleRequestError(error, "图谱加载失败。");
    } finally {
      setBusy("graph", false);
    }
  }, [
    graphIncludeMemory,
    graphIncludeRelationships,
    graphLoadKey,
    graphData,
    graphScope,
    handleRequestError,
    selectedDocumentId,
    selectedKnowledgeBaseId,
    token,
    setBusy,
  ]);

  const loadMemoryView = useCallback(async (options?: { force?: boolean }) => {
    if (!token || !selectedKnowledgeBaseId) {
      return;
    }
    if (!options?.force && memoryLibrary && memoryGovernance && memoryLoadKeyRef.current === memoryLoadKey) {
      return;
    }

    setBusy("memory", true);
    try {
      const [libraryData, governanceData, docLibrary] = await Promise.all([
        api.memoryLibrary(token, selectedKnowledgeBaseId),
        api.memoryGovernance(token, selectedKnowledgeBaseId),
        selectedDocumentId ? api.documentMemory(token, selectedDocumentId) : Promise.resolve(null),
      ]);
      setMemoryLibrary(libraryData);
      setMemoryGovernance(governanceData);
      setDocumentMemoryLibrary(docLibrary);
      memoryLoadKeyRef.current = memoryLoadKey;
    } catch (error) {
      handleRequestError(error, "记忆视图加载失败。");
    } finally {
      setBusy("memory", false);
    }
  }, [handleRequestError, memoryGovernance, memoryLibrary, memoryLoadKey, selectedDocumentId, selectedKnowledgeBaseId, token, setBusy]);

  const loadInsightsView = useCallback(async (options?: { force?: boolean }) => {
    if (!token || !selectedKnowledgeBaseId) {
      return;
    }
    if (!options?.force && profile && profileEvidence && growth && analytics && insightsLoadKeyRef.current === insightsLoadKey) {
      return;
    }

    setBusy("insights", true);
    try {
      const [profileData, evidenceData, growthData, analyticsData] = await Promise.all([
        api.profile(token, selectedKnowledgeBaseId),
        api.profileEvidence(token, selectedKnowledgeBaseId, recentDays),
        api.growth(token, selectedKnowledgeBaseId, recentDays),
        api.analytics(token, selectedKnowledgeBaseId),
      ]);
      setProfile(profileData);
      setProfileEvidence(evidenceData);
      setGrowth(growthData);
      setAnalytics(analyticsData);
      insightsLoadKeyRef.current = insightsLoadKey;
    } catch (error) {
      handleRequestError(error, "洞察视图加载失败。");
    } finally {
      setBusy("insights", false);
    }
  }, [analytics, growth, handleRequestError, insightsLoadKey, profile, profileEvidence, recentDays, selectedKnowledgeBaseId, token, setBusy]);

  useEffect(() => {
    if (authStatus !== "authed") {
      return;
    }
    if (view === "graph") {
      void loadGraph();
    }
    if (view === "memory") {
      void loadMemoryView();
    }
    if (view === "insights") {
      void loadInsightsView();
    }
  }, [authStatus, loadGraph, loadInsightsView, loadMemoryView, view]);

  const handleAuthSubmit = useCallback(
    async (payload: { mode: "login" | "register"; username: string; password: string; displayName?: string }) => {
      setAuthLoading(true);
      setAuthError(null);
      try {
        if (payload.mode === "register") {
          await api.register({
            username: payload.username,
            password: payload.password,
            display_name: payload.displayName ?? null,
          });
        }

        const auth = await api.login({
          username: payload.username,
          password: payload.password,
        });

        invalidateViewCache();
        setAuthStatus("checking");
        localStorage.setItem(TOKEN_KEY, auth.access_token);
        setToken(auth.access_token);
        showBanner("success", payload.mode === "register" ? "注册成功，已进入工作台。" : "登录成功。");
      } catch (error) {
        setAuthError(getErrorMessage(error, payload.mode === "register" ? "注册失败。" : "登录失败。"));
      } finally {
        setAuthLoading(false);
      }
    },
    [invalidateViewCache, showBanner],
  );

  const handleCreateKnowledgeBase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !user || !knowledgeBaseForm.name.trim()) {
      return;
    }

    setBusy("create-kb", true);
    try {
      const created = await api.createKnowledgeBase(user.id, token, {
        name: knowledgeBaseForm.name.trim(),
        description: knowledgeBaseForm.description.trim() || null,
      });
      invalidateViewCache();
      const nextKnowledgeBases = [...knowledgeBases, created].sort((left, right) => left.created_at.localeCompare(right.created_at));
      setKnowledgeBases(nextKnowledgeBases);
      setSelectedKnowledgeBaseId(created.id);
      setKnowledgeBaseForm({ name: "", description: "" });
      showBanner("success", `知识库 ${created.name} 已创建。`);
    } catch (error) {
      handleRequestError(error, "创建知识库失败。");
    } finally {
      setBusy("create-kb", false);
    }
  };

  const handleDeleteKnowledgeBase = async (knowledgeBase: KnowledgeBaseData) => {
    if (!token || !user) {
      return;
    }
    if (!window.confirm(`确认删除知识库“${knowledgeBase.name}”？`)) {
      return;
    }

    setBusy(`delete-kb-${knowledgeBase.id}`, true);
    try {
      await api.deleteKnowledgeBase(user.id, knowledgeBase.id, token);
      invalidateViewCache();
      const nextKnowledgeBases = knowledgeBases.filter((item) => item.id !== knowledgeBase.id);
      setKnowledgeBases(nextKnowledgeBases);
      const fallbackId = nextKnowledgeBases[0]?.id ?? "";
      setSelectedKnowledgeBaseId(fallbackId);
      showBanner("success", `知识库 ${knowledgeBase.name} 已删除。`);
    } catch (error) {
      handleRequestError(error, "删除知识库失败。");
    } finally {
      setBusy(`delete-kb-${knowledgeBase.id}`, false);
    }
  };

  const handleUploadDocument = async () => {
    if (!token || !user || !uploadFile || !selectedKnowledgeBaseId) {
      return;
    }

    setBusy("upload", true);
    try {
      await api.uploadDocument(token, {
        file: uploadFile,
        userId: user.id,
        knowledgeBaseId: selectedKnowledgeBaseId,
      });
      invalidateViewCache();
      setUploadFile(null);
      await refreshDocuments(token, user, selectedKnowledgeBaseId);
      showBanner("success", `文档 ${uploadFile.name} 上传成功。`);
    } catch (error) {
      handleRequestError(error, "文档上传失败。");
    } finally {
      setBusy("upload", false);
    }
  };

  const handleIndexDocument = async (documentId: string) => {
    if (!token) {
      return;
    }

    setBusy(`index-${documentId}`, true);
    try {
      const task = await api.indexDocument(documentId, token);
      invalidateViewCache();
      setTaskMap((current) => ({
        ...current,
        [task.task_id]: {
          id: task.task_id,
          task_type: "document_index",
          target_id: task.document_id,
          status: task.status,
          progress_stage: null,
          queue_name: null,
          celery_task_id: null,
          attempt_count: 0,
          max_attempts: 3,
          result_summary: task.message,
          error_message: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      }));
      showBanner("success", `已提交索引任务 ${task.task_id}。`);
    } catch (error) {
      handleRequestError(error, "索引任务提交失败。");
    } finally {
      setBusy(`index-${documentId}`, false);
    }
  };

  const handleDeleteDocument = async (document: DocumentListItem) => {
    if (!token || !user || !selectedKnowledgeBaseId) {
      return;
    }
    if (!window.confirm(`确认删除文档“${document.file_name}”？`)) {
      return;
    }

    setBusy(`delete-doc-${document.id}`, true);
    try {
      await api.deleteDocument(document.id, token);
      invalidateViewCache();
      await refreshDocuments(token, user, selectedKnowledgeBaseId);
      showBanner("success", `文档 ${document.file_name} 已删除。`);
    } catch (error) {
      handleRequestError(error, "删除文档失败。");
    } finally {
      setBusy(`delete-doc-${document.id}`, false);
    }
  };

  const handleCancelTask = async (taskId: string) => {
    if (!token) {
      return;
    }

    setBusy(`task-cancel-${taskId}`, true);
    try {
      const result = await api.cancelTask(taskId, token);
      const task = await api.getTask(taskId, token);
      invalidateViewCache();
      setTaskMap((current) => ({ ...current, [task.id]: task }));
      showBanner("info", result.message);
    } catch (error) {
      handleRequestError(error, "取消任务失败。");
    } finally {
      setBusy(`task-cancel-${taskId}`, false);
    }
  };

  const handleRetryTask = async (taskId: string) => {
    if (!token) {
      return;
    }

    setBusy(`task-retry-${taskId}`, true);
    try {
      const result = await api.retryTask(taskId, token);
      const task = await api.getTask(taskId, token);
      invalidateViewCache();
      setTaskMap((current) => ({ ...current, [task.id]: task }));
      showBanner("success", result.message);
    } catch (error) {
      handleRequestError(error, "重试任务失败。");
    } finally {
      setBusy(`task-retry-${taskId}`, false);
    }
  };

  const handleChatSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !selectedKnowledgeBaseId || !chatQuestion.trim()) {
      return;
    }

    setBusy("chat", true);
    try {
      const result = await api.chatQuery(token, {
        question: chatQuestion.trim(),
        knowledge_base_id: selectedKnowledgeBaseId,
        top_k: chatTopK,
      });
      setChatResult(result);
    } catch (error) {
      handleRequestError(error, "问答请求失败。");
    } finally {
      setBusy("chat", false);
    }
  };

  const handleCompanionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !selectedKnowledgeBaseId || !companionQuestion.trim()) {
      return;
    }

    setBusy("companion", true);
    try {
      const result = await api.companionReply(token, selectedKnowledgeBaseId, {
        question: companionQuestion.trim(),
        top_k: companionTopK,
      });
      setCompanionResult(result);
    } catch (error) {
      handleRequestError(error, "陪伴回复生成失败。");
    } finally {
      setBusy("companion", false);
    }
  };

  const handleGraphPlannerSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !selectedKnowledgeBaseId || !graphPlannerQuery.trim()) {
      return;
    }

    setBusy("graph-rag", true);
    try {
      const result = await api.graphRag(token, selectedKnowledgeBaseId, {
        query: graphPlannerQuery.trim(),
      });
      setGraphPlannerResult(result);
    } catch (error) {
      handleRequestError(error, "GraphRAG 规划请求失败。");
    } finally {
      setBusy("graph-rag", false);
    }
  };

  const handleGraphRebuild = async () => {
    if (!token) {
      return;
    }

    setBusy("graph-rebuild", true);
    try {
      const result =
        graphScope === "user"
          ? await api.rebuildUserGraph(token)
          : selectedKnowledgeBaseId
            ? await api.rebuildKnowledgeBaseGraph(token, selectedKnowledgeBaseId)
            : null;
      setGraphRebuildResult(result);
      invalidateViewCache(["graph"]);
      showBanner("success", "图投影回填完成。");
      await loadGraph({ force: true });
    } catch (error) {
      handleRequestError(error, "图投影回填失败。");
    } finally {
      setBusy("graph-rebuild", false);
    }
  };

  const handleMemoryRebuild = async () => {
    if (!token || !selectedKnowledgeBaseId) {
      return;
    }

    setBusy("memory-rebuild", true);
    try {
      const result = await api.rebuildMemory(token, selectedKnowledgeBaseId);
      setMemoryRebuildResult(result);
      invalidateViewCache(["memory", "insights", "graph"]);
      showBanner("success", "记忆库重建完成。");
      await loadMemoryView({ force: true });
    } catch (error) {
      handleRequestError(error, "记忆库重建失败。");
    } finally {
      setBusy("memory-rebuild", false);
    }
  };

  const handleAdviceSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !selectedKnowledgeBaseId) {
      return;
    }

    setBusy("advice", true);
    try {
      const result = await api.advice(token, selectedKnowledgeBaseId, adviceGoal.trim() || null);
      setAdvice(result);
    } catch (error) {
      handleRequestError(error, "成长建议生成失败。");
    } finally {
      setBusy("advice", false);
    }
  };

  const renderWorkspace = () => {
    const indexedCount = documents.filter((item) => item.status === "indexed").length;
    const activeCount = documents.filter((item) =>
      ["queued", "indexing", "parsing", "chunking", "embedding", "vector_upserting"].includes(item.status),
    ).length;

    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard label="Knowledge Base" value={selectedKnowledgeBase?.name ?? "None"} hint={selectedKnowledgeBase?.description ?? "当前未选择知识库"} />
          <MetricCard label="Documents" value={documents.length} hint={`${indexedCount} 已完成索引`} />
          <MetricCard label="Active Tasks" value={activeCount} hint="索引中的文档状态会自动轮询刷新" />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <CardSection
            title="Documents"
            description="上传、索引和删除都从这里开始。选中的知识库会作为目标作用域。"
            actions={
              <button
                type="button"
                onClick={() => token && user && selectedKnowledgeBaseId && void refreshDocuments(token, user, selectedKnowledgeBaseId)}
                className="inline-flex items-center gap-2 border border-slate-300 px-3 py-2 text-xs text-slate-600 transition hover:bg-slate-50"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>
            }
          >
            <div className="space-y-4">
              <div className="flex flex-col gap-3 border border-dashed border-slate-300 bg-slate-50 p-4 lg:flex-row lg:items-center">
                <div className="flex-1 text-sm text-slate-600">
                  {uploadFile ? `待上传：${uploadFile.name} · ${formatBytes(uploadFile.size)}` : "选择一个文档后上传到当前知识库。"}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <label className="inline-flex h-10 cursor-pointer items-center gap-2 border border-slate-300 bg-white px-4 text-sm text-slate-700 transition hover:border-slate-950">
                    <Upload className="h-4 w-4" />
                    选择文件
                    <input
                      type="file"
                      className="hidden"
                      onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={!uploadFile || isBusy("upload")}
                    onClick={() => void handleUploadDocument()}
                    className="inline-flex h-10 items-center gap-2 bg-slate-950 px-4 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {isBusy("upload") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                    上传
                  </button>
                </div>
              </div>

              {documents.length ? (
                <div className="overflow-x-auto border border-slate-200">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-[0.18em] text-slate-500">
                      <tr>
                        <th className="px-4 py-3">Document</th>
                        <th className="px-4 py-3">Type</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Created</th>
                        <th className="px-4 py-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {documents.map((document) => {
                        const task = documentTaskMap[document.id];
                        return (
                          <tr
                            key={document.id}
                            className={cn(
                              "align-top transition hover:bg-slate-50",
                              selectedDocumentId === document.id && "bg-indigo-50/60",
                            )}
                          >
                            <td className="px-4 py-4">
                              <button
                                type="button"
                                className="block text-left"
                                onClick={() => {
                                  setSelectedDocumentId(document.id);
                                  setView("graph");
                                  setGraphScope("document");
                                }}
                              >
                                <div className="font-medium text-slate-900">{document.file_name}</div>
                                <div className="mt-1 text-xs text-slate-500">{document.id}</div>
                              </button>
                            </td>
                            <td className="px-4 py-4 text-slate-600">{document.file_type}</td>
                            <td className="px-4 py-4">
                              <div className="space-y-2">
                                <StatusPill text={document.status} />
                                {task ? <div className="text-xs text-slate-500">Task {task.status}</div> : null}
                              </div>
                            </td>
                            <td className="px-4 py-4 text-slate-600">{formatDate(document.created_at)}</td>
                            <td className="px-4 py-4">
                              <div className="flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  disabled={isBusy(`index-${document.id}`)}
                                  onClick={() => void handleIndexDocument(document.id)}
                                  className="border border-slate-300 px-3 py-2 text-xs text-slate-700 transition hover:border-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {isBusy(`index-${document.id}`) ? "提交中" : "索引"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedDocumentId(document.id);
                                    setView("memory");
                                  }}
                                  className="border border-slate-300 px-3 py-2 text-xs text-slate-700 transition hover:border-slate-950"
                                >
                                  记忆
                                </button>
                                <button
                                  type="button"
                                  disabled={isBusy(`delete-doc-${document.id}`)}
                                  onClick={() => void handleDeleteDocument(document)}
                                  className="inline-flex items-center gap-2 border border-rose-200 px-3 py-2 text-xs text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                  删除
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="当前知识库还没有文档" text="先上传文档，再进入索引、问答和分析流程。" />
              )}
            </div>
          </CardSection>

          <div className="space-y-6">
            <CardSection title="Index Tasks" description="这里只显示前端当前追踪过的索引任务。">
              {Object.values(taskMap).length ? (
                <div className="space-y-3">
                  {Object.values(taskMap)
                    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
                    .map((task) => (
                      <div key={task.id} className="border border-slate-200 px-4 py-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-medium text-slate-900">{task.id}</div>
                            <div className="mt-1 text-xs text-slate-500">Target {task.target_id}</div>
                          </div>
                          <StatusPill text={task.status} />
                        </div>
                        <div className="mt-3 text-xs leading-6 text-slate-600">
                          <div>Stage {task.progress_stage || "-"}</div>
                          <div>Updated {formatDate(task.updated_at)}</div>
                          {task.error_message ? <div className="text-rose-600">{task.error_message}</div> : null}
                        </div>
                        <div className="mt-3 flex gap-2">
                          <button
                            type="button"
                            disabled={!ACTIVE_TASK_STATUSES.has(task.status.toLowerCase()) || isBusy(`task-cancel-${task.id}`)}
                            onClick={() => void handleCancelTask(task.id)}
                            className="border border-slate-300 px-3 py-2 text-xs text-slate-700 transition hover:border-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            取消
                          </button>
                          <button
                            type="button"
                            disabled={isBusy(`task-retry-${task.id}`)}
                            onClick={() => void handleRetryTask(task.id)}
                            className="border border-slate-300 px-3 py-2 text-xs text-slate-700 transition hover:border-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            重试
                          </button>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <EmptyState title="还没有任务" text="提交文档索引后，任务状态会出现在这里。" />
              )}
            </CardSection>

            <CardSection title="System" description="后端健康、Neo4j 可用性和生产就绪建议。">
              <div className="space-y-4 text-sm">
                <div className="flex items-center justify-between border border-slate-200 px-4 py-3">
                  <div>
                    <div className="font-medium text-slate-900">API</div>
                    <div className="text-xs text-slate-500">{serviceHealth?.service ?? "agentic-rag"}</div>
                  </div>
                  <StatusPill text={serviceHealth?.status ?? "unknown"} />
                </div>
                <div className="flex items-center justify-between border border-slate-200 px-4 py-3">
                  <div>
                    <div className="font-medium text-slate-900">Neo4j</div>
                    <div className="text-xs text-slate-500">{neo4jHealth?.uri ?? "-"}</div>
                  </div>
                  <StatusPill text={neo4jHealth?.ok ? "ok" : "warn"} />
                </div>
                <div className="border border-slate-200 px-4 py-4">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-slate-900">Readiness</div>
                    <StatusPill text={readiness?.overall_status ?? "unknown"} />
                  </div>
                  <div className="mt-3 space-y-2 text-xs leading-6 text-slate-600">
                    {readiness?.checks.slice(0, 4).map((check) => (
                      <div key={check.name} className="flex items-start justify-between gap-4 border-t border-slate-100 pt-2 first:border-none first:pt-0">
                        <span>{check.name}</span>
                        <span className="text-slate-400">{check.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardSection>
          </div>
        </div>
      </div>
    );
  };

  const renderChat = () => {
    return (
      <div className="grid gap-6 xl:grid-cols-2">
        <CardSection title="Knowledge Base Q&A" description="直接走 `/kb/chat/query`，返回答案、引用、置信度和路由决策。">
          <form className="space-y-4" onSubmit={handleChatSubmit}>
            <textarea
              value={chatQuestion}
              onChange={(event) => setChatQuestion(event.target.value)}
              className="min-h-[160px] w-full border border-slate-300 px-4 py-3 text-sm leading-7 outline-none transition focus:border-slate-950"
              placeholder="输入要在当前知识库里检索和回答的问题"
            />
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                Top K
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={chatTopK}
                  onChange={(event) => setChatTopK(Number(event.target.value) || 4)}
                  className="h-10 w-20 border border-slate-300 px-3 outline-none focus:border-slate-950"
                />
              </label>
              <button
                type="submit"
                disabled={isBusy("chat") || !selectedKnowledgeBaseId}
                className="inline-flex h-10 items-center gap-2 bg-slate-950 px-4 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {isBusy("chat") ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
                发送问答
              </button>
            </div>
          </form>

          {chatResult ? (
            <div className="mt-5 space-y-5">
              <div className="border border-slate-200 bg-slate-50 px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Answer</div>
                  <StatusPill text={chatResult.confidence} />
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{chatResult.answer}</p>
                {chatResult.route ? (
                  <div className="mt-4 border-t border-slate-200 pt-4 text-xs leading-6 text-slate-500">
                    <div>Type {chatResult.route.query_type}</div>
                    <div>Pipeline {chatResult.route.target_pipeline}</div>
                    <div>{chatResult.route.reason}</div>
                  </div>
                ) : null}
              </div>

              <div className="space-y-3">
                {chatResult.citations.map((citation) => (
                  <div key={`${citation.source_id}-${citation.chunk_id}`} className="border border-slate-200 px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium text-slate-900">
                        {citation.source_id} · {citation.document_id}
                      </div>
                      <StatusPill text={citation.validation_status ?? "quote"} />
                    </div>
                    <p className="mt-3 text-sm leading-7 text-slate-700">{citation.quote}</p>
                    <p className="mt-2 text-xs leading-6 text-slate-500">{citation.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <EmptyState title="还没有问答结果" text="提交问题后，这里会显示回答、证据引用和路由判断。" />
            </div>
          )}
        </CardSection>

        <CardSection title="Companion Reply" description="基于检索结果、画像与成长摘要生成更像产品输出的陪伴式回复。">
          <form className="space-y-4" onSubmit={handleCompanionSubmit}>
            <textarea
              value={companionQuestion}
              onChange={(event) => setCompanionQuestion(event.target.value)}
              className="min-h-[160px] w-full border border-slate-300 px-4 py-3 text-sm leading-7 outline-none transition focus:border-slate-950"
              placeholder="输入一个更偏行动、状态或情绪支持的问题"
            />
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                Top K
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={companionTopK}
                  onChange={(event) => setCompanionTopK(Number(event.target.value) || 4)}
                  className="h-10 w-20 border border-slate-300 px-3 outline-none focus:border-slate-950"
                />
              </label>
              <button
                type="submit"
                disabled={isBusy("companion") || !selectedKnowledgeBaseId}
                className="inline-flex h-10 items-center gap-2 bg-slate-950 px-4 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {isBusy("companion") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                生成陪伴回复
              </button>
            </div>
          </form>

          {companionResult ? (
            <div className="mt-5 space-y-4">
              <div className="border border-slate-200 bg-slate-50 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Companion Message</div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{companionResult.companion_message}</p>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="border border-slate-200 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Direct Answer</div>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{companionResult.direct_answer}</p>
                </div>
                <div className="border border-slate-200 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Next Step</div>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{companionResult.next_step_hint}</p>
                </div>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="border border-slate-200 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Profile Snapshot</div>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{companionResult.profile_snapshot}</p>
                </div>
                <div className="border border-slate-200 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Growth Snapshot</div>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{companionResult.growth_snapshot}</p>
                </div>
              </div>
              <div className="border border-slate-200 px-4 py-4">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Follow-up Questions</div>
                <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-700">
                  {companionResult.follow_up_questions.map((question) => (
                    <li key={question}>• {question}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <EmptyState title="还没有陪伴回复" text="这里会组合问答、画像与成长分析，输出更完整的陪伴式反馈。" />
            </div>
          )}
        </CardSection>
      </div>
    );
  };

  const renderGraph = () => {
    return (
      <div className="space-y-6">
        <CardSection
          title="Graph Controls"
          description="支持 user / knowledge_base / document 三种图范围，也可以直接触发图投影回填与 GraphRAG 决策。"
          actions={
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void loadGraph({ force: true })}
                disabled={isBusy("graph")}
                className="inline-flex items-center gap-2 border border-slate-300 px-3 py-2 text-xs text-slate-700 transition hover:border-slate-950"
              >
                {isBusy("graph") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                刷新图谱
              </button>
              <button
                type="button"
                onClick={() => void handleGraphRebuild()}
                disabled={isBusy("graph-rebuild")}
                className="inline-flex items-center gap-2 bg-slate-950 px-3 py-2 text-xs text-white transition hover:bg-slate-800"
              >
                {isBusy("graph-rebuild") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                回填图投影
              </button>
            </div>
          }
        >
          <div className="grid gap-4 lg:grid-cols-[0.9fr_1.6fr]">
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
                <label className="space-y-2 text-sm">
                  <span className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Graph Scope</span>
                  <select
                    value={graphScope}
                    onChange={(event) => setGraphScope(event.target.value as GraphScope)}
                    className="h-11 w-full border border-slate-300 px-3 outline-none focus:border-slate-950"
                  >
                    <option value="knowledge_base">Knowledge Base</option>
                    <option value="user">User</option>
                    <option value="document">Document</option>
                  </select>
                </label>

                {graphScope === "document" ? (
                  <label className="space-y-2 text-sm">
                    <span className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Document</span>
                    <select
                      value={selectedDocumentId}
                      onChange={(event) => setSelectedDocumentId(event.target.value)}
                      className="h-11 w-full border border-slate-300 px-3 outline-none focus:border-slate-950"
                    >
                      {documents.map((document) => (
                        <option key={document.id} value={document.id}>
                          {document.file_name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}

                <div className="space-y-3 border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={graphIncludeMemory}
                      onChange={(event) => setGraphIncludeMemory(event.target.checked)}
                    />
                    Include memory nodes
                  </label>
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={graphIncludeRelationships}
                      onChange={(event) => setGraphIncludeRelationships(event.target.checked)}
                    />
                    Include related edges
                  </label>
                </div>
              </div>

              {selectedGraphNode ? (
                <div className="border border-slate-200 px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium text-slate-900">{selectedGraphNode.label}</div>
                    <StatusPill text={selectedGraphNode.node_type} />
                  </div>
                  <div className="mt-3 space-y-2 text-xs leading-6 text-slate-600">
                    <div>Entity {selectedGraphNode.entity_id}</div>
                    <div>Depth {selectedGraphNode.depth}</div>
                    {Object.entries(selectedGraphNode.metadata).slice(0, 6).map(([key, value]) => (
                      <div key={key} className="break-words">
                        {key} {String(value)}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState title="还没有选中节点" text="加载图谱后，点击任意节点查看它的业务信息。" />
              )}

              {graphRebuildResult ? (
                <div className="border border-slate-200 bg-slate-50 px-4 py-4 text-xs leading-6 text-slate-600">
                  <div className="font-medium text-slate-900">最近一次回填</div>
                  <div className="mt-2">Scope {graphRebuildResult.scope}</div>
                  <div>Documents {graphRebuildResult.document_count}</div>
                  <div>Memory Entries {graphRebuildResult.memory_entry_count}</div>
                </div>
              ) : null}
            </div>

            <div className="h-[540px] min-h-[540px]">
              <Suspense fallback={<PanelSkeleton text="正在加载图谱组件" />}>
                <KnowledgeGraphCanvas
                  data={graphData}
                  selectedNodeId={selectedGraphNode?.id ?? null}
                  onSelectNode={setSelectedGraphNode}
                />
              </Suspense>
            </div>
          </div>
        </CardSection>

        <CardSection title="GraphRAG Planner" description="调用 `/graph/knowledge-bases/{id}/rag` 查看图谱对当前问题是否有帮助。">
          <form className="space-y-4" onSubmit={handleGraphPlannerSubmit}>
            <textarea
              value={graphPlannerQuery}
              onChange={(event) => setGraphPlannerQuery(event.target.value)}
              className="min-h-[120px] w-full border border-slate-300 px-4 py-3 text-sm leading-7 outline-none transition focus:border-slate-950"
              placeholder="输入一个问题，让系统判断图谱是否值得介入检索规划"
            />
            <button
              type="submit"
              disabled={isBusy("graph-rag") || !selectedKnowledgeBaseId}
              className="inline-flex h-10 items-center gap-2 bg-slate-950 px-4 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isBusy("graph-rag") ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitBranch className="h-4 w-4" />}
              生成图谱规划
            </button>
          </form>

          {graphPlannerResult ? (
            <div className="mt-5 grid gap-4 lg:grid-cols-[0.7fr_1.3fr]">
              <div className="border border-slate-200 bg-slate-50 px-4 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium text-slate-900">Planner Decision</div>
                  <StatusPill text={graphPlannerResult.graph_useful ? "useful" : "optional"} />
                </div>
                <p className="mt-3 text-sm leading-7 text-slate-700">{graphPlannerResult.summary}</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MetricCard label="Seeds" value={graphPlannerResult.seed_count} />
                  <MetricCard label="Expansions" value={graphPlannerResult.expansion_count} />
                  <MetricCard label="Contexts" value={graphPlannerResult.context_count} />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {([
                  ["Seeds", graphPlannerResult.seeds],
                  ["Expansions", graphPlannerResult.expansions],
                  ["Contexts", graphPlannerResult.contexts],
                ] as const).map(([title, items]) => (
                  <div key={title} className="border border-slate-200 px-4 py-4">
                    <div className="font-medium text-slate-900">{title}</div>
                    <div className="mt-3 space-y-3 text-xs leading-6 text-slate-600">
                      {items.slice(0, 6).map((item, index) => (
                        <div key={`${title}-${index}`} className="border-t border-slate-100 pt-3 first:border-none first:pt-0">
                          <div className="font-medium text-slate-800">{String(item.title ?? item.document_id ?? item.entry_name ?? `Item ${index + 1}`)}</div>
                          <div>{String(item.reason ?? item.summary ?? "-")}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <EmptyState title="还没有规划结果" text="提交一个查询后，这里会显示种子节点、扩展节点和最终上下文候选。" />
            </div>
          )}
        </CardSection>
      </div>
    );
  };

  const renderMemory = () => {
    return (
      <div className="space-y-6">
        <CardSection
          title="Memory Library"
          description="时间线、按类型分组和主题聚类都来自 `/memory/knowledge-bases/{id}/library`。"
          actions={
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void loadMemoryView({ force: true })}
                disabled={isBusy("memory")}
                className="inline-flex items-center gap-2 border border-slate-300 px-3 py-2 text-xs text-slate-700 transition hover:border-slate-950"
              >
                {isBusy("memory") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                刷新
              </button>
              <button
                type="button"
                onClick={() => void handleMemoryRebuild()}
                disabled={isBusy("memory-rebuild") || !selectedKnowledgeBaseId}
                className="inline-flex items-center gap-2 bg-slate-950 px-3 py-2 text-xs text-white transition hover:bg-slate-800"
              >
                {isBusy("memory-rebuild") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                重建记忆
              </button>
            </div>
          }
        >
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-6">
              <div className="border border-slate-200">
                <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs uppercase tracking-[0.18em] text-slate-500">
                  Timeline
                </div>
                <div className="max-h-[420px] overflow-y-auto divide-y divide-slate-200">
                  {memoryLibrary?.timeline.length ? (
                    memoryLibrary.timeline.map((entry) => (
                      <div key={entry.entry_id} className="px-4 py-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-medium text-slate-900">{entry.entry_name}</div>
                          <StatusPill text={entry.entry_type} />
                        </div>
                        <p className="mt-2 text-sm leading-7 text-slate-700">{entry.summary}</p>
                        <div className="mt-2 text-xs text-slate-500">{formatDate(entry.created_at)}</div>
                      </div>
                    ))
                  ) : (
                    <div className="px-4 py-8 text-sm text-slate-500">当前知识库还没有记忆条目。</div>
                  )}
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="border border-slate-200 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">By Type</div>
                  <div className="mt-3 space-y-3 text-sm text-slate-700">
                    {memoryLibrary ? (
                      Object.entries(memoryLibrary.by_type).map(([type, entries]) => (
                        <div key={type}>
                          <div className="font-medium text-slate-900">{type}</div>
                          <div className="mt-1 text-xs leading-6 text-slate-500">{entries.join(" / ") || "-"}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-500">暂无数据</div>
                    )}
                  </div>
                </div>

                <div className="border border-slate-200 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Themes</div>
                  <div className="mt-3 space-y-3 text-sm text-slate-700">
                    {memoryLibrary?.by_theme.length ? (
                      memoryLibrary.by_theme.map((theme) => (
                        <div key={theme.theme_name}>
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-medium text-slate-900">{theme.theme_name}</span>
                            <span className="text-xs text-slate-400">{theme.count}</span>
                          </div>
                          <div className="mt-1 text-xs leading-6 text-slate-500">{theme.entries.join(" / ")}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-500">暂无主题聚类</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <CardSection title="Governance" compact>
                {memoryGovernance ? (
                  <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-3">
                      <MetricCard label="Raw Entries" value={memoryGovernance.raw_entry_count} />
                      <MetricCard label="Canonical" value={memoryGovernance.canonical_memory_count} />
                      <MetricCard label="Relations" value={memoryGovernance.relation_count} />
                    </div>
                    <div className="space-y-3">
                      {memoryGovernance.canonical_memories.slice(0, 8).map((memory) => (
                        <div key={memory.canonical_id} className="border border-slate-200 px-4 py-4">
                          <div className="flex items-center justify-between gap-3">
                            <div className="font-medium text-slate-900">{memory.entry_name}</div>
                            <StatusPill text={memory.status} />
                          </div>
                          <p className="mt-2 text-sm leading-7 text-slate-700">{memory.summary}</p>
                          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
                            <div>Importance {memory.importance_score.toFixed(2)}</div>
                            <div>Documents {memory.document_count}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState title="治理结果为空" text="加载后会显示 canonical memory、关系类型和重要性分布。" />
                )}
              </CardSection>

              <CardSection title="Selected Document Memory" compact>
                {documentMemoryLibrary?.timeline.length ? (
                  <div className="space-y-3">
                    {documentMemoryLibrary.timeline.map((item) => (
                      <div key={item.entry_id} className="border border-slate-200 px-4 py-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-medium text-slate-900">{item.entry_name}</div>
                          <StatusPill text={item.entry_type} />
                        </div>
                        <p className="mt-2 text-sm leading-7 text-slate-700">{item.summary}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState title="当前文档还没有记忆条目" text="先索引文档，再重建知识库记忆库。" />
                )}
              </CardSection>

              {memoryRebuildResult ? (
                <div className="border border-slate-200 bg-slate-50 px-4 py-4 text-xs leading-6 text-slate-600">
                  <div className="font-medium text-slate-900">最近一次重建</div>
                  <div className="mt-2">Processed {memoryRebuildResult.processed_document_count}</div>
                  <div>Entries {memoryRebuildResult.entry_count}</div>
                  <div>Chunks {memoryRebuildResult.chunk_count}</div>
                </div>
              ) : null}
            </div>
          </div>
        </CardSection>
      </div>
    );
  };

  const renderInsights = () => {
    return (
      <div className="space-y-6">
        <CardSection
          title="Profile / Growth / Analytics"
          description="画像、证据、成长分析和分析报表会一起拉取。Advice 与 Companion 则保留独立触发。"
          actions={
            <div className="flex flex-wrap gap-2">
              <label className="inline-flex items-center gap-2 border border-slate-300 px-3 py-2 text-xs text-slate-600">
                Recent Days
                <input
                  type="number"
                  min={7}
                  max={180}
                  value={recentDays}
                  onChange={(event) => setRecentDays(Number(event.target.value) || 30)}
                  className="w-16 bg-transparent outline-none"
                />
              </label>
              <button
                type="button"
                onClick={() => void loadInsightsView({ force: true })}
                disabled={isBusy("insights")}
                className="inline-flex items-center gap-2 bg-slate-950 px-3 py-2 text-xs text-white transition hover:bg-slate-800"
              >
                {isBusy("insights") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                刷新洞察
              </button>
            </div>
          }
        >
          <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-6">
              <CardSection title="Personal Profile" compact>
                {profile ? (
                  <div className="space-y-4">
                    <p className="text-sm leading-7 text-slate-700">{profile.profile_summary}</p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Themes</div>
                        <div className="mt-3 space-y-3 text-sm text-slate-700">
                          {profile.main_themes.map((theme) => (
                            <div key={theme.theme_name}>
                              <div className="font-medium text-slate-900">{theme.theme_name}</div>
                              <div className="mt-1 text-xs leading-6 text-slate-500">{theme.reason}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Ability Tags</div>
                        <div className="mt-3 space-y-3 text-sm text-slate-700">
                          {profile.ability_tags.map((tag) => (
                            <div key={tag.ability_name}>
                              <div className="font-medium text-slate-900">{tag.ability_name}</div>
                              <div className="mt-1 text-xs leading-6 text-slate-500">{tag.reason}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="border-t border-slate-200 pt-4 text-sm leading-7 text-slate-700">
                      <div>
                        <span className="text-slate-500">Expression Style </span>
                        {profile.expression_style}
                      </div>
                      <div className="mt-2">
                        <span className="text-slate-500">Growth Focus </span>
                        {profile.growth_focus.join(" / ")}
                      </div>
                    </div>
                  </div>
                ) : (
                  <EmptyState title="还没有画像结果" text="选择知识库并刷新后，这里会显示长期主题、能力标签和表达风格。" />
                )}
              </CardSection>

              <CardSection title="Evidence Profile" compact>
                {profileEvidence ? (
                  <div className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-3">
                      <MetricCard label="Entries" value={profileEvidence.entry_count} />
                      <MetricCard label="Canonical" value={profileEvidence.canonical_memory_count} />
                      <MetricCard label="Evidence" value={profileEvidence.evidence.length} />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="border border-slate-200 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Stable Traits</div>
                        <div className="mt-3 space-y-3 text-sm text-slate-700">
                          {profileEvidence.stable_traits.map((trait) => (
                            <div key={trait.trait_name}>
                              <div className="flex items-center justify-between gap-3">
                                <span className="font-medium text-slate-900">{trait.trait_name}</span>
                                <StatusPill text={trait.confidence} />
                              </div>
                              <div className="mt-1 text-xs leading-6 text-slate-500">{trait.summary}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="border border-slate-200 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Risks</div>
                        <div className="mt-3 space-y-3 text-sm text-slate-700">
                          {profileEvidence.risks.map((risk) => (
                            <div key={risk.risk_name}>
                              <div className="font-medium text-slate-900">{risk.risk_name}</div>
                              <div className="mt-1 text-xs leading-6 text-slate-500">{risk.summary}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="border border-slate-200 px-4 py-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Evidence</div>
                      <div className="mt-3 space-y-3 text-sm text-slate-700">
                        {profileEvidence.evidence.slice(0, 6).map((item) => (
                          <div key={item.entry_id} className="border-t border-slate-100 pt-3 first:border-none first:pt-0">
                            <div className="font-medium text-slate-900">{item.entry_name}</div>
                            <div className="mt-1 text-xs leading-6 text-slate-500">{item.evidence_text}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <EmptyState title="还没有证据画像" text="这里会显示 traits、risks、topic timeline 和可追溯证据。" />
                )}
              </CardSection>
            </div>

            <div className="space-y-6">
              <CardSection title="Growth Report" compact>
                {growth ? (
                  <div className="space-y-4 text-sm leading-7 text-slate-700">
                    <p>{growth.stage_summary}</p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="border border-slate-200 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Highlights</div>
                        <ul className="mt-3 space-y-2">
                          {growth.highlights.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="border border-slate-200 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Blockers</div>
                        <ul className="mt-3 space-y-2">
                          {growth.blockers.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                    <div className="border border-slate-200 px-4 py-4">
                      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Next Actions</div>
                      <ul className="mt-3 space-y-2">
                        {growth.next_actions.map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <EmptyState title="还没有成长报告" text="这里会显示阶段总结、亮点、卡点和下一步动作。" />
                )}
              </CardSection>

              <CardSection title="Growth Advice" compact>
                <form className="space-y-4" onSubmit={handleAdviceSubmit}>
                  <input
                    value={adviceGoal}
                    onChange={(event) => setAdviceGoal(event.target.value)}
                    className="h-11 w-full border border-slate-300 px-4 text-sm outline-none transition focus:border-slate-950"
                    placeholder="可选：告诉系统你现在最想关注的目标"
                  />
                  <button
                    type="submit"
                    disabled={isBusy("advice") || !selectedKnowledgeBaseId}
                    className="inline-flex h-10 items-center gap-2 bg-slate-950 px-4 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {isBusy("advice") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    生成建议
                  </button>
                </form>

                {advice ? (
                  <div className="mt-5 space-y-4 text-sm leading-7 text-slate-700">
                    <p>{advice.advice_summary}</p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="border border-slate-200 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Priorities</div>
                        <ul className="mt-3 space-y-2">
                          {advice.current_priorities.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="border border-slate-200 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">One Week Plan</div>
                        <ul className="mt-3 space-y-2">
                          {advice.one_week_plan.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                    <div className="space-y-3">
                      {advice.action_suggestions.map((item) => (
                        <div key={`${item.area}-${item.action}`} className="border border-slate-200 px-4 py-4">
                          <div className="font-medium text-slate-900">{item.area}</div>
                          <div className="mt-2 text-xs leading-6 text-slate-500">{item.why_now}</div>
                          <div className="mt-2">Action {item.action}</div>
                          <div>First Step {item.first_step}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </CardSection>

              <CardSection title="Analytics Markdown" compact>
                {analytics ? (
                  <Suspense fallback={<PanelSkeleton text="正在加载 Markdown 渲染器" />}>
                    <div className="prose prose-sm max-w-none text-slate-700 prose-headings:font-serif prose-headings:text-slate-900 prose-p:text-slate-700 prose-strong:text-slate-900 prose-li:text-slate-700">
                      <ReactMarkdown>{analytics.markdown}</ReactMarkdown>
                    </div>
                  </Suspense>
                ) : (
                  <EmptyState title="还没有分析报表" text="这里会直接渲染后端返回的 Markdown 报告。" />
                )}
              </CardSection>
            </div>
          </div>
        </CardSection>
      </div>
    );
  };

  if (authStatus !== "authed") {
    if (authStatus === "checking" && token) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#0f172a_0%,#111827_100%)] text-slate-100">
          <div className="inline-flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-5 py-4 text-sm shadow-[0_24px_80px_rgba(15,23,42,0.32)]">
            <Loader2 className="h-5 w-5 animate-spin" />
            正在恢复会话并加载工作台
          </div>
        </div>
      );
    }

    return <AuthScreen apiBaseUrl={API_BASE_URL} loading={authLoading} error={authError} onSubmit={handleAuthSubmit} />;
  }

  return (
    <div className="mneme-workbench min-h-screen bg-surface-dim text-on-surface">
      <div className="grid min-h-screen xl:grid-cols-[292px_minmax(0,1fr)]">
        <aside className="relative flex flex-col overflow-hidden border-r border-outline-variant bg-surface-container-lowest text-on-surface">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#2a2721_1px,transparent_1px)] [background-size:18px_18px] opacity-60" />

          <div className="relative border-b border-outline-variant px-5 py-5">
            <div className="inline-flex size-10 items-center justify-center rounded-md bg-primary text-base font-bold text-on-primary">
              M
            </div>
            <div className="mt-4">
              <div className="text-2xl font-semibold leading-none tracking-normal">Mneme</div>
              <div className="mt-2 font-mono text-[10px] uppercase tracking-widest text-text-muted">Memory vault</div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-wider text-text-muted">
              <div className="rounded border border-outline-variant bg-surface px-2 py-1">API</div>
              <div className="max-w-full truncate rounded border border-outline-variant bg-surface px-2 py-1">{user?.display_name || user?.username}</div>
            </div>
          </div>

          <div className="relative space-y-7 overflow-y-auto px-3 py-4">
            <nav className="space-y-1">
              {VIEW_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setView(item.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
                    view === item.id
                      ? "border-primary/40 bg-primary-container/60 text-on-primary-container"
                      : "border-transparent text-on-surface-variant hover:border-outline-variant hover:bg-surface-container-low",
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  <div>
                    <div className="text-sm font-medium">{item.label}</div>
                    <div className="text-[11px] text-text-muted">{item.hint}</div>
                  </div>
                </button>
              ))}
            </nav>

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Vaults</div>
                <span className="text-xs text-text-muted">{knowledgeBases.length}</span>
              </div>

              <form className="space-y-2 rounded-md border border-outline-variant bg-surface p-3" onSubmit={handleCreateKnowledgeBase}>
                <input
                  value={knowledgeBaseForm.name}
                  onChange={(event) => setKnowledgeBaseForm((current) => ({ ...current, name: event.target.value }))}
                  className="h-9 w-full rounded-md border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none placeholder:text-text-muted transition focus:border-primary"
                  placeholder="新知识库名称"
                />
                <input
                  value={knowledgeBaseForm.description}
                  onChange={(event) => setKnowledgeBaseForm((current) => ({ ...current, description: event.target.value }))}
                  className="h-9 w-full rounded-md border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none placeholder:text-text-muted transition focus:border-primary"
                  placeholder="描述，可选"
                />
                <button
                  type="submit"
                  disabled={isBusy("create-kb")}
                  className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-md bg-primary text-sm font-medium text-on-primary transition hover:bg-on-primary-container disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isBusy("create-kb") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  创建知识库
                </button>
              </form>

              <div className="space-y-2">
                {knowledgeBases.map((knowledgeBase) => (
                  <div
                    key={knowledgeBase.id}
                    className={cn(
                      "rounded-md border px-3 py-3 transition",
                      selectedKnowledgeBaseId === knowledgeBase.id
                        ? "border-primary/40 bg-primary-container/40"
                        : "border-outline-variant bg-surface hover:border-outline hover:bg-surface-container-low",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedKnowledgeBaseId(knowledgeBase.id)}
                      className="w-full text-left"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium text-on-surface">{knowledgeBase.name}</div>
                          <div className="mt-1 line-clamp-2 text-xs leading-5 text-text-muted">
                            {knowledgeBase.description || "没有描述"}
                          </div>
                        </div>
                        {knowledgeBase.is_default ? <StatusPill text="default" /> : null}
                      </div>
                    </button>
                    <div className="mt-3 flex items-center justify-between gap-3 text-xs text-text-muted">
                      <span>{formatDate(knowledgeBase.created_at)}</span>
                      {!knowledgeBase.is_default ? (
                        <button
                          type="button"
                          onClick={() => void handleDeleteKnowledgeBase(knowledgeBase)}
                          disabled={isBusy(`delete-kb-${knowledgeBase.id}`)}
                          className="text-red-300 transition hover:text-red-200 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          删除
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-3 rounded-md border border-outline-variant bg-surface p-4 text-xs leading-6 text-on-surface-variant">
              <div className="flex items-center gap-2 font-medium text-on-surface">
                <ShieldCheck className="h-4 w-4" />
                Runtime
              </div>
              <div className="flex items-center justify-between">
                <span>API</span>
                <StatusPill text={serviceHealth?.status ?? "unknown"} />
              </div>
              <div className="flex items-center justify-between">
                <span>Neo4j</span>
                <StatusPill text={neo4jHealth?.ok ? "ok" : "warn"} />
              </div>
              <div className="flex items-center justify-between">
                <span>Readiness</span>
                <StatusPill text={readiness?.overall_status ?? "unknown"} />
              </div>
            </section>
          </div>

          <div className="relative mt-auto border-t border-outline-variant px-3 py-3">
            <div className="flex items-center gap-3 rounded-md border border-outline-variant bg-surface px-3 py-3">
              <div className="flex size-9 items-center justify-center rounded-md bg-surface-container-high text-primary">
                <UserRound className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-on-surface">{user?.display_name || user?.username}</div>
                <div className="truncate text-xs text-text-muted">{user?.username}</div>
              </div>
              <button
                type="button"
                onClick={logout}
                className="inline-flex size-8 items-center justify-center rounded-md border border-outline-variant text-text-muted transition hover:bg-surface-container-high hover:text-on-surface"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </aside>

        <main className="flex min-h-screen flex-col">
          <header className="border-b border-outline-variant bg-surface-container-low/95 backdrop-blur">
            <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
              <div className="flex flex-col gap-5 2xl:flex-row 2xl:items-end 2xl:justify-between">
                <div className="max-w-3xl">
                  <div className="inline-flex items-center gap-2 rounded-md border border-outline-variant bg-surface px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-text-muted">
                    <CurrentViewIcon className="h-3.5 w-3.5" />
                    {currentViewItem.label}
                  </div>
                  <h1 className="mt-4 text-3xl font-semibold tracking-normal text-on-surface sm:text-4xl">
                    {selectedKnowledgeBase?.name || "选择一个知识库开始"}
                  </h1>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-text-muted">
                    当前视图聚焦 {currentViewItem.hint}。
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="min-w-[156px] rounded-md border border-outline-variant bg-surface px-4 py-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Knowledge Bases</div>
                    <div className="mt-2 text-2xl font-semibold text-on-surface">{knowledgeBases.length}</div>
                    <div className="mt-1 text-xs text-text-muted">{user?.display_name || user?.username}</div>
                  </div>
                  <div className="min-w-[156px] rounded-md border border-outline-variant bg-surface px-4 py-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Documents</div>
                    <div className="mt-2 text-2xl font-semibold text-on-surface">{documents.length}</div>
                    <div className="mt-1 text-xs text-slate-500">{indexedDocumentCount} 已完成索引</div>
                  </div>
                  <div className="min-w-[156px] rounded-md border border-outline-variant bg-surface px-4 py-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Active Context</div>
                    <div className="mt-2 text-2xl font-semibold text-on-surface">{activeTaskIds.length}</div>
                    <div className="mt-1 truncate text-xs text-slate-500">{selectedDocument?.file_name || "未选中文档"}</div>
                  </div>
                </div>
              </div>

              {banner ? (
                <div
                  className={cn(
                    "flex items-start gap-3 rounded-md border px-4 py-3 text-sm",
                    banner.tone === "success" && "border-emerald-400/30 bg-emerald-500/10 text-emerald-300",
                    banner.tone === "error" && "border-red-400/30 bg-red-500/10 text-red-300",
                    banner.tone === "info" && "border-primary/30 bg-primary/10 text-on-primary-container",
                  )}
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div className="flex-1">{banner.text}</div>
                  <button type="button" onClick={() => setBanner(null)} className="text-current/70 transition hover:text-current">
                    关闭
                  </button>
                </div>
              ) : null}
            </div>
          </header>

          <div className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto w-full max-w-[1680px]">
              {view === "workspace" && renderWorkspace()}
              {view === "chat" && renderChat()}
              {view === "graph" && renderGraph()}
              {view === "memory" && renderMemory()}
              {view === "insights" && renderInsights()}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
