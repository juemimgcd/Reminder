<script setup lang="ts">
import {
  Check,
  CircleAlert,
  Copy,
  Link2,
  MessageSquareMore,
  Radio,
  RefreshCw,
  RotateCcw,
  ServerCog,
} from "@lucide/vue";
import { reactive, watch } from "vue";
import type { MnemeWorkspace } from "../../composables/useMnemeWorkspace";
import type { AnswerMode, ChannelConversationData } from "../../types";
import UiButton from "../ui/UiButton.vue";
import UiEmptyState from "../ui/UiEmptyState.vue";

const props = defineProps<{
  workspace: MnemeWorkspace;
  formatDate: (value: string | number | Date) => string;
}>();

const drafts = reactive<Record<string, {
  chat_session_id: string;
  knowledge_base_id: string;
  answer_mode: AnswerMode;
}>>({});
const copied = reactive({ value: "" });
const modes: Array<{ value: AnswerMode; label: string }> = [
  { value: "kb_qa", label: "Knowledge base" },
  { value: "memory_query", label: "Memory" },
  { value: "profile_query", label: "Profile" },
  { value: "analysis_query", label: "Analysis" },
  { value: "general_chat", label: "General" },
];

function syncDrafts(items: ChannelConversationData[]) {
  items.forEach((item) => {
    drafts[item.id] = {
      chat_session_id: item.chat_session_id,
      knowledge_base_id: item.knowledge_base_id ?? "",
      answer_mode: item.answer_mode,
    };
  });
}

watch(props.workspace.channelConversations, syncDrafts, { immediate: true });

async function copyText(value: string, key: string) {
  await navigator.clipboard.writeText(value);
  copied.value = key;
  window.setTimeout(() => {
    if (copied.value === key) copied.value = "";
  }, 1600);
}

function saveConversation(conversationId: string) {
  const draft = drafts[conversationId];
  if (!draft) return;
  void props.workspace.updateChannelConversation(conversationId, {
    chat_session_id: draft.chat_session_id || null,
    knowledge_base_id: draft.knowledge_base_id || null,
    answer_mode: draft.answer_mode,
  });
}

function isRetryable(status: string) {
  return ["failed", "dead_letter"].includes(status);
}
</script>

