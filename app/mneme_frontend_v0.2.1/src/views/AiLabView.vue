<script setup lang="ts">
import { Bot, ChevronLeft, MessageSquare, Search, Send, Trash2 } from "@lucide/vue";
import { computed, ref } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import { useI18n } from "../composables/useI18n";
import UiEmptyState from "../components/ui/UiEmptyState.vue";

const props = defineProps<{ workspace: MnemeWorkspace; formatDate: (value: string | number | Date) => string }>();
const { t } = useI18n();
const historyCollapsed = ref(window.matchMedia("(max-width: 1023px)").matches);
const activeSession = computed(() => props.workspace.chatSessions.value.find((session) => session.id === props.workspace.activeChatSessionId.value));
const activeModel = computed(() => props.workspace.aiModelConfigs.value.find((config) => config.id === props.workspace.activeAiModelConfigId.value));
const answerModes = [
  { value: "kb_qa", label: "Knowledge base" },
  { value: "memory_query", label: "Long-term memory" },
  { value: "profile_query", label: "Profile" },
  { value: "analysis_query", label: "Growth" },
  { value: "general_chat", label: "General chat" },
] as const;
</script>

<template>
  <div data-testid="stitch-ai-laboratory-layout" class="ai-layout" :class="{ 'ai-layout--collapsed': historyCollapsed }">
    <aside data-testid="ai-history-rail" class="ai-history-panel" :aria-hidden="historyCollapsed">
      <header><div><small>{{ t("ai.mode") }}</small><h2>{{ t("ai.sessions") }}</h2></div><button aria-label="Close chat history" @click="historyCollapsed = true"><ChevronLeft class="size-4" /></button></header>
      <label class="history-search"><Search class="size-4" /><input v-model="workspace.chatSessionFilter.value" :placeholder="t('ai.search')" /></label>
      <button class="new-chat" @click="workspace.createChatSession"><MessageSquare class="size-4" />{{ t("ai.newChat") }}</button>
      <nav>
        <button v-for="session in workspace.filteredChatSessions.value" :key="session.id" :class="{ active: workspace.activeChatSessionId.value === session.id }" @click="workspace.selectChatSession(session.id); historyCollapsed = true">
          <strong>{{ session.title || "Untitled chat" }}</strong><small>{{ session.last_message_at ? formatDate(session.last_message_at) : "No messages" }}</small>
        </button>
      </nav>
    </aside>

    <section data-testid="chat-function-grid" class="chat-workspace">
      <button data-testid="ai-history-rail-toggle" class="rail-toggle" :title="historyCollapsed ? 'Expand chat history' : 'Collapse chat history'" @click="historyCollapsed = !historyCollapsed"><ChevronLeft :class="{ rotate: historyCollapsed }" /></button>
      <header class="chat-header">
        <div><small>AI Laboratory</small><h1>{{ activeSession?.title || "New chat" }}</h1><p>{{ activeModel?.label || "Default backend model" }} · {{ activeModel?.context_window?.toLocaleString() || "backend" }} tokens</p></div>
        <button class="delete-chat" :aria-label="t('ai.delete')" @click="workspace.deleteActiveChatSession"><Trash2 class="size-4" /><span>{{ t("ai.delete") }}</span></button>
      </header>

      <div class="messages">
        <template v-if="workspace.chatMessages.value.length">
          <article v-for="message in workspace.chatMessages.value" :key="message.id" :class="['message', `message--${message.role}`]">
            <div class="message-avatar"><component :is="message.role === 'user' ? MessageSquare : Bot" class="size-4" /></div>
            <div><small>{{ message.role === "user" ? "You" : "Mneme" }} · {{ message.role === "assistant" ? "Analysis Complete" : "Today, 14:03" }}</small><p>{{ message.content }}</p><div v-if="message.sources.length" class="sources"><span>Referenced Context Nodes</span><button v-for="source in message.sources" :key="source.source_id">{{ source.document_id }}</button></div></div>
          </article>
        </template>
        <UiEmptyState v-else :title="t('ai.emptyTitle')" :description="t('ai.emptyDescription')">
          <template #icon><Bot class="size-5" /></template>
        </UiEmptyState>
      </div>

      <form data-testid="workspace-chat-command" class="composer" @submit.prevent="workspace.sendChatMessage">
        <div data-testid="answer-mode-selector" class="answer-modes" aria-label="Answer mode">
          <button v-for="mode in answerModes" :key="mode.value" type="button" :class="{ active: workspace.chatAnswerMode.value === mode.value }" :aria-pressed="workspace.chatAnswerMode.value === mode.value" @click="workspace.chatAnswerMode.value = mode.value">{{ mode.label }}</button>
        </div>
        <div><textarea v-model="workspace.chatQuestion.value" :placeholder="t('ai.placeholder')" /><button aria-label="Send message"><Send class="size-5" /></button></div>
        <small>{{ t("ai.disclaimer") }}</small>
      </form>
    </section>
  </div>
</template>

