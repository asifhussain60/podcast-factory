/**
 * text-ink.ts — the colours a run of text may be set in, and nothing else.
 *
 * ONE palette, two consumers that mean different things by it:
 *
 *   - the per-selection colour tool in the Book Composer, which colours any run
 *     the human highlights (English prose, an Arabic term, half a sentence), and
 *   - the book-wide Arabic ink setting, which colours display quotations by
 *     default (see arabic-typography.ts, which imports from here).
 *
 * Sharing the list is deliberate: two colour controls offering two different
 * greens would be a product with two ideas of what "forest" is.
 *
 * The VALUES live in quote-typography.css, keyed by these ids (`.ink-*`). This
 * module names the choices; the stylesheet is what they mean, and the PDF reads
 * the same classes — so a hex restated here would be a second place for screen
 * and print to disagree.
 *
 * Every one is measured against the cream, sepia and dark papers and clears
 * WCAG AA (8.3:1 to 16.6:1 on cream). That is why this is a fixed palette rather
 * than a free colour picker: the likeliest first use of a picker is a colour
 * that looks pleasant on screen and is unreadable in print, and this edition is
 * made to be read.
 */

export interface TextInk {
  id: string;
  name: string;
  /** The half-line under the name, and the swatch's tooltip. */
  tagline: string;
  /** For the swatch only — the palette UI needs a colour before the stylesheet
   *  that owns it has been consulted. Kept in step with quote-typography.css by
   *  a fixture test, never by eye. */
  swatch: string;
}

export const TEXT_INKS: readonly TextInk[] = [
  { id: "maroon", name: "Maroon", tagline: "Scripture red", swatch: "#7a1f1f" },
  {
    id: "ink",
    name: "Ink",
    tagline: "The body text colour",
    swatch: "#1f1d18",
  },
  {
    id: "indigo",
    name: "Indigo",
    tagline: "Cool, deep blue",
    swatch: "#23356b",
  },
  { id: "forest", name: "Forest", tagline: "Deep green", swatch: "#1d4d33" },
  {
    id: "brown",
    name: "Brown",
    tagline: "Warm, close to the page",
    swatch: "#6b4423",
  },
];

/** The id every consumer treats as "no colour of its own". */
export const DEFAULT_TEXT_INK = "ink";

export const TEXT_INK_IDS: readonly string[] = TEXT_INKS.map((i) => i.id);

export const isTextInk = (v: unknown): v is string =>
  typeof v === "string" && TEXT_INK_IDS.includes(v);
