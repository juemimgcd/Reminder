<script setup lang="ts">
import MetricCard from '@/components/common/MetricCard.vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import ActivityFeed from '@/components/dashboard/ActivityFeed.vue';
import { useWorkspaceStore } from '@/stores/workspace';

const workspace = useWorkspaceStore();
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="Workspace Overview"
      title="把 RAG 主链路做成一眼能看清的工作台"
      description="总览页优先展示当前上下文、索引状态、近期活动和可追踪的增长指标。"
    />

    <section class="metric-grid">
      <MetricCard
        v-for="metric in workspace.dashboardMetrics"
        :key="metric.label"
        :change="metric.change"
        :label="metric.label"
        :tone="metric.tone"
        :value="metric.value"
      />
    </section>

    <section class="dashboard-grid">
      <SurfacePanel eyebrow="Current Context" title="当前知识库">
        <div v-if="workspace.currentKnowledgeBase" class="context-card">
          <strong>{{ workspace.currentKnowledgeBase.name }}</strong>
          <p>{{ workspace.currentKnowledgeBase.description }}</p>
          <dl class="context-card__meta">
            <div>
              <dt>文档数量</dt>
              <dd>{{ workspace.currentKnowledgeBase.document_count }}</dd>
            </div>
            <div>
              <dt>记忆条目</dt>
              <dd>{{ workspace.currentKnowledgeBase.memory_count }}</dd>
            </div>
          </dl>
        </div>
      </SurfacePanel>

      <SurfacePanel eyebrow="Recent Activity" title="最近动态">
        <ActivityFeed :items="workspace.activityFeed" />
      </SurfacePanel>
    </section>
  </div>
</template>
