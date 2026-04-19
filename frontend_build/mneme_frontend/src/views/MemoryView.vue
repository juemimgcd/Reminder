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
        description="等文档索引和记忆提取接通后，这里会显示主题化结果。"
      />
    </SurfacePanel>
  </div>
</template>