<style scoped>
.ai-layout { position: relative; display: grid; height: 100%; min-height: 0; grid-template-columns: 280px minmax(0, 1fr); background: var(--bg-canvas); }
.ai-layout--collapsed { grid-template-columns: 0 minmax(0, 1fr); }
.ai-history-panel { z-index: 20; min-width: 0; overflow: auto; padding: 1rem; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.ai-history-panel[aria-hidden="true"] { visibility: hidden; overflow: hidden; padding: 0; pointer-events: none; }
.ai-history-panel header, .chat-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
small { color: var(--text-tertiary); font: 0.66rem var(--font-mono); }
h1, h2, p { margin: 0; }
.ai-history-panel h2 { margin-top: 0.2rem; font-size: 0.85rem; }
.ai-history-panel header button { display: none; }
.history-search { display: flex; height: 2.35rem; align-items: center; gap: 0.5rem; margin-top: 1rem; padding: 0 0.65rem; color: var(--text-tertiary); background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.history-search input { min-width: 0; flex: 1; background: transparent; border: 0; outline: 0; }
.new-chat { display: flex; width: 100%; align-items: center; justify-content: center; gap: 0.45rem; margin-top: 0.65rem; padding: 0.65rem; color: var(--text-primary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.ai-history-panel nav { display: grid; gap: 0.2rem; margin-top: 1rem; }
.ai-history-panel nav button { padding: 0.65rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.4rem; }
.ai-history-panel nav button.active { color: var(--text-primary); background: var(--accent-soft); }
.ai-history-panel nav strong, .ai-history-panel nav small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-history-panel nav small { margin-top: 0.2rem; }
.chat-workspace { position: relative; display: flex; min-width: 0; min-height: 0; flex-direction: column; }
.rail-toggle { position: absolute; top: 50%; left: -1rem; z-index: 35; display: grid; width: 2rem; height: 2.6rem; place-items: center; color: var(--text-secondary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.45rem; }
.rail-toggle svg { width: 1rem; transition: transform 140ms ease; }
.rail-toggle svg.rotate { transform: rotate(180deg); }
.chat-header { min-height: 4.7rem; padding: 0.8rem 1.25rem; border-bottom: 1px solid var(--border-muted); }
.chat-header h1 { margin-top: 0.15rem; font: 600 1.35rem var(--font-serif); }
.chat-header p { margin-top: 0.25rem; color: var(--text-secondary); font-size: 0.72rem; }
.delete-chat { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.45rem 0.65rem; color: var(--danger); background: transparent; border: 1px solid color-mix(in srgb, var(--danger) 32%, var(--border-muted)); border-radius: 0.35rem; font-size: 0.72rem; }
.messages { flex: 1; overflow: auto; padding: 1.5rem max(1rem, calc((100% - 820px) / 2)); }
.message { display: grid; grid-template-columns: 2rem minmax(0, 1fr); gap: 0.8rem; padding: 1rem 0; }
.message-avatar { display: grid; width: 2rem; height: 2rem; place-items: center; color: var(--accent); background: var(--accent-soft); border-radius: 0.45rem; }
.message p { margin-top: 0.35rem; color: var(--text-primary); line-height: 1.7; }
.message--assistant { border-bottom: 1px solid var(--border-muted); }
.sources { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.8rem; }
.sources > span { width: 100%; color: var(--text-tertiary); font: 0.64rem var(--font-mono); text-transform: uppercase; }
.sources button { padding: 0.25rem 0.4rem; color: var(--accent); background: var(--accent-soft); border: 0; border-radius: 0.3rem; font-size: 0.66rem; }
.composer { position: sticky; bottom: 0; padding: 0.75rem max(1rem, calc((100% - 820px) / 2)) 1rem; background: color-mix(in srgb, var(--bg-canvas) 94%, transparent); border-top: 1px solid var(--border-muted); }
.answer-modes { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.45rem; }
.answer-modes button { width: auto; height: auto; padding: 0.3rem 0.55rem; color: var(--text-secondary); background: var(--bg-elevated); border: 1px solid transparent; border-radius: 999px; font-size: 0.68rem; }
.answer-modes button.active { color: var(--accent); background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 35%, transparent); }
.composer > div:nth-child(2) { display: flex; align-items: end; gap: 0.5rem; padding: 0.55rem; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.5rem; }
.composer textarea { min-height: 2.8rem; flex: 1; resize: none; background: transparent; border: 0; outline: 0; }
.composer > div:nth-child(2) > button { display: grid; width: 2.5rem; height: 2.5rem; place-items: center; color: var(--accent-contrast); background: var(--accent); border: 0; border-radius: 0.4rem; }
.composer > small { display: block; margin-top: 0.4rem; text-align: center; }
@media (max-width: 1023px) { .ai-layout, .ai-layout--collapsed { grid-template-columns: minmax(0, 1fr); } .ai-history-panel { position: absolute; inset: 0 auto 0 0; width: min(84vw, 320px); box-shadow: var(--shadow-float); } .ai-history-panel[aria-hidden="true"] { display: none; } .ai-history-panel header button { display: grid; place-items: center; color: var(--text-secondary); background: transparent; border: 0; } .rail-toggle { left: 0.4rem; } }
@media (max-width: 767px) { .chat-header { padding-left: 3rem; } .delete-chat span { display: none; } .messages { padding: 1rem; } .composer { padding: 0.65rem; } }
</style>
