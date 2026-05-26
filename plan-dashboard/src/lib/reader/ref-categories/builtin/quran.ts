import type { RefCategory, RefMatch } from '../types';

/**
 * Quran reference detector.
 *
 * Matches `Quran 54:49`, `Q 5:93`, `Quran 70:6–7`, `Quran 89:27-30`. Format
 * across kitab-al-riyad contracts is highly consistent — false-positive rate
 * is effectively zero.
 *
 * Operates on the HTML string directly; the pattern contains no `<` or `>`
 * so it never accidentally matches inside tags.
 */
const PATTERN = /\b(?:Quran|Qur[ʾ']an|Q\.?)\s+(\d+):(\d+)(?:[–-](\d+))?\b/g;

export const quran: RefCategory = {
  id: 'quran',
  label: 'Quran',
  glyph: '📖',
  colorToken: 'yellow',
  typography: {
    fontFamily: '"EB Garamond", "Garamond", "Georgia", serif',
    fontWeight: 600,
    fontStyle: 'normal',
  },
  shortcuts: { next: 'n', prev: 'N' },
  priority: 5,
  // enabledByDefault controls whether the DETECTOR runs (wraps spans into the DOM).
  // It must stay true so spans exist for keyboard nav and future comment anchoring.
  // The user-facing highlight visibility defaults to OFF via ReaderControls' empty
  // `enabled` Set; toggling the chip adds/removes from <body data-cat-enabled>.
  enabledByDefault: true,
  detect: (html) => {
    const matches: RefMatch[] = [];
    PATTERN.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = PATTERN.exec(html)) !== null) {
      const verseRange = m[3] ? `${m[2]}-${m[3]}` : m[2];
      matches.push({
        start: m.index,
        end: m.index + m[0].length,
        value: `${m[1]}:${verseRange}`,
        attrs: { surah: m[1], verse: verseRange },
      });
    }
    return matches;
  },
};
