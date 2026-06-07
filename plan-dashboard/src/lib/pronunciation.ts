/**
 * pronunciation.ts — server-side reader for the /pronunciation utility.
 *
 * Discovers Islamic books that have a probe (`_system/probe/probe-terms.json`),
 * reads their ranked terms, and overlays the LIVE cross-book pronunciation
 * library (`content/knowledge-base/pronunciations.jsonl`) so a term already
 * confirmed in a PRIOR book shows as known. Writes go through the Python applier
 * (see api/pronunciation.ts) — this module is read-only.
 *
 * Mirrors: scripts/podcast/probe/score_pronunciation_risk.py (term shape) and
 * scripts/podcast/knowledge/pronunciation_ledger.py (normalizeKey, entry shape).
 */
import { join } from 'node:path';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { getRepoRoot, listContent, findContent, slugToTitle } from './content-paths';

export const PROBE_REL = '_system/probe/probe-terms.json';
export const PROBE_AUDIO_REL =
  '_system/probe/EP00-pronunciation-probe/audio/EP00-pronunciation-probe.m4a';

export interface ProbeTerm {
  n: number;
  term: string;
  transliteration: string;
  phonetic: string;            // intended (from _phonetics.md; may be IPA/invalid)
  house_style_ok: boolean;
  suggested_baseline: string;  // deterministic pattern baseline (pre-fill)
  signature: string[];
  segment: string;
  snippet: string;
  freq: number;
  score: number;
  reasons: string[];
  // ── live library overlay (added here) ──
  libraryStatus: 'confirmed' | 'unfixable' | null;
  libraryPhonetic: string;
  libraryGloss: string;
}

export interface ProbeBookSummary {
  slug: string;
  title: string;
  bucket: string;
  termCount: number;
  needsRespell: number;        // count of non-house-style intended phonetics
  alreadyKnown: number;        // count already confirmed/unfixable in the library
  hasAudio: boolean;
}

export interface LibraryEntry {
  key: string;
  term: string;
  phonetic: string;
  status: 'confirmed' | 'unfixable';
  transliteration: string;
  gloss: string;
  source_books: string[];
  confirmed_date: string;
}

/** Diacritic- and case-insensitive key — mirror of ledger.normalize_key. */
export function normalizeKey(s: string): string {
  return s
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .replace(/[ʿʾ'‘’`]/g, '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ');
}

export async function loadLibrary(): Promise<Map<string, LibraryEntry>> {
  const p = join(getRepoRoot(), 'content', 'knowledge-base', 'pronunciations.jsonl');
  const map = new Map<string, LibraryEntry>();
  if (!existsSync(p)) return map;
  const raw = await readFile(p, 'utf-8');
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    try {
      const e = JSON.parse(t) as LibraryEntry;
      const key = e.key || normalizeKey(e.term);
      map.set(key, e);
    } catch {
      /* skip malformed line */
    }
  }
  return map;
}

async function readProbeTerms(dir: string): Promise<any | null> {
  const p = join(dir, PROBE_REL);
  if (!existsSync(p)) return null;
  try {
    return JSON.parse(await readFile(p, 'utf-8'));
  } catch {
    return null;
  }
}

/** All Islamic books that have a generated probe. */
export async function listProbeBooks(): Promise<ProbeBookSummary[]> {
  const refs = await listContent({ bucket: 'Islamic' });
  const lib = await loadLibrary();
  const out: ProbeBookSummary[] = [];
  for (const ref of refs) {
    const data = await readProbeTerms(ref.dir);
    if (!data || !Array.isArray(data.terms)) continue;
    const terms = data.terms as ProbeTerm[];
    out.push({
      slug: ref.slug,
      title: slugToTitle(ref.slug),
      bucket: ref.bucket,
      termCount: terms.length,
      needsRespell: terms.filter((t) => !t.house_style_ok).length,
      alreadyKnown: terms.filter((t) => lib.has(normalizeKey(t.term))).length,
      hasAudio: existsSync(join(ref.dir, PROBE_AUDIO_REL)),
    });
  }
  return out.sort((a, b) => a.title.localeCompare(b.title));
}

export interface ProbeDetail {
  slug: string;
  title: string;
  terms: ProbeTerm[];
  audioUrl: string | null;
  generatedNote: string;
}

/** One book's probe terms with the live library overlaid. */
export async function getProbe(slug: string): Promise<ProbeDetail | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const data = await readProbeTerms(ref.dir);
  if (!data || !Array.isArray(data.terms)) return null;
  const lib = await loadLibrary();

  const terms: ProbeTerm[] = (data.terms as ProbeTerm[]).map((t) => {
    const hit = lib.get(normalizeKey(t.term));
    return {
      ...t,
      libraryStatus: hit ? hit.status : null,
      libraryPhonetic: hit?.phonetic ?? '',
      libraryGloss: hit?.gloss ?? '',
    };
  });

  const hasAudio = existsSync(join(ref.dir, PROBE_AUDIO_REL));
  const audioUrl = hasAudio
    ? `/api/library/file?slug=${encodeURIComponent(slug)}&path=${encodeURIComponent(PROBE_AUDIO_REL)}`
    : null;

  return {
    slug,
    title: slugToTitle(slug),
    terms,
    audioUrl,
    generatedNote: `${terms.length} terms · ${terms.filter((t) => !t.house_style_ok).length} need a respelling`,
  };
}
