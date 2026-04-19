import type {
  AbilityTag,
  ActivityItem,
  AuthToken,
  ChatExchange,
  DashboardMetric,
  DocumentItem,
  GrowthReport,
  KnowledgeBase,
  MemoryLibrary,
  PersonalProfile,
  User,
} from '@/lib/types';

export const demoUser: User = {
  id: 1,
  username: 'mneme_demo',
  display_name: 'Mneme Demo',
  avatar_url: '/static/avatars/default.png',
  created_at: '2026-04-18T09:00:00Z',
};

export const demoToken: AuthToken = {
  access_token: 'demo-mneme-token',
  token_type: 'bearer',
};

export const knowledgeBases: KnowledgeBase[] = [
  {
    id: 'kb_life_writing',
    user_id: 1,
    name: '人生写作总库',
    description: '博客、年度总结、长文复盘和播客笔记。',
    is_default: true,
    created_at: '2026-04-01T12:20:00Z',
    document_count: 12,
    memory_count: 86,
    updated_at: '2026-04-18T12:20:00Z',
    status: 'ready',
  },
  {
    id: 'kb_product_research',
    user_id: 1,
    name: '产品研究档案',
    description: '竞品拆解、访谈纪要、需求假设和实验记录。',
    is_default: false,
    created_at: '2026-04-02T16:10:00Z',
    document_count: 8,
    memory_count: 52,
    updated_at: '2026-04-17T16:10:00Z',
    status: 'indexing',
  },
  {
    id: 'kb_reading_notes',
    user_id: 1,
    name: '阅读卡片库',
    description: '书摘、课程摘要与引用片段。',
    is_default: false,
    created_at: '2026-04-03T08:40:00Z',
    document_count: 24,
    memory_count: 131,
    updated_at: '2026-04-16T08:40:00Z',
    status: 'ready',
  },
];

export const documents: DocumentItem[] = [
  {
    id: 'doc_annual_review_2025',
    user_id: 1,
    file_name: '2025 年度复盘.pdf',
    name: '2025 年度复盘.pdf',
    knowledge_base_id: 'kb_life_writing',
    file_type: 'pdf',
    status: 'indexed',
    page_count: 18,
    chunk_count: 64,
    created_at: '2026-04-18T09:20:00Z',
    size_label: '4.8 MB',
  },
  {
    id: 'doc_habit_field_notes',
    user_id: 1,
    file_name: '习惯实验田野笔记.md',
    name: '习惯实验田野笔记.md',
    knowledge_base_id: 'kb_life_writing',
    file_type: 'md',
    status: 'indexed',
    page_count: 7,
    chunk_count: 26,
    created_at: '2026-04-17T11:30:00Z',
    size_label: '320 KB',
  },
  {
    id: 'doc_product_interviews',
    user_id: 1,
    file_name: '用户访谈第 4 轮.txt',
    name: '用户访谈第 4 轮.txt',
    knowledge_base_id: 'kb_product_research',
    file_type: 'txt',
    status: 'indexing',
    page_count: 10,
    chunk_count: 0,
    created_at: '2026-04-18T10:12:00Z',
    size_label: '160 KB',
  },
];

export const chatHistory: ChatExchange[] = [
  {
    id: 'chat_1',
    question: '我在 2025 年的成长主题里，最反复出现的关键词是什么？',
    answer:
      '从已索引内容看，出现频率最高的是“长期主义”“节律修复”和“写作作为认知外骨骼”。这些主题同时出现在年度复盘、习惯实验和阅读卡片中，说明你的成长并不是围绕一次性冲刺，而是围绕稳定可复用的个人系统在收敛。',
    sources: [
      {
        knowledge_base_id: 'kb_life_writing',
        document_id: 'doc_annual_review_2025',
        chunk_id: 'chunk_annual_17..chunk_annual_18',
        page_no: null,
        text: '我不再把效率理解成多做，而是把它理解成能否长期维持写作、运动、复盘这三个底盘动作。',
        source_chunk_ids: ['chunk_annual_17', 'chunk_annual_18'],
        source_page_nos: [6, 7],
        merged_chunk_count: 2,
      },
    ],
    created_at: '2026-04-18T12:40:00Z',
  },
];

