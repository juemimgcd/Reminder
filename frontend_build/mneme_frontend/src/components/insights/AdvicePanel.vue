<script setup lang="ts">
import type { GrowthAdvice } from '@/lib/types';

defineProps<{
  advice: GrowthAdvice | null;
}>();
</script>

<template>
  <div v-if="advice" class="advice-stack">
    <article class="advice-card advice-card--summary">
      <header>
        <strong>建议摘要</strong>
        <span v-if="advice.focus_goal" class="inline-badge">{{ advice.focus_goal }}</span>
      </header>
      <p>{{ advice.advice_summary }}</p>
      <div v-if="advice.current_priorities.length" class="chip-wrap">
        <span v-for="item in advice.current_priorities" :key="item" class="memory-chip">{{ item }}</span>
      </div>
    </article>

    <article
      v-for="item in advice.action_suggestions"
      :key="`${item.area}-${item.action}`"
      class="advice-card"
    >
      <header>
        <strong>{{ item.area }}</strong>
        <span class="growth-card__trend" data-trend="up">现在做</span>
      </header>
      <p>{{ item.why_now }}</p>
      <dl class="advice-card__detail">
        <div>
          <dt>动作</dt>
          <dd>{{ item.action }}</dd>
        </div>
        <div>
          <dt>第一步</dt>
          <dd>{{ item.first_step }}</dd>
        </div>
      </dl>
      <div v-if="item.evidence_entries.length" class="chip-wrap">
        <span v-for="entry in item.evidence_entries" :key="entry" class="memory-chip">{{ entry }}</span>
      </div>
    </article>

    <article v-if="advice.one_week_plan.length" class="advice-card">
      <strong>一周计划</strong>
      <p>{{ advice.one_week_plan.join(' / ') }}</p>
    </article>

    <article v-if="advice.avoid_list.length" class="advice-card">
      <strong>当前先别分散的方向</strong>
      <p>{{ advice.avoid_list.join(' / ') }}</p>
    </article>

    <article v-if="advice.reflection_questions.length" class="advice-card">
      <strong>继续复盘的问题</strong>
      <p>{{ advice.reflection_questions.join(' / ') }}</p>
    </article>
  </div>
</template>
