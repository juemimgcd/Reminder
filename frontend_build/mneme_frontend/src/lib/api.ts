import { requestJson, shouldUseMocks } from '@/lib/http';
import type {
  AuthPayload,
  AuthToken,
  ChatExchange,
  DocumentItem,
  GrowthReport,
  IndexSubmission,
  KnowledgeBase,
  MemoryLibrary,
  PersonalProfile,
  User,
} from '@/lib/types';
import {
  mockChatHistory,
  mockChatQuery,
  mockCreateKnowledgeBase,
  mockDocuments,
  mockGrowth,
  mockIndexDocument,
  mockKnowledgeBases,
  mockLogin,
  mockMe,
  mockMemoryLibrary,
  mockProfile,
  mockRegister,
  mockUploadDocuments,
} from '@/mocks/api';

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number') {
    return String(value);
  }
  return fallback;
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function firstPresent(source: Record<string, unknown>, keys: string[], fallback?: unknown) {
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== null) {
      return source[key];
    }
  }
  return fallback;
}

function normalizeUser(raw: unknown): User {
  const source = isObject(raw) ? raw : {};
  return {
    id: asNumber(firstPresent(source, ['id', 'user_id']), 1),
    username: asString(firstPresent(source, ['username', 'name', 'user_name']), 'mneme_user'),
    display_name: asString(firstPresent(source, ['display_name']), ''),
    avatar_url: asString(firstPresent(source, ['avatar_url']), ''),
    created_at: asString(
      firstPresent(source, ['created_at', 'createdAt', 'updated_at']),
      new Date().toISOString(),
    ),
  };
}

function normalizeAuthToken(raw: unknown): AuthToken {
  const source = isObject(raw) ? raw : {};
  return {
    access_token: asString(firstPresent(source, ['access_token', 'token', 'jwt_token'])),
    token_type: asString(firstPresent(source, ['token_type', 'type']), 'bearer'),
  };
}

function normalizeKnowledgeBase(raw: unknown): KnowledgeBase {
  const source = isObject(raw) ? raw : {};
  const rawStatus = asString(firstPresent(source, ['status', 'index_status']), '');
  return {
    id: asString(firstPresent(source, ['id', 'knowledge_base_id']), crypto.randomUUID()),
    user_id: asNumber(firstPresent(source, ['user_id']), 0),
    name: asString(firstPresent(source, ['name', 'title']), '未命名知识库'),
    description: asString(firstPresent(source, ['description', 'summary']), ''),
    is_default: Boolean(firstPresent(source, ['is_default'], false)),
    created_at: asString(firstPresent(source, ['created_at']), new Date().toISOString()),
    document_count: asNumber(firstPresent(source, ['document_count', 'documents_count', 'doc_count'])),
    memory_count: asNumber(firstPresent(source, ['memory_count', 'entry_count', 'entries_count'])),
    updated_at: asString(
      firstPresent(source, ['updated_at', 'updatedAt', 'created_at']),
      new Date().toISOString(),
    ),
    status:
      rawStatus === 'queued' || rawStatus === 'indexing' || rawStatus === 'draft'
        ? rawStatus
        : firstPresent(source, ['is_default'], false)
          ? 'ready'
          : 'draft',
  };
}

function normalizeDocumentStatus(value: unknown): DocumentItem['status'] {
  const status = asString(value, 'uploaded');
  const map: Record<string, DocumentItem['status']> = {
    uploaded: 'uploaded',
    queued: 'queued',
    indexing: 'indexing',
    parsing: 'parsing',
    chunking: 'chunking',
    embedding: 'embedding',
    vector_upserting: 'vector_upserting',
    indexed: 'indexed',
    completed: 'indexed',
    ready: 'indexed',
    failed: 'failed',
  };
  return map[status] ?? 'uploaded';
}

function normalizeDocument(raw: unknown): DocumentItem {
  const source = isObject(raw) ? raw : {};
  const fileName = asString(firstPresent(source, ['file_name', 'name', 'filename', 'title']), '未命名文档');
  const fileType = asString(firstPresent(source, ['file_type']), fileName.split('.').pop() ?? '');
  return {
    id: asString(firstPresent(source, ['id', 'document_id']), crypto.randomUUID()),
    user_id: asNumber(firstPresent(source, ['user_id']), 0),
    file_name: fileName,
    name: fileName,
    knowledge_base_id: asString(firstPresent(source, ['knowledge_base_id', 'kb_id']), ''),
    file_type: fileType,
    status: normalizeDocumentStatus(firstPresent(source, ['status', 'index_status'])),
    page_count: asNumber(firstPresent(source, ['page_count', 'pages'])),
    chunk_count: asNumber(firstPresent(source, ['chunk_count', 'chunks', 'chunk_total'])),
    created_at: asString(firstPresent(source, ['created_at', 'uploaded_at']), new Date().toISOString()),
    size_label: asString(firstPresent(source, ['size_label']), source.file_size ? `${Math.round(asNumber(source.file_size) / 1024)} KB` : '--'),
    task_id: asString(firstPresent(source, ['task_id']), ''),
  };
}

