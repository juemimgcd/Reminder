<script setup lang="ts">
import { Bot, MessageSquare, Send, Trash2 } from "@lucide/vue";
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
</script>
<template>
  <div data-testid="stitch-ai-laboratory-layout" class="ai-layout">
    <aside data-testid="ai-history-rail">
      <header>
        <h2>Chats</h2>
        <button @click="workspace.createChatSession">New chat</button>
      </header>
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
    <section class="chat">
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
        <button class="danger" @click="workspace.deleteActiveChatSession">
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
              ><span v-if="message.route" class="mode">{{
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
      <form @submit.prevent="workspace.sendChatMessage()">
        <div class="modes" role="radiogroup" aria-label="Answer mode">
          <button
            v-for="mode in modes"
            :key="mode.value"
            type="button"
            role="radio"
            :aria-checked="workspace.chatAnswerMode.value === mode.value"
            :class="{ active: workspace.chatAnswerMode.value === mode.value }"
            @click="workspace.selectChatAnswerMode(mode.value)"
          >
            {{ mode.label }}
          </button>
        </div>
        <div class="composer">
          <textarea
            v-model="workspace.chatQuestion.value"
            :disabled="workspace.chatPending.value"
            placeholder="Ask Mneme…"
          /><button aria-label="Send" :disabled="workspace.chatPending.value">
            <Send />
          </button>
        </div>
        <small
          >The selected mode is authoritative; Mneme will not infer another
          mode.</small
        >
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
.composer svg {
  width: 1rem;
}
@media (max-width: 760px) {
  .ai-layout {
    grid-template-columns: 1fr;
  }
  aside {
    display: none;
  }
}
</style>
