import type { ApiEnvelope } from '@/lib/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? '';

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function extractEnvelopeData<T>(payload: unknown): T | undefined {
  if (!isObject(payload)) {
    return undefined;
  }

  if ('data' in payload && payload.data !== undefined) {
    return payload.data as T;
  }

  const candidates = ['result', 'payload'];
  for (const key of candidates) {
    if (payload[key] !== undefined) {
      return payload[key] as T;
    }
  }

  return undefined;
}

function resolvePayload<T>(payload: T | ApiEnvelope<T>): T {
  const extracted = extractEnvelopeData<T>(payload);
  if (extracted !== undefined) {
    return extracted;
  }

  return payload as T;
}

function joinPath(prefix: string, path: string) {
  const normalizedPrefix = prefix.replace(/\/+$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedPrefix}${normalizedPath}`;
}

function buildCandidatePaths(path: string) {
  const prefixCandidates = [API_PREFIX, '', '/api/v1'];
  const seen = new Set<string>();
  const candidates: string[] = [];

  for (const prefix of prefixCandidates) {
    const joined = joinPath(prefix, path);
    if (!seen.has(joined)) {
      seen.add(joined);
      candidates.push(joined);
    }
  }

  return candidates;
}

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let lastError: Error | null = null;
  for (const candidatePath of buildCandidatePaths(path)) {
    const response = await fetch(`${API_BASE_URL}${candidatePath}`, {
      ...init,
      headers,
    });

    if (response.status === 404) {
      lastError = new Error(`Not found for path ${candidatePath}`);
      continue;
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed: ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const payload = (await response.json()) as T | ApiEnvelope<T>;
    return resolvePayload(payload);
  }

  throw lastError ?? new Error(`Unable to resolve request path for ${path}`);
}

export function shouldUseMocks() {
  return (import.meta.env.VITE_USE_MOCKS ?? 'true') === 'true';
}
