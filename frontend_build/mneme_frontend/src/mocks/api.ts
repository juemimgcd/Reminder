import type {
  AuthPayload,
  PersonalProfile,
  AuthToken,
  ChatExchange,
  ChatSource,
  DocumentItem,
  GrowthReport,
  KnowledgeBase,
  MemoryLibrary,
  User,
} from '@/lib/types';
import {
  chatHistory,
  demoToken,
  demoUser,
  documents,
  growthMetrics,
  knowledgeBases,
  memoryLibrary,
  profileInsights,
} from '@/mocks/data';

const wait = (ms = 220) => new Promise((resolve) => setTimeout(resolve, ms));

const kbState = [...knowledgeBases];
const documentState = [...documents];
const chatState = [...chatHistory];

export async function mockRegister(payload: AuthPayload): Promise<User> {
  await wait();
  return {
    ...demoUser,
    username: payload.username,
  };
}

export async function mockLogin(_: AuthPayload): Promise<AuthToken> {
  await wait();
  return demoToken;
}

export async function mockMe(): Promise<User> {
  await wait();
  return demoUser;
}

export async function mockKnowledgeBases(): Promise<KnowledgeBase[]> {
  await wait();
  return kbState;
}

export async function mockCreateKnowledgeBase(payload: {
  name: string;
  description: string;
}): Promise<KnowledgeBase> {
  await wait();
  const created: KnowledgeBase = {
    id: `kb_${Math.random().toString(36).slice(2, 10)}`,
    user_id: 1,
    name: payload.name,
    description: payload.description,
    is_default: false,
    created_at: new Date().toISOString(),
    document_count: 0,
    memory_count: 0,
    updated_at: new Date().toISOString(),
    status: 'draft',
  };
  kbState.unshift(created);
  return created;
}

export async function mockDocuments(knowledgeBaseId?: string): Promise<DocumentItem[]> {
  await wait();
  if (!knowledgeBaseId) {
    return documentState;
  }
  return documentState.filter((item) => item.knowledge_base_id === knowledgeBaseId);
}

export async function mockUploadDocuments(
  userId: number,
  knowledgeBaseId: string,
  files: File[],
): Promise<DocumentItem[]> {
  await wait(300);
  const uploaded = files.map((file, index) => ({
    id: `doc_upload_${Date.now()}_${index}`,
    user_id: userId,
    file_name: file.name,
    name: file.name,
    knowledge_base_id: knowledgeBaseId,
    file_type: file.name.split('.').pop() ?? '',
    status: 'uploaded' as const,
    page_count: Math.max(1, Math.round(file.size / 48000)),
    chunk_count: 0,
    created_at: new Date().toISOString(),
    size_label: `${Math.max(1, Math.round(file.size / 1024))} KB`,
  }));

  uploaded.forEach((item) => documentState.unshift(item));
  return uploaded;
}

export async function mockIndexDocument(documentId: string): Promise<DocumentItem> {
  await wait(350);
  const target = documentState.find((item) => item.id === documentId);
  if (!target) {
    throw new Error('Document not found');
  }

  target.status = 'indexed';
  target.chunk_count = target.chunk_count || 24;
  return target;
}

export async function mockChatQuery(payload: {
  knowledgeBaseId: string;
  question: string;
}): Promise<ChatExchange> {
  await wait(280);
  const relatedDocument =
    documentState.find(
      (item) => item.knowledge_base_id === payload.knowledgeBaseId && item.status === 'indexed',
    ) ?? documentState[0];

  const sources: ChatSource[] = [
    {
      knowledge_base_id: payload.knowledgeBaseId,
      document_id: relatedDocument.id,
      chunk_id: `${relatedDocument.id}_chunk_01..${relatedDocument.id}_chunk_02`,
      page_no: null,
      text: '检索结果显示，最近材料反复提到“长期记忆系统”“写作即索引”“让知识能被再次调用”。',
      source_chunk_ids: [`${relatedDocument.id}_chunk_01`, `${relatedDocument.id}_chunk_02`],
      source_page_nos: [1, 2],
      merged_chunk_count: 2,
    },
  ];

  const exchange: ChatExchange = {
    id: `chat_${Date.now()}`,
    question: payload.question,
    answer:
      '基于当前知识库，系统更倾向把你的内容生产视为“持续提炼记忆的过程”，而不是一次性完成的文档归档。前端中我会把这个过程拆成上传、索引、检索、主题聚合和分析回看五个可见阶段。',
    sources,
    created_at: new Date().toISOString(),
  };

  chatState.unshift(exchange);
  return exchange;
}

export async function mockChatHistory(): Promise<ChatExchange[]> {
  await wait();
  return chatState;
}

export async function mockMemoryLibrary(): Promise<MemoryLibrary> {
  await wait();
  return memoryLibrary;
}

export async function mockProfile(): Promise<PersonalProfile> {
  await wait();
  return profileInsights;
}

export async function mockGrowth(): Promise<GrowthReport> {
  await wait();
  return growthMetrics;
}
