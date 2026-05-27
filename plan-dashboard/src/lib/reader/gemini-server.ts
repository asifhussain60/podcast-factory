/**
 * Server-only Gemini client.
 *
 * Reads `gemini_api_key` from macOS keychain on first call and caches the
 * key in process memory for subsequent calls. NEVER imported from a
 * browser bundle — only from /src/pages/api/* endpoints.
 *
 * Models:
 *  - gemini-2.0-flash       — popovers + summaries (fast, cheap)
 *  - gemini-2.0-pro-exp     — ask-this-chapter (long context, best reasoning)
 *
 * Both names fall through to gemini-1.5-flash / gemini-1.5-pro if the
 * 2.0 series isn't available on this account yet (the API auto-aliases
 * for the rolling-default models).
 */

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);

let cachedKey: string | null = null;
let keyPromise: Promise<string> | null = null;

export async function getGeminiKey(): Promise<string> {
  if (cachedKey) return cachedKey;
  if (process.env.GEMINI_API_KEY) {
    cachedKey = process.env.GEMINI_API_KEY;
    return cachedKey;
  }
  if (!keyPromise) {
    keyPromise = (async () => {
      const user = process.env.USER || process.env.USERNAME || '';
      try {
        const { stdout } = await exec('security', ['find-generic-password', '-s', 'gemini_api_key', '-a', user, '-w']);
        const key = stdout.trim();
        if (!key) throw new Error('empty key from keychain');
        cachedKey = key;
        return key;
      } catch (e) {
        keyPromise = null;
        throw new Error(`Could not read gemini_api_key from keychain: ${(e as Error).message}`);
      }
    })();
  }
  return keyPromise;
}

export type GeminiModel = 'flash' | 'pro';

function modelId(m: GeminiModel): string {
  return m === 'pro' ? 'gemini-2.5-pro' : 'gemini-2.5-flash';
}

export interface GeminiPart { text: string; }
export interface GeminiContent { role: 'user' | 'model'; parts: GeminiPart[]; }

interface GenerateOptions {
  model?: GeminiModel;
  systemInstruction?: string;
  contents: GeminiContent[];
  temperature?: number;
  maxOutputTokens?: number;
  /** When true, asks Gemini to emit application/json (no markdown fences). */
  jsonMode?: boolean;
}

/**
 * Non-streaming generateContent call. Returns the concatenated text.
 */
export async function generate(opts: GenerateOptions): Promise<string> {
  const key = await getGeminiKey();
  const model = modelId(opts.model ?? 'flash');
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;
  const body = {
    contents: opts.contents,
    ...(opts.systemInstruction ? { systemInstruction: { role: 'system', parts: [{ text: opts.systemInstruction }] } } : {}),
    generationConfig: {
      temperature: opts.temperature ?? 0.4,
      maxOutputTokens: opts.maxOutputTokens ?? 600,
      ...(opts.jsonMode ? { responseMimeType: 'application/json' } : {}),
    },
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini ${res.status}: ${errText.slice(0, 300)}`);
  }
  const data = await res.json() as any;
  const text = data?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || '').join('') ?? '';
  return text.trim();
}

/**
 * Streaming generateContent (SSE proxy). Yields incremental text chunks
 * so the client can render tokens as they arrive.
 */
export async function* generateStream(opts: GenerateOptions): AsyncGenerator<string> {
  const key = await getGeminiKey();
  const model = modelId(opts.model ?? 'flash');
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse&key=${encodeURIComponent(key)}`;
  const body = {
    contents: opts.contents,
    ...(opts.systemInstruction ? { systemInstruction: { role: 'system', parts: [{ text: opts.systemInstruction }] } } : {}),
    generationConfig: {
      temperature: opts.temperature ?? 0.4,
      maxOutputTokens: opts.maxOutputTokens ?? 1500,
    },
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const errText = await res.text().catch(() => '');
    throw new Error(`Gemini stream ${res.status}: ${errText.slice(0, 300)}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';
    for (const ev of events) {
      const dataLine = ev.split('\n').find((l) => l.startsWith('data:'));
      if (!dataLine) continue;
      const payload = dataLine.slice(5).trim();
      if (!payload || payload === '[DONE]') continue;
      try {
        const obj = JSON.parse(payload);
        const text = obj?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || '').join('') ?? '';
        if (text) yield text;
      } catch { /* skip malformed chunk */ }
    }
  }
}

// ---------------------------------------------------------------------------
// Grounded generation — Gemini 2.0 Flash + Google Search tool
// ---------------------------------------------------------------------------

export interface GroundedResult {
  text: string;
  /** Source URLs returned by the grounding metadata (may be empty). */
  sources: string[];
}

export async function generateWithGrounding(prompt: string): Promise<GroundedResult> {
  const key = await getGeminiKey();
  const model = modelId('flash');
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;
  const body = {
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    tools: [{ google_search: {} }],
    generationConfig: { temperature: 0.4, maxOutputTokens: 1200 },
  };
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`Gemini grounding ${res.status}: ${errText.slice(0, 300)}`);
  }
  const data = await res.json() as {
    candidates?: { content: { parts: { text?: string }[] }; groundingMetadata?: { groundingChunks?: { web?: { uri: string } }[] } }[];
  };
  const candidate = data.candidates?.[0];
  const text = candidate?.content.parts.map((p) => p.text ?? '').join('') ?? '';
  const sources = (candidate?.groundingMetadata?.groundingChunks ?? [])
    .map((c) => c.web?.uri)
    .filter(Boolean) as string[];
  return { text, sources };
}

// ---------------------------------------------------------------------------
// Soft rate-limit: cap requests per minute to prevent runaway costs.
// ---------------------------------------------------------------------------
const RATE_WINDOW_MS = 60_000;
const RATE_MAX = 60;
const rateHits: number[] = [];

export function rateLimitCheck(): { ok: boolean; retryMs?: number } {
  const now = Date.now();
  while (rateHits.length && now - rateHits[0] > RATE_WINDOW_MS) rateHits.shift();
  if (rateHits.length >= RATE_MAX) {
    return { ok: false, retryMs: RATE_WINDOW_MS - (now - rateHits[0]) };
  }
  rateHits.push(now);
  return { ok: true };
}
