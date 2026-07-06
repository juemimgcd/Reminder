import {
  AlertCircle,
  Bell,
  BookOpen,
  Bot,
  Calendar,
  CirclePlus,
  Copy,
  Cpu,
  FileText,
  FolderGit2,
  GitBranch,
  HardDrive,
  HelpCircle,
  Info,
  Loader2,
  LogOut,
  MessageSquare,
  MoreHorizontal,
  Palette,
  Plus,
  RefreshCw,
  Send,
  ScanSearch,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Tag,
  Trash2,
  Upload,
  UserRound,
} from "lucide-react";
import { Suspense, lazy, type FormEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";

import AuthScreen from "./components/AuthScreen";
import { ApiError, api, API_BASE_URL, IS_PREVIEW_MODE, PREVIEW_TOKEN } from "./lib/api";
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
type WorkspaceCommandTab = "create" | "upload" | "ask" | "companion";

interface BannerState {
  tone: BannerTone;
  text: string;
}

const TOKEN_KEY = "mneme.access_token";
const SELECTED_KB_KEY = "mneme.selected_kb";
const ACTIVE_TASK_STATUSES = new Set(["queued", "running", "pending", "created", "retrying"]);
const VIEW_CACHE_TARGETS = ["graph", "notes", "settings"] as const;

const VIEW_ITEMS: Array<{ id: WorkspaceView; label: string; icon: typeof FolderGit2; hint: string }> = [
  { id: "dashboard", label: "Dashboard", icon: FolderGit2, hint: "Knowledge base at a glance" },
  { id: "notes", label: "Notes", icon: FileText, hint: "Documents and durable memory" },
  { id: "graph", label: "Graph", icon: GitBranch, hint: "GraphRAG structure" },
  { id: "ai", label: "AI Chat", icon: Bot, hint: "Ask and companion replies" },
  { id: "settings", label: "Settings", icon: Settings, hint: "Health, profile, and analytics" },
];

const WORKSPACE_COMMANDS: Array<{ id: WorkspaceCommandTab; label: string; hint: string; icon: typeof FolderGit2 }> = [
  { id: "create", label: "Create Vault", hint: "新建知识库", icon: Plus },
  { id: "upload", label: "Upload File", hint: "加入当前 vault", icon: Upload },
  { id: "ask", label: "Ask Vault", hint: "检索问答", icon: ScanSearch },
  { id: "companion", label: "Companion", hint: "陪伴式回复", icon: Bot },
];

const iconButtonClass =
  "inline-flex size-8 items-center justify-center rounded-md text-text-muted transition hover:bg-surface-container-high hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 disabled:cursor-not-allowed disabled:opacity-50";

const secondaryButtonClass =
  "inline-flex h-8 items-center justify-center gap-2 rounded-md border border-outline-variant bg-surface-container px-3 text-xs font-medium text-on-surface-variant transition hover:border-outline hover:bg-surface-container-high hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 disabled:cursor-not-allowed disabled:opacity-50";

const primaryButtonClass =
  "inline-flex h-8 items-center justify-center gap-2 rounded-md bg-primary px-3 text-xs font-semibold text-on-primary transition hover:bg-on-primary-container focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 disabled:cursor-not-allowed disabled:opacity-50";

const inputClass =
  "premium-input h-9 w-full rounded-md px-3 text-sm text-on-surface placeholder:text-text-muted disabled:cursor-not-allowed disabled:opacity-60";

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
    <section className="premium-card rounded-xl">
      <div
        className={cn(
          "premium-card-content flex items-start justify-between gap-4 border-b border-white/5 bg-surface-container-low/30",
          compact ? "px-4 py-3" : "px-5 py-4",
        )}
      >
        <div>
          <h2 className="text-sm font-semibold text-on-surface">{title}</h2>
          {description ? <p className="mt-1 text-xs leading-5 text-text-muted">{description}</p> : null}
        </div>
        {actions}
      </div>
      <div className={cn("premium-card-content", compact ? "px-4 py-4" : "px-5 py-5")}>{children}</div>
    </section>
  );
}

function FunctionBlock({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="glass-panel rounded-xl p-5">
      <div className="border-b border-white/10 pb-3">
        <div className="text-sm font-semibold text-on-surface">{title}</div>
        {description ? <div className="mt-1 text-xs leading-5 text-text-muted">{description}</div> : null}
      </div>
      <div className="pt-4">{children}</div>
    </section>
  );
}

function OutputWorkspace({
  title,
  meta,
  children,
  testId,
  className,
  contentClassName,
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  testId?: string;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <section data-testid={testId} className={cn("glass-panel min-h-[360px] overflow-hidden rounded-xl", className)}>
      <div className="flex min-h-14 items-center justify-between gap-3 border-b border-white/10 bg-surface-container-low/30 px-5">
        <div className="truncate text-sm font-semibold text-on-surface">{title}</div>
        {meta ? <div className="flex shrink-0 items-center gap-2 text-xs text-text-muted">{meta}</div> : null}
      </div>
      <div className={cn("px-5 py-5", contentClassName)}>{children}</div>
    </section>
  );
}

function MetricCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="premium-tag rounded-lg px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">{label}</div>
      <div className="mt-1 truncate text-lg font-semibold text-on-surface">{value}</div>
      {hint ? <div className="mt-1 truncate text-xs text-text-muted">{hint}</div> : null}
    </div>
  );
}

function DashboardStatCard({
  label,
  value,
  suffix,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  hint: string;
  icon: typeof FolderGit2;
}) {
  return (
    <div className="premium-card rounded-xl p-6">
      <div className="premium-card-content flex h-full flex-col justify-between gap-8">
        <div className="flex items-start justify-between gap-4">
          <div className="rounded-xl border border-border-subtle/40 bg-surface-container-high/60 p-2.5 text-primary shadow-inner">
            <Icon className="h-5 w-5 drop-shadow-[0_0_5px_rgba(124,58,237,0.4)]" />
          </div>
          <span className="font-mono text-[11px] font-bold uppercase tracking-[0.15em] text-on-surface-variant/80">{label}</span>
        </div>
        <div>
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-[42px] font-bold leading-none tracking-normal text-on-surface">{value}</span>
            {suffix ? <span className="text-lg font-medium text-on-surface-variant">{suffix}</span> : null}
          </div>
          <p className="mt-3 text-sm font-medium text-on-surface-variant/70">{hint}</p>
        </div>
      </div>
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
    <div className="border border-dashed border-outline-variant/80 bg-surface-container-low/42 px-5 py-8 text-center">
      <div className="text-sm font-medium text-on-surface">{title}</div>
      <div className="mx-auto mt-2 max-w-xl text-xs leading-6 text-text-muted">{text}</div>
    </div>
  );
}

