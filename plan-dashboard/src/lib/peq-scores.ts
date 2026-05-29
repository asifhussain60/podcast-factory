/**
 * peq-scores.ts — TypeScript port of the PEQ (Podcast Episode Quality) scorer.
 *
 * Mirrors the logic in scripts/podcast/_quality.py and
 * scripts/podcast/intelligence/challenger_scoring.py.
 * Pure maths + regex — no API calls, no external dependencies.
 *
 * FORMULA: PEQ = 0.35×Fidelity + 0.25×Voice + 0.20×Structure + 0.20×Enrichment
 * PASS ≥ 85 · WARN 70–84 · FAIL < 70
 */
import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const THRESHOLD_PASS = 85;
export const THRESHOLD_WARN = 70;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PEQAxes {
  fidelity: number;   // 0–100
  voice: number;      // 0–100
  structure: number;  // 0–100
  enrichment: number; // 0–100
  total: number;      // 0–100
  verdict: 'PASS' | 'WARN' | 'FAIL';
}

export interface ChapterScore {
  slug: string;
  title: string;
  scores: PEQAxes;
}

export interface BookScore {
  slug: string;
  archetype: string | null;
  avg: number;
  passCount: number;
  warnCount: number;
  failCount: number;
  chapters: ChapterScore[];
}

// ---------------------------------------------------------------------------
// Axis helpers — mirrors Python implementations
// ---------------------------------------------------------------------------

function quranRefs(text: string): number {
  return (text.match(/\bQ?\d+:\d+\b/g) ?? []).length;
}

function domainTerms(text: string): { total: number; glossed: number } {
  const italics = new Set((text.match(/\*([^*]+)\*/g) ?? []).map((s) => s.slice(1, -1)));

  const STOP = new Set(['that','this','with','from','into','also','such','when',
    'then','than','what','which','some','have','been','were','they','their',
    'there','here','each','both']);
  const bareGlosses = new Set<string>();
  for (const m of text.matchAll(/\b([A-Za-z\u0101\u012b\u016b\u1e0d\u1e6d\u1e93\u1e25\u1e63\u02bf\u02be]{4,})\s*\([^)]{5,80}\)/g)) {
    if (!STOP.has(m[1].toLowerCase())) bareGlosses.add(m[1]);
  }

  const total = italics.size + [...bareGlosses].filter((t) => !italics.has(t)).length;
  const glossedItalic = (text.match(/\*[^*]+\*\s*\([^)]+\)/g) ?? []).length;
  const glossed = glossedItalic + bareGlosses.size;
  return { total, glossed: Math.min(glossed, total) };
}

function arcLabels(text: string): string[] {
  const labels: string[] = [];

  if (/let us begin|opening|before we dive|where this chapter picks up|this chapter covers|the argument of this chapter|picks up|chapter picks up|where we left|where the chapter|##\s*(where|opening|introduction|context|background)|established the doctrine|settled the architecture/i.test(text)) {
    labels.push('open_hook');
  }
  if (/\bfirst\b|\bsecond\b|\bthird\b|point one|point two|##\s*movement\s+\d|##\s*section\s+\d|##\s*part\s+\d|\bmovement \d|\bphase \d|\bstep \d|\bone[,:]|\btwo[,:]|\bthree[,:]|the first|the second|the third/i.test(text)) {
    labels.push('three_points');
  }
  if (/in closing|to close|so as we end|let that sit|what comes next|where this chapter ends|this is where.*ends|the next (chapter|sub-chapter|section)|we ask god|ask god to|may god|all[aā]h|inshallah|##\s*(what comes next|closing|conclusion|summary|end)|leaves the reader|has earned/i.test(text)) {
    labels.push('close');
  }
  return labels;
}

function fidelityScore(sourceIds: string[], foundIds: string[]): number {
  if (sourceIds.length === 0 && foundIds.length === 0) return 100;
  const s = new Set(sourceIds);
  const f = new Set(foundIds);
  const intersection = [...s].filter((x) => f.has(x)).length;
  const union = new Set([...s, ...f]).size;
  return union === 0 ? 100 : Math.round((intersection / union) * 10000) / 100;
}

