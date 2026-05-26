/**
 * Wrap reference matches in the rendered HTML with `<span>` elements
 * carrying `data-ref-type`, `data-ref-value`, and a `ref-{id}` class.
 *
 * Pipeline order:
 *   markdown text → renderMarkdown() → HTML → highlightRefs() → HTML with spans
 *
 * The HighlightRenderer iterates over all enabled RefCategories, collects
 * matches, resolves overlaps by priority (higher wins) then by length
 * (longer wins), then by registration order (first wins), and finally
 * splices `<span>` wrappers into the HTML.
 *
 * Each detector receives the FULL HTML string and is expected to return
 * matches whose offsets are valid into that string. Detectors that target
 * specific HTML structures (e.g. `<em>...</em>` spans) use their own
 * regex; detectors that target plain text (e.g. Quran "Q 5:93") rely on
 * the fact that their pattern can't accidentally match HTML attribute
 * content.
 */

import type { RefCategory, RefMatch } from './ref-categories/types';
import { getEnabledCategories, type CategoryPrefs } from './ref-categories';

interface ResolvedMatch extends RefMatch {
  category: RefCategory;
}

export interface HighlightResult {
  html: string;
  /** Counts per category id — used by TOC sidebar and toolbar chips. */
  counts: Record<string, number>;
  /** Ordered list of matches in document order — used by keyboard nav. */
  matches: Array<{ id: string; type: string; value: string; start: number; end: number }>;
}

export function highlightRefs(html: string, prefs: CategoryPrefs = {}): HighlightResult {
  const categories = getEnabledCategories(prefs);
  if (categories.length === 0) {
    return { html, counts: {}, matches: [] };
  }

  // 1. Collect all matches across categories.
  const all: ResolvedMatch[] = [];
  for (const category of categories) {
    const found = category.detect(html, { html });
    for (const m of found) {
      all.push({ ...m, category });
    }
  }

  if (all.length === 0) {
    return { html, counts: {}, matches: [] };
  }

  // 2. Resolve overlaps: sort by (start ASC, priority DESC, length DESC).
  all.sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start;
    const pa = a.category.priority ?? 0;
    const pb = b.category.priority ?? 0;
    if (pa !== pb) return pb - pa;
    return (b.end - b.start) - (a.end - a.start);
  });

  const accepted: ResolvedMatch[] = [];
  let cursor = -1;
  for (const m of all) {
    if (m.start >= cursor) {
      accepted.push(m);
      cursor = m.end;
    }
  }

  // 3. Splice spans into the HTML.
  const parts: string[] = [];
  let pos = 0;
  let seq = 0;
  const counts: Record<string, number> = {};
  const matchesOut: HighlightResult['matches'] = [];

  for (const m of accepted) {
    parts.push(html.slice(pos, m.start));
    const refId = `ref-${m.category.id}-${seq++}`;
    const inner = html.slice(m.start, m.end);
    const extraAttrs = m.attrs
      ? Object.entries(m.attrs)
          .map(([k, v]) => ` data-${escapeAttr(k)}="${escapeAttr(v)}"`)
          .join('')
      : '';
    parts.push(
      `<span id="${refId}" class="ref ref-${m.category.id}" data-ref-type="${m.category.id}" data-ref-value="${escapeAttr(m.value)}"${extraAttrs}>${inner}</span>`
    );
    pos = m.end;
    counts[m.category.id] = (counts[m.category.id] ?? 0) + 1;
    matchesOut.push({
      id: refId,
      type: m.category.id,
      value: m.value,
      start: m.start,
      end: m.end,
    });
  }
  parts.push(html.slice(pos));

  return { html: parts.join(''), counts, matches: matchesOut };
}

function escapeAttr(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
