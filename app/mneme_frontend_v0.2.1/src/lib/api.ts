import previewApi, { isPreviewMode, PREVIEW_API_BASE_URL, PREVIEW_TOKEN } from "./previewApi";
import type {
  AiModelConfigData,
  AiModelConfigListData,
  AgentStreamEvent,
  AgentRunData,
  AnswerMode,
  ApiResponse,
  AuthTokenData,
  ChatSessionDetailData,
  ChatSessionListData,
  ChatQueryData,
  CompanionAnswerResult,
  DocumentContentData,
  DocumentDeleteData,
  DocumentFolderData,
  DocumentIndexTaskData,
  DocumentListData,
  DocumentPreviewData,
  DocumentUploadData,
  DocumentVersionListData,
  EvidenceProfileData,
  GraphData,
  GraphProjectionRebuildData,
  GraphRagDecisionData,
  GrowthAdviceResult,
  GrowthReportResult,
  KnowledgeBaseAnalyticsReportData,
  KnowledgeBaseData,
  KnowledgeBaseDeleteData,
  KnowledgeBaseListData,
  MemoryGovernanceData,
  MemoryLibraryData,
  MemoryRebuildData,
  Neo4jHealthData,
  PersonalProfileResult,
  PlannedSupportData,
  ProductionReadinessReportData,
  ServiceHealthData,
  TaskActionData,
  TaskRecordData,
  UserPublic,
} from "../types";

export class ApiError extends Error {
  status: number;
  code?: number;

  constructor(message: string, status: number, code?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function resolveApiBaseUrl() {
  const envBase = import.meta.env.VITE_API_BASE_URL?.trim();
  if (envBase) {
    return envBase.replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    if (window.location.port === "3000") {
      return "http://127.0.0.1:8000";
    }
    return window.location.origin.replace(/\/+$/, "");
  }

  return "http://127.0.0.1:8000";
}

export const IS_PREVIEW_MODE = isPreviewMode();
export { PREVIEW_TOKEN };
export const API_BASE_URL = IS_PREVIEW_MODE ? PREVIEW_API_BASE_URL : resolveApiBaseUrl();

type Primitive = string | number | boolean;
type QueryValue = Primitive | null | undefined;

function buildQuery(params: Record<string, QueryValue>) {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") {
      return;
    }
    search.set(key, String(value));
  });

  const query = search.toString();
  return query ? `?${query}` : "";
}

type RequestOptions = Omit<RequestInit, "body"> & {
  token?: string;
  body?: BodyInit | Record<string, unknown> | null;
  rawBody?: boolean;
};

const inflightRequests = new Map<string, Promise<unknown>>();

function normalizeErrorDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") return String(item);
        const record = item as Record<string, unknown>;
        const location = Array.isArray(record.loc) ? record.loc.slice(1).join(".") : "";
        const message = typeof record.msg === "string" ? record.msg : "Invalid value";
        return location ? `${location}: ${message}` : message;
      })
      .join("; ");
  }
  return detail ? String(detail) : "Request failed";
}

function resolveRequestKey(path: string, options: RequestOptions) {
  const method = (options.method ?? "GET").toUpperCase();
  if ((method !== "GET" && method !== "HEAD") || options.signal) {
    return null;
  }

  return `${method}:${options.token ?? ""}:${path}`;
}

async function responseError(response: Response) {
  const text = await response.text();
  let payload: Record<string, unknown> | null = null;
  if (text) {
    try {
      payload = JSON.parse(text) as Record<string, unknown>;
    } catch {
      payload = null;
    }
  }
  const detail = (payload?.detail ?? payload?.message ?? text) || "Request failed";
  return new ApiError(normalizeErrorDetail(detail), response.status);
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const requestKey = resolveRequestKey(path, options);
  if (requestKey) {
    const inflight = inflightRequests.get(requestKey);
    if (inflight) {
      return inflight as Promise<T>;
    }
  }

  const executor = async () => {
  const headers = new Headers(options.headers);

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  let body: BodyInit | undefined;
  if (options.body instanceof FormData || options.body === null || options.rawBody) {
    body = options.body as BodyInit | undefined;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body,
  });

  const text = await response.text();
  let payload: ApiResponse<T> | Record<string, unknown> | null = null;

  if (text) {
    try {
      payload = JSON.parse(text) as ApiResponse<T> | Record<string, unknown>;
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const detail = (
      (payload && typeof payload === "object" && "detail" in payload ? payload.detail : undefined) ??
      (payload && typeof payload === "object" && "message" in payload ? payload.message : undefined) ??
      text
    ) || "Request failed";
    throw new ApiError(normalizeErrorDetail(detail), response.status);
  }

  if (!payload || typeof payload !== "object" || !("code" in payload)) {
    throw new ApiError("Unexpected API response.", response.status);
  }

  const apiPayload = payload as ApiResponse<T>;
  if (apiPayload.code !== 0) {
    throw new ApiError(apiPayload.message || "Request failed", response.status, apiPayload.code);
  }

  return apiPayload.data;
  };

  const nextRequest = executor();
  if (!requestKey) {
    return nextRequest;
  }

  inflightRequests.set(requestKey, nextRequest);
  try {
    return await nextRequest;
  } finally {
    inflightRequests.delete(requestKey);
  }
}

