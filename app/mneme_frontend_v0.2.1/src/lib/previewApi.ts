import type {
  AiModelConfigData,
  AiModelConfigListData,
  AuthTokenData,
  ChatMessageData,
  ChatQueryData,
  ChatSessionData,
  ChatSessionDetailData,
  CompanionAnswerResult,
  DocumentDeleteData,
  DocumentIndexTaskData,
  DocumentListItem,
  DocumentPreviewData,
  DocumentUploadData,
  EvidenceProfileData,
  GraphData,
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
  PlannedSupportData,
  ProductionReadinessReportData,
  ServiceHealthData,
  TaskActionData,
  TaskRecordData,
  UserPublic,
} from "../types";

export const PREVIEW_TOKEN = "mneme-preview-token";
export const PREVIEW_API_BASE_URL = "Preview demo data";

const now = "2026-06-24T08:00:00.000Z";

const previewUser: UserPublic = {
  id: 1,
  username: "mneme.preview",
  display_name: "Preview User",
  avatar_url: "",
};

let knowledgeBases: KnowledgeBaseData[] = [
  {
    id: "kb-demo-research",
    user_id: previewUser.id,
    name: "Demo Research Vault",
    description: "A populated preview vault for exploring Mneme without a backend.",
    is_default: true,
    created_at: "2026-06-20T09:00:00.000Z",
  },
  {
    id: "kb-product-notes",
    user_id: previewUser.id,
    name: "Product Notes",
    description: "Example planning notes, decisions, and meeting summaries.",
    is_default: false,
    created_at: "2026-06-22T11:30:00.000Z",
  },
];

let documents: DocumentListItem[] = [
  {
    id: "doc-zettelkasten",
    user_id: previewUser.id,
    knowledge_base_id: "kb-demo-research",
    file_name: "zettelkasten-principles.md",
    file_type: "markdown",
    status: "indexed",
    created_at: "2026-06-20T10:15:00.000Z",
  },
  {
    id: "doc-memory-graph",
    user_id: previewUser.id,
    knowledge_base_id: "kb-demo-research",
    file_name: "memory-graph-design.pdf",
    file_type: "pdf",
    status: "indexed",
    created_at: "2026-06-21T14:45:00.000Z",
  },
  {
    id: "doc-roadmap",
    user_id: previewUser.id,
    knowledge_base_id: "kb-product-notes",
    file_name: "preview-roadmap.md",
    file_type: "markdown",
    status: "parsed",
    created_at: "2026-06-23T16:20:00.000Z",
  },
];

let tasks: Record<string, TaskRecordData> = {};

let chatSessions: ChatSessionData[] = [
  {
    id: "chat-preview-vault-review",
    user_id: previewUser.id,
    knowledge_base_id: "kb-demo-research",
    title: "Preview Vault Review",
    message_count: 2,
    last_message_at: now,
    archived_at: null,
    created_at: now,
    updated_at: now,
  },
];

let chatMessages: Record<string, ChatMessageData[]> = {
  "chat-preview-vault-review": [
    {
      id: "msg-preview-user-1",
      session_id: "chat-preview-vault-review",
      user_id: previewUser.id,
      knowledge_base_id: "kb-demo-research",
      role: "user",
      content: "How should I review this vault?",
      sources: [],
      citations: [],
      route: null,
      model_config_id: "model-preview-deepseek",
      created_at: "2026-06-24T08:01:00.000Z",
    },
    {
      id: "msg-preview-assistant-1",
      session_id: "chat-preview-vault-review",
      user_id: previewUser.id,
      knowledge_base_id: "kb-demo-research",
      role: "assistant",
      content: "Start with the indexed documents, then inspect graph neighborhoods that connect memory entries to source notes.",
      sources: [],
      citations: [],
      route: null,
      model_config_id: "model-preview-deepseek",
      created_at: "2026-06-24T08:01:10.000Z",
    },
  ],
};

let aiModelConfigs: AiModelConfigData[] = [
  {
    id: "model-preview-deepseek",
    user_id: previewUser.id,
    label: "Preview DeepSeek",
    provider: "deepseek",
    base_url: "https://api.deepseek.com",
    model_name: "deepseek-v4-flash",
    temperature: 0,
    context_window: 64000,
    is_default: true,
    enabled: true,
    has_api_key: true,
    created_at: now,
    updated_at: now,
  },
];

