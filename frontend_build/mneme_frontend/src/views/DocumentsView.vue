<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue';
import SectionHeader from '@/components/common/SectionHeader.vue';
import SurfacePanel from '@/components/common/SurfacePanel.vue';
import DocumentsTable from '@/components/documents/DocumentsTable.vue';
import UploadZone from '@/components/documents/UploadZone.vue';
import { useSessionStore } from '@/stores/session';
import { useWorkspaceStore } from '@/stores/workspace';

const session = useSessionStore();
const workspace = useWorkspaceStore();

async function upload(files: File[]) {
  if (!session.token) {
    return;
  }
  await workspace.uploadDocuments(session.token, files);
}

async function indexDocument(documentId: string) {
  if (!session.token) {
    return;
  }
  await workspace.indexDocument(session.token, documentId);
}
</script>

<template>
  <div class="view-stack">
    <SectionHeader
      eyebrow="Documents"
      title="上传、排队、索引，明确看到每份材料的状态"
      description="文档页用最少的信息噪音，展示最关键的处理进度和可操作动作。"
    />

    <UploadZone @upload="upload" />

    <SurfacePanel eyebrow="Queue" title="文档索引队列">
      <DocumentsTable
        v-if="workspace.filteredDocuments.length"
        :items="workspace.filteredDocuments"
        @index="indexDocument"
      />
      <EmptyState
        v-else
        title="当前知识库还没有文档"
        description="先上传文档，再触发索引，之后它们就能参与问答与分析。"
      />
    </SurfacePanel>
  </div>
</template>
