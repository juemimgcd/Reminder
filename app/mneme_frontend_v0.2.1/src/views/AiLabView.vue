<script setup lang="ts">
import { Activity, Bot, ChevronLeft, MessageSquare, Search, Send, Square, Trash2 } from "@lucide/vue";
import { computed, ref } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import UiEmptyState from "../components/ui/UiEmptyState.vue";
const props = defineProps<{
  workspace: MnemeWorkspace;
  formatDate: (value: string | number | Date) => string;
}>();
const modes = [
  { value: "kb_qa", label: "Knowledge base" },
  { value: "memory_query", label: "Long-term memory" },
  { value: "profile_query", label: "Profile" },
  { value: "analysis_query", label: "Analysis" },
  { value: "general_chat", label: "General chat" },
] as const;
const modeLabel = (value?: string) =>
  modes.find((m) => m.value === value)?.label ?? "Assistant";
const historyCollapsed = ref(window.matchMedia("(max-width: 1023px)").matches);
const modeDescription = computed(() => ({
  kb_qa: "Answer from indexed documents in the active knowledge base.",
  memory_query: "Answer from stored memory evidence for the active workspace.",
  profile_query: "Summarize the profile evidence associated with this workspace.",
  analysis_query: "Analyze growth signals and evidence-backed patterns.",
  general_chat: "Use a general conversation without private retrieval.",
}[props.workspace.chatAnswerMode.value]));
</script>
<template>
  <div data-testid="stitch-ai-laboratory-layout" class="ai-layout" :class="{ 'ai-layout--collapsed': historyCollapsed }">
    <aside data-testid="ai-history-rail" class="ai-history-panel" :aria-hidden="historyCollapsed">
      <header>
        <h2>Chats</h2>
        <button @click="workspace.createChatSession">New chat</button>
      </header>
      <label class="history-search"><Search /><input v-model="workspace.chatSessionFilter.value" placeholder="Search history..." /></label>
      <nav>
        <button
          v-for="s in workspace.filteredChatSessions.value"
          :key="s.id"
          :class="{ active: s.id === workspace.activeChatSessionId.value }"
          @click="workspace.selectChatSession(s.id)"
        >
          <strong>{{ s.title || "Untitled chat" }}</strong
          ><small>{{
            s.last_message_at ? formatDate(s.last_message_at) : "No messages"
          }}</small>
        </button>
      </nav>
    </aside>
    <section data-testid="chat-function-grid" class="chat">
      <button
        data-testid="ai-history-rail-toggle"
        class="rail-toggle"
        :title="historyCollapsed ? 'Expand chat history' : 'Collapse chat history'"
        @click="historyCollapsed = !historyCollapsed"
      ><ChevronLeft :class="{ rotate: historyCollapsed }" /></button>
      <header>
        <div>
          <small>AI Laboratory</small>
          <h1>
            {{
              workspace.chatSessions.value.find(
                (s) => s.id === workspace.activeChatSessionId.value,
              )?.title || "New chat"
            }}
          </h1>
        </div>
        <button class="danger" aria-label="Delete active chat" @click="workspace.deleteActiveChatSession">
          <Trash2 />Delete
        </button>
      </header>
      <main>
        <template v-if="workspace.chatMessages.value.length"
          ><article
            v-for="(message, index) in workspace.chatMessages.value"
            :key="message.id"
            :class="message.role"
          >
            <div class="avatar">
              <component :is="message.role === 'user' ? MessageSquare : Bot" />
            </div>
            <div>
              <small
                >{{ message.role === "user" ? "You" : "Mneme" }} ·
                {{ formatDate(message.created_at) }}</small
              ><span v-if="message.route" data-testid="answer-mode-badge" class="mode">{{
                modeLabel(message.route.query_type)
              }}</span>
              <p>{{ message.content }}</p>
              <div v-if="message.role === 'assistant'" class="meta">
                <span v-if="message.agent_run_id"
                  >Run {{ message.agent_run_id }}</span
                ><span v-if="message.confidence !== null"
                  >Confidence {{ Math.round(message.confidence * 100) }}%</span
                ><span v-if="message.insufficient_evidence"
                  >Insufficient evidence</span
                ><span v-if="message.uncertainty"
                  >Uncertainty: {{ message.uncertainty }}</span
                ><button
                  :disabled="workspace.chatPending.value"
                  @click="
                    workspace.regenerateChatMessage(
                      workspace.chatMessages.value[index - 1]?.id,
                      workspace.chatAnswerMode.value,
                    )
                  "
                >
                  Regenerate in selected mode
                </button>
              </div>
              <div v-if="message.sources.length" class="sources">
                <span
                  v-for="source in message.sources"
                  :key="
                    source.evidence_id ||
                    source.source_id ||
                    source.document_id ||
                    source.chunk_id
                  "
                  >{{ source.source_type || "source" }} ·
                  {{
                    source.document_id ||
                    source.source_id ||
                    source.evidence_id
                  }}<template v-if="source.source_time">
                    · {{ formatDate(source.source_time) }}</template
                  ></span
                >
              </div>
            </div>
          </article></template
        ><UiEmptyState
          v-else
          title="Start a conversation"
          description="Choose an answer mode, then ask a question."
          ><template #icon><Bot /></template
        ></UiEmptyState>
        <aside
          v-if="workspace.chatRunTrace.value.length"
          data-testid="agent-run-trace"
          class="run-trace"
          aria-live="polite"
        >
          <header>
            <div><Activity /><strong>Live run trace</strong></div>
            <span :data-state="workspace.chatStreamState.value">{{
              workspace.chatStreamState.value
            }}</span>
          </header>
          <ol>
            <li
              v-for="item in workspace.chatRunTrace.value"
              :key="item.id"
              :data-state="item.state"
            >
              <i></i>
              <span>{{ item.label }}</span>
              <small v-if="item.sequence">#{{ item.sequence }}</small>
            </li>
          </ol>
        </aside>
      </main>
      <div v-if="workspace.chatError.value" class="error" role="alert">
        {{ workspace.chatError.value.message }}
        <button
          v-if="workspace.chatError.value.retryable"
          :disabled="workspace.chatPending.value"
          @click="workspace.retryFailedChatMessage"
        >
          Retry saved message
        </button>
      </div>
      <form data-testid="workspace-chat-command" @submit.prevent="workspace.sendChatMessage()">
        <div data-testid="answer-mode-selector" class="modes" role="radiogroup" aria-label="Answer mode">
          <button
            v-for="mode in modes"
            :key="mode.value"
            type="button"
            :aria-pressed="workspace.chatAnswerMode.value === mode.value"
            :class="{ active: workspace.chatAnswerMode.value === mode.value }"
            @click="workspace.selectChatAnswerMode(mode.value)"
          >
            {{ mode.label }}
          </button>
        </div>
        <label
          class="multi-agent-option"
          :class="{ 'multi-agent-option--active': workspace.chatMultiAgentEnabled.value }"
        >
          <input
            data-testid="multi-agent-toggle"
            type="checkbox"
            :checked="workspace.chatMultiAgentEnabled.value"
            :disabled="
              workspace.chatPending.value ||
              !workspace.chatMultiAgentAvailable.value
            "
            @change="
              workspace.setChatMultiAgentEnabled(
                ($event.target as HTMLInputElement).checked,
              )
            "
          />
          <span class="multi-agent-switch" aria-hidden="true"><i></i></span>
          <span>
            <strong>Multi-Agent thinking</strong>
            <small>{{
              workspace.chatMultiAgentAvailable.value
                ? "Optional for this chat · parallel source retrieval and evidence review"
                : "Available in Analysis mode"
            }}</small>
          </span>
        </label>
        <div class="composer">
          <textarea
            v-model="workspace.chatQuestion.value"
            :disabled="workspace.chatPending.value"
            placeholder="Ask Mneme…"
          /><button
            v-if="workspace.chatPending.value"
            type="button"
            class="stop-run"
            aria-label="Stop generating"
            @click="workspace.cancelActiveChatRun"
          >
            <Square />
          </button>
          <button v-else aria-label="Send message">
            <Send />
          </button>
        </div>
        <small v-if="workspace.chatRunProgress.value" class="run-progress" role="status">
          {{ workspace.chatRunProgress.value }}
        </small>
        <small data-testid="answer-mode-description">{{ modeDescription }}</small>
      </form>
    </section>
  </div>