const documentPreviews: Record<string, DocumentPreviewData> = {
  "doc-zettelkasten": {
    document_id: "doc-zettelkasten",
    knowledge_base_id: "kb-demo-research",
    file_name: "zettelkasten-principles.md",
    file_type: "markdown",
    status: "indexed",
    summary: "Atomic notes are easier to recombine when each note carries a clear relationship to its neighbors.",
    chunks: [
      {
        chunk_id: "chunk-zettel-1",
        chunk_index: 0,
        text: "Atomic notes are easier to recombine across contexts when links include intent.",
        page_no: null,
        section_title: "Atomicity",
      },
    ],
    memory_entries: [
      {
        entry_id: "memory-atomic",
        entry_name: "Atomic notes",
        entry_type: "principle",
        summary: "Small notes are easier to recombine across contexts.",
        importance_score: 0.86,
      },
    ],
  },
  "doc-memory-graph": {
    document_id: "doc-memory-graph",
    knowledge_base_id: "kb-demo-research",
    file_name: "memory-graph-design.pdf",
    file_type: "pdf",
    status: "indexed",
    summary: "Graph neighborhoods can provide retrieval context before vector search, improving answer grounding and source inspection.",
    chunks: [
      {
        chunk_id: "chunk-graph-1",
        chunk_index: 0,
        text: "Graph neighborhoods can provide retrieval context before vector search.",
        page_no: 2,
        section_title: "Retrieval Context",
      },
    ],
    memory_entries: [
      {
        entry_id: "memory-context",
        entry_name: "Contextual recall",
        entry_type: "insight",
        summary: "Graph neighborhoods can provide retrieval context before vector search.",
        importance_score: 0.82,
      },
    ],
  },
};

function delay<T>(value: T): Promise<T> {
  return Promise.resolve(value);
}

function requireKnowledgeBase(knowledgeBaseId: string) {
  return knowledgeBases.find((item) => item.id === knowledgeBaseId) ?? knowledgeBases[0];
}

function createTask(taskId: string, targetId: string, status = "completed"): TaskRecordData {
  const task: TaskRecordData = {
    id: taskId,
    task_type: "preview_task",
    target_id: targetId,
    status,
    progress_stage: "preview",
    queue_name: "preview",
    celery_task_id: null,
    attempt_count: 1,
    max_attempts: 3,
    result_summary: "Preview mode simulated this task locally.",
    error_message: null,
    created_at: now,
    updated_at: now,
  };
  tasks[task.id] = task;
  return task;
}

const previewGraph: GraphData = {
  scope: "knowledge_base",
  generated_at: now,
  root_node_id: "node-kb-demo",
  include_memory: true,
  include_relationships: true,
  relationship_strategy: "preview",
  relationship_scope: "knowledge_base",
  min_shared_memory_count: 2,
  min_relationship_score: 0.35,
  max_related_edges: 80,
  node_count: 6,
  edge_count: 6,
  node_type_counts: { knowledge_base: 1, document: 2, memory_entry: 3 },
  edge_type_counts: { contains: 2, reinforces: 2, references: 2 },
  nodes: [
    { id: "node-kb-demo", entity_id: "kb-demo-research", node_type: "knowledge_base", label: "Demo Research Vault", parent_id: null, depth: 0, metadata: { status: "preview" } },
    { id: "node-doc-zettel", entity_id: "doc-zettelkasten", node_type: "document", label: "Zettelkasten Principles", parent_id: "node-kb-demo", depth: 1, metadata: { status: "indexed" } },
    { id: "node-doc-graph", entity_id: "doc-memory-graph", node_type: "document", label: "Memory Graph Design", parent_id: "node-kb-demo", depth: 1, metadata: { status: "indexed" } },
    { id: "node-memory-atomic", entity_id: "memory-atomic", node_type: "memory_entry", label: "Atomic notes", parent_id: "node-doc-zettel", depth: 2, metadata: { importance: 0.86 } },
    { id: "node-memory-links", entity_id: "memory-links", node_type: "memory_entry", label: "Bidirectional links", parent_id: "node-doc-zettel", depth: 2, metadata: { importance: 0.78 } },
    { id: "node-memory-context", entity_id: "memory-context", node_type: "memory_entry", label: "Contextual recall", parent_id: "node-doc-graph", depth: 2, metadata: { importance: 0.82 } },
  ],
  edges: [
    { id: "edge-1", source: "node-kb-demo", target: "node-doc-zettel", edge_type: "contains", metadata: {} },
    { id: "edge-2", source: "node-kb-demo", target: "node-doc-graph", edge_type: "contains", metadata: {} },
    { id: "edge-3", source: "node-doc-zettel", target: "node-memory-atomic", edge_type: "references", metadata: {} },
    { id: "edge-4", source: "node-doc-zettel", target: "node-memory-links", edge_type: "references", metadata: {} },
    { id: "edge-5", source: "node-memory-links", target: "node-memory-context", edge_type: "reinforces", metadata: { score: 0.72 } },
    { id: "edge-6", source: "node-doc-graph", target: "node-memory-context", edge_type: "references", metadata: {} },
  ],
};

