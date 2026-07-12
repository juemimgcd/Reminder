<script setup lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed } from "vue";
import type { DocumentContentData } from "../../types";
import { useI18n } from "../../composables/useI18n";

const props = defineProps<{
  content: DocumentContentData;
  blobUrl: string | null;
  blobPhase: "idle" | "loading" | "ready" | "error";
  blobError: string;
}>();
const emit = defineEmits<{ download: []; retry: [] }>();
const { t } = useI18n();

const pdfErrorText = computed(() => {
  if (/\b(401|403)\b/.test(props.blobError)) return t("reader.pdfAuthError");
  if (/\b404\b/.test(props.blobError)) return t("reader.pdfMissingError");
  if (/\b5\d\d\b/.test(props.blobError)) return t("reader.pdfServerError");
  if (/network|failed to fetch/i.test(props.blobError)) return t("reader.pdfNetworkError");
  return t("reader.pdfError");
});

const safeMarkdown = computed(() => {
  if (!(["markdown", "office"] as string[]).includes(props.content.render_mode)) return "";
  const parsed = marked.parse(props.content.text ?? "", { async: false }) as string;
  const sanitized = DOMPurify.sanitize(parsed, {
    ALLOWED_TAGS: ["a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "li", "ol", "p", "pre", "strong", "table", "tbody", "td", "th", "thead", "tr", "ul"],
    ALLOWED_ATTR: ["href", "title"],
    FORBID_TAGS: ["svg", "math", "image", "use", "script", "iframe", "object", "embed", "style", "img", "input", "video", "audio", "source"],
    FORBID_ATTR: ["src", "srcset", "poster", "xlink:href", "onerror", "onload", "onclick", "style", "srcdoc"],
    ALLOW_UNKNOWN_PROTOCOLS: false,
  });
  const template = document.createElement("template");
  template.innerHTML = sanitized;
  template.content.querySelectorAll("a").forEach((anchor) => {
    const href = anchor.getAttribute("href") ?? "";
    if (!/^(https?:|mailto:|#)/i.test(href)) anchor.removeAttribute("href");
    anchor.setAttribute("rel", "noopener noreferrer");
    if (/^https?:/i.test(href)) anchor.setAttribute("target", "_blank");
  });
  return template.innerHTML;
});
</script>

<template>
  <div class="document-content">
    <div v-if="content.parse_warning" class="reader-warning" role="status">
      <span>{{ content.parse_warning }}</span>
      <button type="button" @click="emit('download')">{{ t("reader.downloadOriginal") }}</button>
    </div>

    <article
      v-if="content.render_mode === 'markdown'"
      data-testid="document-markdown"
      class="prose"
      v-html="safeMarkdown"
    />
    <article
      v-else-if="content.render_mode === 'office'"
      data-testid="document-office"
      class="prose"
      v-html="safeMarkdown"
    />
    <pre v-else-if="content.render_mode === 'text'" data-testid="document-text" v-text="content.text" />
    <pre v-else-if="content.render_mode === 'structured'" data-testid="document-structured" v-text="content.text" />
    <iframe
      v-else-if="content.render_mode === 'pdf' && blobUrl"
      data-testid="document-pdf"
      :title="t('reader.pdfTitle')"
      :src="blobUrl"
    />
    <section v-else-if="content.render_mode === 'pdf' && blobPhase === 'error'" data-testid="document-pdf-error" class="reader-placeholder" role="alert">
      <p>{{ pdfErrorText }}</p>
      <div><button type="button" @click="emit('retry')">{{ t("reader.retryPdf") }}</button><button type="button" @click="emit('download')">{{ t("reader.downloadOriginal") }}</button></div>
    </section>
    <section v-else-if="content.render_mode === 'pdf'" class="reader-placeholder" aria-live="polite">
      {{ t("reader.pdfLoading") }}
    </section>
    <section v-else class="reader-placeholder">
      <p>{{ t("reader.unsupported") }}</p>
      <button type="button" @click="emit('download')">{{ t("reader.downloadOriginal") }}</button>
    </section>
  </div>
</template>

<style scoped>
.document-content { min-height: 100%; }
.prose { width: min(100%, 74ch); margin: 0 auto; padding: clamp(2rem, 5vw, 4.5rem) clamp(1.25rem, 6vw, 5.5rem) 6rem; color: var(--text-primary); font-size: 0.96rem; line-height: 1.8; }
.prose :deep(h1), .prose :deep(h2), .prose :deep(h3) { color: var(--text-primary); font-family: var(--font-serif); line-height: 1.2; letter-spacing: -0.012em; }
.prose :deep(h1) { margin: 0 0 1.8rem; font-size: clamp(2rem, 4vw, 3.25rem); font-weight: 600; }
.prose :deep(h2) { margin: 2.4rem 0 0.8rem; padding-bottom: 0.45rem; border-bottom: 1px solid var(--border-muted); font-size: 1.45rem; }
.prose :deep(p), .prose :deep(ul), .prose :deep(ol), .prose :deep(blockquote) { margin: 0 0 1.2rem; }
.prose :deep(blockquote) { padding-left: 1rem; color: var(--text-secondary); border-left: 2px solid var(--accent); }
.prose :deep(code) { padding: 0.12rem 0.3rem; background: var(--bg-elevated); border-radius: 0.25rem; font: 0.88em var(--font-mono); }
.prose :deep(pre) { overflow: auto; padding: 1rem; background: var(--bg-sidebar); border: 1px solid var(--border-muted); border-radius: 0.45rem; }
.prose :deep(a) { color: var(--accent); text-underline-offset: 0.2em; }
pre[data-testid] { min-height: 100%; margin: 0; padding: clamp(1.5rem, 5vw, 4rem); color: var(--text-primary); white-space: pre-wrap; overflow-wrap: anywhere; background: transparent; font: 0.88rem/1.75 var(--font-mono); }
iframe { display: block; width: 100%; height: 100%; min-height: 34rem; border: 0; background: var(--bg-panel); }
.reader-warning { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.65rem 1rem; color: var(--warning, var(--text-secondary)); background: color-mix(in srgb, var(--warning, #c99b55) 10%, var(--bg-panel)); border-bottom: 1px solid var(--border-muted); font-size: 0.76rem; }
.reader-warning button, .reader-placeholder button { color: var(--accent); background: transparent; border: 0; text-decoration: underline; text-underline-offset: 0.2em; }
.reader-placeholder { display: grid; min-height: 24rem; place-items: center; align-content: center; gap: 0.8rem; color: var(--text-secondary); }
button:focus-visible, a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (max-width: 767px) { .prose { padding: 1.5rem 1rem 5rem; } iframe { min-height: calc(100dvh - 12rem); } }
</style>
