export type ViewState = "login" | "daily-notes" | "editor" | "graph" | "search" | "starred";

export interface Note {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  tags: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: "document" | "tag" | "concept";
}

export interface GraphLink {
  source: string;
  target: string;
}

export type WorkspaceView = "dashboard" | "notes" | "graph" | "ai" | "memory" | "settings";

export type AuthMode = "login" | "register";

export interface PlannedSupportData {
  status: "planned";
  message: string;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface UserPublic {
  id: number;
  username: string;
  display_name: string | null;
  avatar_url: string;
}

export interface AuthTokenData {
  access_token: string;
  token_type: string;
}

export interface KnowledgeBaseData {
  id: string;
  user_id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  created_at: string;
}

export interface KnowledgeBaseListData {
  items: KnowledgeBaseData[];
  total: number;
}

export interface KnowledgeBaseDeleteData {
  knowledge_base_id: string;
  document_count: number;
  chunk_count: number;
  deleted_memory_entry_count: number;
  deleted_task_count: number;
  deleted_vector_count: number;
}

export interface DocumentListItem {
  id: string;
  user_id: number;
  knowledge_base_id: string;
  folder_id: string;
  file_name: string;
  file_type: string;
  status: string;
  content_sha256?: string;
  version_group_id: string;
  version_number: number;
  duplicate_of_document_id: string | null;
  created_at: string;
}

export interface DocumentListData {
  items: DocumentListItem[];
  total: number;
}

export interface DocumentUploadData {
  disposition: "created" | "duplicate";
  document_id: string;
  canonical_document_id: string;
  user_id: number;
  knowledge_base_id: string | null;
  folder_id: string;
  folder_path: string[];
  file_name: string;
  file_type: string;
  file_size: number;
  status: string;
  version_group_id: string;
  version_number: number;
}

export interface DocumentFolderData {
  id: string;
  parent_id: string;
  name: string;
  is_root: boolean;
  children: DocumentFolderData[];
}

export interface DocumentVersionData {
  document_id: string;
  version_group_id: string;
  version_number: number;
  file_name: string;
  created_at: string;
}

export interface DocumentVersionListData {
  items: DocumentVersionData[];
  total: number;
}

export interface DocumentContentSection {
  title: string | null;
  text: string;
}

export interface DocumentContentData {
  document_id: string;
  folder_id: string;
  file_name: string;
  render_mode: "markdown" | "text" | "structured" | "office" | "pdf" | "unsupported";
  mime_type: string;
  text: string | null;
  sections: DocumentContentSection[];
  parse_warning: string | null;
}

export interface DocumentTab {
  documentId: string;
  title: string;
  blobUrl: string | null;
}

export interface DocumentIndexTaskData {
  task_id: string;
  document_id: string;
  knowledge_base_id: string;
  status: string;
  message: string;
}

export interface DocumentDeleteData {
  document_id: string;
  knowledge_base_id: string;
  chunk_count: number;
  deleted_memory_entry_count: number;
  deleted_task_count: number;
  deleted_vector_count: number;
}

export interface DocumentPreviewChunk {
  chunk_id: string;
  chunk_index: number;
  text: string;
  page_no: number | null;
  section_title: string | null;
}

export interface DocumentPreviewMemoryEntry {
  entry_id: string;
  entry_name: string;
  entry_type: string;
  summary: string;
  importance_score: number;
}

export interface DocumentPreviewData {
  document_id: string;
  knowledge_base_id: string;
  folder_id?: string;
  file_name: string;
  file_type: string;
  status: string;
  content_sha256?: string;
  version_group_id?: string;
  version_number?: number;
  summary: string;
  chunks: DocumentPreviewChunk[];
  memory_entries: DocumentPreviewMemoryEntry[];
}

export interface TaskRecordData {
  id: string;
  task_type: string;
  target_id: string;
  status: string;
  progress_stage: string | null;
  queue_name: string | null;
  celery_task_id: string | null;
  attempt_count: number;
  max_attempts: number;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskActionData {
  task_id: string;
  status: string;
  document_id: string | null;
  message: string;
}

export interface QueryRouteDecision {
  query_type: string;
  requires_retrieval: boolean;
  target_pipeline: string;
  confidence: string;
  reason: string;
}

export type AnswerMode = "kb_qa" | "memory_query" | "profile_query" | "analysis_query" | "general_chat";

export interface ChatSourceItem {
  source_id: string | null;
  knowledge_base_id: string | null;
  document_id: string | null;
  chunk_id: string | null;
  source_type?: string | null;
  evidence_id?: string | null;
  source_time?: string | null;
  page_no: number | null;
  text: string;
}

export interface ChatCitationItem {
  source_id: string | null;
  document_id: string | null;
  chunk_id: string | null;
  source_type?: string | null;
  evidence_id?: string | null;
  source_time?: string | null;
  page_no: number | null;
  quote: string;
  reason: string;
  validation_status: string | null;
  quote_found: boolean | null;
  validation_reason: string | null;
}

export interface RetrievalDebugData {
  route: Record<string, unknown> | null;
  query_terms: string[];
  lexical_backend: string | null;
  counts: Record<string, number>;
  vector_candidates: Record<string, unknown>[];
  lexical_candidates: Record<string, unknown>[];
  memory_candidates: Record<string, unknown>[];
  fused_candidates: Record<string, unknown>[];
  final_context: Record<string, unknown>[];
  answer_debug: Record<string, unknown> | null;
}

export interface ChatQueryData {
  answer: string;
  sources: ChatSourceItem[];
  citations: ChatCitationItem[];
  confidence: string;
  uncertainty: string | null;
  route: QueryRouteDecision | null;
  debug: RetrievalDebugData | null;
}

export interface ChatMessageData {
  id: string;
  session_id: string;
  user_id: number;
  knowledge_base_id: string | null;
  role: "user" | "assistant" | string;
  content: string;
  sources: ChatSourceItem[];
  citations: ChatCitationItem[];
  tool_calls?: Record<string, unknown>[];
  route: QueryRouteDecision | null;
  model_config_id: string | null;
  agent_run_id: string | null;
  confidence: number | null;
  uncertainty: string | null;
  insufficient_evidence: boolean;
  created_at: string;
}

export interface ChatSessionData {
  id: string;
  user_id: number;
  knowledge_base_id: string | null;
  answer_mode: AnswerMode;
  title: string | null;
  message_count: number;
  last_message_at: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CanonicalMemory {
  memory_id: string; knowledge_base_id: string | null; memory_type: string; subject: string; predicate: string;
  value: string; confidence: number; status: string; active_revision_id: string; created_at: string; updated_at: string;
}
export interface MemoryCandidate {
  candidate_id: string; knowledge_base_id: string | null; memory_type: string; subject: string; predicate: string;
  value: string; confidence: number; status: string; created_at: string; decided_at: string | null;
}
export interface MemoryRevision { revision_id: string; subject: string; predicate: string; value: string; valid_from: string; valid_to: string | null; reason: string }
export interface MemoryEvidence { evidence_id: string; revision_id: string; source_type: string; source_id: string; source_document_id: string | null; excerpt: string; source_time: string }
export interface MemoryDetail { memory: CanonicalMemory; revisions: MemoryRevision[]; evidence: MemoryEvidence[] }
export interface MemoryPage<T> { items: T[]; next_cursor: string | null; total: number; pending_count?: number }
export interface MemorySettings { automatic_conversation_memory: boolean; applied: boolean }
export interface MemoryConfirmation { action: string; target_id: string; expires_at: string; confirmation_token: string }
export interface MemoryPurgeResult { purged: boolean; deleted_evidence_count: number; deleted_candidate_count: number; deleted_revision_count: number; deleted_memory_count: number }

export interface ChatSessionListData {
  items: ChatSessionData[];
  total: number;
}

export interface ChatSessionDetailData {
  session: ChatSessionData;
  messages: ChatMessageData[];
}

export interface AgentStreamEvent {
  type: "lifecycle" | "assistant" | "tool" | "compaction" | "error";
  phase?: string;
  content?: string;
  tool?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export type AgentRunStatus = "queued" | "running" | "completed" | "failed" | "aborting" | "aborted";

export interface AgentRunData {
  run_id: string;
  session_id: string;
  user_id: number;
  question: string;
  top_k: number;
  answer_mode: AnswerMode;
  status: AgentRunStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  last_event_id: string | null;
}

export interface GraphNodeData {
  id: string;
  entity_id: string;
  node_type: string;
  label: string;
  parent_id: string | null;
  depth: number;
  metadata: Record<string, unknown>;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  edge_type: string;
  metadata: Record<string, unknown>;
}

export interface GraphData {
  scope: string;
  generated_at: string;
  root_node_id: string;
  include_memory: boolean;
  include_relationships: boolean;
  relationship_strategy: string | null;
  relationship_scope: string | null;
  min_shared_memory_count: number | null;
  min_relationship_score: number | null;
  max_related_edges: number | null;
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  node_count: number;
  edge_count: number;
  node_type_counts: Record<string, number>;
  edge_type_counts: Record<string, number>;
}

export interface GraphProjectionRebuildData {
  scope: string;
  user_id: number;
  knowledge_base_id: string | null;
  knowledge_base_count: number | null;
  document_count: number;
  memory_entry_count: number;
  status: string;
}

export interface GraphRagContextItem {
  document_id: string;
  title?: string | null;
  reason?: string | null;
  score?: number | null;
  [key: string]: unknown;
}

export interface GraphRagDecisionData {
  knowledge_base_id: string;
  query: string;
  graph_useful: boolean;
  summary: string;
  seed_count: number;
  expansion_count: number;
  context_count: number;
  seeds: GraphRagContextItem[];
  expansions: GraphRagContextItem[];
  contexts: GraphRagContextItem[];
}

export interface MemoryTimelineItem {
  entry_id: string;
  entry_name: string;
  entry_type: string;
  summary: string;
  created_at: string;
}

export interface MemoryThemeItem {
  theme_name: string;
  entries: string[];
  count: number;
}

export interface MemoryLibraryData {
  timeline: MemoryTimelineItem[];
  by_type: Record<string, string[]>;
  by_theme: MemoryThemeItem[];
}

export interface MemoryRebuildData {
  knowledge_base_id: string;
  document_count: number;
  processed_document_count: number;
  chunk_count: number;
  deleted_entry_count: number;
  entry_count: number;
}

export interface CanonicalMemoryItem {
  canonical_id: string;
  entry_name: string;
  entry_type: string;
  summary: string;
  representative_entry_id: string;
  entry_ids: string[];
  evidence_count: number;
  document_count: number;
  importance_score: number;
  status: string;
  first_seen_at: string;
  last_seen_at: string;
}

export interface MemoryRelationItem {
  relation_id: string;
  source_entry_id: string;
  target_entry_id: string;
  relation_type: string;
  confidence: number;
  reason: string;
}

export interface MemoryGovernanceData {
  knowledge_base_id: string;
  raw_entry_count: number;
  canonical_memory_count: number;
  relation_count: number;
  relation_type_counts: Record<string, number>;
  canonical_memories: CanonicalMemoryItem[];
  relations: MemoryRelationItem[];
}

export interface ProfileThemeItem {
  theme_name: string;
  reason: string;
  evidence_entries: string[];
}

export interface AbilityTagItem {
  ability_name: string;
  reason: string;
  evidence_entries: string[];
}

export interface PersonalProfileResult {
  knowledge_base_id: string;
  entry_count: number;
  profile_summary: string;
  main_themes: ProfileThemeItem[];
  ability_tags: AbilityTagItem[];
  expression_style: string;
  growth_focus: string[];
}

export interface ProfileEvidenceItem {
  entry_id: string;
  entry_name: string;
  entry_type: string;
  summary: string;
  evidence_text: string;
  document_id: string;
  chunk_id: string;
  created_at: string;
}

export interface EvidenceProfileTraitItem {
  trait_name: string;
  summary: string;
  confidence: string;
  evidence_entry_ids: string[];
}

export interface EvidenceProfileRiskItem {
  risk_name: string;
  summary: string;
  relation_type: string;
  evidence_entry_ids: string[];
}

export interface TopicTimelineItem {
  topic_name: string;
  entry_type: string;
  entry_count: number;
  first_seen_at: string;
  last_seen_at: string;
  evidence_entry_ids: string[];
}

export interface ProfileToolCallItem {
  tool_name: string;
  input: Record<string, unknown>;
  output_count: number;
  evidence_entry_ids: string[];
}

export interface EvidenceProfileData {
  knowledge_base_id: string;
  entry_count: number;
  canonical_memory_count: number;
  stable_traits: EvidenceProfileTraitItem[];
  recent_focus: EvidenceProfileTraitItem[];
  goals: EvidenceProfileTraitItem[];
  risks: EvidenceProfileRiskItem[];
  topic_timeline: TopicTimelineItem[];
  evidence: ProfileEvidenceItem[];
  tool_calls: ProfileToolCallItem[];
  uncertainty: string | null;
}

export interface ThemeChangeItem {
  theme_name: string;
  change_type: string;
  reason: string;
  evidence_entries: string[];
}

export interface GrowthReportResult {
  knowledge_base_id: string;
  analysis_window: string;
  stage_summary: string;
  recent_focus: string[];
  theme_changes: ThemeChangeItem[];
  highlights: string[];
  blockers: string[];
  next_actions: string[];
}

export interface StatusCountData {
  name: string;
  count: number;
}

export interface BackendStatusData {
  backend: string;
  status_counts: StatusCountData[];
  total: number;
}

export interface KnowledgeBaseAnalyticsReportData {
  knowledge_base_id: string;
  generated_at: string;
  documents: {
    document_count: number;
    total_file_size: number;
    status_counts: StatusCountData[];
  };
  chunks: {
    chunk_count: number;
    avg_chunks_per_document: number;
    section_count: number;
  };
  memory: {
    memory_entry_count: number;
    entry_type_counts: StatusCountData[];
  };
  tasks: {
    task_count: number;
    active_task_count: number;
    failed_task_count: number;
    status_counts: StatusCountData[];
  };
  outbox: {
    event_count: number;
    failed_event_count: number;
    dead_letter_count: number;
    backend_status: BackendStatusData[];
  };
  markdown: string;
}

export interface ActionSuggestionItem {
  area: string;
  why_now: string;
  action: string;
  first_step: string;
  evidence_entries: string[];
}

export interface GrowthAdviceResult {
  knowledge_base_id: string;
  focus_goal: string | null;
  advice_summary: string;
  current_priorities: string[];
  action_suggestions: ActionSuggestionItem[];
  avoid_list: string[];
  one_week_plan: string[];
  reflection_questions: string[];
}

export interface CompanionCitationItem {
  document_id: string;
  chunk_id: string;
  page_no: number | null;
  text: string;
  reason: string;
}

export interface CompanionAnswerResult {
  knowledge_base_id: string;
  question: string;
  direct_answer: string;
  citations: CompanionCitationItem[];
  profile_snapshot: string;
  growth_snapshot: string;
  next_step_hint: string;
  follow_up_questions: string[];
  companion_message: string;
}

export interface AiModelProviderPreset {
  provider: string;
  label: string;
  base_url: string;
  model_name: string;
}

export interface AiModelConfigData {
  id: string;
  user_id: number;
  label: string;
  provider: string;
  base_url: string;
  model_name: string;
  temperature: number;
  context_window: number;
  is_default: boolean;
  enabled: boolean;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface AiModelConfigListData {
  provider_presets: AiModelProviderPreset[];
  items: AiModelConfigData[];
  default_config_id: string | null;
}

export interface ServiceHealthData {
  service: string;
  status: string;
}

export interface Neo4jHealthData {
  enabled: boolean;
  backend: string;
  database: string;
  uri: string;
  ok: boolean;
  error: string | null;
}

export interface ReadinessCheckData {
  name: string;
  status: string;
  reason: string;
}

export interface FrameworkDecisionData {
  area: string;
  decision: string;
  reason: string;
}

export interface ProductionReadinessReportData {
  overall_status: string;
  checks: ReadinessCheckData[];
  framework_decisions: FrameworkDecisionData[];
  default_stack: string[];
  optional_stack: string[];
  avoid_by_default: string[];
  markdown: string;
}