const memoryLibraryData: MemoryLibraryData = {
  timeline: [
    { entry_id: "memory-atomic", entry_name: "Atomic notes", entry_type: "principle", summary: "Small notes are easier to recombine across contexts.", created_at: "2026-06-20T10:20:00.000Z" },
    { entry_id: "memory-links", entry_name: "Bidirectional links", entry_type: "practice", summary: "Links should carry reasons, not just pointers.", created_at: "2026-06-21T09:40:00.000Z" },
    { entry_id: "memory-context", entry_name: "Contextual recall", entry_type: "insight", summary: "Graph neighborhoods can provide retrieval context before vector search.", created_at: "2026-06-22T12:00:00.000Z" },
  ],
  by_type: {
    principle: ["Atomic notes"],
    practice: ["Bidirectional links"],
    insight: ["Contextual recall"],
  },
  by_theme: [
    { theme_name: "Knowledge structure", entries: ["Atomic notes", "Bidirectional links"], count: 2 },
    { theme_name: "Retrieval quality", entries: ["Contextual recall"], count: 1 },
  ],
};

const memoryGovernanceData: MemoryGovernanceData = {
  knowledge_base_id: "kb-demo-research",
  raw_entry_count: 9,
  canonical_memory_count: 3,
  relation_count: 2,
  relation_type_counts: { reinforces: 2 },
  canonical_memories: [
    { canonical_id: "canonical-atomic", entry_name: "Atomic notes", entry_type: "principle", summary: "Keep notes scoped to one idea.", representative_entry_id: "memory-atomic", entry_ids: ["memory-atomic"], evidence_count: 3, document_count: 1, importance_score: 0.86, status: "active", first_seen_at: "2026-06-20T10:20:00.000Z", last_seen_at: now },
    { canonical_id: "canonical-links", entry_name: "Bidirectional links", entry_type: "practice", summary: "Links are stronger when they include intent.", representative_entry_id: "memory-links", entry_ids: ["memory-links"], evidence_count: 4, document_count: 2, importance_score: 0.78, status: "active", first_seen_at: "2026-06-21T09:40:00.000Z", last_seen_at: now },
  ],
  relations: [
    { relation_id: "rel-1", source_entry_id: "memory-links", target_entry_id: "memory-context", relation_type: "reinforces", confidence: 0.74, reason: "Link context improves recall quality." },
    { relation_id: "rel-2", source_entry_id: "memory-atomic", target_entry_id: "memory-links", relation_type: "reinforces", confidence: 0.69, reason: "Atomic notes make meaningful links easier." },
  ],
};

const profileData: PersonalProfileResult = {
  knowledge_base_id: "kb-demo-research",
  entry_count: 3,
  profile_summary: "The preview profile emphasizes structured thinking, careful retrieval, and iterative knowledge design.",
  main_themes: [
    { theme_name: "Structured memory", reason: "Most entries discuss durable organization patterns.", evidence_entries: ["memory-atomic", "memory-links"] },
    { theme_name: "Retrieval confidence", reason: "Graph context is repeatedly tied to answer quality.", evidence_entries: ["memory-context"] },
  ],
  ability_tags: [
    { ability_name: "Systems thinking", reason: "Connects UX, graph structure, and retrieval workflows.", evidence_entries: ["memory-links"] },
  ],
  expression_style: "Concise, analytical, and implementation-oriented.",
  growth_focus: ["Turn repeated insights into explicit operating rules", "Track uncertainty in generated answers"],
};

