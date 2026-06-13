/**
 * glossary.ts — load per-book Arabic-script overlay glossary.
 *
 * Ported from podcast-reader/src/lib/glossary.ts. Same parser; new path
 * lookup goes through content-paths.findContent so it picks up the
 * canonical content/<stage>/<category>/<slug>/_system/glossary.yml.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { findContent } from '../content-paths';

export interface GlossaryEntry {
  phonetic: string;
  transliteration: string;
  arabic_script: string;
  audio_phonetic: string;
  first_seen_snippet: string;
  // Schema v2 — human curation (set in the reader before audio). Optional;
  // absent means the entry behaves exactly as schema v1 did.
  decision?: GlossaryDecision;
  corrected_phonetic?: string;
  corrected_arabic?: string;
  english_override?: string;
  decided_by?: string;
  decided_at?: string;
  // Teaching-relevance class (set by scripts/podcast/teaching_relevance_classifier.py):
  // how much the term carries the book's TEACHING vs incidental reference. Drives
  // which terms are recited in Arabic + how the curation review prioritises them.
  teaching_relevance?: TeachingRelevance;
}

export type TeachingRelevance = 'teaching' | 'name' | 'incidental' | 'referential';

export type GlossaryDecision =
  | 'keep'
  | 'fix_phonetic'
  | 'correct_arabic'
  | 'replace_english';

/** Effective phonetic match-key + Arabic script after applying the human decision.
 *  Mirror of pronunciation_compiler.resolve_curation (Python) so the on-page
 *  overlay and the spoken audio agree. */
export function resolveCuration(e: GlossaryEntry): {
  phonetic: string;
  arabic: string;
  dropArabic: boolean;
} {
  const decision = (e.decision || 'keep').trim().toLowerCase();
  let phonetic = (e.phonetic || '').trim();
  let arabic = (e.arabic_script || '').trim();
  if (decision === 'fix_phonetic' && (e.corrected_phonetic || '').trim()) {
    phonetic = (e.corrected_phonetic as string).trim();
  } else if (decision === 'correct_arabic' && (e.corrected_arabic || '').trim()) {
    arabic = (e.corrected_arabic as string).trim();
  }
  return { phonetic, arabic, dropArabic: decision === 'replace_english' };
}

function unq(s: string): string {
  let t = s.trim();
  if (t.length >= 2 && t[0] === '"' && t[t.length - 1] === '"') t = t.slice(1, -1);
  return t.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
}

function parseGlossaryYaml(text: string): GlossaryEntry[] {
  const entries: GlossaryEntry[] = [];
  let current: Partial<GlossaryEntry> | null = null;
  let inEntries = false;

  for (const raw of text.split('\n')) {
    if (raw.startsWith('#') || raw.trim() === '') continue;
    if (raw.startsWith('entries:')) { inEntries = true; continue; }
    if (!inEntries) continue;
    if (raw.startsWith('  - ')) {
      if (current) entries.push(current as GlossaryEntry);
      current = { phonetic: '', transliteration: '', arabic_script: '', audio_phonetic: '', first_seen_snippet: '' };
      const kv = raw.slice(4);
      const idx = kv.indexOf(':');
      if (idx > 0) {
        const k = kv.slice(0, idx).trim();
        const v = unq(kv.slice(idx + 1));
        (current as Record<string, string>)[k] = v;
      }
    } else if (raw.startsWith('    ') && current) {
      const kv = raw.slice(4);
      const idx = kv.indexOf(':');
      if (idx > 0) {
        const k = kv.slice(0, idx).trim();
        const v = unq(kv.slice(idx + 1));
        (current as Record<string, string>)[k] = v;
      }
    }
  }
  if (current) entries.push(current as GlossaryEntry);
  return entries;
}

export async function loadGlossary(slug: string): Promise<GlossaryEntry[]> {
  const ref = await findContent(slug);
  if (!ref) return [];
  const p = join(ref.dir, '_system', 'glossary.yml');
  try {
    const buf = await readFile(p, 'utf-8');
    const entries = parseGlossaryYaml(buf);
    return entries.filter((e) => e.phonetic && e.arabic_script);
  } catch {
    return [];
  }
}

/** Every entry (no arabic_script filter) — for the curation review surface,
 *  which must show terms still awaiting an Arabic script too. */
export async function loadGlossaryAll(slug: string): Promise<GlossaryEntry[]> {
  const ref = await findContent(slug);
  if (!ref) return [];
  const p = join(ref.dir, '_system', 'glossary.yml');
  try {
    const buf = await readFile(p, 'utf-8');
    return parseGlossaryYaml(buf).filter((e) => e.phonetic);
  } catch {
    return [];
  }
}

