/**
 * localServerClient.ts — Wave J (J2): shared probe + typed response helpers
 * for the source_library_server.py running at localhost:4390.
 *
 * Pattern:
 *   - Module-level availability flag, re-probed every 60 s.
 *   - All fetch calls use a 300 ms timeout so a stopped server never stalls the UI.
 *   - On timeout or network error: returns null (caller falls back to external service).
 */

const LOCAL_BASE = "http://localhost:4390";
const PROBE_INTERVAL_MS = 60_000;
const FETCH_TIMEOUT_MS = 300;

let _available = false;
let _lastProbe = 0;

async function _probe(): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
    const res = await fetch(`${LOCAL_BASE}/health`, { signal: ctrl.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

export async function isLocalAvailable(): Promise<boolean> {
  const now = Date.now();
  if (now - _lastProbe > PROBE_INTERVAL_MS) {
    _lastProbe = now;
    _available = await _probe();
  }
  return _available;
}

async function localFetch(path: string): Promise<any | null> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
    const res = await fetch(`${LOCAL_BASE}${path}`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// ── Typed response shapes ──────────────────────────────────────────────────

export interface LocalVerseData {
  surah: number;
  ayat: number;
  arabic: string;
  pickthall: string;
  asad: string;
  urdu: string;
  phonetic: string;
}

export interface LocalTermDef {
  found: boolean;
  term?: string;
  arabic?: string;
  definition?: string;
  etymology?: string;
  related?: string[];
  source?: string;
}

export interface LocalEtymology {
  found: boolean;
  term?: string;
  arabic?: string;
  root?: string;
  grammar_tag?: string;
  definition?: string;
  etymology?: string;
  related?: string[];
}

export interface LocalTopic {
  topic_id: number;
  binder_slug: string;
  chapter_slug: string;
  topic: string;
  content: string;
  linked_ayats?: Array<{
    surah: number;
    ayat: number;
    arabic: string;
    pickthall: string;
  }>;
}

// ── Query helpers ──────────────────────────────────────────────────────────

export async function fetchLocalVerse(
  surah: number,
  ayat: number,
): Promise<LocalVerseData | null> {
  return localFetch(`/quran/verse?surah=${surah}&ayat=${ayat}`);
}

export async function fetchLocalTermDef(
  term: string,
): Promise<LocalTermDef | null> {
  return localFetch(`/term/define?term=${encodeURIComponent(term)}`);
}

export async function fetchLocalEtymology(
  term: string,
): Promise<LocalEtymology | null> {
  return localFetch(`/etymology?term=${encodeURIComponent(term)}`);
}

export async function fetchLocalTopic(id: number): Promise<LocalTopic | null> {
  return localFetch(`/topic/get?id=${id}`);
}
