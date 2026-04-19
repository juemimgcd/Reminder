<script setup lang="ts">
import { reactive } from 'vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import KnowledgeBaseGrid from '@/components/knowledge/KnowledgeBaseGrid.vue';
import { useSessionStore } from '@/stores/session';
import { useWorkspaceStore } from '@/stores/workspace';

const session = useSessionStore();
const workspace = useWorkspaceStore();
const form = reactive({
  name: '',
  description: '',
});

async function createKnowledgeBase() {
  if (!session.user || !session.token) {
    return;
  }
  await workspace.createKnowledgeBase(form, session.user.id, session.token);
  form.name = '';
  form.description = '';
}

async function selectKnowledgeBase(id: string) {
  if (!session.token) {
    return;
  }
  await workspace.selectKnowledgeBase(id, session.token);
}
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="Knowledge Bases"
      title="为不同的人生主题建立独立上下文"
      description="前端将知识库作为所有索引、问答和分析动作的顶层上下文。"
    />

    <SurfacePanel eyebrow="Create" title="新建知识库">
      <form class="inline-form" @submit.prevent="createKnowledgeBase">
        <label>
          <span>名称</span>
          <input v-model="form.name" maxlength="24" required />
        </label>
        <label>
          <span>说明</span>
          <input v-model="form.description" maxlength="120" required />
        </label>
        <button class="primary-button" type="submit">创建</button>
      </form>
    </SurfacePanel>

    <KnowledgeBaseGrid
      :active-id="workspace.activeKnowledgeBaseId"
      :items="workspace.knowledgeBases"
      @select="selectKnowledgeBase"
    />
  </div>
</template>