const profileEvidenceData: EvidenceProfileData = {
  knowledge_base_id: "kb-demo-research",
  entry_count: 3,
  canonical_memory_count: 3,
  stable_traits: [{ trait_name: "Analytical", summary: "Prefers evidence-backed conclusions.", confidence: "high", evidence_entry_ids: ["memory-context"] }],
  recent_focus: [{ trait_name: "Previewability", summary: "Separates frontend exploration from backend availability.", confidence: "medium", evidence_entry_ids: ["memory-links"] }],
  goals: [{ trait_name: "Better demos", summary: "Make the workbench explorable with representative data.", confidence: "high", evidence_entry_ids: ["memory-atomic"] }],
  risks: [{ risk_name: "Mock drift", summary: "Preview data can fall behind API shape if untested.", relation_type: "risk", evidence_entry_ids: ["memory-context"] }],
  topic_timeline: [{ topic_name: "Preview mode", entry_type: "implementation", entry_count: 3, first_seen_at: "2026-06-20T10:20:00.000Z", last_seen_at: now, evidence_entry_ids: ["memory-atomic", "memory-links"] }],
  evidence: [{ entry_id: "memory-context", entry_name: "Contextual recall", entry_type: "insight", summary: "Graph neighborhoods can provide retrieval context.", evidence_text: "Graph context helps explain why a source is useful.", document_id: "doc-memory-graph", chunk_id: "chunk-graph-1", created_at: now }],
  tool_calls: [{ tool_name: "preview_api", input: { mode: "preview" }, output_count: 3, evidence_entry_ids: ["memory-atomic"] }],
  uncertainty: "Preview data is illustrative and does not represent a live backend.",
};

const growthData: GrowthReportResult = {
  knowledge_base_id: "kb-demo-research",
  analysis_window: "Last 30 days",
  stage_summary: "The vault is moving from raw notes toward reusable memory structures.",
  recent_focus: ["Preview mode", "Knowledge graph usability", "Evidence-backed answers"],
  theme_changes: [{ theme_name: "Operational clarity", change_type: "increased", reason: "More notes now map ideas to actions.", evidence_entries: ["memory-links"] }],
  highlights: ["Core workspace has representative documents", "Graph and memory views have enough data to inspect layout"],
  blockers: ["Live ingestion is disabled in preview mode"],
  next_actions: ["Review graph density", "Check empty states after deleting preview items"],
};

const analyticsData: KnowledgeBaseAnalyticsReportData = {
  knowledge_base_id: "kb-demo-research",
  generated_at: now,
  documents: { document_count: 2, total_file_size: 420000, status_counts: [{ name: "indexed", count: 2 }] },
  chunks: { chunk_count: 42, avg_chunks_per_document: 21, section_count: 8 },
  memory: { memory_entry_count: 9, entry_type_counts: [{ name: "principle", count: 3 }, { name: "practice", count: 4 }, { name: "insight", count: 2 }] },
  tasks: { task_count: Object.keys(tasks).length, active_task_count: 0, failed_task_count: 0, status_counts: [{ name: "completed", count: Object.keys(tasks).length }] },
  outbox: { event_count: 0, failed_event_count: 0, dead_letter_count: 0, backend_status: [{ backend: "preview", status_counts: [{ name: "ok", count: 1 }], total: 1 }] },
  markdown: "## Preview Analytics\n\nThis report is generated from local demo data. It is meant to exercise the analytics layout without a running backend.\n\n- Documents: 2 indexed examples\n- Memory entries: 9 illustrative entries\n- Tasks: simulated locally",
};

