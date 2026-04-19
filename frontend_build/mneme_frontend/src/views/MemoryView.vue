<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import TimelineList from '@/components/memory/TimelineList.vue';
import { useWorkspaceStore } from '@/stores/workspace';

const workspace = useWorkspaceStore();
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="Memory Library"
      title="把片段知识重组为时间线、类型簇和主题簇"
      description="记忆库页强调结构化沉淀，而不是只看原始文档列表。"
    />

    <SurfacePanel eyebrow="Structured Memory" title="知识库记忆视图">
      <TimelineList v-if="workspace.memoryLibrary" :library="workspace.memoryLibrary" />
      <EmptyState
        v-else
        title="记忆库暂时为空"
        description="完成索引后这里会自动出现结果；如果已有 chunk 但没有记忆，也可以去洞察页手动重建。"
      />
    </SurfacePanel>
  </div>
</template>
