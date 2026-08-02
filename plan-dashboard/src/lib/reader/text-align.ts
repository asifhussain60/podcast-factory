/**
 * text-align.ts — the alignments a paragraph may take.
 *
 * `left` is the DEFAULT and is deliberately not a stored value: an unaligned
 * paragraph already reads left, so recording it would be a second declaration
 * that has to agree with the first. Choosing Left in the toolbar therefore
 * REMOVES the paragraph's entry rather than writing one.
 *
 * The VALUES live in quote-typography.css keyed by these ids (`.align-*`), and
 * the PDF reads the same classes. Mirrors ALIGN_IDS in
 * scripts/lib/text-align.mjs — ids only there, because the print build runs
 * under bare node and has no use for display names.
 */
export interface TextAlignment {
  id: string;
  name: string;
  /** What the control says it will do, in the tooltip. */
  detail: string;
}

/** In the order the toolbar draws them. `left` first because it is the default. */
export const TEXT_ALIGNMENTS: readonly TextAlignment[] = [
  {
    id: "left",
    name: "Align left",
    detail:
      "The book's default — flush left, ragged right. Choosing it removes any alignment set on the paragraph.",
  },
  {
    id: "center",
    name: "Align centre",
    detail:
      "Centres the paragraph the cursor is in. For a dedication, a heading-like line, or a verse set apart.",
  },
  {
    id: "right",
    name: "Align right",
    detail: "Sets the paragraph flush right.",
  },
];

export const DEFAULT_TEXT_ALIGN = "left";

/** The two that are actually stored — `left` is absence. */
export const STORED_ALIGN_IDS: readonly string[] = TEXT_ALIGNMENTS.filter(
  (a) => a.id !== DEFAULT_TEXT_ALIGN,
).map((a) => a.id);

export const isStoredAlign = (v: unknown): v is string =>
  typeof v === "string" && STORED_ALIGN_IDS.includes(v);