function voiceScore(text: string, exemplarVector: number[] | null): number {
  if (!exemplarVector || exemplarVector.length === 0) return 0;
  const tokens = text.toLowerCase().split(/\s+/);
  const bigrams: Record<string, number> = {};
  for (let i = 0; i < tokens.length - 1; i++) {
    const bg = `${tokens[i]}_${tokens[i + 1]}`;
    bigrams[bg] = (bigrams[bg] ?? 0) + 1;
  }
  const ratio = Math.min(Object.keys(bigrams).length / Math.max(exemplarVector.length, 1), 1.0);
  return Math.round(ratio * 10000) / 100;
}

function structureScore(arcRules: string[], found: string[]): number {
  if (arcRules.length === 0) return 100;
  const foundSet = new Set(found);
  const hits = arcRules.filter((r) => foundSet.has(r)).length;
  return Math.round((hits / arcRules.length) * 10000) / 100;
}

function enrichmentScore(termCount: number, glossedCount: number, qrefs: number, wordCount: number): number {
  if (wordCount === 0) return 0;
  const glossingRatio = glossedCount / Math.max(termCount, 1);
  const quranDensity = Math.min(qrefs / Math.max(wordCount / 100, 1), 1.0);
  return Math.round((0.70 * glossingRatio + 0.30 * quranDensity) * 10000) / 100;
}

function peqTotal(fidelity: number, voice: number, structure: number, enrichment: number, hasVector: boolean): number {
  if (!hasVector) {
    // Redistribute Voice weight (0.25) to Fidelity when no exemplar
    return Math.round((0.60 * fidelity + 0.20 * structure + 0.20 * enrichment) * 100) / 100;
  }
  return Math.round((0.35 * fidelity + 0.25 * voice + 0.20 * structure + 0.20 * enrichment) * 100) / 100;
}

function verdict(total: number): 'PASS' | 'WARN' | 'FAIL' {
  return total >= THRESHOLD_PASS ? 'PASS' : total >= THRESHOLD_WARN ? 'WARN' : 'FAIL';
}

// ---------------------------------------------------------------------------
// Exemplar vector loader
// ---------------------------------------------------------------------------

const _vectorCache = new Map<string, number[] | null>();

async function loadExemplarVector(archetypeSlug: string | null): Promise<number[] | null> {
  if (!archetypeSlug) return null;
  if (_vectorCache.has(archetypeSlug)) return _vectorCache.get(archetypeSlug)!;

  // Try both CONTENT/ and content/ case variants (Mac filesystem quirk)
  const candidates = [
    join(process.cwd(), '..', 'CONTENT', '_shared', 'archetypes', archetypeSlug, 'exemplar_vector.json'),
    join(process.cwd(), '..', 'content', '_shared', 'archetypes', archetypeSlug, 'exemplar_vector.json'),
    join(process.cwd(), 'CONTENT', '_shared', 'archetypes', archetypeSlug, 'exemplar_vector.json'),
    join(process.cwd(), 'content', '_shared', 'archetypes', archetypeSlug, 'exemplar_vector.json'),
  ];
  for (const p of candidates) {
    try {
      const vec = JSON.parse(await readFile(p, 'utf-8')) as number[];
      _vectorCache.set(archetypeSlug, vec);
      return vec;
    } catch { /* try next */ }
  }
  _vectorCache.set(archetypeSlug, null);
  return null;
}

// ---------------------------------------------------------------------------
// Per-chapter scorer
// ---------------------------------------------------------------------------

