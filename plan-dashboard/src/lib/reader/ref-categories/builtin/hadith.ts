import type { RefCategory, RefMatch } from '../types';

/**
 * Hadith reference detector.
 *
 * Heuristic: an italicized span (rendered as `<em>...</em>` by the markdown
 * pipeline) preceded within ~120 characters by a hadith-context marker
 * ("Prophetic word", "the Prophet", "Prophet ﷺ", "saying of the Prophet").
 *
 * Hadith refs are inherently less mechanical than Quran refs in this content,
 * so false-positive rate is non-zero. Higher priority than Arabic-translit
 * so overlapping matches resolve in hadith's favor.
 */
const EM_RE = /<em>([^<]{3,260})<\/em>/g;
const CONTEXT_RE = /\b(Prophetic word|Prophet\s+ﷺ|the Prophet|saying of the Prophet|the Messenger of Allah)\b/i;

export const hadith: RefCategory = {
  id: 'hadith',
  label: 'Hadith',
  glyph: '📜',
  colorToken: 'orange',
  typography: {
    fontFamily: '"EB Garamond", "Garamond", "Georgia", serif',
    fontWeight: 400,
    fontStyle: 'italic',
  },
  shortcuts: { next: 'h', prev: 'H' },
  priority: 10,
  // See quran.ts: detector always runs so spans exist for navigation.
  enabledByDefault: true,
  detect: (html) => {
    const matches: RefMatch[] = [];
    EM_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = EM_RE.exec(html)) !== null) {
      const start = Math.max(0, m.index - 120);
      const before = html.slice(start, m.index);
      if (CONTEXT_RE.test(before)) {
        matches.push({
          start: m.index,
          end: m.index + m[0].length,
          value: m[1].trim().slice(0, 80),
        });
      }
    }
    return matches;
  },
};
