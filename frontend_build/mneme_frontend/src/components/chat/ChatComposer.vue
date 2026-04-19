<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{
  (event: 'submit', payload: { question: string; topK: number }): void;
}>();

const question = ref('');
const topK = ref(4);

function submit() {
  if (!question.value.trim()) {
    return;
  }

  emit('submit', {
    question: question.value.trim(),
    topK: topK.value,
  });
  question.value = '';
}
</script>

<template>
  <form class="chat-composer" @submit.prevent="submit">
    <label>
      <span>提问内容</span>
      <textarea
        v-model="question"
        rows="4"
        placeholder="例如：总结我近一个月关于长期主义的核心观点，并给出证据来源。"
      />
    </label>

    <div class="chat-composer__footer">
      <label>
        <span>召回数量</span>
        <input v-model="topK" min="1" max="8" type="number" />
      </label>
      <button class="primary-button" type="submit">发起检索问答</button>
    </div>
  </form>
</template>
