<script setup lang="ts">
import ChatComposer from '@/components/chat/ChatComposer.vue';
import SourceCard from '@/components/chat/SourceCard.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import { useSessionStore } from '@/stores/session';
import { useWorkspaceStore } from '@/stores/workspace';

const session = useSessionStore();
const workspace = useWorkspaceStore();

async function submit(payload: { question: string; topK: number }) {
  if (!session.token) {
    return;
  }
  await workspace.ask(session.token, payload);
}
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="RAG Query"
      title="在答案旁边保留来源，而不是把检索过程藏起来"
      description="问答页同时展示问题、回答、chunk 来源和页码集合，适配 Mneme 的检索优先结构。"
    />

    <ChatComposer @submit="submit" />

    <section v-if="workspace.chats.length" class="chat-stack">
      <SurfacePanel
        v-for="exchange in workspace.chats"
        :key="exchange.id"
        eyebrow="Conversation"
        title="一次检索问答"
      >
        <div class="chat-answer">
          <div class="chat-bubble chat-bubble--question">
            <strong>问</strong>
            <p>{{ exchange.question }}</p>
          </div>
          <div class="chat-bubble chat-bubble--answer">
            <strong>答</strong>
            <p>{{ exchange.answer }}</p>
          </div>
        </div>

        <div class="sources-grid">
          <SourceCard
            v-for="source in exchange.sources"
            :key="`${exchange.id}-${source.chunk_id}`"
            :source="source"
          />
        </div>
      </SurfacePanel>
    </section>

    <EmptyState
      v-else
      title="还没有问答记录"
      description="发起一个问题，工作台会把回答和来源片段一起记录下来。"
    />
  </div>
</template>