function normalizeSource(raw: unknown) {
  const source = isObject(raw) ? raw : {};
  const pages = asArray<number>(firstPresent(source, ['source_page_nos', 'pages'], []));
  const chunkIds = asArray<string>(firstPresent(source, ['source_chunk_ids', 'chunk_ids'], []));
  return {
    knowledge_base_id: asString(firstPresent(source, ['knowledge_base_id', 'kb_id'])),
    document_id: asString(firstPresent(source, ['document_id', 'doc_id'])),
    chunk_id: asString(firstPresent(source, ['chunk_id']), chunkIds.join('..')),
    page_no:
      firstPresent(source, ['page_no']) !== undefined
        ? asNumber(firstPresent(source, ['page_no']), 0)
        : null,
    text: asString(firstPresent(source, ['text', 'content', 'source_text'])),
    source_chunk_ids: chunkIds,
    source_page_nos: pages,
    merged_chunk_count: asNumber(firstPresent(source, ['merged_chunk_count']), Math.max(1, chunkIds.length)),
  };
}

function normalizeChatExchange(raw: unknown, questionFallback = ''): ChatExchange {
  const source = isObject(raw) ? raw : {};
  const nestedData = isObject(source.data) ? source.data : source;
  return {
    id: asString(firstPresent(nestedData, ['id', 'chat_id']), crypto.randomUUID()),
    question: asString(firstPresent(nestedData, ['question']), questionFallback),
    answer: asString(firstPresent(nestedData, ['answer', 'response']), ''),
    sources: asArray(firstPresent(nestedData, ['sources', 'citations'], [])).map(normalizeSource),
    created_at: asString(firstPresent(nestedData, ['created_at', 'timestamp']), new Date().toISOString()),
  };
}

function normalizeMemoryLibrary(raw: unknown): MemoryLibrary {
  const source = isObject(raw) ? raw : {};
  const timeline = asArray(firstPresent(source, ['timeline', 'entries'], []))
    .map((entry) => (isObject(entry) ? entry : {}))
    .map((entry, index) => ({
      entry_id: asString(firstPresent(entry, ['entry_id', 'id']), `entry_${index}`),
      entry_name: asString(firstPresent(entry, ['entry_name', 'name']), `条目 ${index + 1}`),
      entry_type: asString(firstPresent(entry, ['entry_type', 'type']), 'memory'),
      summary: asString(firstPresent(entry, ['summary', 'text', 'description']), ''),
      created_at: asString(firstPresent(entry, ['created_at']), new Date().toISOString()),
    }));

  const byTypeSource = isObject(firstPresent(source, ['by_type'], {}))
    ? (firstPresent(source, ['by_type'], {}) as Record<string, unknown>)
    : {};

  const byTheme = asArray(firstPresent(source, ['by_theme', 'themes'], []))
    .map((item) => (isObject(item) ? item : {}))
    .map((item) => ({
      theme_name: asString(firstPresent(item, ['theme_name', 'name']), '未命名主题'),
      entries: asArray<string>(firstPresent(item, ['entries', 'items'], [])),
      count: asNumber(firstPresent(item, ['count']), asArray(firstPresent(item, ['entries'], [])).length),
    }));

  return {
    timeline,
    by_type: Object.fromEntries(
      Object.entries(byTypeSource).map(([key, value]) => [key, asArray<string>(value)]),
    ),
    by_theme: byTheme,
  };
}

function normalizeProfileInsightsRecord(raw: unknown, index: number) {
  const source = isObject(raw) ? raw : {};
  return {
    theme_name: asString(firstPresent(source, ['theme_name', 'title', 'label', 'name']), `主题 ${index + 1}`),
    reason: asString(firstPresent(source, ['reason', 'summary', 'description', 'content']), ''),
    evidence_entries: asArray<string>(firstPresent(source, ['evidence_entries', 'tags', 'keywords'], [])),
  };
}

