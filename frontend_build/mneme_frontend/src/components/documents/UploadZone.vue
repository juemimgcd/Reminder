<script setup lang="ts">
import { ref } from 'vue';
import AppIcon from '@/components/common/AppIcon.vue';

const emit = defineEmits<{
  (event: 'upload', files: File[]): void;
}>();

const files = ref<File[]>([]);
const acceptedTypes =
  '.pdf,.txt,.md,.docx,.pptx,.xlsx,.xls,.csv,.json,.xml,.html,.htm,.epub';

function handleFiles(event: Event) {
  const nextFiles = Array.from((event.target as HTMLInputElement).files ?? []);
  files.value = nextFiles;
}

function submit() {
  if (!files.value.length) {
    return;
  }
  emit('upload', files.value);
  files.value = [];
}
</script>

<template>
  <div class="upload-zone">
    <div class="upload-zone__icon">
      <AppIcon name="upload" />
    </div>
    <div>
      <h3>上传待索引材料</h3>
      <p>支持 PDF、Word、PowerPoint、Excel、CSV、HTML、JSON、XML、EPUB、Markdown、TXT。服务端会先统一转换为 Markdown，再进入索引。</p>
    </div>
    <input aria-label="上传文档" type="file" :accept="acceptedTypes" multiple @change="handleFiles" />
    <button class="primary-button" type="button" @click="submit">加入索引队列</button>
  </div>
</template>