export const memoryLibrary: MemoryLibrary = {
  timeline: [
    {
      entry_id: 'entry_01',
      entry_name: '重建晨间节律',
      entry_type: 'habit',
      summary: '通过写作和步行恢复日内节律，把一天的开头固定下来。',
      created_at: '2026-03-10T09:00:00Z',
    },
    {
      entry_id: 'entry_02',
      entry_name: '从记录转向分析',
      entry_type: 'insight',
      summary: '不只保存素材，而是开始提取主题与证据链。',
      created_at: '2026-03-28T20:00:00Z',
    },
    {
      entry_id: 'entry_03',
      entry_name: '知识库即作品集',
      entry_type: 'belief',
      summary: '把知识库看作持续生成的作品，而不是归档抽屉。',
      created_at: '2026-04-08T22:30:00Z',
    },
  ],
  by_type: {
    habit: ['重建晨间节律', '固定每周复盘'],
    insight: ['从记录转向分析', '长期写作比短期爆发更重要'],
    belief: ['知识库即作品集'],
  },
  by_theme: [
    {
      theme_name: '长期主义',
      entries: ['重建晨间节律', '固定每周复盘', '知识库即作品集'],
      count: 3,
    },
    {
      theme_name: '认知升级',
      entries: ['从记录转向分析', '长期写作比短期爆发更重要'],
      count: 2,
    },
  ],
};

const abilityTags: AbilityTag[] = [
  {
    ability_name: '叙事型学习',
    reason: '你反复通过写作和复盘整合材料，而不是只保留碎片记录。',
    evidence_entries: ['从记录转向分析', '知识库即作品集'],
  },
  {
    ability_name: '结构化实验',
    reason: '会在习惯和产品研究中构造假设、追踪变化、记录反馈。',
    evidence_entries: ['重建晨间节律'],
  },
];

export const profileInsights: PersonalProfile = {
  knowledge_base_id: 'kb_life_writing',
  entry_count: 86,
  profile_summary:
    '你更像通过写作和长期积累来构建认知系统的人，关注节律、复盘和主题收敛，而不是一次性冲刺。',
  main_themes: [
    {
      theme_name: '长期主义',
      reason: '多个时期的词条都指向稳定投入和缓慢积累。',
      evidence_entries: ['重建晨间节律', '知识库即作品集'],
    },
    {
      theme_name: '认知整理',
      reason: '内容不只停留在记录层，而是持续向结构化分析推进。',
      evidence_entries: ['从记录转向分析'],
    },
  ],
  ability_tags: abilityTags,
  expression_style: '偏叙事、偏总结、重视上下文和自我观察。',
  growth_focus: ['稳定写作节律', '主题收敛', '让知识可复用'],
};

export const growthMetrics: GrowthReport = {
  knowledge_base_id: 'kb_life_writing',
  analysis_window: '最近 30 天',
  stage_summary: '你正从“收集材料”过渡到“持续提炼自己的主题系统”。',
  recent_focus: ['长期主义', '节律修复', '写作即索引'],
  theme_changes: [
    {
      theme_name: '长期主义',
      change_type: 'stronger',
      reason: '近期条目中该主题的频率更高，且表述更具体。',
      evidence_entries: ['重建晨间节律', '知识库即作品集'],
    },
  ],
  highlights: ['阶段性输出更稳定', '开始把素材转成主题簇'],
  blockers: ['旧材料仍未完全索引', '部分主题还停留在单点记录'],
  next_actions: ['优先清理待索引文档', '继续围绕固定主题做周复盘'],
};

export const dashboardMetrics: DashboardMetric[] = [
  {
    label: '知识库',
    value: '3',
    change: '+1 本周',
    tone: 'teal',
  },
  {
    label: '已索引文档',
    value: '44',
    change: '86 条记忆',
    tone: 'indigo',
  },
  {
    label: '最近 7 天提问',
    value: '19',
    change: '检索成功率 94%',
    tone: 'amber',
  },
  {
    label: '待处理索引',
    value: '1',
    change: '建议尽快完成',
    tone: 'coral',
  },
];

export const activityFeed: ActivityItem[] = [
  {
    id: 'activity_1',
    title: '年度复盘完成索引',
    detail: '新增 64 个 chunk，可用于问答与主题分析。',
    timestamp: '今天 12:20',
    tone: 'teal',
  },
  {
    id: 'activity_2',
    title: '产品研究库开始新一轮索引',
    detail: '系统已接收《用户访谈第 4 轮》并进入异步处理。',
    timestamp: '今天 10:12',
    tone: 'amber',
  },
  {
    id: 'activity_3',
    title: '画像报告更新',
    detail: '从最近两周材料中提炼出“叙事型学习者”标签。',
    timestamp: '昨天 21:40',
    tone: 'indigo',
  },
];
