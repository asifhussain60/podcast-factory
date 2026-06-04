/**
 * Convenience: markdown → HTML → ref-highlighted HTML in one call.
 *
 * Centralises the pipeline so ContractView and the chapter reader use the
 * same code path. Returns both the final HTML and the counts/matches for
 * TOC and keyboard nav.
 */

import { renderMarkdown } from './markdown';
import { highlightRefs, type HighlightResult } from './highlight-renderer';
import type { CategoryPrefs } from './ref-categories';

export interface ProseRenderResult extends HighlightResult {
  /** Sum of all category counts — used for "N refs in this section" labels. */
  totalRefs: number;
}

export function renderProseWithRefs(source: string, prefs: CategoryPrefs = {}): ProseRenderResult {
  const html = renderMarkdown(source);
  const highlighted = highlightRefs(html, prefs);
  const totalRefs = Object.values(highlighted.counts).reduce((a, b) => a + b, 0);
  return { ...highlighted, totalRefs };
}
