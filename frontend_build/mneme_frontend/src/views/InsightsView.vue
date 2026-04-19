<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import InsightColumn from '@/components/insights/InsightColumn.vue';
import { useWorkspaceStore } from '@/stores/workspace';

const workspace = useWorkspaceStore();
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="Profile & Growth"
      title="把画像和成长分析收敛成可读、可比较、可回看的洞察面板"
      description="这部分针对 Mneme 的增强能力做了独立的信息层，让未来 advice / companion 也能顺滑挂进来。"
    />

    <SurfacePanel eyebrow="Insight Deck" title="当前洞察">
      <InsightColumn
        v-if="workspace.profile || workspace.growth"
        :growth="workspace.growth"
        :profile="workspace.profile"
      />
      <EmptyState
        v-else
        title="还没有洞察结果"
        description="等画像和成长分析接口输出稳定后，这里会展示最新分析。"
      />
    </SurfacePanel>
  </div>
</template>
