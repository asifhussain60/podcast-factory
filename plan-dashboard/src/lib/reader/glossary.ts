/**
 * glossary.ts — load per-book Arabic-script overlay glossary.
 *
 * Ported from podcast-reader/src/lib/glossary.ts. Same parser; new path
 * lookup goes through content-paths.findContent so it picks up the
 * canonical content/<stage>/<category>/<slug>/_system/glossary.yml.
 */
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

import { findContent } from '../content-paths';

export interface GlossaryEntry {
  phonetic: string;
  transliteration: string;
  arabic_script: string;
  audio_phonetic: string;
  first_seen_snippet: string;
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

export function wrapPhoneticTokens(html: string, entries: GlossaryEntry[]): string {
  if (!entries.length) return html;
  const sorted = [...entries].sort((a, b) => b.phonetic.length - a.phonetic.length);

  let current = html;
  for (const e of sorted) {
    const esc = e.phonetic.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`\\b(${esc})\\b`, 'g');
    const scriptAttr = escapeAttr(e.arabic_script);
    const audioAttr  = escapeAttr(e.audio_phonetic || '');
    const trAttr     = escapeAttr(e.transliteration || e.phonetic);
    const scriptInner = escapeHtml(e.arabic_script);

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
