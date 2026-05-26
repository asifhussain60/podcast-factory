/**
 * glossary.ts — load per-book Arabic-script overlay glossary.
 *
 * Source: BOOK_DIR/_system/glossary.yml emitted by
 * scripts/podcast/build_glossary.py and populated by
 * scripts/podcast/fill_glossary_arabic.py.
 *
 * The reader uses entries to wrap phonetic tokens in chapter/episode prose
 * with a span carrying the Arabic script. CSS toggled via body[data-arabic]
 * controls whether the script is visible.
 *
 * No YAML dep: hand-rolled parser for the fixed glossary schema (matches
 * the emitter format in build_glossary.py exactly — quoted scalars,
 * one entry per dash, four fields per entry).
 */

import fs from 'node:fs/promises';
import path from 'node:path';

export interface GlossaryEntry {
  phonetic: string;
  transliteration: string;
  arabic_script: string;
  audio_phonetic: string;
  first_seen_snippet: string;
}

const REPO_ROOT_DEPTH = 2; // podcast-reader/src/lib → repo root

function repoRoot(): string {
  // Astro runs from podcast-reader/, so resolve up from this file's known path.
  return path.resolve(import.meta.dirname ?? process.cwd(), '..', '..', '..');
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
    if (raw.startsWith('entries:')) {
      inEntries = true;
      continue;
    }
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

/**
 * Loads a book's glossary from any of its known locations under the
 * monorepo (drafts/<book>/_system/glossary.yml or
 * published/books/<book>/_system/glossary.yml). Returns [] if absent.
 */
export async function loadGlossary(worktree: string, book: string): Promise<GlossaryEntry[]> {
  const root = repoRoot();
  const candidates = [
    path.join(root, 'content', 'drafts', book, '_system', 'glossary.yml'),
    path.join(root, 'content', 'published', 'books', book, '_system', 'glossary.yml'),
    // Pre-restructure worktree shape (deprecated 2026-05-23):
    path.join(root, 'worktrees', worktree, 'content', 'podcast', 'library', 'books', book, '_system', 'glossary.yml'),
  ];
  for (const p of candidates) {
    try {
      const buf = await fs.readFile(p, 'utf-8');
      const entries = parseGlossaryYaml(buf);
      // Filter to entries that actually carry an Arabic script; the empty
      // ones add no value and slow the wrap step for nothing.
      return entries.filter((e) => e.phonetic && e.arabic_script);
    } catch {
      // try next
    }
  }
  return [];
}

/**
 * Wrap occurrences of each glossary entry's `phonetic` form in the HTML
 * with a span carrying both the English (transliterated) form and the
 * Arabic script as sibling spans. CSS gated on body[data-arabic="on"]
 * decides which sibling renders. Copy-paste preserves the visible form
 * in both modes (font-size:0 trick breaks selection).
 *
 *   <span class="ar-overlay"
 *         data-script="حُجَّة"
 *         data-audio="HUJ-jah"
 *         data-transliteration="Ḥujjah">
 *     <span class="ar-en">Hujjah</span>
 *     <span class="ar-script" aria-hidden="true" lang="ar" dir="rtl">حُجَّة</span>
 *   </span>
 *
 * Sorted by phonetic length DESC so longer multi-word forms win over
 * their substrings.
 */
export function wrapPhoneticTokens(html: string, entries: GlossaryEntry[]): string {
  if (!entries.length) return html;
  const sorted = [...entries].sort((a, b) => b.phonetic.length - a.phonetic.length);
  const parts = html.split(/(<[^>]+>)/g);
  for (let i = 0; i < parts.length; i++) {
    if (parts[i].startsWith('<')) continue;
    let chunk = parts[i];
    for (const e of sorted) {
      const esc = e.phonetic.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp(`\\b(${esc})\\b`, 'g');
      const scriptAttr = e.arabic_script.replace(/"/g, '&quot;');
      const audioAttr = (e.audio_phonetic || '').replace(/"/g, '&quot;');
      const trAttr = (e.transliteration || e.phonetic).replace(/"/g, '&quot;');
      chunk = chunk.replace(
        re,
        `<span class="ar-overlay" data-script="${scriptAttr}" data-audio="${audioAttr}" data-transliteration="${trAttr}" data-phonetic="$1"><span class="ar-en">$1</span><span class="ar-script" aria-hidden="true" lang="ar" dir="rtl">${e.arabic_script}</span></span>`,
      );
    }
    parts[i] = chunk;
  }
  return parts.join('');
}
