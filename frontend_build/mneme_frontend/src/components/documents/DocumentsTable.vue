<script setup lang="ts">
import type { DocumentItem } from '@/lib/types';

defineProps<{
  items: DocumentItem[];
}>();

const emit = defineEmits<{
  (event: 'index', documentId: string): void;
}>();
</script>

<template>
  <div class="table-shell">
    <table class="data-table">
      <thead>
        <tr>
          <th>文档</th>
          <th>状态</th>
          <th>页数 / Chunk</th>
          <th>上传时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>
            <strong>{{ item.name }}</strong>
            <span>{{ item.size_label }}</span>
          </td>
          <td><span class="status-pill" :data-status="item.status">{{ item.status }}</span></td>
          <td>{{ item.page_count }} / {{ item.chunk_count || '待生成' }}</td>
          <td>{{ new Date(item.created_at).toLocaleString('zh-CN') }}</td>
          <td>
            <button
              v-if="!['queued', 'indexing', 'parsing', 'chunking', 'embedding', 'vector_upserting', 'indexed'].includes(item.status)"
              class="ghost-button"
              type="button"
              @click="emit('index', item.id)"
            >
              触发索引
            </button>
            <span
              v-else-if="item.status !== 'indexed'"
              class="inline-badge"
            >
              {{ item.status }}
            </span>
            <span v-else class="inline-badge">已可检索</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