</template>
<style scoped>
.ai-layout {
  display: grid;
  height: 100%;
  grid-template-columns: 260px minmax(0, 1fr);
  background: var(--bg-canvas);
}
.ai-layout--collapsed {
  grid-template-columns: 0 minmax(0, 1fr);
}
.ai-history-panel[aria-hidden="true"] {
  visibility: hidden;
  overflow: hidden;
  padding: 0;
  pointer-events: none;
}
.chat {
  position: relative;
}
.rail-toggle {
  position: absolute;
  top: 50%;
  left: -1rem;
  z-index: 20;
  display: grid;
  width: 2rem;
  height: 2.5rem;
  place-items: center;
}
.rail-toggle svg {
  width: 1rem;
  transition: transform 140ms ease;
}
.rail-toggle svg.rotate {
  transform: rotate(180deg);
}
.history-search {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  padding: 0.45rem;
  background: var(--bg-canvas);
  border: 1px solid var(--border-muted);
  border-radius: 0.4rem;
}
.history-search svg {
  width: 1rem;
}
.history-search input {
  min-width: 0;
  flex: 1;
  background: transparent;
  border: 0;
  outline: 0;
}
aside {
  padding: 1rem;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-muted);
}
aside header,
.chat > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
aside h2,
h1 {
  margin: 0;
}
aside nav {
  display: grid;
  gap: 0.25rem;
  margin-top: 1rem;
}
aside nav button {
  display: grid;
  padding: 0.65rem;
  text-align: left;
  color: var(--text-secondary);
  background: transparent;
  border: 0;
  border-radius: 0.4rem;
}
aside nav button.active {
  background: var(--accent-soft);
}
small {
  color: var(--text-tertiary);
}
.chat {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.chat > header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-muted);
}
.chat > header svg {
  width: 1rem;
}
.danger {
  color: var(--danger);
}
main {
  flex: 1;
  overflow: auto;
  padding: 1rem max(1rem, calc((100% - 820px) / 2));
}
article {
  display: grid;
  grid-template-columns: 2rem 1fr;
  gap: 0.75rem;
  padding: 1rem 0;
}
article.assistant {
  border-bottom: 1px solid var(--border-muted);
}
.avatar {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 0.4rem;
}
.avatar svg {
  width: 1rem;
}
article p {
  margin: 0.4rem 0;
  line-height: 1.65;
}
.mode {
  margin-left: 0.4rem;
  padding: 0.15rem 0.35rem;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 1rem;
  font-size: 0.62rem;
}
.meta,
.sources {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  color: var(--text-tertiary);
  font: 0.62rem var(--font-mono);
}
button {
  padding: 0.35rem 0.55rem;
  color: var(--text-secondary);
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.35rem;
}
.error {
  padding: 0.55rem 1rem;
  color: var(--danger);
}
form {
  padding: 0.75rem max(1rem, calc((100% - 820px) / 2));
  border-top: 1px solid var(--border-muted);
}
.modes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.5rem;
}
.modes button.active {
  color: var(--accent);
  background: var(--accent-soft);
}
.multi-agent-option {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.55rem;
  padding: 0.5rem 0.65rem;
  color: var(--text-secondary);
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.4rem;
  cursor: pointer;
}
.multi-agent-option--active {
  border-color: color-mix(in srgb, var(--accent) 55%, var(--border-muted));
  background: var(--accent-soft);
}
.multi-agent-option:has(input:disabled) {
  opacity: 0.62;
  cursor: not-allowed;
}
.multi-agent-option input {
  position: absolute;
  z-index: 1;
  width: 2rem;
  height: 1.1rem;
  margin: 0;
  opacity: 0;
  cursor: inherit;
}
.multi-agent-option > span:last-child {
  display: grid;
  min-width: 0;
  gap: 0.1rem;
}
.multi-agent-option strong {
  font-size: 0.72rem;
}
.multi-agent-option small {
  line-height: 1.3;
}
.multi-agent-switch {
  position: relative;
  width: 2rem;
  height: 1.1rem;
  flex: 0 0 auto;
  background: var(--bg-active);
  border: 1px solid var(--border-strong);
  border-radius: 1rem;
  pointer-events: none;
}
.multi-agent-switch i {
  position: absolute;
  top: 0.14rem;
  left: 0.16rem;
  width: 0.7rem;
  height: 0.7rem;
  background: var(--text-tertiary);
  border-radius: 50%;
  transition: transform 140ms ease, background 140ms ease;
}
.multi-agent-option input:checked + .multi-agent-switch i {
  background: var(--accent);
  transform: translateX(0.82rem);
}
.multi-agent-option input:focus-visible + .multi-agent-switch {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.composer {
  display: flex;
  gap: 0.5rem;
}
.composer textarea {
  min-height: 3rem;
  flex: 1;
  padding: 0.55rem;
  color: var(--text-primary);
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.4rem;
}
.composer button {
  color: var(--accent-contrast);
  background: var(--accent);
}
.composer button.stop-run {
  color: var(--text-primary);
  background: var(--bg-panel);
  border-color: var(--border-strong);
}
.composer button.stop-run:hover {
  background: var(--bg-active);
}
.composer button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.run-progress {
  display: block;
  min-height: 1.25rem;
  margin-top: 0.35rem;
  color: var(--text-secondary);
}
.run-trace {
  margin: 0.75rem 0 1.25rem 2.75rem;
  padding: 0.75rem 0.9rem;
  background: var(--bg-sidebar);
  border: 1px solid var(--border-muted);
  border-radius: 0.45rem;
}
.run-trace header,
.run-trace header > div {
  display: flex;
  align-items: center;
}
.run-trace header {
  justify-content: space-between;
  gap: 0.75rem;
}
.run-trace header > div {
  gap: 0.4rem;
}
.run-trace header svg {
  width: 0.9rem;
  color: var(--accent);
}
.run-trace header strong {
  font-size: 0.72rem;
}
.run-trace header > span {
  padding: 0.15rem 0.4rem;
  color: var(--text-tertiary);
  border: 1px solid var(--border-muted);
  border-radius: 1rem;
  font: 0.6rem var(--font-mono);
  text-transform: uppercase;
}
.run-trace header > span[data-state="streaming"],
.run-trace header > span[data-state="completed"] {
  color: var(--success);
  border-color: color-mix(in srgb, var(--success) 45%, var(--border-muted));
}
.run-trace header > span[data-state="reconnecting"],
.run-trace header > span[data-state="failed"] {
  color: var(--danger);
}
.run-trace ol {
  display: grid;
  margin: 0.65rem 0 0;
  padding: 0;
  list-style: none;
}
.run-trace li {
  display: grid;
  min-height: 1.65rem;
  grid-template-columns: 0.75rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.35rem;
  color: var(--text-secondary);
  font-size: 0.7rem;
}
.run-trace li i {
  width: 0.38rem;
  height: 0.38rem;
  background: var(--success);
  border-radius: 50%;
}
.run-trace li[data-state="active"] i {
  background: var(--accent);
  box-shadow: 0 0 0 0.2rem var(--accent-soft);
}
.run-trace li[data-state="warning"] i {
  background: var(--danger);
}
.run-trace li small {
  font: 0.58rem var(--font-mono);
}
.composer svg {
  width: 1rem;
}
@media (max-width: 1023px) {
  .ai-layout,
  .ai-layout--collapsed {
    grid-template-columns: 1fr;
  }
  .ai-history-panel {
    position: absolute;
    inset: 0 auto 0 0;
    z-index: 10;
    width: min(84vw, 320px);
  }
  .ai-history-panel[aria-hidden="true"] {
    display: none;
  }
  .rail-toggle {
    left: 0.4rem;
  }
}
@media (max-width: 560px) {
  .run-trace {
    margin-left: 0;
  }
}
</style>