function normalizeAbilityTag(raw: unknown, index: number) {
  const source = isObject(raw) ? raw : {};
  return {
    ability_name: asString(firstPresent(source, ['ability_name', 'label', 'title', 'name']), `能力 ${index + 1}`),
    reason: asString(firstPresent(source, ['reason', 'summary', 'description']), ''),
    evidence_entries: asArray<string>(firstPresent(source, ['evidence_entries'], [])),
  };
}

function normalizePersonalProfile(raw: unknown): PersonalProfile {
  const source = isObject(raw) ? raw : {};
  return {
    knowledge_base_id: asString(firstPresent(source, ['knowledge_base_id']), ''),
    entry_count: asNumber(firstPresent(source, ['entry_count']), 0),
    profile_summary: asString(firstPresent(source, ['profile_summary']), ''),
    main_themes: asArray(firstPresent(source, ['main_themes'], [])).map(normalizeProfileInsightsRecord),
    ability_tags: asArray(firstPresent(source, ['ability_tags'], [])).map(normalizeAbilityTag),
    expression_style: asString(firstPresent(source, ['expression_style']), ''),
    growth_focus: asArray<string>(firstPresent(source, ['growth_focus'], [])),
  };
}

function normalizeThemeChange(raw: unknown, index: number) {
  const source = isObject(raw) ? raw : {};
  return {
    theme_name: asString(firstPresent(source, ['theme_name', 'name']), `主题变化 ${index + 1}`),
    change_type: asString(firstPresent(source, ['change_type']), 'stable'),
    reason: asString(firstPresent(source, ['reason', 'summary', 'description']), ''),
    evidence_entries: asArray<string>(firstPresent(source, ['evidence_entries'], [])),
  };
}

function normalizeGrowthReport(raw: unknown): GrowthReport {
  const source = isObject(raw) ? raw : {};
  return {
    knowledge_base_id: asString(firstPresent(source, ['knowledge_base_id']), ''),
    analysis_window: asString(firstPresent(source, ['analysis_window']), ''),
    stage_summary: asString(firstPresent(source, ['stage_summary']), ''),
    recent_focus: asArray<string>(firstPresent(source, ['recent_focus'], [])),
    theme_changes: asArray(firstPresent(source, ['theme_changes'], [])).map(normalizeThemeChange),
    highlights: asArray<string>(firstPresent(source, ['highlights'], [])),
    blockers: asArray<string>(firstPresent(source, ['blockers'], [])),
    next_actions: asArray<string>(firstPresent(source, ['next_actions'], [])),
  };
}

function normalizeIndexSubmission(raw: unknown, documentId: string): IndexSubmission {
  const source = isObject(raw) ? raw : {};
  return {
    document_id: asString(firstPresent(source, ['document_id', 'id']), documentId),
    status: normalizeDocumentStatus(firstPresent(source, ['status'], 'queued')),
    task_id: asString(firstPresent(source, ['task_id'])),
    message: asString(firstPresent(source, ['message', 'detail'])),
  };
}

