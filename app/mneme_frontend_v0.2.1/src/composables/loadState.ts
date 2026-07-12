import { ref } from 'vue';

export type LoadPhase = 'idle' | 'loading' | 'ready' | 'empty' | 'error';
export type LoadState = ReturnType<typeof createLoadState>;

export function createLoadState() {
  return {
    phase: ref<LoadPhase>('idle'),
    message: ref(''),
  };
}
