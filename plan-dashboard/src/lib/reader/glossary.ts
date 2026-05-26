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
 * Wrap phonetic tokens in HTML with an Arabic-script overlay span. CSS toggled
 * via body[data-arabic="on"] controls visibility. See chapter-viewer styles.
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
