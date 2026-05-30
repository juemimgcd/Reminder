import type {
  ApiResponse,
  AuthTokenData,
  ChatQueryData,
  CompanionAnswerResult,
  DocumentDeleteData,
  DocumentIndexTaskData,
  DocumentListData,
  DocumentUploadData,
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

export const API_BASE_URL = resolveApiBaseUrl();

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

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
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
    const detail =
      (payload && typeof payload === "object" && "detail" in payload ? payload.detail : undefined) ??
      (payload && typeof payload === "object" && "message" in payload ? payload.message : undefined) ??
      text ??
      "Request failed";
    throw new ApiError(String(detail), response.status);
  }

  if (!payload || typeof payload !== "object" || !("code" in payload)) {
    throw new ApiError("Unexpected API response.", response.status);
  }

  const apiPayload = payload as ApiResponse<T>;
  if (apiPayload.code !== 0) {
    throw new ApiError(apiPayload.message || "Request failed", response.status, apiPayload.code);
  }

  return apiPayload.data;
}

export const api = {
  health() {
    return request<ServiceHealthData>("/health");
  },
  neo4jHealth() {
    return request<Neo4jHealthData>("/health/neo4j");
  },
  readiness() {
    return request<ProductionReadinessReportData>("/health/readiness");
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
  getTask(taskId: string, token: string) {
    return request<TaskRecordData>(`/tasks/${taskId}`, { token });
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
    payload: { question: string; knowledge_base_id: string; top_k?: number; session_id?: string | null },
  ) {
    return request<ChatQueryData>("/kb/chat/query", {
      method: "POST",
      token,
      body: {
        question: payload.question,
        knowledge_base_id: payload.knowledge_base_id,
        top_k: payload.top_k ?? 4,
        session_id: payload.session_id ?? null,
      },
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
