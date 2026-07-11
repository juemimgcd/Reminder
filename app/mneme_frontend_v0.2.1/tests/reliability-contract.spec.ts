import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const source = (path: string) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');

test('workspace reliability primitives exist', () => {
  expect(source('composables/loadState.ts')).toContain('export type LoadPhase');
  expect(source('composables/loadState.ts')).toContain('createLoadState');
  expect(source('lib/safeStorage.ts')).toContain('safeStorageSet');
  expect(source('lib/safeStorage.ts')).toContain('catch');
});
