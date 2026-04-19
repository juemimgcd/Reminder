<script setup lang="ts">
import type { GrowthReport, PersonalProfile } from '@/lib/types';

defineProps<{
  profile: PersonalProfile | null;
  growth: GrowthReport | null;
}>();
</script>

<template>
  <div class="insight-columns">
    <section class="insight-stack">
      <article v-if="profile" class="insight-card">
        <strong>画像摘要</strong>
        <p>{{ profile.profile_summary }}</p>
        <div class="chip-wrap">
          <span v-for="tag in profile.growth_focus" :key="tag" class="memory-chip">{{ tag }}</span>
        </div>
      </article>

      <article
        v-for="item in profile?.main_themes ?? []"
        :key="item.theme_name"
        class="insight-card"
      >
        <strong>{{ item.theme_name }}</strong>
        <p>{{ item.reason }}</p>
        <div class="chip-wrap">
          <span v-for="tag in item.evidence_entries" :key="tag" class="memory-chip">{{ tag }}</span>
        </div>
      </article>

      <article
        v-for="item in profile?.ability_tags ?? []"
        :key="item.ability_name"
        class="insight-card"
      >
        <strong>{{ item.ability_name }}</strong>
        <p>{{ item.reason }}</p>
      </article>
    </section>

    <section class="growth-stack">
      <article v-if="growth" class="growth-card">
        <header>
          <strong>阶段总结</strong>
          <span class="growth-card__trend" data-trend="up">{{ growth.analysis_window }}</span>
        </header>
        <p>{{ growth.stage_summary }}</p>
      </article>

      <article
        v-for="item in growth?.theme_changes ?? []"
        :key="`${item.theme_name}-${item.change_type}`"
        class="growth-card"
      >
        <header>
          <strong>{{ item.theme_name }}</strong>
          <span class="growth-card__trend" :data-trend="item.change_type === 'stronger' ? 'up' : 'steady'">
            {{ item.change_type }}
          </span>
        </header>
        <p>{{ item.reason }}</p>
      </article>

      <article v-if="growth?.next_actions.length" class="growth-card">
        <header>
          <strong>下一步建议</strong>
          <span class="growth-card__trend" data-trend="steady">{{ growth.next_actions.length }} 条</span>
        </header>
        <p>{{ growth.next_actions.join(' / ') }}</p>
      </article>
    </section>
  </div>
</template>