async function streamAgentEvents(
  path: string,
  token: string,
  body: Record<string, unknown>,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) throw await responseError(response);
  await consumeAgentEventStream(response, onEvent);
}

async function consumeAgentEventStream(
  response: Response,
  onEvent: (event: AgentStreamEvent) => void,
): Promise<void> {
  if (!response.body) throw new ApiError("Streaming response has no body.", response.status);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data) onEvent(JSON.parse(data) as AgentStreamEvent);
    }
    if (done) break;
  }
}

const realApi = {
  health() {
    return request<ServiceHealthData>("/health");
  },
  neo4jHealth() {
    return request<Neo4jHealthData>("/health/neo4j");
  },
  readiness() {
    return request<ProductionReadinessReportData>("/health/readiness");
  },
  documentationStatus() {
    return request<PlannedSupportData>("/support/documentation");
  },
  supportStatus() {
    return request<PlannedSupportData>("/support/contact");
  },
  register(payload: { username: string; password: string; display_name?: string | null }) {
    return request<UserPublic>("/auth/register", {
      method: "POST",
      body: {
        username: payload.username,
        password: payload.password,
        display_name: payload.display_name ?? null,
      },
    });
  },
  login(payload: { username: string; password: string }) {
    return request<AuthTokenData>("/auth/login", {
      method: "POST",
      body: payload,
    });
  },
  me(token: string) {
    return request<UserPublic>("/auth/me", { token });
  },
  listKnowledgeBases(userId: number, token: string) {
    return request<KnowledgeBaseListData>(`/users/${userId}/knowledge-bases`, { token });
  },
  createKnowledgeBase(
    userId: number,
    token: string,
    payload: { name: string; description?: string | null },
  ) {
    return request<KnowledgeBaseData>(`/users/${userId}/knowledge-bases`, {
      method: "POST",
      token,
      body: {
        name: payload.name,
        description: payload.description ?? null,
      },
    });
  },
  deleteKnowledgeBase(userId: number, knowledgeBaseId: string, token: string) {
    return request<KnowledgeBaseDeleteData>(`/users/${userId}/knowledge-bases/${knowledgeBaseId}`, {
      method: "DELETE",
      token,
    });
  },
  listDocuments(
    token: string,
    params: {
      userId?: number | null;
      knowledgeBaseId?: string | null;
    },
  ) {
    return request<DocumentListData>(
      `/kb/documents${buildQuery({
        user_id: params.userId ?? undefined,
        knowledge_base_id: params.knowledgeBaseId ?? undefined,
      })}`,
      { token },
    );
  },
  uploadDocument(
    token: string,
    payload: {
      file: File;
      userId?: number | null;
      knowledgeBaseId?: string | null;
      folderId?: string | null;
    },
  ) {
    const formData = new FormData();
    formData.append("file", payload.file);
    if (payload.userId) {
      formData.append("user_id", String(payload.userId));
    }
    if (payload.knowledgeBaseId) {
      formData.append("knowledge_base_id", payload.knowledgeBaseId);
    }
    if (payload.folderId) {
      formData.append("folder_id", payload.folderId);
    }

    return request<DocumentUploadData>("/kb/documents/upload", {
      method: "POST",
      token,
      body: formData,
      rawBody: true,
    });
  },
  indexDocument(documentId: string, token: string) {
    return request<DocumentIndexTaskData>(`/kb/documents/${documentId}/index`, {
      method: "POST",
      token,
    });
  },
  deleteDocument(documentId: string, token: string) {
    return request<DocumentDeleteData>(`/kb/documents/${documentId}`, {
      method: "DELETE",
      token,
    });
  },
  documentPreview(token: string, documentId: string, chunkLimit = 5) {
    return request<DocumentPreviewData>(`/kb/documents/${documentId}/preview${buildQuery({ chunk_limit: chunkLimit })}`, { token });
  },
  listDocumentFolders(token: string, knowledgeBaseId: string) {
    return request<DocumentFolderData[]>(
      `/kb/document-folders${buildQuery({ knowledge_base_id: knowledgeBaseId })}`,
      { token },
    );
  },
  createDocumentFolder(token: string, payload: { knowledge_base_id: string; parent_id: string; name: string }) {
    return request<DocumentFolderData>("/kb/document-folders", { method: "POST", token, body: payload });
  },
  updateDocumentFolder(token: string, folderId: string, payload: { name?: string; parent_id?: string }) {
    return request<DocumentFolderData>(`/kb/document-folders/${folderId}`, { method: "PATCH", token, body: payload });
  },
  deleteDocumentFolder(token: string, folderId: string) {
    return request<{ id: string }>(`/kb/document-folders/${folderId}`, { method: "DELETE", token });
  },
  moveDocument(token: string, documentId: string, folderId: string) {
    return request<{ document_id: string; folder_id: string }>(
      `/kb/document-folders/documents/${documentId}/move`,
      { method: "POST", token, body: { folder_id: folderId } },
    );
  },
  documentContent(token: string, documentId: string, options: { signal?: AbortSignal } = {}) {
    return request<DocumentContentData>(`/kb/documents/${documentId}/content`, { token, signal: options.signal });
  },
  documentVersions(token: string, documentId: string) {
    return request<DocumentVersionListData>(`/kb/documents/${documentId}/versions`, { token });
  },
  async documentRawBlob(token: string, documentId: string, disposition: "inline" | "attachment" = "inline", options: { signal?: AbortSignal } = {}) {
    const response = await fetch(
      `${API_BASE_URL}/kb/documents/${documentId}/raw${buildQuery({ disposition })}`,
      { headers: { Authorization: `Bearer ${token}` }, signal: options.signal },
    );
    if (!response.ok) throw await responseError(response);
    return response.blob();
  },
  getTask(taskId: string, token: string, options: { signal?: AbortSignal } = {}) {
    return request<TaskRecordData>(`/tasks/${taskId}`, { token, signal: options.signal });
  },
  cancelTask(taskId: string, token: string) {
    return request<TaskActionData>(`/tasks/${taskId}/cancel`, {
      method: "POST",
      token,
    });
  },
  retryTask(taskId: string, token: string) {
    return request<TaskActionData>(`/tasks/${taskId}/retry`, {
      method: "POST",
      token,
    });
  },
  chatQuery(
    token: string,
    payload: { question: string; knowledge_base_id: string; answer_mode: AnswerMode; top_k?: number; session_id?: string | null },
  ) {
    return request<ChatQueryData>("/kb/chat/query", {
      method: "POST",
      token,
      body: {
        question: payload.question,
        knowledge_base_id: payload.knowledge_base_id,
        answer_mode: payload.answer_mode,
        top_k: payload.top_k ?? 4,
        session_id: payload.session_id ?? null,
      },
    });
  },
  listChatSessions(token: string, knowledgeBaseId: string) {
    return request<ChatSessionListData>(`/kb/chat/sessions${buildQuery({ knowledge_base_id: knowledgeBaseId })}`, { token });
  },
  createChatSession(token: string, payload: { knowledge_base_id: string; title?: string | null }) {
    return request<ChatSessionDetailData["session"]>("/kb/chat/sessions", {
      method: "POST",
      token,
      body: {
        knowledge_base_id: payload.knowledge_base_id,
        title: payload.title ?? null,
      },
    });
  },
  getChatSession(token: string, sessionId: string) {
    return request<ChatSessionDetailData>(`/kb/chat/sessions/${sessionId}`, { token });
  },
  deleteChatSession(token: string, sessionId: string) {
    return request<{ session_id: string; deleted_count: number }>(`/kb/chat/sessions/${sessionId}`, {
      method: "DELETE",
      token,
    });
  },
  sendChatSessionMessage(token: string, sessionId: string, payload: { question: string; answer_mode: AnswerMode; top_k?: number }) {
    return request<ChatSessionDetailData>(`/kb/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      token,
      body: {
        question: payload.question,
        answer_mode: payload.answer_mode,
        top_k: payload.top_k ?? 4,
      },
    });
  },
  streamChatSessionMessage(
    token: string,
    sessionId: string,
    payload: { question: string; answer_mode: AnswerMode; top_k?: number },
    onEvent: (event: AgentStreamEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) {
    return streamAgentEvents(
      `/kb/chat/sessions/${sessionId}/messages/stream`,
      token,
      {
        question: payload.question,
        answer_mode: payload.answer_mode,
        top_k: payload.top_k ?? 4,
      },
      onEvent,
      options.signal,
    );
  },
  createAgentRun(
    token: string,
    sessionId: string,
    payload: { question: string; answer_mode: AnswerMode; top_k?: number },
  ) {
    return request<AgentRunData>(`/kb/chat/sessions/${sessionId}/runs`, {
      method: "POST",
      token,
      body: {
        question: payload.question,
        answer_mode: payload.answer_mode,
        top_k: payload.top_k ?? 4,
      },
    });
  },
  async streamAgentRun(
    token: string,
    runId: string,
    onEvent: (event: AgentStreamEvent) => void,
    options: { signal?: AbortSignal; cursor?: string } = {},
  ) {
    const response = await fetch(`${API_BASE_URL}/kb/chat/runs/${runId}/stream`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "text/event-stream",
        ...(options.cursor ? { "Last-Event-ID": options.cursor } : {}),
      },
      signal: options.signal,
    });
    if (!response.ok) throw await responseError(response);
    await consumeAgentEventStream(response, onEvent);
  },
  getAgentRun(token: string, runId: string) {
    return request<AgentRunData>(`/kb/chat/runs/${runId}`, { token });
  },
  abortAgentRun(token: string, runId: string) {
    return request<AgentRunData>(`/kb/chat/runs/${runId}/abort`, { method: "POST", token });
  },
  listAiModelConfigs(token: string) {
    return request<AiModelConfigListData>("/settings/ai-models", { token });
  },
  createAiModelConfig(
    token: string,
    payload: {
      label: string;
      provider: string;
      base_url: string;
      model_name: string;
      api_key?: string | null;
      temperature?: number;
      context_window?: number;
      is_default?: boolean;
      enabled?: boolean;
    },
  ) {
    return request<AiModelConfigData>("/settings/ai-models", {
      method: "POST",
      token,
      body: payload,
    });
  },
  updateAiModelConfig(token: string, configId: string, payload: Partial<{ label: string; provider: string; base_url: string; model_name: string; api_key: string | null; temperature: number; context_window: number; enabled: boolean }>) {
    return request<AiModelConfigData>(`/settings/ai-models/${configId}`, {
      method: "PATCH",
      token,
      body: payload,
    });
  },
  testAiModelConfig(token: string, configId: string) {
    return request<{ config_id: string; ok: boolean; message: string }>(`/settings/ai-models/${configId}/test`, {
      method: "POST",
      token,
    });
  },
  setDefaultAiModelConfig(token: string, configId: string) {
    return request<AiModelConfigData>(`/settings/ai-models/${configId}/default`, {
      method: "POST",
      token,
    });
  },
  deleteAiModelConfig(token: string, configId: string) {
    return request<{ config_id: string; deleted_count: number }>(`/settings/ai-models/${configId}`, {
      method: "DELETE",
      token,
    });
  },
  companionReply(
    token: string,
    knowledgeBaseId: string,
    payload: { question: string; top_k?: number },
  ) {
    return request<CompanionAnswerResult>(`/companion/knowledge-bases/${knowledgeBaseId}/reply`, {
      method: "POST",
      token,
      body: {
        question: payload.question,
        top_k: payload.top_k ?? 4,
      },
    });
  },
  getUserGraph(
    token: string,
    params: {
      include_memory?: boolean;
      include_relationships?: boolean;
      min_shared_memory_count?: number;
      min_relationship_score?: number;
      max_related_edges?: number;
    },
  ) {
    return request<GraphData>(
      `/graph${buildQuery({
        include_memory: params.include_memory,
        include_relationships: params.include_relationships,
        min_shared_memory_count: params.min_shared_memory_count,
        min_relationship_score: params.min_relationship_score,
        max_related_edges: params.max_related_edges,
      })}`,
      { token },
    );
  },
  getKnowledgeBaseGraph(
    token: string,
    knowledgeBaseId: string,
    params: {
      include_memory?: boolean;
      include_relationships?: boolean;
      min_shared_memory_count?: number;
      min_relationship_score?: number;
      max_related_edges?: number;
    },
  ) {
    return request<GraphData>(
      `/graph/knowledge-bases/${knowledgeBaseId}${buildQuery({
        include_memory: params.include_memory,
        include_relationships: params.include_relationships,
        min_shared_memory_count: params.min_shared_memory_count,
        min_relationship_score: params.min_relationship_score,
        max_related_edges: params.max_related_edges,
      })}`,
      { token },
    );
  },
  getDocumentGraph(
    token: string,
    documentId: string,
    params: {
      include_memory?: boolean;
      include_relationships?: boolean;
      min_shared_memory_count?: number;
      min_relationship_score?: number;
      max_related_edges?: number;
      relationship_scope?: string;
    },
  ) {
    return request<GraphData>(
      `/graph/documents/${documentId}${buildQuery({
        include_memory: params.include_memory,
        include_relationships: params.include_relationships,
        min_shared_memory_count: params.min_shared_memory_count,
        min_relationship_score: params.min_relationship_score,
        max_related_edges: params.max_related_edges,
        relationship_scope: params.relationship_scope,
      })}`,
      { token },
    );
  },
  rebuildUserGraph(token: string) {
    return request<GraphProjectionRebuildData>("/graph/rebuild", {
      method: "POST",
      token,
    });
  },
  rebuildKnowledgeBaseGraph(token: string, knowledgeBaseId: string) {
    return request<GraphProjectionRebuildData>(`/graph/knowledge-bases/${knowledgeBaseId}/rebuild`, {
      method: "POST",
      token,
    });
  },
  graphRag(
    token: string,
    knowledgeBaseId: string,
    params: { query: string; top_k?: number; max_expansions?: number },
  ) {
    return request<GraphRagDecisionData>(
      `/graph/knowledge-bases/${knowledgeBaseId}/rag${buildQuery({
        query: params.query,
        top_k: params.top_k ?? 6,
        max_expansions: params.max_expansions ?? 8,
      })}`,
      { token },
    );
  },
  memoryLibrary(token: string, knowledgeBaseId: string) {
    return request<MemoryLibraryData>(`/memory/knowledge-bases/${knowledgeBaseId}/library`, { token });
  },
  memoryGovernance(token: string, knowledgeBaseId: string) {
    return request<MemoryGovernanceData>(`/memory/knowledge-bases/${knowledgeBaseId}/governance`, { token });
  },
  rebuildMemory(token: string, knowledgeBaseId: string) {
    return request<MemoryRebuildData>(`/memory/knowledge-bases/${knowledgeBaseId}/rebuild`, {
      method: "POST",
      token,
    });
  },
  documentMemory(token: string, documentId: string) {
    return request<MemoryLibraryData>(`/memory/documents/${documentId}/library`, { token });
  },
  profile(token: string, knowledgeBaseId: string) {
    return request<PersonalProfileResult>(`/profile/knowledge-bases/${knowledgeBaseId}`, { token });
  },
  profileEvidence(token: string, knowledgeBaseId: string, recentDays = 30) {
    return request<EvidenceProfileData>(
      `/profile/knowledge-bases/${knowledgeBaseId}/evidence${buildQuery({ recent_days: recentDays })}`,
      { token },
    );
  },
  growth(token: string, knowledgeBaseId: string, recentDays = 30) {
    return request<GrowthReportResult>(
      `/analysis/knowledge-bases/${knowledgeBaseId}/growth${buildQuery({ recent_days: recentDays })}`,
      { token },
    );
  },
  analytics(token: string, knowledgeBaseId: string) {
    return request<KnowledgeBaseAnalyticsReportData>(`/analysis/knowledge-bases/${knowledgeBaseId}/analytics`, {
      token,
    });
  },
  advice(token: string, knowledgeBaseId: string, focusGoal?: string | null) {
    return request<GrowthAdviceResult>(`/advice/knowledge-bases/${knowledgeBaseId}`, {
      method: "POST",
      token,
      body: {
        focus_goal: focusGoal ?? null,
      },
    });
  },
};

export const api: typeof realApi = IS_PREVIEW_MODE ? previewApi : realApi;