// `_q` inverse of `unq` — escape for double-quoted YAML scalars. MUST match
// scripts/podcast/build_glossary.py::_q so Python and TS round-trip the same file.
function q(s: string): string {
  return (s || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

const _BASE_FIELDS = [
  'phonetic', 'transliteration', 'arabic_script', 'audio_phonetic', 'first_seen_snippet',
] as const;
// Order MUST match scripts/podcast/fill_glossary_arabic.py::_V2_FIELDS so the
// Python and TS emitters round-trip the file byte-identically.
const _V2_FIELDS = [
  'teaching_relevance', 'decision', 'corrected_phonetic', 'corrected_arabic',
  'english_override', 'decided_by', 'decided_at',
] as const;

/** Serialise the glossary in the EXACT shape the Python emitters produce
 *  (scripts/podcast/{build_glossary,fill_glossary_arabic}.py) so a write here
 *  round-trips cleanly through the pipeline. */
export function emitGlossaryYaml(entries: GlossaryEntry[], schemaVersion = 2): string {
  const lines: string[] = [
    '# Per-book glossary — phonetic ↔ Arabic-script overlay for the reader.',
    '# Generated by scripts/podcast/build_glossary.py; arabic_script filled by',
    '# scripts/podcast/fill_glossary_arabic.py from _system/source/ocr/raw-extract.md.',
    '',
    `schema_version: ${schemaVersion}`,
    'entries:',
  ];
  for (const e of entries) {
    const rec = e as unknown as Record<string, string>;
    lines.push(`  - phonetic: "${q(rec.phonetic || '')}"`);
    for (const f of _BASE_FIELDS.slice(1)) {
      lines.push(`    ${f}: "${q(rec[f] || '')}"`);
    }
    for (const f of _V2_FIELDS) {
      const v = (rec[f] || '').trim();
      if (v) lines.push(`    ${f}: "${q(v)}"`);
    }
  }
  return lines.join('\n') + '\n';
}

/**
 * Wrap phonetic tokens in HTML with an Arabic-script overlay span.
 *
 * BUG FIX 2025-05-26: the prior loop split HTML once outside the entries
 * loop, then applied every entry's regex to the SAME chunks — so later
 * (shorter) entries would match inside the data-* attributes of already-
 * inserted ar-overlay spans, corrupting the HTML (raw attribute text
 * leaked into the page). Fix: re-split after each entry so subsequent
 * matches only see text-not-tags. Also escape `&` and `<` in attribute
 * values + the arabic_script inner HTML.
 */
function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export interface GlossaryDecisionPatch {
  decision: GlossaryDecision;
  corrected_phonetic?: string;
  corrected_arabic?: string;
  english_override?: string;
  decided_by?: string;
}

/** Persist a human curation decision INTO _system/glossary.yml (schema v2),
 *  keyed by the entry's original `phonetic`. Single source of truth: both the
 *  audio render and the reader overlay read the result. Returns the updated
 *  entry, or null when the term/glossary is absent. */
export async function writeGlossaryDecision(
  slug: string,
  phonetic: string,
  patch: GlossaryDecisionPatch,
): Promise<GlossaryEntry | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const p = join(ref.dir, '_system', 'glossary.yml');
  let entries: GlossaryEntry[];
  try {
    entries = parseGlossaryYaml(await readFile(p, 'utf-8'));
  } catch {
    return null;
  }
  const target = entries.find((e) => e.phonetic === phonetic);
  if (!target) return null;
  const now = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  target.decision = patch.decision;
  if (patch.corrected_phonetic !== undefined) target.corrected_phonetic = patch.corrected_phonetic;
  if (patch.corrected_arabic !== undefined) target.corrected_arabic = patch.corrected_arabic;
  if (patch.english_override !== undefined) target.english_override = patch.english_override;
  target.decided_by = patch.decided_by || 'reader';
  target.decided_at = now;
  await writeFile(p, emitGlossaryYaml(entries), 'utf-8');
  return target;
}

export function wrapPhoneticTokens(html: string, entries: GlossaryEntry[]): string {
  if (!entries.length) return html;
  // Apply human curation: replace-with-English entries are NOT wrapped (the term
  // stays English on the page and is not recited); correct/fix use the resolved
  // values so the overlay matches the spoken audio.
  const resolved = entries
    .map((e) => ({ e, c: resolveCuration(e) }))
    .filter(({ c }) => !c.dropArabic && c.phonetic && c.arabic);
  const sorted = resolved.sort((a, b) => b.c.phonetic.length - a.c.phonetic.length);

  let current = html;
  for (const { e, c } of sorted) {
    const esc = c.phonetic.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`\\b(${esc})\\b`, 'g');
    const scriptAttr = escapeAttr(c.arabic);
    const audioAttr  = escapeAttr(e.audio_phonetic || '');
    const trAttr     = escapeAttr(e.transliteration || c.phonetic);
    const scriptInner = escapeHtml(c.arabic);

    // Re-split BEFORE each entry — newly-inserted ar-overlay spans from
    // the previous entry's pass become tag-only parts that we skip.
    const parts = current.split(/(<[^>]+>)/g);
    let touched = false;
    for (let i = 0; i < parts.length; i++) {
      if (parts[i].startsWith('<')) continue;
      const replaced = parts[i].replace(re, (_m, p1) => {
        const phoneticAttr = escapeAttr(p1);
        return `<span class="ar-overlay" data-script="${scriptAttr}" data-audio="${audioAttr}" data-transliteration="${trAttr}" data-phonetic="${phoneticAttr}"><span class="ar-en">${escapeHtml(p1)}</span><span class="ar-script" aria-hidden="true" lang="ar" dir="rtl">${scriptInner}</span></span>`;
      });
      if (replaced !== parts[i]) {
        parts[i] = replaced;
        touched = true;
      }
    }
    if (touched) current = parts.join('');
  }
  return current;
}
