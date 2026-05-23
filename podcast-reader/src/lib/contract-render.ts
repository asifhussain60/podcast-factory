/**
 * Render every prose section of a ChapterContract with ref highlighting
 * applied, and aggregate per-category counts across the whole document.
 *
 * Page-level code calls this once, passes the pre-rendered sections to
 * ContractView for display, and passes the counts to ReaderControls.
 */

import type { ChapterContract } from './contract-parser';
import { renderProseWithRefs, type ProseRenderResult } from './render-prose';
import { getAllCategories, type CategoryPrefs } from './ref-categories';
import type { CategoryDescriptor } from '~/components/reader/ReaderControls';

export interface RenderedAnchorPassage {
  cite?: string;
  rendered: ProseRenderResult;
}

export interface RenderedContract {
  audience: ProseRenderResult | null;
  keyTensions: ProseRenderResult[];
  toneConstraints: ProseRenderResult[];
  anchorPassages: RenderedAnchorPassage[];
  showNotesBlurb: ProseRenderResult | null;
  showNotesBullets: ProseRenderResult[];
  /** Per-category total counts across the whole contract. */
  counts: Record<string, number>;
  /** Sum of all category counts. */
  totalRefs: number;
}

export function renderContract(contract: ChapterContract, prefs: CategoryPrefs = {}): RenderedContract {
  const counts: Record<string, number> = {};
  const accumulate = (r: ProseRenderResult) => {
    for (const [k, v] of Object.entries(r.counts)) {
      counts[k] = (counts[k] ?? 0) + v;
    }
    return r;
  };

  const audience = contract.audience ? accumulate(renderProseWithRefs(contract.audience, prefs)) : null;
  const keyTensions = contract.keyTensions.map((t) => accumulate(renderProseWithRefs(t, prefs)));
  const toneConstraints = contract.toneConstraints.map((t) => accumulate(renderProseWithRefs(t, prefs)));
  const anchorPassages = contract.anchorPassages.map((p) => ({
    cite: p.cite,
    rendered: accumulate(renderProseWithRefs(p.text, prefs)),
  }));
  const showNotesBlurb = contract.showNotes?.blurb ? accumulate(renderProseWithRefs(contract.showNotes.blurb, prefs)) : null;
  const showNotesBullets = (contract.showNotes?.bullets ?? []).map((b) => accumulate(renderProseWithRefs(b, prefs)));

  const totalRefs = Object.values(counts).reduce((a, b) => a + b, 0);

  return {
    audience,
    keyTensions,
    toneConstraints,
    anchorPassages,
    showNotesBlurb,
    showNotesBullets,
    counts,
    totalRefs,
  };
}

/**
 * Build the array passed to <ReaderControls categories={...} />.
 *
 * One descriptor per registered category, including counts. Categories with
 * zero matches in the current document are included so the user can see
 * "Hadith: 0" — useful confirmation rather than silent omission.
 */
export function buildCategoryDescriptors(counts: Record<string, number>): CategoryDescriptor[] {
  return getAllCategories().map((c) => ({
    id: c.id,
    label: c.label,
    glyph: c.glyph,
    colorToken: c.colorToken,
    shortcuts: c.shortcuts,
    count: counts[c.id] ?? 0,
  }));
}