export async function scoreChapter(
  chapterText: string,
  archetypeSlug: string | null,
): Promise<PEQAxes> {
  const exemplar = await loadExemplarVector(archetypeSlug);

  const words = chapterText.split(/\s+/).filter(Boolean).length;
  const qrefs = quranRefs(chapterText);
  const { total: termCount, glossed: glossedCount } = domainTerms(chapterText);
  const arc = arcLabels(chapterText);
  const citationsFound = chapterText.match(/(?:quran|hadith|doctrine):\S+/g) ?? [];

  const fid = fidelityScore([], citationsFound);
  const voi = voiceScore(chapterText, exemplar);
  const str = structureScore(['open_hook', 'three_points', 'close'], arc);
  const enr = enrichmentScore(termCount, glossedCount, qrefs, words);
  const tot = peqTotal(fid, voi, str, enr, exemplar !== null);

  return { fidelity: fid, voice: voi, structure: str, enrichment: enr, total: tot, verdict: verdict(tot) };
}

// ---------------------------------------------------------------------------
// Whole-book scorer
// ---------------------------------------------------------------------------

const ARC_RULES = ['open_hook', 'three_points', 'close'];

export async function scoreBook(
  bookDir: string,
  archetypeSlug: string | null,
): Promise<BookScore | null> {
  const chaptersDir = join(bookDir, 'chapters');
  let entries: string[];
  try { entries = await readdir(chaptersDir); } catch { return null; }

  const txtFiles = entries
    .filter((n) => (n.endsWith('.txt') || n.endsWith('.md')) && !n.startsWith('_') && !n.startsWith('.'))
    .sort();

  if (txtFiles.length === 0) return null;

  const exemplar = await loadExemplarVector(archetypeSlug);
  const chapters: ChapterScore[] = [];

  for (const fname of txtFiles) {
    const slug = fname.replace(/\.(txt|md)$/i, '');
    let text = '';
    try { text = await readFile(join(chaptersDir, fname), 'utf-8'); } catch { continue; }

    const title = (() => {
      const m = text.match(/^#\s+(.+)$/m);
      return m ? m[1].trim() : slug.replace(/^ch\d+-/i, '').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    })();

    const words = text.split(/\s+/).filter(Boolean).length;
    const qrefs = quranRefs(text);
    const { total: termCount, glossed: glossedCount } = domainTerms(text);
    const arc = arcLabels(text);
    const citationsFound = text.match(/(?:quran|hadith|doctrine):\S+/g) ?? [];

    const fid = fidelityScore([], citationsFound);
    const voi = voiceScore(text, exemplar);
    const str = structureScore(ARC_RULES, arc);
    const enr = enrichmentScore(termCount, glossedCount, qrefs, words);
    const tot = peqTotal(fid, voi, str, enr, exemplar !== null);

    chapters.push({ slug, title, scores: { fidelity: fid, voice: voi, structure: str, enrichment: enr, total: tot, verdict: verdict(tot) } });
  }

  const totals = chapters.map((c) => c.scores.total);
  const avg = totals.length > 0 ? Math.round(totals.reduce((a, b) => a + b, 0) / totals.length * 10) / 10 : 0;

  return {
    slug: bookDir.split('/').pop() ?? '',
    archetype: archetypeSlug,
    avg,
    passCount: totals.filter((t) => t >= THRESHOLD_PASS).length,
    warnCount: totals.filter((t) => t >= THRESHOLD_WARN && t < THRESHOLD_PASS).length,
    failCount: totals.filter((t) => t < THRESHOLD_WARN).length,
    chapters,
  };
}

// ---------------------------------------------------------------------------
// Human-friendly helpers
// ---------------------------------------------------------------------------

export function verdictLabel(v: 'PASS' | 'WARN' | 'FAIL' | string): string {
  if (v === 'PASS') return 'Excellent';
  if (v === 'WARN') return 'Good';
  return 'Needs work';
}

export function verdictColor(v: 'PASS' | 'WARN' | 'FAIL' | string): string {
  if (v === 'PASS') return '#22c55e'; // green
  if (v === 'WARN') return '#f59e0b'; // amber
  return '#ef4444'; // red
}

export function scoreGrade(total: number): string {
  if (total >= 90) return 'A';
  if (total >= 85) return 'B';
  if (total >= 80) return 'C';
  if (total >= 70) return 'D';
  return 'F';
}
