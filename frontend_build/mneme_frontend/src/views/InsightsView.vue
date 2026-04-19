<script setup lang="ts">
import { ref } from 'vue';

import EmptyState from '@/components/common/EmptyState.vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import AdvicePanel from '@/components/insights/AdvicePanel.vue';
import InsightColumn from '@/components/insights/InsightColumn.vue';
import { useSessionStore } from '@/stores/session';
import { useWorkspaceStore } from '@/stores/workspace';

const session = useSessionStore();
const workspace = useWorkspaceStore();
const focusGoal = ref('');

async function refreshInsights() {
  if (!session.token) {
    return;
  }
  await workspace.refreshInsights(session.token);
}

async function rebuildMemory() {
  if (!session.token) {
    return;
  }
  await workspace.rebuildMemory(session.token);
}

async function generateAdvice() {
  if (!session.token) {
    return;
  }
  await workspace.generateAdvice(session.token, focusGoal.value);
}
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="Profile & Growth"
      title="把画像、成长分析和行动建议收敛成可回看的洞察面板"
      description="洞察页现在同时支持自动生成后的回刷，以及手动重建 memory / 重新生成建议。"
    />

    <SurfacePanel eyebrow="Insight Deck" title="当前洞察">
      <div class="surface-actions">
        <button class="ghost-button" type="button" :disabled="workspace.insightsLoading" @click="refreshInsights">
          {{ workspace.insightsLoading ? '刷新中...' : '刷新洞察' }}
        </button>
        <button class="ghost-button" type="button" :disabled="workspace.insightsLoading" @click="rebuildMemory">
          {{ workspace.insightsLoading ? '重建中...' : '重建记忆' }}
        </button>
      </div>

      <InsightColumn
        v-if="workspace.profile || workspace.growth"
        :growth="workspace.growth"
        :profile="workspace.profile"
      />
      <EmptyState
        v-else
        title="还没有洞察结果"
        description="先让文档完成索引，或使用“重建记忆”从已有 chunk 重新抽取 memory。"
      />
    </SurfacePanel>

    <SurfacePanel eyebrow="Advice" title="行动建议">
      <form class="inline-form inline-form--stacked" @submit.prevent="generateAdvice">
        <label>
          <span>本次希望优先关注什么</span>
          <input
            v-model="focusGoal"
            maxlength="120"
            placeholder="例如：把已有知识库整理成可持续输出节律"
          />
        </label>
        <div class="surface-actions">
          <button
            class="primary-button"
            type="submit"
            :disabled="workspace.adviceLoading || !workspace.memoryLibrary?.timeline.length"
          >
            {{ workspace.adviceLoading ? '生成中...' : '生成 Advice' }}
          </button>
        </div>
      </form>

      <AdvicePanel v-if="workspace.advice" :advice="workspace.advice" />
      <EmptyState
        v-else
        title="还没有建议"
        description="输入一个当前目标，点击生成 advice；如果记忆库为空，先重建 memory。"
      />
    </SurfacePanel>
  </div>
</template>
