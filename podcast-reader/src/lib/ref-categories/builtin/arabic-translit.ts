import type { RefCategory, RefMatch } from '../types';
import { buildAllowlistRegex } from '~/data/arabic-terms';

/**
 * Arabic transliteration detector — four passes.
 *
 * Pass 1: italicised <em>...</em> spans with a diacritic or apostrophe
 *         (the original pass — catches *al-qada*, *taʾwīl*, *qaʿda*).
 *
 * Pass 2: plain-text `al-X` / `el-X` / `ad-X` / `ar-X` / `as-X` / `at-X`
 *         / `az-X` / `an-X` / `ash-X` / `adh-X` definite-article prefix
 *         followed by an uppercase word. Catches al-Riyad, al-Sijistani,
 *         al-Zaki, al-Razi, al-Islah, ash-Shariah, etc.
 *
 * Pass 3: plain-text Abu/Ibn/Bint/Umm name compounds, with optional
 *         continuation into al-X / ibn X. Captures "Abu Ya'qub al-Sijistani"
 *         as ONE match, not two — important for not double-wrapping.
 *
 * Pass 4: plain-text words containing diacritics (ʿ ʾ ā ū ī ḥ ṣ ḍ ṭ ẓ).
 *         Catches isolated diacriticised words outside <em> spans.
 *
 * Pass 5: closed-list match — proper names and concept terms from the
 *         allowlist in src/data/arabic-terms.ts. Catches Jalal, Hayula,
 *         Sunnah, Tawhid, etc. that don't match any pattern.
 *
 * All plain-text passes operate on TEXT SEGMENTS only (the spans
 * between HTML tags), so we never match inside attribute values or
 * already-wrapped <em> content. Overlap resolution at the highlight
 * renderer keeps the widest match when patterns collide.
 */

const EM_RE = /<em>([^<]{2,80})<\/em>/g;
const ARABIC_SIGNAL = /[ʿʾāūīĀŪĪḥṣḍṭẓḤṢḌṬẒĀĒĪŌŪēīōū']/;
const PURE_PUNCTUATION = /^[\s\p{P}]+$/u;
const ENGLISH_STOPWORDS = new Set([
  'important', 'really', 'very', 'just', 'most', 'best', 'now', 'then', 'this',
  'that', 'these', 'those', 'between', 'within', 'across', 'because',
]);

// Plain-text patterns
const AL_PREFIX_RE = /\b(?:al|el|ad|ar|as|at|az|an|ash|adh)-[A-Z][a-zA-Zʿʾāūīʼʻ'][a-zA-Zʿʾāūīʼʻ']*/g;
const ABU_IBN_RE = /\b(?:Abu|Ibn|Bint|Umm) [A-Z][a-zA-Zʿʾāūīʼʻ']+(?:\s+(?:al|el|ibn|bin)-[A-Z][a-zA-Zʿʾāūīʼʻ']+)?/g;
const DIACRITIC_WORD_RE = /\b[a-zA-Zʿʾāūīʼʻ']*[ʿʾāūīĀŪĪḥṣḍṭẓḤṢḌṬẒ][a-zA-Zʿʾāūīʼʻ']*\b/g;
const ALLOWLIST_RE = buildAllowlistRegex();

/**
 * Tokenise HTML into text-only segments, excluding tag interiors and
 * <em>...</em> content (which is handled separately by pass 1).
 */
function extractTextSegments(html: string): Array<{ start: number; text: string }> {
  const segments: Array<{ start: number; text: string }> = [];
  let i = 0;
  let inEm = 0;

  while (i < html.length) {
    const ch = html[i];
    if (ch === '<') {
      const tagEnd = html.indexOf('>', i);
      if (tagEnd === -1) break;
      const tagContent = html.slice(i, tagEnd + 1).toLowerCase();
      if (tagContent.startsWith('<em') && !tagContent.startsWith('<embed')) inEm += 1;
      else if (tagContent.startsWith('</em')) inEm = Math.max(0, inEm - 1);
      i = tagEnd + 1;
    } else {
      const start = i;
      const nextTag = html.indexOf('<', i);
      const end = nextTag === -1 ? html.length : nextTag;
      if (inEm === 0 && end > start) {
        segments.push({ start, text: html.slice(start, end) });
      }
      i = end;
    }
  }

  return segments;
}

function pushAll(target: RefMatch[], re: RegExp, segText: string, segStart: number, valueTransform?: (m: string) => string) {
  re.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(segText)) !== null) {
    const text = m[0];
    target.push({
      start: segStart + m.index,
      end: segStart + m.index + text.length,
      value: valueTransform ? valueTransform(text) : text,
    });
  }
}

export const arabicTranslit: RefCategory = {
  id: 'arabic',
  label: 'Arabic',
  glyph: 'ع',
  colorToken: 'emerald',
  typography: {
    fontFamily: '"Gentium Plus", "Gentium Book Basic", "Georgia", serif',
    fontWeight: 400,
    fontStyle: 'italic',
  },
  shortcuts: { next: 'a', prev: 'A' },
  priority: 1,
  // See quran.ts: detector always runs so spans exist for navigation.
  enabledByDefault: true,
  detect: (html) => {
    const matches: RefMatch[] = [];

    // Pass 1: italicised <em>...</em> with Arabic signal
    EM_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = EM_RE.exec(html)) !== null) {
      const inner = m[1].trim();
      if (PURE_PUNCTUATION.test(inner)) continue;
      if (!ARABIC_SIGNAL.test(inner)) continue;
      if (ENGLISH_STOPWORDS.has(inner.toLowerCase())) continue;
      matches.push({
        start: m.index,
        end: m.index + m[0].length,
        value: inner,
      });
    }

    // Passes 2–5 operate on text segments only
    const segments = extractTextSegments(html);
    for (const seg of segments) {
      pushAll(matches, ABU_IBN_RE, seg.text, seg.start);          // pass 3 first — longer
      pushAll(matches, AL_PREFIX_RE, seg.text, seg.start);        // pass 2
      pushAll(matches, DIACRITIC_WORD_RE, seg.text, seg.start);   // pass 4
      pushAll(matches, ALLOWLIST_RE, seg.text, seg.start);        // pass 5
    }

    return matches;
  },
};