function PanelSkeleton({ text = "正在加载面板" }: { text?: string }) {
  return (
    <div className="flex min-h-[220px] items-center justify-center border border-dashed border-outline-variant/80 bg-surface-container-low/42 text-sm text-text-muted">
      <div className="inline-flex items-center gap-3">
        <Loader2 className="h-4 w-4 animate-spin" />
        {text}
      </div>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => (IS_PREVIEW_MODE ? PREVIEW_TOKEN : localStorage.getItem(TOKEN_KEY) ?? ""));
  const [authStatus, setAuthStatus] = useState<AuthStatus>(() => (IS_PREVIEW_MODE || localStorage.getItem(TOKEN_KEY) ?"checking" : "guest"));
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [busyKeys, setBusyKeys] = useState<Record<string, boolean>>({});

  const [view, setView] = useState<WorkspaceView>("dashboard");
  const [workspaceCommandTab, setWorkspaceCommandTab] = useState<WorkspaceCommandTab>("ask");
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
    if (targets.includes("notes")) {
      memoryLoadKeyRef.current = "";
    }
    if (targets.includes("settings")) {
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
    if (view === "notes") {
      void loadMemoryView();
    }
    if (view === "settings") {
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
      invalidateViewCache(["notes", "settings", "graph"]);
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
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-4">
          <DashboardStatCard label="Documents" value={documents.length} hint={`${indexedDocumentCount} indexed notes`} icon={FileText} />
          <DashboardStatCard label="Vaults" value={knowledgeBases.length} hint={selectedKnowledgeBase?.name || "No active vault"} icon={BookOpen} />
          <div className="premium-card rounded-xl p-6 md:col-span-1 lg:col-span-2">
            <div className="premium-card-content flex h-full min-h-48 flex-col">
              <div className="mb-8 flex items-center justify-between gap-4">
                <h3 className="text-xl font-bold tracking-normal text-on-surface">Knowledge Graph Activity</h3>
                <span className="premium-tag rounded-full px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-on-surface-variant">
                  Live State
                </span>
              </div>
              <div className="flex flex-1 items-end gap-3 pt-4">
                {[30, 50, 40, 85, 60, 95, 70].map((height, index) => (
                  <div
                    key={height + index}
                    className="w-full rounded-t-md bg-primary/20 transition hover:bg-primary/50 hover:shadow-[0_0_15px_rgba(124,58,237,0.3)]"
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>
          </div>
          <DashboardStatCard label="Tasks" value={activeTaskIds.length} hint={`${Object.values(taskMap).length} tracked operations`} icon={RefreshCw} />
          <DashboardStatCard label="Runtime" value={serviceHealth?.status ?? "unknown"} hint={neo4jHealth?.ok ? "Neo4j reachable" : "Neo4j waiting"} icon={ShieldCheck} />
        </div>
        <section data-testid="unified-command-module" className="premium-card rounded-xl">
          <div className="premium-card-content flex min-h-14 items-center justify-between gap-3 border-b border-white/10 bg-surface-container-low/30 px-5">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-on-surface">Workspace Commands</div>
              <div className="truncate text-xs text-text-muted">知识库、文件上传和对话集中在一个命令面板里。</div>
            </div>
            <StatusPill text={selectedKnowledgeBase?.name ?? "no vault"} />
          </div>

          <div className="premium-card-content grid min-h-[360px] xl:grid-cols-[248px_minmax(0,1fr)]">
            <nav data-testid="workspace-command-tabs" className="border-b border-white/10 bg-surface-container-low/20 p-2 xl:border-b-0 xl:border-r">
              <div className="px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-text-muted">Commands</div>
              <div className="mt-1 grid gap-1 sm:grid-cols-4 xl:grid-cols-1">
                {WORKSPACE_COMMANDS.map((command) => (
                  <button
                    key={command.id}
                    type="button"
                    onClick={() => setWorkspaceCommandTab(command.id)}
                    aria-pressed={workspaceCommandTab === command.id}
                    className={cn(
                      "premium-tag flex min-h-12 items-center gap-2 rounded-md px-2.5 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
                      workspaceCommandTab === command.id ? "text-on-surface" : "text-on-surface-variant",
                    )}
                    data-active={workspaceCommandTab === command.id}
                  >
                    <command.icon className="h-4 w-4 shrink-0 text-primary" />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">{command.label}</span>
                      <span className="block truncate text-[11px] text-text-muted">{command.hint}</span>
                    </span>
                  </button>
                ))}
              </div>
            </nav>

            <div data-testid="workspace-command-panel" className="min-w-0 p-4">
              {workspaceCommandTab === "create" ? (
                <form data-testid="workspace-create-kb-command" className="mx-auto grid max-w-3xl gap-3" onSubmit={handleCreateKnowledgeBase}>
                  <div>
                    <div className="text-sm font-semibold text-on-surface">Create Vault</div>
                    <div className="mt-1 text-xs leading-5 text-text-muted">创建新的知识库后会自动切换到它。</div>
                  </div>
                  <input
                    value={knowledgeBaseForm.name}
                    onChange={(event) => setKnowledgeBaseForm((current) => ({ ...current, name: event.target.value }))}
                    className={inputClass}
                    placeholder="新知识库名称"
                  />
                  <input
                    value={knowledgeBaseForm.description}
                    onChange={(event) => setKnowledgeBaseForm((current) => ({ ...current, description: event.target.value }))}
                    className={inputClass}
                    placeholder="描述，可选"
                  />
                  <div>
                    <button type="submit" disabled={isBusy("create-kb")} className={primaryButtonClass}>
                      {isBusy("create-kb") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                      创建知识库
                    </button>
                  </div>
                </form>
              ) : null}

              {workspaceCommandTab === "upload" ? (
                <div data-testid="workspace-upload-command" className="mx-auto grid max-w-3xl gap-3">
                  <div>
                    <div className="text-sm font-semibold text-on-surface">Upload File</div>
                    <div className="mt-1 text-xs leading-5 text-text-muted">文件会加入当前 vault，随后可在 Documents 中索引。</div>
                  </div>
                  <div className="border border-dashed border-outline-variant/80 bg-surface-container-low/36 px-4 py-5">
                    <div className="truncate text-sm text-on-surface">
                      {uploadFile ? uploadFile.name : "当前没有待上传文件"}
                    </div>
                    <div className="mt-1 text-xs text-text-muted">{uploadFile ? formatBytes(uploadFile.size) : "选择一个文件后再上传。"}</div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <label className={cn(secondaryButtonClass, "cursor-pointer")}>
                        <Upload className="h-4 w-4" />
                        选择文件
                        <input type="file" className="hidden" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
                      </label>
                      <button
                        type="button"
                        disabled={!uploadFile || isBusy("upload") || !selectedKnowledgeBaseId}
                        onClick={() => void handleUploadDocument()}
                        className={primaryButtonClass}
                      >
                        {isBusy("upload") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                        上传
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}

              {workspaceCommandTab === "ask" ? (
                <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                  <form data-testid="workspace-chat-command" className="space-y-3" onSubmit={handleChatSubmit}>
                    <div>
                      <div className="text-sm font-semibold text-on-surface">Ask Vault</div>
                      <div className="mt-1 text-xs leading-5 text-text-muted">对当前知识库提问，右侧显示最近一次回答。</div>
                    </div>
                    <textarea
                      value={chatQuestion}
                      onChange={(event) => setChatQuestion(event.target.value)}
                      className="min-h-[132px] w-full rounded-md border border-outline-variant bg-surface-container-low px-3 py-2.5 text-sm leading-6 text-on-surface outline-none transition placeholder:text-text-muted focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                      placeholder="输入要检索和回答的问题"
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="inline-flex h-8 items-center gap-2 rounded-md border border-outline-variant bg-surface-container px-2.5 text-xs text-text-muted">
                        Top K
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={chatTopK}
                          onChange={(event) => setChatTopK(Number(event.target.value) || 4)}
                          className="h-6 w-12 border-none bg-transparent px-0 text-on-surface outline-none"
                        />
                      </label>
                      <button type="submit" disabled={isBusy("chat") || !selectedKnowledgeBaseId} className={primaryButtonClass}>
                        {isBusy("chat") ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
                        提问
                      </button>
                    </div>
                  </form>

                  <section className="min-h-[214px] rounded-md border border-outline-variant/80 bg-surface-container-low/28 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Answer</div>
                      {chatResult ? <StatusPill text={chatResult.confidence} /> : null}
                    </div>
                    {chatResult ? (
                      <div className="mt-3 space-y-3">
                        <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{chatResult.answer}</p>
                        <div className="flex flex-wrap gap-3 text-xs text-text-muted">
                          <span>{chatResult.citations.length} citations</span>
                          {chatResult.route ? <span>{chatResult.route.target_pipeline}</span> : null}
                        </div>
                      </div>
                    ) : (
                      <div className="mt-3 text-xs leading-6 text-text-muted">还没有问答结果。</div>
                    )}
                  </section>
                </div>
              ) : null}

              {workspaceCommandTab === "companion" ? (
                <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                  <form className="space-y-3" onSubmit={handleCompanionSubmit}>
                    <div>
                      <div className="text-sm font-semibold text-on-surface">Companion Reply</div>
                      <div className="mt-1 text-xs leading-5 text-text-muted">需要行动建议、状态整理或陪伴式反馈时使用。</div>
                    </div>
                    <textarea
                      value={companionQuestion}
                      onChange={(event) => setCompanionQuestion(event.target.value)}
                      className="min-h-[132px] w-full rounded-md border border-outline-variant bg-surface-container-low px-3 py-2.5 text-sm leading-6 text-on-surface outline-none transition placeholder:text-text-muted focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
                      placeholder="输入你的问题或当前状态"
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="inline-flex h-8 items-center gap-2 rounded-md border border-outline-variant bg-surface-container px-2.5 text-xs text-text-muted">
                        Top K
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={companionTopK}
                          onChange={(event) => setCompanionTopK(Number(event.target.value) || 4)}
                          className="h-6 w-12 border-none bg-transparent px-0 text-on-surface outline-none"
                        />
                      </label>
                      <button type="submit" disabled={isBusy("companion") || !selectedKnowledgeBaseId} className={primaryButtonClass}>
                        {isBusy("companion") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                        生成
                      </button>
                    </div>
                  </form>

                  <section className="min-h-[214px] rounded-md border border-outline-variant/80 bg-surface-container-low/28 px-4 py-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Reply</div>
                    {companionResult ? (
                      <div className="mt-3 space-y-3">
                        <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{companionResult.companion_message}</p>
                        <div className="text-xs leading-6 text-text-muted">{companionResult.next_step_hint}</div>
                      </div>
                    ) : (
                      <div className="mt-3 text-xs leading-6 text-text-muted">还没有陪伴回复。</div>
                    )}
                  </section>
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
          <CardSection
            title="Documents"
            description="这里仅管理当前知识库文档，上传入口已经集中到 Workspace Commands。"
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
                                    setView("notes");
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
      <div className="space-y-5">
        <div data-testid="chat-function-grid" className="grid gap-3 xl:grid-cols-2">
          <FunctionBlock title="Knowledge Base Q&A" description="只负责提交检索问答，不承载结果区。">
            <form className="space-y-3" onSubmit={handleChatSubmit}>
              <textarea
                value={chatQuestion}
                onChange={(event) => setChatQuestion(event.target.value)}
                className="min-h-[116px] w-full border border-slate-300 px-3 py-2.5 text-sm leading-6 outline-none transition focus:border-slate-950"
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
                    className="h-9 w-20 border border-slate-300 px-3 outline-none focus:border-slate-950"
                  />
                </label>
                <button
                  type="submit"
                  disabled={isBusy("chat") || !selectedKnowledgeBaseId}
                  className="inline-flex h-9 items-center gap-2 bg-slate-950 px-3 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {isBusy("chat") ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
                  发送问答
                </button>
              </div>
            </form>
          </FunctionBlock>

          <FunctionBlock title="Companion Reply" description="只负责生成陪伴式回复，不承载输出区。">
            <form className="space-y-3" onSubmit={handleCompanionSubmit}>
              <textarea
                value={companionQuestion}
                onChange={(event) => setCompanionQuestion(event.target.value)}
                className="min-h-[116px] w-full border border-slate-300 px-3 py-2.5 text-sm leading-6 outline-none transition focus:border-slate-950"
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
                    className="h-9 w-20 border border-slate-300 px-3 outline-none focus:border-slate-950"
                  />
                </label>
                <button
                  type="submit"
                  disabled={isBusy("companion") || !selectedKnowledgeBaseId}
                  className="inline-flex h-9 items-center gap-2 bg-slate-950 px-3 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {isBusy("companion") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                  生成陪伴回复
                </button>
              </div>
            </form>
          </FunctionBlock>
        </div>

        <OutputWorkspace
          testId="chat-output-workspace"
          title="Generated Workspace"
          meta={
            <>
              {chatResult ? <StatusPill text={chatResult.confidence} /> : null}
              {companionResult ? <StatusPill text="companion" /> : null}
            </>
          }
        >
          <div className="grid gap-5 xl:grid-cols-2">
            <section className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Knowledge Base Answer</div>
              {chatResult ? (
                <div className="mt-3 space-y-4">
                  <div className="border border-slate-200 bg-slate-50 px-4 py-4">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{chatResult.answer}</p>
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
                <div className="mt-3">
                  <EmptyState title="还没有问答结果" text="提交问题后，回答、证据引用和路由判断会出现在这个独立工作区。" />
                </div>
              )}
            </section>

            <section className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-widest text-text-muted">Companion Output</div>
              {companionResult ? (
                <div className="mt-3 space-y-4">
                  <div className="border border-slate-200 bg-slate-50 px-4 py-4">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{companionResult.companion_message}</p>
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
                <div className="mt-3">
                  <EmptyState title="还没有陪伴回复" text="陪伴式反馈、下一步建议和追问会集中显示在这里。" />
                </div>
              )}
            </section>
          </div>
        </OutputWorkspace>
      </div>
    );
  };

  const renderGraph = () => {
    return (
      <div className="space-y-5">
        <div data-testid="graph-function-grid" className="grid gap-3 xl:grid-cols-[0.9fr_1.1fr]">
          <FunctionBlock title="Graph Scope" description="选择范围、关系和节点类型，只负责控制图谱。">
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
              <label className="space-y-2 text-sm">
                <span className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Graph Scope</span>
                <select
                  value={graphScope}
                  onChange={(event) => setGraphScope(event.target.value as GraphScope)}
                  className="h-10 w-full border border-slate-300 px-3 outline-none focus:border-slate-950"
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
                    className="h-10 w-full border border-slate-300 px-3 outline-none focus:border-slate-950"
                  >
                    {documents.map((document) => (
                      <option key={document.id} value={document.id}>
                        {document.file_name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <div className="flex flex-wrap gap-3 text-sm text-slate-600">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={graphIncludeMemory} onChange={(event) => setGraphIncludeMemory(event.target.checked)} />
                  Memory nodes
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={graphIncludeRelationships} onChange={(event) => setGraphIncludeRelationships(event.target.checked)} />
                  Related edges
                </label>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => void loadGraph({ force: true })} disabled={isBusy("graph")} className="inline-flex h-9 items-center gap-2 border border-slate-300 px-3 text-xs text-slate-700 transition hover:border-slate-950">
                {isBusy("graph") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                刷新图谱
              </button>
              <button type="button" onClick={() => void handleGraphRebuild()} disabled={isBusy("graph-rebuild")} className="inline-flex h-9 items-center gap-2 bg-slate-950 px-3 text-xs text-white transition hover:bg-slate-800">
                {isBusy("graph-rebuild") ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                回填图投影
              </button>
            </div>
          </FunctionBlock>

          <FunctionBlock title="GraphRAG Planner" description="提交规划查询，结果进入下方统一输出区。">
            <form className="space-y-3" onSubmit={handleGraphPlannerSubmit}>
              <textarea
                value={graphPlannerQuery}
                onChange={(event) => setGraphPlannerQuery(event.target.value)}
                className="min-h-[112px] w-full border border-slate-300 px-3 py-2.5 text-sm leading-6 outline-none transition focus:border-slate-950"
                placeholder="输入一个问题，让系统判断图谱是否值得介入检索规划"
              />
              <button type="submit" disabled={isBusy("graph-rag") || !selectedKnowledgeBaseId} className="inline-flex h-9 items-center gap-2 bg-slate-950 px-3 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300">
                {isBusy("graph-rag") ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitBranch className="h-4 w-4" />}
                生成图谱规划
              </button>
            </form>
          </FunctionBlock>
        </div>

        <OutputWorkspace
          testId="graph-output-workspace"
          title="Graph Workspace"
          meta={graphData ? <span>{graphData.node_count} nodes · {graphData.edge_count} edges</span> : null}
          className="min-h-[calc(100vh-164px)]"
          contentClassName="h-[calc(100vh-216px)] min-h-[640px] p-0"
        >
          <div className="grid h-full min-h-0 gap-0 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="relative min-h-[640px] xl:order-1 xl:min-h-0">
              <Suspense fallback={<PanelSkeleton text="正在加载图谱组件" />}>
                <KnowledgeGraphCanvas data={graphData} selectedNodeId={selectedGraphNode?.id ?? null} onSelectNode={setSelectedGraphNode} />
              </Suspense>
              <div className="glass-panel absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 gap-2 rounded-full p-1.5">
                <button
                  type="button"
                  onClick={() => void loadGraph({ force: true })}
                  disabled={isBusy("graph")}
                  className="premium-action-btn flex size-10 items-center justify-center rounded-full text-text-dim disabled:cursor-not-allowed disabled:opacity-50"
                  title="Refresh graph"
                  aria-label="Refresh graph"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => void handleGraphRebuild()}
                  disabled={isBusy("graph-rebuild")}
                  className="premium-action-btn flex size-10 items-center justify-center rounded-full text-text-dim disabled:cursor-not-allowed disabled:opacity-50"
                  title="Run layout rebuild"
                  aria-label="Run layout rebuild"
                >
                  <Sparkles className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedGraphNode(null)}
                  className="premium-action-btn flex size-10 items-center justify-center rounded-full text-text-dim"
                  title="Clear selection"
                  aria-label="Clear selection"
                >
                  <GitBranch className="h-4 w-4" />
                </button>
              </div>
            </div>

            <aside className="space-y-4 border-t border-outline-variant/70 bg-surface-container-low/24 p-3 xl:order-2 xl:border-l xl:border-t-0">
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
              {graphPlannerResult ? (
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
              ) : null}
            </aside>
          </div>
        </OutputWorkspace>
      </div>
    );
  };

  const renderMemory = () => {
    return (
      <div className="space-y-5">
        <div data-testid="memory-function-grid" className="grid gap-3 xl:grid-cols-[0.72fr_1.28fr]">
          <FunctionBlock title="Memory Actions" description="只负责刷新和重建记忆库，结果统一进入下方输出区。">
            <div className="flex flex-wrap gap-2">
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
          </FunctionBlock>
        </div>

        <OutputWorkspace testId="memory-output-workspace" title="Memory Workspace" meta={memoryLibrary ? <span>{memoryLibrary.timeline.length} timeline entries</span> : null}>
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
        </OutputWorkspace>
      </div>
    );
  };

  const renderInsights = () => {
    return (
      <div className="space-y-6">
        <div data-testid="insights-function-grid" className="grid gap-3 xl:grid-cols-[0.85fr_1.15fr]">
          <FunctionBlock title="Insight Refresh" description="只负责拉取画像、证据、成长分析和报表。">
            <div className="flex flex-wrap items-center gap-2">
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
          </FunctionBlock>

          <FunctionBlock title="Growth Advice" description="只负责提交目标，生成内容进入下方输出区。">
            <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]" onSubmit={handleAdviceSubmit}>
              <input
                value={adviceGoal}
                onChange={(event) => setAdviceGoal(event.target.value)}
                className="h-10 w-full border border-slate-300 bg-transparent px-3 text-sm outline-none transition focus:border-slate-950"
                placeholder="可选：告诉系统你现在最想关注的目标"
              />
              <button
                type="submit"
                disabled={isBusy("advice") || !selectedKnowledgeBaseId}
                className="inline-flex h-10 items-center justify-center gap-2 bg-slate-950 px-4 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {isBusy("advice") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                生成建议
              </button>
            </form>
          </FunctionBlock>
        </div>

        <OutputWorkspace testId="insights-output-workspace" title="Insights Workspace" meta={<span>{recentDays} recent days</span>}>
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
                {advice ? (
                  <div className="space-y-4 text-sm leading-7 text-slate-700">
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
                ) : (
                  <EmptyState title="还没有成长建议" text="在上方 Growth Advice 输入目标后，建议会集中显示在这里。" />
                )}
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
        </OutputWorkspace>
      </div>
    );
  };

  const renderStitchDashboard = () => {
    const recentDocuments = documents.slice(0, 3);
    const taskItems = Object.values(taskMap).slice(0, 4);

    return (
      <div data-testid="stitch-dashboard-grid" className="mx-auto w-full max-w-[1200px] px-8 py-12">
        <div className="mb-12 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-[40px] font-bold leading-tight tracking-normal text-on-surface">Overview</h2>
            <p className="mt-2 text-base text-on-surface-variant">Your knowledge base at a glance.</p>
          </div>
          <button type="button" className="h-11 rounded-lg border border-border-subtle bg-surface-container-high/80 px-6 text-sm font-medium text-on-surface transition hover:bg-surface-raised">
            Export Activity
          </button>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-4">
          <div className="premium-card rounded-2xl p-8">
            <div className="premium-card-content">
              <div className="mb-10 flex items-start justify-between">
                <div className="rounded-xl border border-border-subtle/40 bg-surface-container-high/60 p-3 text-primary shadow-inner">
                  <HardDrive className="h-6 w-6" />
                </div>
                <span className="font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant/80">Storage</span>
              </div>
              <div className="text-[44px] font-bold leading-none tracking-normal text-on-surface">
                {Math.max(documents.length * 2.1, 1.2).toFixed(1)}
                <span className="ml-1.5 text-lg font-medium text-on-surface-variant">GB</span>
              </div>
              <div className="mt-7 h-2 overflow-hidden rounded-full border border-white/5 bg-surface-base shadow-inner">
                <div className="h-full w-[65%] rounded-full bg-gradient-to-r from-primary-container to-primary" />
              </div>
              <p className="mt-3 text-sm font-medium text-on-surface-variant/70">65% of 64GB used</p>
            </div>
          </div>

          <div className="premium-card rounded-2xl p-8">
            <div className="premium-card-content">
              <div className="mb-10 flex items-start justify-between">
                <div className="rounded-xl border border-border-subtle/40 bg-surface-container-high/60 p-3 text-primary shadow-inner">
                  <Cpu className="h-6 w-6" />
                </div>
                <span className="font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant/80">Memory</span>
              </div>
              <div className="text-[44px] font-bold leading-none tracking-normal text-on-surface">
                {(knowledgeBases.length + 1.4).toFixed(1)}
                <span className="ml-1.5 text-lg font-medium text-on-surface-variant">GB</span>
              </div>
              <div className="mt-7 h-2 overflow-hidden rounded-full border border-white/5 bg-surface-base shadow-inner">
                <div className="h-full w-[40%] bg-gradient-to-r from-primary-container to-primary" />
              </div>
              <p className="mt-3 text-sm font-medium text-on-surface-variant/70">Active processes: {activeTaskIds.length + 12}</p>
            </div>
          </div>

          <div className="premium-card rounded-2xl p-8 md:col-span-1 lg:col-span-2">
            <div className="premium-card-content flex h-full min-h-[230px] flex-col">
              <div className="mb-8 flex items-center justify-between gap-4">
                <h3 className="text-xl font-bold tracking-normal text-on-surface">Knowledge Graph Activity</h3>
                <span className="premium-tag rounded-full px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.16em] text-on-surface-variant">Last 7 Days</span>
              </div>
              <div className="flex flex-1 items-end gap-4 pt-4">
                {[30, 50, 40, 85, 60, 95, 70].map((height, index) => (
                  <div
                    key={`${height}-${index}`}
                    className={cn(
                      "w-full rounded-t-md bg-primary/15 transition hover:bg-primary/50",
                      index === 3 || index === 5 ? "bg-gradient-to-t from-primary/40 to-primary/70 shadow-[0_0_18px_rgba(124,58,237,0.25)]" : null,
                    )}
                    style={{ height: `${height}%` }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="premium-card rounded-2xl p-0 md:col-span-2">
            <div className="premium-card-content flex h-[450px] flex-col">
              <div className="flex items-center justify-between border-b border-white/5 bg-surface-container-low/30 p-8">
                <h3 className="text-xl font-bold tracking-normal text-on-surface">Recent Notes</h3>
                <button type="button" onClick={() => setView("notes")} className="font-mono text-xs font-bold uppercase tracking-wider text-primary">
                  View All
                </button>
              </div>
              <div className="code-scroll flex-1 overflow-y-auto p-2">
                {(recentDocuments.length ? recentDocuments : documents).slice(0, 3).map((document) => (
                  <button
                    key={document.id}
                    type="button"
                    onClick={() => {
                      setSelectedDocumentId(document.id);
                      setView("notes");
                    }}
                    className="group w-full rounded-xl border-l-2 border-transparent p-6 text-left transition hover:border-primary hover:bg-surface-container-high/50"
                  >
                    <div className="mb-2 flex items-baseline justify-between gap-4">
                      <h4 className="truncate text-[15px] font-semibold text-on-surface group-hover:text-primary">{document.file_name}</h4>
                      <span className="shrink-0 text-xs text-on-surface-variant/70">{formatDate(document.created_at)}</span>
                    </div>
                    <p className="line-clamp-2 text-[13px] leading-6 text-on-surface-variant">
                      {selectedKnowledgeBase?.description || "Updated references and indexed knowledge for this vault."}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="premium-card rounded-2xl p-0 md:col-span-2">
            <div className="premium-card-content flex h-[450px] flex-col">
              <div className="flex items-center justify-between border-b border-white/5 bg-surface-container-low/30 p-8">
                <h3 className="text-xl font-bold tracking-normal text-on-surface">Action Items</h3>
                <span className="premium-tag rounded-full px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.16em] text-on-surface-variant">
                  {Math.min(taskItems.length, 2)}/{Math.max(taskItems.length, 4)} Done
                </span>
              </div>
              <div className="flex-1 space-y-3 p-6">
                {(taskItems.length ? taskItems : [{ id: "review", status: "completed" }, { id: "draft", status: "pending" }]).slice(0, 4).map((task, index) => (
                  <label key={task.id} className="flex items-start gap-4 rounded-xl border border-transparent p-4 text-[15px] transition hover:border-border-subtle/30 hover:bg-surface-container-high/40">
                    <input type="checkbox" readOnly checked={index === 0 || String(task.status).toLowerCase() === "completed"} className="mt-1 size-4 rounded border-border-subtle bg-surface-container-highest accent-primary" />
                    <span className={cn("text-on-surface", index === 0 ? "text-on-surface-variant/70 line-through" : "font-medium")}>
                      {task.id === "review" ? "Review PR #402 for nav logic" : task.id === "draft" ? "Draft Q4 planning document" : `${task.id} - ${task.status}`}
                    </span>
                  </label>
                ))}
              </div>
              <div className="border-t border-white/5 bg-surface-container-lowest/30 p-6">
                <div className="relative">
                  <input className="premium-input h-12 w-full rounded-xl px-5 pr-12 text-sm text-on-surface placeholder:text-on-surface-variant/40" placeholder="Add new task..." />
                  <CirclePlus className="absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-on-surface-variant" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-20 flex justify-center font-mono text-xs uppercase tracking-[0.28em] text-on-surface-variant/30">// End of Dashboard</div>
      </div>
    );
  };

  const renderStitchNotes = () => {
    const activeDocument = selectedDocument ?? documents[0] ?? null;

    return (
      <div data-testid="stitch-notes-layout" className="grid h-screen min-h-0 grid-cols-[400px_minmax(0,1fr)] bg-surface-base">
        <aside className="min-h-0 border-r border-border-subtle bg-surface-muted">
          <div className="border-b border-border-subtle p-5">
            <label className="flex h-10 items-center gap-3 rounded-md border border-border-subtle bg-surface-base px-4 text-sm text-text-dim">
              <Search className="h-4 w-4" />
              <span>Search notes...</span>
            </label>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="premium-tag rounded-full px-3 py-1 text-sm font-semibold text-primary">#architecture</span>
              <span className="premium-tag rounded-full px-3 py-1 text-sm font-semibold text-on-surface-variant">#v2</span>
              <span className="premium-tag rounded-full px-3 py-1 text-sm font-semibold text-on-surface-variant">+ tag</span>
            </div>
          </div>
          <div className="code-scroll min-h-0 overflow-y-auto">
            {documents.map((document) => (
              <button
                key={document.id}
                type="button"
                onClick={() => setSelectedDocumentId(document.id)}
                className={cn(
                  "block w-full border-b border-border-subtle p-5 text-left transition hover:bg-surface-container",
                  activeDocument?.id === document.id && "border-l-4 border-l-primary bg-surface-container-high/60",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <h3 className="line-clamp-1 text-base font-semibold text-on-surface">{document.file_name}</h3>
                  <span className="shrink-0 text-xs text-on-surface-variant">{formatDate(document.created_at)}</span>
                </div>
                <p className="mt-3 line-clamp-2 text-sm leading-6 text-on-surface-variant">
                  {selectedKnowledgeBase?.description || "Refactored the core event loop to support asynchronous processing."}
                </p>
                <div className="mt-4 flex gap-2 text-xs text-on-surface-variant">
                  <span>#{document.file_type}</span>
                  <span>#{document.status}</span>
                </div>
              </button>
            ))}
          </div>
        </aside>

        <article className="min-h-0 overflow-y-auto bg-surface-base">
          <div className="flex h-20 items-center justify-between border-b border-border-subtle px-12">
            <div className="flex items-center gap-3 text-sm text-on-surface-variant">
              <span>Sanctuary</span>
              <span>/</span>
              <span>{selectedKnowledgeBase?.name || "Engineering"}</span>
              <span>/</span>
              <span className="rounded-md border border-border-subtle bg-surface-container px-3 py-1 text-on-surface">{activeDocument?.file_name || "Untitled"}</span>
            </div>
            <div className="flex items-center gap-5 text-on-surface-variant">
              <span className="inline-flex items-center gap-2 text-sm"><span className="size-2 rounded-full bg-emerald-500" />Saved</span>
              <RefreshCw className="h-4 w-4" />
              <MoreHorizontal className="h-4 w-4" />
            </div>
          </div>

          <div className="mx-auto max-w-[860px] px-12 py-16">
            <h1 className="text-[46px] font-bold leading-tight tracking-normal text-on-surface">{activeDocument?.file_name || "System Architecture Design v2"}</h1>
            <div className="mt-8 flex flex-wrap gap-3">
              <span className="inline-flex items-center gap-2 rounded-md border border-border-subtle bg-surface-container px-3 py-2 text-sm text-on-surface-variant"><Calendar className="h-4 w-4" />Oct 24, 2023</span>
              <span className="inline-flex items-center gap-2 rounded-md border border-border-subtle bg-surface-container px-3 py-2 text-sm text-on-surface-variant"><UserRound className="h-4 w-4" />{user?.display_name || user?.username || "Alex Dev"}</span>
              <span className="inline-flex items-center gap-2 rounded-md border border-border-subtle bg-surface-container px-3 py-2 text-sm text-on-surface-variant"><Tag className="h-4 w-4" />Add Tag...</span>
            </div>
            <div className="my-10 h-px bg-border-subtle" />
            <div className="space-y-8 text-[21px] leading-9 text-on-surface-variant">
              <p>This document outlines the proposed architectural changes for the core platform. The primary goal is to decouple the monolithic job queue into specialized services communicating via an event bus.</p>
              <h2 className="text-3xl font-bold text-on-surface">1. Event-Driven Messaging</h2>
              <p>We will replace the legacy polling mechanism with a robust pub/sub model. This ensures near real-time updates across client connections and reduces database load significantly during peak hours.</p>
              <div className="rounded-r-xl border-l-4 border-primary bg-primary/8 p-6">
                <div className="flex items-center gap-3 text-lg font-bold text-primary"><Info className="h-5 w-5" />Migration Requirement</div>
                <p className="mt-2 text-base leading-7 text-on-surface-variant">All existing worker nodes must be drained before the cutover to prevent message duplication in the new DLQ.</p>
              </div>
              <h3 className="text-2xl font-bold text-on-surface">Implementation Example</h3>
              <div className="overflow-hidden rounded-lg border border-border-subtle bg-surface-muted">
                <div className="border-b border-border-subtle px-5 py-3 font-mono text-xs font-bold uppercase tracking-widest text-on-surface-variant">Typescript</div>
                <pre className="overflow-x-auto p-5 font-mono text-sm leading-7 text-on-surface"><code>{`import { EventBus } from '@sanctuary/core';\n\nclass JobProcessor {\n  constructor(private bus: EventBus) {}\n}`}</code></pre>
              </div>
            </div>
          </div>
        </article>
      </div>
    );
  };

  const renderStitchAi = () => {
    return (
      <div data-testid="stitch-ai-layout" className="grid h-screen min-h-0 grid-cols-[280px_minmax(0,1fr)] bg-surface-base">
        <aside className="min-h-0 border-r border-border-subtle bg-surface-muted">
          <div className="border-b border-border-subtle px-5 py-4 font-mono text-xs font-bold uppercase tracking-widest text-on-surface-variant">Chat History</div>
          {["React Performance", "Database Schema Design", "Explain Quantum Gravity", "Weekly Meal Prep"].map((item, index) => (
            <button key={item} type="button" className={cn("flex h-12 w-full items-center gap-3 px-5 text-left text-sm text-on-surface-variant hover:bg-surface-container", index === 0 && "bg-surface-container text-on-surface")}>
              <MessageSquare className="h-4 w-4" />
              <span className="truncate">{item}</span>
            </button>
          ))}
        </aside>
        <section className="relative min-h-0 overflow-y-auto">
          <div className="flex h-16 items-center justify-between border-b border-border-subtle px-10">
            <nav className="flex h-full items-center gap-8 text-sm font-semibold text-on-surface-variant">
              <button type="button" className="h-full border-b-2 border-primary text-primary">Recent</button>
              <button type="button">Starred</button>
              <button type="button">Archived</button>
            </nav>
            <div className="flex items-center gap-5 text-on-surface-variant">
              <RefreshCw className="h-4 w-4" />
              <HelpCircle className="h-5 w-5" />
              <div className="size-9 rounded-full border border-border-subtle bg-surface-raised" />
            </div>
          </div>

          <div className="mx-auto max-w-[760px] px-10 pb-36 pt-10">
            <div className="mx-auto mb-9 w-fit rounded-full border border-border-subtle bg-surface-container px-4 py-1 text-sm text-on-surface-variant">Today</div>
            <div className="ml-auto max-w-[600px] rounded-xl border border-border-subtle bg-surface-container-high px-6 py-5 text-base leading-7 text-on-surface">
              I'm noticing some performance drops in my knowledge base when rendering long lists. How can I optimize this?
            </div>
            <div className="mt-9 flex gap-5">
              <div className="mt-1 size-9 shrink-0 rounded-md bg-primary-container" />
              <div className="premium-card flex-1 rounded-xl p-7">
                <div className="premium-card-content space-y-5 text-base leading-7 text-on-surface">
                  <p>This is a common issue when dealing with large knowledge lists. The most effective way to prevent unnecessary re-renders is by keeping note rows stable and virtualizing long panels.</p>
                  <p>Additionally, wrap expensive derived data before passing it to children. Here is an example in a dark-theme friendly code block:</p>
                  <div className="overflow-hidden rounded-xl border border-border-subtle bg-surface-muted">
                    <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3 font-mono text-xs font-semibold text-on-surface-variant">
                      React Optimization Example (jsx)
                      <span className="inline-flex items-center gap-2"><Copy className="h-4 w-4" />Copy</span>
                    </div>
                    <pre className="code-scroll max-h-[420px] overflow-auto p-5 font-mono text-sm leading-7 text-on-surface"><code>{`import React, { useMemo } from 'react';\n\nconst StableList = ({ data }) => {\n  const rows = useMemo(() => data.map(item => item.value), [data]);\n  return rows.map(row => <ListItem key={row} value={row} />);\n};`}</code></pre>
                  </div>
                  <p className="text-on-surface-variant">By wrapping derived data, the list avoids recalculating when unrelated parent state changes.</p>
                </div>
              </div>
            </div>
          </div>

          <form onSubmit={handleChatSubmit} className="absolute bottom-8 left-1/2 w-[min(760px,calc(100%-80px))] -translate-x-1/2">
            <div className="glass-panel flex min-h-20 items-center gap-4 rounded-2xl px-5">
              <input value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} className="flex-1 bg-transparent text-base text-on-surface outline-none placeholder:text-on-surface-variant" placeholder="Message Sanctuary AI..." />
              <button type="submit" disabled={isBusy("chat") || !selectedKnowledgeBaseId} className="flex size-12 items-center justify-center rounded-xl bg-primary text-on-primary disabled:opacity-60">
                {isBusy("chat") ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </button>
            </div>
            <p className="mt-5 text-center text-xs font-semibold tracking-wide text-on-surface-variant">AI responses may be inaccurate. Verify important technical information.</p>
          </form>
        </section>
      </div>
    );
  };

  const renderStitchGraph = () => {
    return (
      <div data-testid="stitch-graph-canvas" className="relative h-screen min-h-0 overflow-hidden bg-[#0a0a0c]">
        <Suspense fallback={<PanelSkeleton text="Loading graph" />}>
          <KnowledgeGraphCanvas data={graphData} selectedNodeId={selectedGraphNode?.id ?? null} onSelectNode={setSelectedGraphNode} />
        </Suspense>
        <div className="glass-panel absolute right-8 top-40 z-20 w-80 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-on-surface">Graph Controls</h3>
          <p className="mt-2 text-sm text-text-dim">Adjust graph filters and display options.</p>
          <div className="my-6 h-px bg-white/10" />
          <label className="text-sm font-medium text-on-surface">Search Nodes</label>
          <label className="premium-input mt-3 flex h-10 items-center gap-3 rounded-md bg-white px-3 text-slate-400">
            <Search className="h-4 w-4" />
            <span>Search...</span>
          </label>
          <div className="mt-4 flex gap-2">
            <span className="premium-tag rounded-md px-3 py-1 text-xs font-semibold text-text-dim">#design</span>
            <span className="premium-tag rounded-md px-3 py-1 text-xs font-semibold text-primary" data-active="true">#architecture</span>
            <span className="premium-tag rounded-md px-3 py-1 text-xs font-semibold text-text-dim">#notes</span>
          </div>
          <div className="my-6 h-px bg-white/10" />
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-on-surface">Show Labels</span>
              <span className="h-6 w-11 rounded-full bg-primary-container p-1 shadow-[0_0_12px_rgba(124,58,237,0.4)]"><span className="ml-auto block size-4 rounded-full bg-white" /></span>
            </div>
            <label className="block">
              <span className="flex justify-between text-sm"><span>Node Size</span><span className="text-text-dim">Adaptive</span></span>
              <input className="premium-range mt-3 w-full appearance-none bg-transparent" type="range" defaultValue={50} />
            </label>
            <label className="block">
              <span className="flex justify-between text-sm"><span>Link Forces</span><span className="text-text-dim">Tight</span></span>
              <input className="premium-range mt-3 w-full appearance-none bg-transparent" type="range" defaultValue={80} />
            </label>
          </div>
        </div>
        <div className="glass-panel absolute bottom-8 left-1/2 z-20 flex -translate-x-1/2 gap-2 rounded-full p-1.5">
          {[Search, RefreshCw, Settings, Send].map((Icon, index) => (
            <button key={index} type="button" className="premium-action-btn flex size-10 items-center justify-center rounded-full text-text-dim">
              <Icon className="h-4 w-4" />
            </button>
          ))}
        </div>
        <div className="glass-panel absolute bottom-8 right-8 z-20 h-32 w-48 rounded-xl p-5">
          <div className="relative h-full border border-primary/25 bg-primary/10">
            {[20, 36, 50, 62, 74].map((left, index) => <span key={left} className="absolute size-1.5 rounded-full bg-on-surface-variant" style={{ left: `${left}%`, top: `${30 + index * 10}%` }} />)}
          </div>
        </div>
      </div>
    );
  };

  const renderStitchSettings = () => {
    const settingsTabs: Array<{ icon: typeof UserRound; label: string }> = [
      { icon: UserRound, label: "Profile" },
      { icon: Palette, label: "Appearance" },
      { icon: Bell, label: "Notifications" },
      { icon: SlidersHorizontal, label: "Advanced" },
    ];

    return (
      <div data-testid="stitch-settings-layout" className="mx-auto w-full max-w-[1200px] px-8 py-12">
        <div className="mb-12">
          <h2 className="text-[40px] font-bold leading-tight tracking-normal text-on-surface">Settings</h2>
          <p className="mt-3 text-lg text-on-surface-variant">Manage your account settings and preferences.</p>
        </div>
        <div className="grid gap-5 lg:grid-cols-[285px_minmax(0,1fr)]">
          <nav className="space-y-3">
            {settingsTabs.map(({ icon: Icon, label }, index) => (
              <button key={label} type="button" className={cn("flex h-14 w-full items-center gap-4 rounded-lg px-6 text-left text-xl font-bold text-on-surface-variant", index === 0 && "border border-border-subtle bg-surface-container-high text-primary")}>
                <Icon className="h-6 w-6" />
                {label}
              </button>
            ))}
          </nav>
          <section className="premium-card rounded-xl p-10">
            <div className="premium-card-content">
              <h3 className="text-3xl font-bold text-on-surface">Profile Information</h3>
              <div className="my-7 h-px bg-border-subtle" />
              <div className="grid gap-10 lg:grid-cols-[260px_minmax(0,1fr)]">
                <div className="text-center">
                  <div className="mx-auto flex size-28 items-center justify-center rounded-full border-2 border-border-subtle bg-surface-base text-primary">
                    <UserRound className="h-12 w-12" />
                  </div>
                  <p className="mt-6 font-mono text-sm font-bold uppercase tracking-widest text-on-surface-variant">JPG, GIF or PNG. Max size of 800K</p>
                </div>
                <form className="grid gap-6">
                  <div className="grid gap-5 md:grid-cols-2">
                    <label className="grid gap-3 text-sm font-bold text-on-surface">
                      Username
                      <input className="premium-input h-12 rounded-lg px-5 text-base text-on-surface" value={user?.username || "alexmercer"} readOnly />
                    </label>
                    <label className="grid gap-3 text-sm font-bold text-on-surface">
                      Email Address
                      <input className="premium-input h-12 rounded-lg px-5 text-base text-on-surface" value={IS_PREVIEW_MODE ? "alex@sanctuary.app" : "user@mneme.local"} readOnly />
                    </label>
                  </div>
                  <label className="grid gap-3 text-sm font-bold text-on-surface">
                    Bio
                    <textarea className="premium-input min-h-32 rounded-lg px-5 py-4 text-base leading-7 text-on-surface" value="Digital architect and knowledge synthesizer. Building sanctuaries for thought." readOnly />
                  </label>
                  <p className="text-base text-on-surface-variant">Brief description for your profile. URLs are hyperlinked.</p>
                </form>
              </div>
              <div className="my-8 h-px bg-border-subtle" />
              <div className="flex justify-end">
                <button type="button" className="h-12 rounded-lg bg-primary-container px-8 text-xl font-bold text-on-primary-container">Save Changes</button>
              </div>
            </div>
          </section>
        </div>
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
    <div data-testid="obsidian-shell" className="mneme-workbench min-h-screen bg-surface-base text-on-surface">
      <div className="min-h-screen lg:grid lg:grid-cols-[256px_minmax(0,1fr)]">
        <aside
          data-testid="sanctuary-sidebar"
          className="hidden min-h-screen flex-col border-r border-outline-variant bg-surface-muted lg:flex"
        >
          <div className="flex items-center gap-3 p-6 pb-8">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary-container text-sm font-bold text-on-primary-container shadow-[0_0_15px_rgba(124,58,237,0.2)]">
              M
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-2xl font-bold tracking-normal text-primary">Mneme</h1>
              <p className="truncate font-mono text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant">Knowledge Base</p>
            </div>
          </div>

          <div className="px-6">
            <button
              type="button"
              onClick={() => {
                setView("dashboard");
                setWorkspaceCommandTab("create");
              }}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md border border-primary-container bg-primary-container px-4 text-sm font-medium text-on-primary-container shadow-[0_0_15px_rgba(124,58,237,0.2)] transition hover:bg-inverse-primary"
            >
              <Plus className="h-4 w-4" />
              New Vault
            </button>
          </div>

          <nav className="mt-8 flex flex-col gap-1 px-2">
            {VIEW_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setView(item.id)}
                aria-pressed={view === item.id}
                className={cn(
                  "relative flex min-h-10 items-center gap-3 rounded-r-md border-l-2 px-4 text-left text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
                  view === item.id
                    ? "border-primary bg-surface-container-low text-primary"
                    : "border-transparent text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface",
                )}
              >
                <item.icon className="h-4 w-4 shrink-0 text-primary" />
                <span className="truncate">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="mt-8 flex-1 overflow-y-auto px-4 pb-5">
            <section data-testid="sidebar-group-vaults" className="flex flex-col gap-2">
              <div className="flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-widest text-text-dim">
                <span>Vaults</span>
                <span>{knowledgeBases.length}</span>
              </div>
              <div className="flex flex-col gap-1">
                {knowledgeBases.length ? (
                  knowledgeBases.map((knowledgeBase) => (
                    <div
                      key={knowledgeBase.id}
                      className={cn(
                        "rounded-md border transition",
                        selectedKnowledgeBaseId === knowledgeBase.id
                          ? "border-border-subtle bg-surface-raised"
                          : "border-transparent hover:border-border-subtle hover:bg-surface-container",
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => setSelectedKnowledgeBaseId(knowledgeBase.id)}
                        className="flex w-full items-start gap-3 px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                      >
                        <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-on-surface">{knowledgeBase.name}</span>
                          <span className="mt-0.5 line-clamp-2 text-xs leading-5 text-text-dim">
                            {knowledgeBase.description || "No description"}
                          </span>
                        </span>
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="rounded-md border border-dashed border-border-subtle px-3 py-6 text-center text-xs leading-6 text-text-dim">
                    No vaults yet
                  </div>
                )}
              </div>
            </section>

            <section data-testid="sidebar-group-files" className="mt-6 flex flex-col gap-2">
              <div className="flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-widest text-text-dim">
                <span>Notes</span>
                <span>{indexedDocumentCount}/{documents.length}</span>
              </div>
              <div className="flex flex-col gap-1">
                {documents.length ? (
                  documents.map((document) => {
                    const task = documentTaskMap[document.id];
                    return (
                      <button
                        key={document.id}
                        type="button"
                        onClick={() => {
                          setSelectedDocumentId(document.id);
                          setView("notes");
                        }}
                        className={cn(
                          "flex w-full items-start gap-3 rounded-md px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
                          selectedDocumentId === document.id
                            ? "bg-primary-container/28 text-on-primary-container"
                            : "text-on-surface-variant hover:bg-surface-container",
                        )}
                      >
                        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm">{document.file_name}</span>
                          <span className="mt-1 flex items-center gap-2 text-[11px] text-text-dim">
                            <span className="truncate">{document.file_type}</span>
                            <span>{task?.status ?? document.status}</span>
                          </span>
                        </span>
                      </button>
                    );
                  })
                ) : (
                  <div className="rounded-md border border-dashed border-border-subtle px-3 py-6 text-center text-xs leading-6 text-text-dim">
                    No notes in this vault
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="border-t border-border-subtle p-6">
            <div className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-full border border-border-subtle bg-surface-raised text-primary">
                <UserRound className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold">{user?.display_name || user?.username}</div>
                <div className="truncate text-xs text-text-dim">{IS_PREVIEW_MODE ? "Preview" : "Online"}</div>
              </div>
              <button type="button" onClick={logout} className={iconButtonClass} title="Log out" aria-label="Log out">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </aside>

        <main className="flex min-h-screen flex-col overflow-hidden bg-surface-base">
          {view !== "graph" && view !== "notes" && view !== "ai" ? (
          <header data-testid="sanctuary-topbar" className="border-b border-border-subtle bg-surface-base/80 backdrop-blur-md lg:h-16">
            <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:h-full lg:px-8">
              <div className="flex min-w-0 flex-1 items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-md bg-primary-container text-sm font-bold text-white lg:hidden">M</div>
                <label className="hidden h-10 w-full max-w-sm items-center gap-3 rounded-md border border-border-subtle bg-surface-muted px-4 text-sm text-text-dim sm:flex">
                  <Search className="h-4 w-4 shrink-0" />
                  <span className="truncate">Search commands, notes</span>
                  <span className="ml-auto rounded border border-border-subtle px-1.5 py-0.5 font-mono text-[10px]">K</span>
                </label>
              </div>

              <nav className="hidden items-center gap-8 text-sm font-semibold text-on-surface-variant md:flex">
                <button type="button" onClick={() => setView("dashboard")} className="transition hover:text-on-surface">
                  Recent
                </button>
                <button type="button" onClick={() => setView("notes")} className="transition hover:text-on-surface">
                  Starred
                </button>
                <button type="button" onClick={() => setView("settings")} className="transition hover:text-on-surface">
                  Archived
                </button>
              </nav>

              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => token && user && selectedKnowledgeBaseId && void refreshDocuments(token, user, selectedKnowledgeBaseId)}
                  className={iconButtonClass}
                  title="Refresh files"
                  aria-label="Refresh files"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
                <button type="button" onClick={() => setView("settings")} className={iconButtonClass} title="Settings" aria-label="Settings">
                  <Settings className="h-4 w-4" />
                </button>
              </div>
            </div>

            <nav className="grid grid-cols-5 gap-1 border-t border-outline-variant px-2 py-2 lg:hidden">
              {VIEW_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setView(item.id)}
                  className={cn(
                    "flex min-h-11 flex-col items-center justify-center gap-1 rounded-md px-1 text-[11px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
                    view === item.id ? "bg-primary-container text-on-primary-container" : "text-text-dim hover:bg-surface-container",
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  <span className="truncate">{item.label}</span>
                </button>
              ))}
            </nav>

            {banner ? (
              <div
                className={cn(
                  "mx-4 mb-4 flex items-start gap-3 rounded-md border px-4 py-3 text-sm sm:mx-6 lg:mx-10",
                  banner.tone === "success" && "border-emerald-400/30 bg-emerald-500/10 text-emerald-300",
                  banner.tone === "error" && "border-red-400/30 bg-red-500/10 text-red-300",
                  banner.tone === "info" && "border-primary/30 bg-primary/10 text-on-primary-container",
                )}
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="flex-1">{banner.text}</div>
                <button type="button" onClick={() => setBanner(null)} className="text-current/70 transition hover:text-current">
                  Close
                </button>
              </div>
            ) : null}
          </header>
          ) : null}

          <div
            data-testid="obsidian-editor-pane"
            className={cn(
              "flex-1 overflow-y-auto",
              view === "graph" ? "p-0" : view === "notes" || view === "ai" ? "p-0" : "px-4 py-7 sm:px-6 lg:px-8 lg:py-8",
            )}
          >
            <div className={cn("w-full", view === "graph" || view === "notes" || view === "ai" ? "h-full max-w-none" : "mx-auto max-w-[1200px]")}>
              {view !== "graph" && view !== "notes" && view !== "ai" ? (
              <div data-testid="sanctuary-active-view" className="mb-10 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
                <div className="min-w-0">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-text-dim">{currentViewItem.hint}</div>
                  <h2 className="mt-3 truncate text-4xl font-bold text-on-surface sm:text-5xl">{currentViewItem.label}</h2>
                  <p className="mt-3 text-base text-on-surface-variant">
                    {selectedDocument?.file_name || selectedKnowledgeBase?.name || "Select a vault to begin."}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-widest text-text-dim">
                  <span>{knowledgeBases.length} vaults</span>
                  <span>{documents.length} notes</span>
                  <span>{indexedDocumentCount} indexed</span>
                  <span>{activeTaskIds.length} active</span>
                </div>
              </div>
              ) : null}

              {view === "dashboard" && <div data-testid="dashboard-overview">{renderStitchDashboard()}</div>}
              {view === "notes" && renderStitchNotes()}
              {view === "graph" && renderStitchGraph()}
              {view === "ai" && renderStitchAi()}
              {view === "settings" && renderStitchSettings()}
            </div>
          </div>

          {view !== "graph" && view !== "notes" && view !== "ai" ? (
          <footer className="flex min-h-9 items-center justify-between gap-3 border-t border-outline-variant bg-surface-base px-4 font-mono text-[11px] uppercase tracking-widest text-text-dim sm:px-6 lg:px-10">
            <span className="truncate">{selectedKnowledgeBase?.name || "No vault selected"}</span>
            <span className="hidden truncate sm:inline">{selectedDocument?.file_name || "No active note"}</span>
            <span>{API_BASE_URL.replace(/^https?:\/\//, "")}</span>
          </footer>
          ) : null}
        </main>
      </div>
    </div>
  );
}

export default App;