function unwrapCollection(raw: unknown, collectionKeys: string[]) {
  if (Array.isArray(raw)) {
    return raw;
  }
  if (!isObject(raw)) {
    return [];
  }

  for (const key of collectionKeys) {
    const candidate = raw[key];
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  const nestedData = isObject(raw.data) ? raw.data : null;
  if (nestedData) {
    for (const key of collectionKeys) {
      const candidate = nestedData[key];
      if (Array.isArray(candidate)) {
        return candidate;
      }
    }
  }

  return [];
}

async function withFallback<T>(online: () => Promise<T>, offline: () => Promise<T>) {
  if (shouldUseMocks()) {
    return offline();
  }

  return online();
}

export const api = {
  register(payload: AuthPayload) {
    return withFallback(
      async () =>
        normalizeUser(
          await requestJson<unknown>('/auth/register', {
            method: 'POST',
            body: JSON.stringify(payload),
          }),
        ),
      () => mockRegister(payload),
    );
  },
  login(payload: AuthPayload) {
    return withFallback(
      async () =>
        normalizeAuthToken(
          await requestJson<unknown>('/auth/login', {
            method: 'POST',
            body: JSON.stringify(payload),
          }),
        ),
      () => mockLogin(payload),
    );
  },
  me(token: string) {
    return withFallback(
      async () => normalizeUser(await requestJson<unknown>('/auth/me', {}, token)),
      () => mockMe(),
    );
  },
  knowledgeBases(userId: number, token: string) {
    return withFallback(
      async () => {
        const raw = await requestJson<unknown>(`/users/${userId}/knowledge-bases`, {}, token);
        return unwrapCollection(raw, ['knowledge_bases', 'items', 'records']).map(normalizeKnowledgeBase);
      },
      () => mockKnowledgeBases(),
    );
  },
  createKnowledgeBase(
    userId: number,
    payload: { name: string; description: string },
    token: string,
  ) {
    return withFallback(
      async () =>
        normalizeKnowledgeBase(
          await requestJson<unknown>(
          `/users/${userId}/knowledge-bases`,
          { method: 'POST', body: JSON.stringify(payload) },
          token,
          ),
        ),
      () => mockCreateKnowledgeBase(payload),
    );
  },
  documents(userId: number, token: string, knowledgeBaseId?: string) {
    const query = new URLSearchParams();
    query.set('user_id', String(userId));
    if (knowledgeBaseId) {
      query.set('knowledge_base_id', knowledgeBaseId);
    }
    return withFallback(
      async () => {
        const raw = await requestJson<unknown>(`/kb/documents?${query.toString()}`, {}, token);
        return unwrapCollection(raw, ['documents', 'items', 'records']).map(normalizeDocument);
      },
      () => mockDocuments(knowledgeBaseId),
    );
  },
  uploadDocuments(token: string, userId: number, knowledgeBaseId: string, files: File[]) {
    return withFallback(
      async () => {
        const uploadedDocuments: DocumentItem[] = [];
        for (const file of files) {
          const formData = new FormData();
          formData.append('user_id', String(userId));
          formData.append('knowledge_base_id', knowledgeBaseId);
          formData.append('file', file);
          const raw = await requestJson<unknown>(
            '/kb/documents/upload',
            { method: 'POST', body: formData },
            token,
          );
          uploadedDocuments.push(
            normalizeDocument({
              ...(isObject(raw) ? raw : {}),
              user_id: userId,
              knowledge_base_id: knowledgeBaseId,
              file_name: file.name,
              file_size: file.size,
            }),
          );
        }
        return uploadedDocuments;
      },
      () => mockUploadDocuments(userId, knowledgeBaseId, files),
    );
  },
  indexDocument(token: string, documentId: string) {
    return withFallback(
      async () =>
        normalizeIndexSubmission(
          await requestJson<unknown>(`/kb/documents/${documentId}/index`, { method: 'POST' }, token),
          documentId,
        ),
      async () => {
        const mockDocument = await mockIndexDocument(documentId);
        return normalizeIndexSubmission(
          {
            document_id: mockDocument.id,
            status: mockDocument.status,
            task_id: mockDocument.task_id,
          },
          documentId,
        );
      },
    );
  },
  chatQuery(
    token: string,
    payload: { userId: number; knowledgeBaseId: string; question: string; topK: number },
  ) {
    return withFallback(
      async () =>
        normalizeChatExchange(
          await requestJson<unknown>(
            '/kb/chat/query',
            {
              method: 'POST',
              body: JSON.stringify({
                user_id: payload.userId,
                knowledge_base_id: payload.knowledgeBaseId,
                question: payload.question,
                top_k: payload.topK,
                session_id: `session_${payload.knowledgeBaseId}`,
              }),
            },
            token,
          ),
          payload.question,
        ),
      () => mockChatQuery(payload),
    );
  },
  chatHistory() {
    if (shouldUseMocks()) {
      return mockChatHistory();
    }
    return Promise.resolve([]);
  },
  memoryLibrary(token: string, knowledgeBaseId: string, userId: number) {
    return withFallback(
      async () =>
        normalizeMemoryLibrary(
          await requestJson<unknown>(
            `/memory/knowledge-bases/${knowledgeBaseId}/library?user_id=${userId}`,
            {},
            token,
          ),
        ),
      () => mockMemoryLibrary(),
    );
  },
  profile(token: string, knowledgeBaseId: string) {
    return withFallback(
      async () =>
        normalizePersonalProfile(
          await requestJson<unknown>(`/profile/knowledge-bases/${knowledgeBaseId}`, {}, token),
        ),
      () => mockProfile(),
    );
  },
  growth(token: string, knowledgeBaseId: string) {
    return withFallback(
      async () =>
        normalizeGrowthReport(
          await requestJson<unknown>(
            `/analysis/knowledge-bases/${knowledgeBaseId}/growth`,
            {},
            token,
          ),
        ),
      () => mockGrowth(),
    );
  },
};