<template>
  <article id="channels" class="channel-panel" data-testid="channel-gateway-panel">
    <header>
      <div>
        <small>External channels</small>
        <h2>Feishu gateway</h2>
        <p>Route Feishu conversations into Mneme's RAG pipeline and inspect outbound delivery.</p>
      </div>
      <div class="gateway-actions">
        <span
          v-if="workspace.channelConfiguration.value"
          class="readiness"
          :data-ready="workspace.channelConfiguration.value.ready"
        >
          <i></i>
          {{ workspace.channelConfiguration.value.ready ? "Ready" : "Needs configuration" }}
        </span>
        <UiButton
          variant="ghost"
          size="sm"
          :loading="workspace.channelPending.value"
          aria-label="Refresh channel state"
          @click="workspace.refreshChannelGateway"
        ><template #icon><RefreshCw /></template>Refresh</UiButton>
      </div>
    </header>

    <div v-if="!workspace.channelConfiguration.value" class="channel-loading" role="status">
      <span></span><span></span><span></span>
    </div>

    <template v-else>
      <section class="gateway-strip">
        <div class="gateway-node"><Radio /><span>Feishu event</span></div>
        <i></i>
        <div class="gateway-node"><Link2 /><span>Identity + route</span></div>
        <i></i>
        <div class="gateway-node"><ServerCog /><span>RAG run</span></div>
        <i></i>
        <div class="gateway-node"><MessageSquareMore /><span>Delivery</span></div>
      </section>

      <section class="deployment-config">
        <div class="section-heading">
          <div><small>Deployment boundary</small><h3>Gateway configuration</h3></div>
          <code>{{ workspace.channelConfiguration.value.account_id }}</code>
        </div>
        <div class="config-grid">
          <div><span>Gateway enabled</span><strong :data-ok="workspace.channelConfiguration.value.enabled">{{ workspace.channelConfiguration.value.enabled ? "Enabled" : "Disabled" }}</strong></div>
          <div><span>App ID</span><strong :data-ok="workspace.channelConfiguration.value.app_id_configured">{{ workspace.channelConfiguration.value.app_id_configured ? "Configured" : "Missing" }}</strong></div>
          <div><span>App secret</span><strong :data-ok="workspace.channelConfiguration.value.app_secret_configured">{{ workspace.channelConfiguration.value.app_secret_configured ? "Configured" : "Missing" }}</strong></div>
          <div><span>Verification token</span><strong :data-ok="workspace.channelConfiguration.value.verification_token_configured">{{ workspace.channelConfiguration.value.verification_token_configured ? "Configured" : "Missing" }}</strong></div>
        </div>
        <div class="callback-row">
          <span>Callback path</span>
          <code>{{ workspace.channelConfiguration.value.callback_path }}</code>
          <button aria-label="Copy callback path" @click="copyText(workspace.channelConfiguration.value.callback_path, 'callback')">
            <Check v-if="copied.value === 'callback'" /><Copy v-else />
          </button>
        </div>
        <p class="security-note"><CircleAlert />Credentials stay deployment-managed through <code>FEISHU_APP_ID</code>, <code>FEISHU_APP_SECRET</code>, and <code>FEISHU_VERIFICATION_TOKEN</code>; secret values are never sent to this page.</p>
      </section>

      <div class="channel-columns">
        <section class="binding-section">
          <div class="section-heading">
            <div><small>User identity</small><h3>Account binding</h3></div>
            <UiButton
              variant="primary"
              size="sm"
              :loading="workspace.channelPending.value"
              @click="workspace.createFeishuLinkCode"
            ><template #icon><Link2 /></template>Generate code</UiButton>
          </div>
          <div v-if="workspace.channelLinkCode.value" class="binding-command">
            <div><small>Send this command to the bot</small><code>{{ workspace.channelLinkCode.value.binding_command }}</code></div>
            <button aria-label="Copy binding command" @click="copyText(workspace.channelLinkCode.value.binding_command, 'binding')">
              <Check v-if="copied.value === 'binding'" /><Copy v-else />
            </button>
            <span>Expires {{ formatDate(workspace.channelLinkCode.value.expires_at) }}</span>
          </div>
          <ul v-if="workspace.channelIdentities.value.length" class="identity-list">
            <li v-for="identity in workspace.channelIdentities.value" :key="identity.id">
              <i></i>
              <div><strong>{{ identity.external_user_id }}</strong><small>{{ identity.account_id }} · verified {{ formatDate(identity.verified_at) }}</small></div>
              <span>{{ identity.status }}</span>
            </li>
          </ul>
          <UiEmptyState v-else title="No linked Feishu account" description="Generate a one-time code, then send the command to the Feishu bot.">
            <template #icon><Link2 /></template>
          </UiEmptyState>
        </section>

        <section class="routing-section">
          <div class="section-heading"><div><small>Conversation ownership</small><h3>RAG routing</h3></div><span>{{ workspace.channelConversations.value.length }} routes</span></div>
          <div v-if="workspace.channelConversations.value.length" class="route-list">
            <form v-for="conversation in workspace.channelConversations.value" :key="conversation.id" @submit.prevent="saveConversation(conversation.id)">
              <div class="route-id"><MessageSquareMore /><div><strong>{{ conversation.external_conversation_id }}</strong><small>{{ conversation.external_thread_id || "Main thread" }}</small></div></div>
              <label>Mode<select v-model="drafts[conversation.id].answer_mode"><option v-for="mode in modes" :key="mode.value" :value="mode.value">{{ mode.label }}</option></select></label>
              <label>Knowledge base<select v-model="drafts[conversation.id].knowledge_base_id"><option value="">None</option><option v-for="kb in workspace.knowledgeBases.value" :key="kb.id" :value="kb.id">{{ kb.name }}</option></select></label>
              <label>Chat session<select v-model="drafts[conversation.id].chat_session_id"><option value="">Automatic</option><option v-if="conversation.chat_session_id && !workspace.chatSessions.value.some((session) => session.id === conversation.chat_session_id)" :value="conversation.chat_session_id">Current mapping · {{ conversation.chat_session_id }}</option><option v-for="session in workspace.chatSessions.value" :key="session.id" :value="session.id">{{ session.title || "Untitled chat" }}</option></select></label>
              <UiButton size="sm" :disabled="workspace.channelPending.value" type="submit">Save route</UiButton>
            </form>
          </div>
          <UiEmptyState v-else title="No Feishu conversations yet" description="Routes appear after a linked user sends the bot its first message.">
            <template #icon><MessageSquareMore /></template>
          </UiEmptyState>
        </section>
      </div>

      <section class="delivery-section">
        <div class="section-heading"><div><small>Outbox</small><h3>Recent deliveries</h3></div><code>{{ workspace.channelConfiguration.value.delivery_queue }}</code></div>
        <div v-if="workspace.channelDeliveries.value.length" class="delivery-table">
          <div class="delivery-header"><span>Status</span><span>Run</span><span>Parts</span><span>Attempts</span><span>Last activity</span><span></span></div>
          <div v-for="delivery in workspace.channelDeliveries.value" :key="delivery.id" class="delivery-row">
            <strong :data-status="delivery.status">{{ delivery.status }}</strong>
            <code>{{ delivery.agent_run_id || "—" }}</code>
            <span>{{ delivery.parts_sent }}/{{ delivery.part_count }}</span>
            <span>{{ delivery.attempt_count }}</span>
            <span :title="delivery.last_error || ''">{{ delivery.last_error || (delivery.processed_at ? formatDate(delivery.processed_at) : "Pending") }}</span>
            <UiButton v-if="isRetryable(delivery.status)" variant="ghost" size="sm" :loading="workspace.channelPending.value" @click="workspace.retryChannelDelivery(delivery.id)"><template #icon><RotateCcw /></template>Retry</UiButton>
          </div>
        </div>
        <UiEmptyState v-else title="No deliveries recorded" description="Outbound answers will appear here after Feishu conversations begin.">
          <template #icon><Radio /></template>
        </UiEmptyState>
      </section>
    </template>

    <p v-if="workspace.channelActionStatus.value" class="channel-status" role="status">{{ workspace.channelActionStatus.value }}</p>
  </article>