const previewApi = {
  health(): Promise<ServiceHealthData> {
    return delay({ service: "mneme-preview", status: "preview" });
  },
  neo4jHealth(): Promise<Neo4jHealthData> {
    return delay({ enabled: false, backend: "preview", database: "demo", uri: "local-preview", ok: true, error: null });
  },
  readiness(): Promise<ProductionReadinessReportData> {
    return delay({
      overall_status: "preview",
      checks: [{ name: "backend", status: "skipped", reason: "Preview mode uses local fixture data." }],
      framework_decisions: [{ area: "frontend", decision: "mock-api", reason: "Allows visual review without backend services." }],
      default_stack: ["Vue", "TypeScript", "Vite", "Local preview API"],
      optional_stack: [],
      avoid_by_default: ["Network calls in preview mode"],
      markdown: "## Preview Readiness\n\nThe frontend is running against local demo data.",
    });
  },
  documentationStatus(): Promise<PlannedSupportData> {
    return delay({
      status: "planned",
      message: "Documentation workspace is reserved for a future release.",
    });
  },
  supportStatus(): Promise<PlannedSupportData> {
    return delay({
      status: "planned",
      message: "Support contact workflow is reserved for a future release.",
    });
  },
  register(_payload?: { username: string; password: string; display_name?: string | null }): Promise<UserPublic> {
    return delay(previewUser);
  },
  login(_payload?: { username: string; password: string }): Promise<AuthTokenData> {
    return delay({ access_token: PREVIEW_TOKEN, token_type: "bearer" });
  },
  me(): Promise<UserPublic> {
    return delay(previewUser);
  },
  listKnowledgeBases(): Promise<{ items: KnowledgeBaseData[]; total: number }> {
    return delay({ items: knowledgeBases, total: knowledgeBases.length });
  },
  createKnowledgeBase(_userId: number, _token: string, payload: { name: string; description?: string | null }): Promise<KnowledgeBaseData> {
    const created: KnowledgeBaseData = {
      id: `kb-preview-${Date.now()}`,
      user_id: previewUser.id,
      name: payload.name,
      description: payload.description ?? null,
      is_default: false,
      created_at: new Date().toISOString(),
    };
    knowledgeBases = [...knowledgeBases, created];
    return delay(created);
  },
  deleteKnowledgeBase(_userId: number, knowledgeBaseId: string): Promise<{ knowledge_base_id: string; document_count: number; chunk_count: number; deleted_memory_entry_count: number; deleted_task_count: number; deleted_vector_count: number }> {
    const documentCount = documents.filter((item) => item.knowledge_base_id === knowledgeBaseId).length;
    knowledgeBases = knowledgeBases.filter((item) => item.id !== knowledgeBaseId || item.is_default);
    documents = documents.filter((item) => item.knowledge_base_id !== knowledgeBaseId || item.knowledge_base_id === "kb-demo-research");
    return delay({ knowledge_base_id: knowledgeBaseId, document_count: documentCount, chunk_count: documentCount * 12, deleted_memory_entry_count: 0, deleted_task_count: 0, deleted_vector_count: 0 });
  },
  listDocuments(_token: string, params: { userId?: number | null; knowledgeBaseId?: string | null }): Promise<{ items: DocumentListItem[]; total: number }> {
    const items = documents.filter((item) => !params.knowledgeBaseId || item.knowledge_base_id === params.knowledgeBaseId);
    return delay({ items, total: items.length });
  },
  uploadDocument(_token: string, payload: { file: File; userId?: number | null; knowledgeBaseId?: string | null }): Promise<DocumentUploadData> {
    const documentId = `doc-preview-${Date.now()}`;
    const knowledgeBaseId = payload.knowledgeBaseId ?? knowledgeBases[0].id;
    documents = [...documents, { id: documentId, user_id: payload.userId ?? previewUser.id, knowledge_base_id: knowledgeBaseId, file_name: payload.file.name, file_type: payload.file.name.split(".").pop() ?? "file", status: "uploaded", created_at: new Date().toISOString() }];
    return delay({ document_id: documentId, user_id: payload.userId ?? previewUser.id, knowledge_base_id: knowledgeBaseId, file_name: payload.file.name, file_type: payload.file.type || "application/octet-stream", file_size: payload.file.size, status: "uploaded" });
  },
  indexDocument(documentId: string): Promise<DocumentIndexTaskData> {
    documents = documents.map((item) => item.id === documentId ? { ...item, status: "indexed" } : item);
    const task = createTask(`task-index-${documentId}`, documentId);
    return delay({ task_id: task.id, document_id: documentId, knowledge_base_id: documents.find((item) => item.id === documentId)?.knowledge_base_id ?? knowledgeBases[0].id, status: task.status, message: "Preview document indexed locally." });
  },
  deleteDocument(documentId: string): Promise<DocumentDeleteData> {
    const document = documents.find((item) => item.id === documentId);
    documents = documents.filter((item) => item.id !== documentId);
    return delay({ document_id: documentId, knowledge_base_id: document?.knowledge_base_id ?? knowledgeBases[0].id, chunk_count: 12, deleted_memory_entry_count: 2, deleted_task_count: 0, deleted_vector_count: 12 });
  },
  documentPreview(_token: string, documentId: string): Promise<DocumentPreviewData> {
    const document = documents.find((item) => item.id === documentId) ?? documents[0];
    return delay(
      documentPreviews[documentId] ?? {
        document_id: document.id,
        knowledge_base_id: document.knowledge_base_id,
        file_name: document.file_name,
        file_type: document.file_type,
        status: document.status,
        summary: "No indexed preview content is available for this document yet.",
        chunks: [],
        memory_entries: [],
      },
    );
  },
  getTask(taskId: string): Promise<TaskRecordData> {
    return delay(tasks[taskId] ?? createTask(taskId, "preview-target"));
  },
  cancelTask(taskId: string): Promise<TaskActionData> {
    const task = createTask(taskId, "preview-target", "cancelled");
    return delay({ task_id: task.id, status: task.status, document_id: task.target_id, message: "Preview task cancelled." });
  },
  retryTask(taskId: string): Promise<TaskActionData> {
    const task = createTask(taskId, "preview-target", "completed");
    return delay({ task_id: task.id, status: task.status, document_id: task.target_id, message: "Preview task retried." });
  },
  chatQuery(_token: string, payload: { question: string; knowledge_base_id: string; top_k?: number; session_id?: string | null }): Promise<ChatQueryData> {
    return delay({ answer: `Preview answer for: ${payload.question}`, confidence: "medium", uncertainty: "This is local demo data, not a backend answer.", route: { query_type: "preview", requires_retrieval: true, target_pipeline: "mock", confidence: "medium", reason: "Preview mode returns deterministic fixture content." }, sources: [{ source_id: "source-preview-1", knowledge_base_id: payload.knowledge_base_id, document_id: "doc-zettelkasten", chunk_id: "chunk-zettel-1", page_no: null, text: "Atomic notes are easier to recombine across contexts." }], citations: [{ source_id: "source-preview-1", document_id: "doc-zettelkasten", chunk_id: "chunk-zettel-1", page_no: null, quote: "Atomic notes are easier to recombine", reason: "Matches the preview question theme.", validation_status: "preview", quote_found: true, validation_reason: "Fixture quote." }], debug: null });
  },
  listChatSessions(_token: string, knowledgeBaseId: string): Promise<{ items: ChatSessionData[]; total: number }> {
    const items = chatSessions.filter((session) => session.knowledge_base_id === knowledgeBaseId && !session.archived_at);
    return delay({ items, total: items.length });
  },
  createChatSession(_token: string, payload: { knowledge_base_id: string; title?: string | null }): Promise<ChatSessionData> {
    const session: ChatSessionData = {
      id: `chat-preview-${Date.now()}`,
      user_id: previewUser.id,
      knowledge_base_id: payload.knowledge_base_id,
      title: payload.title || "New Chat",
      message_count: 0,
      last_message_at: null,
      archived_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    chatSessions = [session, ...chatSessions];
    chatMessages[session.id] = [];
    return delay(session);
  },
  getChatSession(_token: string, sessionId: string): Promise<ChatSessionDetailData> {
    const session = chatSessions.find((item) => item.id === sessionId) ?? chatSessions[0];
    return delay({ session, messages: chatMessages[session.id] ?? [] });
  },
  deleteChatSession(_token: string, sessionId: string): Promise<{ session_id: string; deleted_count: number }> {
    chatSessions = chatSessions.filter((item) => item.id !== sessionId);
    delete chatMessages[sessionId];
    return delay({ session_id: sessionId, deleted_count: 1 });
  },
  sendChatSessionMessage(_token: string, sessionId: string, payload: { question: string; top_k?: number }): Promise<ChatSessionDetailData> {
    const session = chatSessions.find((item) => item.id === sessionId) ?? chatSessions[0];
    const createdAt = new Date().toISOString();
    const nextMessages: ChatMessageData[] = [
      {
        id: `msg-preview-user-${Date.now()}`,
        session_id: session.id,
        user_id: previewUser.id,
        knowledge_base_id: session.knowledge_base_id,
        role: "user",
        content: payload.question,
        sources: [],
        citations: [],
        route: null,
        model_config_id: "model-preview-deepseek",
        created_at: createdAt,
      },
      {
        id: `msg-preview-assistant-${Date.now()}`,
        session_id: session.id,
        user_id: previewUser.id,
        knowledge_base_id: session.knowledge_base_id,
        role: "assistant",
        content: `Preview answer for: ${payload.question}`,
        sources: [],
        citations: [],
        route: { query_type: "preview", requires_retrieval: true, target_pipeline: "mock", confidence: "medium", reason: "Preview session message." },
        model_config_id: "model-preview-deepseek",
        created_at: createdAt,
      },
    ];
    chatMessages[session.id] = [...(chatMessages[session.id] ?? []), ...nextMessages];
    session.message_count = chatMessages[session.id].length;
    session.last_message_at = createdAt;
    return delay({ session, messages: nextMessages });
  },
  listAiModelConfigs(): Promise<AiModelConfigListData> {
    return delay({
      provider_presets: [
        { provider: "deepseek", label: "DeepSeek", base_url: "https://api.deepseek.com", model_name: "deepseek-v4-flash" },
        { provider: "qwen", label: "Qwen", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model_name: "qwen-plus" },
      ],
      items: aiModelConfigs,
      default_config_id: aiModelConfigs.find((item) => item.is_default)?.id ?? null,
    });
  },
  createAiModelConfig(_token: string, payload: { label: string; provider: string; base_url: string; model_name: string; api_key?: string | null; temperature?: number; context_window?: number; is_default?: boolean; enabled?: boolean }): Promise<AiModelConfigData> {
    const config: AiModelConfigData = { id: `model-preview-${Date.now()}`, user_id: previewUser.id, label: payload.label, provider: payload.provider, base_url: payload.base_url, model_name: payload.model_name, temperature: payload.temperature ?? 0, context_window: payload.context_window ?? 64000, is_default: Boolean(payload.is_default), enabled: payload.enabled ?? true, has_api_key: Boolean(payload.api_key), created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
    if (config.is_default) {
      aiModelConfigs = aiModelConfigs.map((item) => ({ ...item, is_default: false }));
    }
    aiModelConfigs = [...aiModelConfigs, config];
    return delay(config);
  },
  updateAiModelConfig(_token: string, configId: string, payload: Partial<{ label: string; provider: string; base_url: string; model_name: string; api_key: string | null; temperature: number; context_window: number; enabled: boolean }>): Promise<AiModelConfigData> {
    aiModelConfigs = aiModelConfigs.map((item) => item.id === configId ? { ...item, ...payload, has_api_key: payload.api_key !== undefined ? Boolean(payload.api_key) : item.has_api_key, updated_at: new Date().toISOString() } : item);
    return delay(aiModelConfigs.find((item) => item.id === configId) ?? aiModelConfigs[0]);
  },
  testAiModelConfig(_token: string, configId: string): Promise<{ config_id: string; ok: boolean; message: string }> {
    return delay({ config_id: configId, ok: true, message: "Preview model config is ready." });
  },
  setDefaultAiModelConfig(_token: string, configId: string): Promise<AiModelConfigData> {
    aiModelConfigs = aiModelConfigs.map((item) => ({ ...item, is_default: item.id === configId }));
    return delay(aiModelConfigs.find((item) => item.id === configId) ?? aiModelConfigs[0]);
  },
  deleteAiModelConfig(_token: string, configId: string): Promise<{ config_id: string; deleted_count: number }> {
    aiModelConfigs = aiModelConfigs.filter((item) => item.id !== configId);
    return delay({ config_id: configId, deleted_count: 1 });
  },
  companionReply(_token: string, knowledgeBaseId: string, payload: { question: string; top_k?: number }): Promise<CompanionAnswerResult> {
    return delay({ knowledge_base_id: knowledgeBaseId, question: payload.question, direct_answer: "In preview mode, Mneme can show how companion answers will be laid out without calling the backend.", citations: [{ document_id: "doc-memory-graph", chunk_id: "chunk-graph-1", page_no: 2, text: "Graph context improves answer grounding.", reason: "Preview citation." }], profile_snapshot: profileData.profile_summary, growth_snapshot: growthData.stage_summary, next_step_hint: "Try switching to Graph or Insights to inspect populated preview panels.", follow_up_questions: ["Which documents anchor this answer?", "What changed in the last 30 days?"], companion_message: "This is a local preview companion response." });
  },
  getUserGraph(): Promise<GraphData> {
    return delay({ ...previewGraph, scope: "user" });
  },
  getKnowledgeBaseGraph(_token: string, knowledgeBaseId: string): Promise<GraphData> {
    return delay({ ...previewGraph, scope: "knowledge_base", root_node_id: requireKnowledgeBase(knowledgeBaseId).id === "kb-demo-research" ? "node-kb-demo" : "node-kb-demo" });
  },
  getDocumentGraph(): Promise<GraphData> {
    return delay({ ...previewGraph, scope: "document", relationship_scope: "knowledge_base" });
  },
  rebuildUserGraph(): Promise<GraphProjectionRebuildData> {
    return delay({ scope: "user", user_id: previewUser.id, knowledge_base_id: null, knowledge_base_count: knowledgeBases.length, document_count: documents.length, memory_entry_count: 9, status: "completed" });
  },
  rebuildKnowledgeBaseGraph(_token: string, knowledgeBaseId: string): Promise<GraphProjectionRebuildData> {
    return delay({ scope: "knowledge_base", user_id: previewUser.id, knowledge_base_id: knowledgeBaseId, knowledge_base_count: null, document_count: documents.filter((item) => item.knowledge_base_id === knowledgeBaseId).length, memory_entry_count: 9, status: "completed" });
  },
  graphRag(_token: string, knowledgeBaseId: string, params: { query: string; top_k?: number; max_expansions?: number }): Promise<GraphRagDecisionData> {
    return delay({ knowledge_base_id: knowledgeBaseId, query: params.query, graph_useful: true, summary: "Preview GraphRAG found a compact neighborhood around memory graph design.", seed_count: 2, expansion_count: 2, context_count: 3, seeds: [{ document_id: "doc-memory-graph", title: "Memory Graph Design", reason: "Matches graph-related terms.", score: 0.82 }], expansions: [{ document_id: "doc-zettelkasten", title: "Zettelkasten Principles", reason: "Related through atomic note practice.", score: 0.68 }], contexts: [{ document_id: "doc-memory-graph", title: "Memory Graph Design", reason: "Primary preview context.", score: 0.82 }] });
  },
  memoryLibrary(): Promise<MemoryLibraryData> {
    return delay(memoryLibraryData);
  },
  memoryGovernance(): Promise<MemoryGovernanceData> {
    return delay(memoryGovernanceData);
  },
  rebuildMemory(_token: string, knowledgeBaseId: string): Promise<MemoryRebuildData> {
    return delay({ knowledge_base_id: knowledgeBaseId, document_count: documents.filter((item) => item.knowledge_base_id === knowledgeBaseId).length, processed_document_count: 2, chunk_count: 42, deleted_entry_count: 0, entry_count: 9 });
  },
  documentMemory(): Promise<MemoryLibraryData> {
    return delay(memoryLibraryData);
  },
  profile(_token: string, knowledgeBaseId: string): Promise<PersonalProfileResult> {
    return delay({ ...profileData, knowledge_base_id: knowledgeBaseId });
  },
  profileEvidence(_token: string, knowledgeBaseId: string): Promise<EvidenceProfileData> {
    return delay({ ...profileEvidenceData, knowledge_base_id: knowledgeBaseId });
  },
  growth(_token: string, knowledgeBaseId: string): Promise<GrowthReportResult> {
    return delay({ ...growthData, knowledge_base_id: knowledgeBaseId });
  },
  analytics(_token: string, knowledgeBaseId: string): Promise<KnowledgeBaseAnalyticsReportData> {
    return delay({ ...analyticsData, knowledge_base_id: knowledgeBaseId });
  },
  advice(_token: string, knowledgeBaseId: string, focusGoal?: string | null): Promise<GrowthAdviceResult> {
    return delay({ knowledge_base_id: knowledgeBaseId, focus_goal: focusGoal ?? null, advice_summary: "Use preview mode to inspect dense states before connecting a backend.", current_priorities: ["Validate layout", "Check navigation", "Review empty and populated states"], action_suggestions: [{ area: "Frontend preview", why_now: "Backend-free demos shorten UI review loops.", action: "Keep fixtures representative", first_step: "Update preview data when API response shapes change.", evidence_entries: ["memory-context"] }], avoid_list: ["Treating preview answers as live data"], one_week_plan: ["Review workspace", "Exercise Graph tab", "Exercise Insights tab"], reflection_questions: ["Which panel still needs richer fixture data?"] });
  },
};

export function isPreviewMode() {
  const envPreview = import.meta.env.VITE_MNEME_PREVIEW === "true" || import.meta.env.MODE === "preview";
  if (envPreview) {
    return true;
  }

  if (typeof window === "undefined") {
    return false;
  }

  const searchParams = new URLSearchParams(window.location.search);
  if (searchParams.get("preview") === "1" || searchParams.get("preview") === "true") {
    return true;
  }

  const hash = window.location.hash.replace(/^#/, "");
  const hashQuery = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : hash;
  const hashParams = new URLSearchParams(hashQuery);
  return hashParams.get("preview") === "1" || hashParams.get("preview") === "true";
}

export default previewApi;
