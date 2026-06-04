/**
 * Tiny localStorage cache for AI responses.
 *
 * Two namespaces:
 *   term-cache:<book>  → keyed by phonetic (lowercase). Definitions don't drift.
 *   section-summary    → keyed by SHA-1 of section text. Stable input → stable output.
 *
 * Both are versioned via a schema-version sentinel so we can evolve the
 * response shape later without breaking already-cached entries.
 */

const SCHEMA = 1;

async function sha1(s: string): Promise<string> {
  const buf = new TextEncoder().encode(s);
  const hash = await crypto.subtle.digest('SHA-1', buf);
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
}

interface CacheEntry<T> { schema: number; v: T; at: number; }

function read<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const e = JSON.parse(raw) as CacheEntry<T>;
    if (e.schema !== SCHEMA) return null;
    return e.v;
  } catch { return null; }
}

function write<T>(key: string, v: T): void {
  try { localStorage.setItem(key, JSON.stringify({ schema: SCHEMA, v, at: Date.now() } satisfies CacheEntry<T>)); }
  catch { /* quota or private mode */ }
}

export function getTermDef(book: string, phonetic: string): unknown | null {
  return read(`podcast-reader:term:${book}:${phonetic.toLowerCase()}`);
}
export function setTermDef(book: string, phonetic: string, value: unknown): void {
  write(`podcast-reader:term:${book}:${phonetic.toLowerCase()}`, value);
}

export async function getSectionSummary(text: string): Promise<unknown | null> {
  const h = await sha1(text);
  return read(`podcast-reader:section:${h}`);
}
export async function setSectionSummary(text: string, value: unknown): Promise<void> {
  const h = await sha1(text);
  write(`podcast-reader:section:${h}`, value);
}