</template>

<style scoped>
.channel-panel {
  min-width: 0;
  scroll-margin-top: 1rem;
  padding: 1.25rem;
  background: var(--bg-panel);
  border: 1px solid var(--border-muted);
  border-radius: 0.5rem;
}
.channel-panel > header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-muted);
}
.channel-panel > header { align-items: flex-start; }
.channel-panel > header p { max-width: 38rem; margin: 0.4rem 0 0; color: var(--text-secondary); font-size: 0.78rem; line-height: 1.55; }
.gateway-actions, .section-heading, .route-id, .callback-row, .security-note { display: flex; align-items: center; }
.gateway-actions { gap: 0.5rem; }
.gateway-actions svg, .section-heading svg { width: 0.9rem; }
.readiness { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.25rem 0.5rem; color: var(--danger); border: 1px solid color-mix(in srgb, var(--danger) 38%, var(--border-muted)); border-radius: 1rem; font: 0.64rem var(--font-mono); }
.readiness[data-ready="true"] { color: var(--success); border-color: color-mix(in srgb, var(--success) 40%, var(--border-muted)); }
.readiness i { width: 0.4rem; height: 0.4rem; background: currentColor; border-radius: 50%; }
.gateway-strip { display: grid; grid-template-columns: auto 1fr auto 1fr auto 1fr auto; align-items: center; gap: 0.6rem; margin: 1rem 0; padding: 0.65rem; background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.gateway-strip > i { height: 1px; background: var(--border-strong); }
.gateway-node { display: flex; align-items: center; gap: 0.35rem; color: var(--text-secondary); font-size: 0.68rem; white-space: nowrap; }
.gateway-node svg { width: 0.85rem; color: var(--accent); }
.deployment-config, .binding-section, .routing-section, .delivery-section { min-width: 0; padding: 0.9rem; background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.section-heading { justify-content: space-between; gap: 1rem; }
.section-heading h3 { margin: 0.2rem 0 0; font-size: 0.86rem; }
.section-heading > span, .section-heading > code { color: var(--text-tertiary); font: 0.65rem var(--font-mono); }
.config-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 0.8rem; border: 1px solid var(--border-muted); }
.config-grid > div { display: grid; gap: 0.3rem; padding: 0.7rem; border-right: 1px solid var(--border-muted); }
.config-grid > div:last-child { border-right: 0; }
.config-grid span { color: var(--text-tertiary); font-size: 0.64rem; }
.config-grid strong { color: var(--danger); font-size: 0.72rem; }
.config-grid strong[data-ok="true"] { color: var(--success); }
.callback-row { display: grid; grid-template-columns: 7rem minmax(0, 1fr) auto; gap: 0.5rem; margin-top: 0.7rem; padding: 0.5rem 0.65rem; background: var(--bg-sidebar); border-radius: 0.3rem; }
.callback-row span { color: var(--text-tertiary); font-size: 0.66rem; }
.callback-row code { overflow: hidden; color: var(--text-secondary); font-size: 0.68rem; text-overflow: ellipsis; }
.callback-row button, .binding-command button { display: grid; width: 1.8rem; height: 1.8rem; place-items: center; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.3rem; }
.callback-row button:hover, .binding-command button:hover { color: var(--accent); background: var(--accent-soft); }
.callback-row svg, .binding-command svg { width: 0.85rem; }
.security-note { gap: 0.4rem; margin: 0.65rem 0 0; color: var(--text-tertiary); font-size: 0.66rem; line-height: 1.5; }
.security-note svg { width: 0.85rem; flex: 0 0 auto; color: var(--accent); }
.channel-columns { display: grid; grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr); gap: 0.75rem; margin-top: 0.75rem; }
.binding-command { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0.35rem; margin-top: 0.75rem; padding: 0.65rem; background: var(--accent-soft); border-left: 2px solid var(--accent); }
.binding-command div { display: grid; gap: 0.25rem; }
.binding-command code { color: var(--text-primary); font-size: 0.78rem; }
.binding-command > span { grid-column: 1 / -1; color: var(--text-tertiary); font-size: 0.62rem; }
.identity-list, .route-list { display: grid; gap: 0.45rem; margin: 0.75rem 0 0; padding: 0; list-style: none; }
.identity-list li { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.5rem; padding: 0.55rem; border-top: 1px solid var(--border-muted); }
.identity-list li > i { width: 0.4rem; height: 0.4rem; background: var(--success); border-radius: 50%; }
.identity-list div { display: grid; min-width: 0; gap: 0.15rem; }
.identity-list strong { overflow: hidden; font: 0.68rem var(--font-mono); text-overflow: ellipsis; }
.identity-list span { color: var(--success); font-size: 0.62rem; }
.route-list form { display: grid; grid-template-columns: minmax(8rem, 1.3fr) repeat(3, minmax(6rem, 1fr)) auto; align-items: end; gap: 0.45rem; padding: 0.6rem 0; border-top: 1px solid var(--border-muted); }
.route-id { min-width: 0; gap: 0.45rem; align-self: center; }
.route-id svg { width: 0.9rem; flex: 0 0 auto; color: var(--accent); }
.route-id div { display: grid; min-width: 0; gap: 0.1rem; }
.route-id strong { overflow: hidden; font: 0.66rem var(--font-mono); text-overflow: ellipsis; }
.route-list label { display: grid; gap: 0.25rem; color: var(--text-tertiary); font-size: 0.6rem; }
.route-list select { min-width: 0; height: 2rem; padding: 0 0.4rem; color: var(--text-primary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.3rem; font-size: 0.68rem; }
.delivery-section { margin-top: 0.75rem; }
.delivery-table { margin-top: 0.75rem; overflow-x: auto; }
.delivery-header, .delivery-row { display: grid; min-width: 680px; grid-template-columns: 6rem minmax(9rem, 1.2fr) 4rem 4rem minmax(9rem, 1fr) 5rem; align-items: center; gap: 0.5rem; padding: 0.5rem; }
.delivery-header { color: var(--text-tertiary); border-bottom: 1px solid var(--border-muted); font-size: 0.62rem; }
.delivery-row { border-bottom: 1px solid var(--border-muted); color: var(--text-secondary); font-size: 0.68rem; }
.delivery-row strong { color: var(--text-secondary); text-transform: capitalize; }
.delivery-row strong[data-status="succeeded"] { color: var(--success); }
.delivery-row strong[data-status="dead_letter"], .delivery-row strong[data-status="failed"] { color: var(--danger); }
.delivery-row code, .delivery-row > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.channel-status { margin: 0.75rem 0 0; padding: 0.6rem; color: var(--text-secondary); background: var(--bg-sidebar); border-left: 2px solid var(--accent); font-size: 0.72rem; }
.channel-loading { display: grid; gap: 0.5rem; padding: 1rem 0; }
.channel-loading span { height: 3rem; background: var(--bg-canvas); border-radius: 0.35rem; animation: pulse 1.4s ease-in-out infinite; }
:deep(.ui-empty-state) { min-height: 9rem; padding: 1.2rem; }
button:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@keyframes pulse { 50% { opacity: 0.48; } }
@media (max-width: 1400px) {
  .channel-columns { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .gateway-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .gateway-strip > i { display: none; }
  .gateway-node { justify-content: center; white-space: normal; text-align: center; }
  .route-list form { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .route-id { grid-column: 1 / -1; }
}
@media (max-width: 560px) {
  .channel-panel > header, .gateway-actions { align-items: stretch; flex-direction: column; }
  .config-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .config-grid > div:nth-child(2) { border-right: 0; }
  .config-grid > div:nth-child(-n + 2) { border-bottom: 1px solid var(--border-muted); }
  .callback-row { grid-template-columns: minmax(0, 1fr) auto; }
  .callback-row span { grid-column: 1 / -1; }
  .gateway-node { flex-direction: column; }
  .route-list form { grid-template-columns: 1fr; }
  .route-id { grid-column: auto; }
}
</style>
