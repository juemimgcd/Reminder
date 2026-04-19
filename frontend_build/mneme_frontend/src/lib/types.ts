export interface ApiEnvelope<T> {
  code?: number;
  message?: string;
  data?: T;
  detail?: string;
}

export interface User {
  id: number;
  username: string;
  display_name?: string | null;
  avatar_url?: string;
  created_at?: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface AuthPayload {
  username: string;
  password: string;
}

export interface KnowledgeBase {
  id: string;
  user_id?: number;
  name: string;
  description: string | null;
  is_default?: boolean;
  created_at?: string;
  document_count: number;
  memory_count: number;
  updated_at: string;
  status: 'ready' | 'indexing' | 'draft' | 'queued';
}

export interface DocumentItem {
  id: string;
  user_id?: number;
  file_name: string;
  name: string;
  knowledge_base_id: string;
  file_type?: string;
  status:
    | 'uploaded'
    | 'queued'
    | 'indexing'
    | 'parsing'
    | 'chunking'
    | 'embedding'
    | 'vector_upserting'
    | 'indexed'
    | 'failed';
  page_count: number;
  chunk_count: number;
  created_at: string;
  size_label: string;
  task_id?: string;
}

export interface ChatSource {
  knowledge_base_id: string;
  document_id: string;
  chunk_id: string;
  page_no: number | null;
  text: string;
  source_chunk_ids: string[];
  source_page_nos: number[];
  merged_chunk_count: number;
}

export interface ChatExchange {
  id: string;
  question: string;
  answer: string;
  sources: ChatSource[];
  created_at: string;
}

export interface MemoryTimelineEntry {
  entry_id: string;
  entry_name: string;
  entry_type: string;
  summary: string;
  created_at: string;
}

export interface MemoryThemeGroup {
  theme_name: string;
  entries: string[];
  count: number;
}

export interface MemoryLibrary {
  timeline: MemoryTimelineEntry[];
  by_type: Record<string, string[]>;
  by_theme: MemoryThemeGroup[];
}

export interface ProfileInsight {
  theme_name: string;
  reason: string;
  evidence_entries: string[];
}

export interface AbilityTag {
  ability_name: string;
  reason: string;
  evidence_entries: string[];
}

export interface PersonalProfile {
  knowledge_base_id: string;
  entry_count: number;
  profile_summary: string;
  main_themes: ProfileInsight[];
  ability_tags: AbilityTag[];
  expression_style: string;
  growth_focus: string[];
}

export interface ThemeChange {
  theme_name: string;
  change_type: string;
  reason: string;
  evidence_entries: string[];
}

export interface GrowthReport {
  knowledge_base_id: string;
  analysis_window: string;
  stage_summary: string;
  recent_focus: string[];
  theme_changes: ThemeChange[];
  highlights: string[];
  blockers: string[];
  next_actions: string[];
}

export interface IndexSubmission {
  document_id: string;
  status: DocumentItem['status'];
  task_id?: string;
  message?: string;
}

export interface DashboardMetric {
  label: string;
  value: string;
  change: string;
  tone: 'teal' | 'amber' | 'indigo' | 'coral';
}

export interface ActivityItem {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
  tone: 'teal' | 'amber' | 'indigo';
}
