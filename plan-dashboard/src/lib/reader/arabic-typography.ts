/**
 * arabic-typography.ts — the book's Arabic face, size and ink, in one place.
 *
 * These three settings are chosen in TWO surfaces now: the chips in the Book
 * Composer's Typography panel (server-rendered by compose.astro) and the face
 * dropdown + size stepper on the editor toolbar (built at runtime by
 * book-composer.ts). Both had to list the same options, and a list copied into
 * two files is a list that disagrees with itself the first time one is edited —
 * so it lives here and both import it.
 *
 * What is NOT here, deliberately: the VALUES. A face's font stack, a size's two
 * measurements and an ink's hex all live in quote-typography.css, keyed by the
 * `id`s below (`.ar-*`, `.ars-*`, `.ari-*`). This module names the choices; the
 * stylesheet is what they mean. The PDF reads the same classes, so a value
 * restated here would be a third place for the page and the print to diverge.
 *
 * Two copies remain outside TypeScript's reach and say so in their own headers:
 * `api/studio/citation-style.ts` (which validates a save and cannot import a
 * browser module into its allow-lists without dragging the display strings into
 * the API contract) and `scripts/lib/book-html.mjs` (plain .mjs, run by the PDF
 * build under bare node). Both hold ids ONLY — never a name or a tagline — so
 * what they duplicate is the smallest thing that could be duplicated.
 */

/** One selectable option: the id stamped as a class, and how it reads to a human. */
export interface ArabicChoice {
  id: string;
  name: string;
  /** The half-line under the name in the chips, and the dropdown's title text. */
  tagline: string;
}

/**
 * The NON-Qur'anic Arabic face — hadith, sayings, poetry, the book's own Arabic
 * phrases.
 *
 * Scripture is deliberately absent and always will be: a run the Arabic audit
 * resolved against the canonical mushaf is set in the KFGQPC Uthmanic script
 * because that is the orthography the text is written in. That is a correctness
 * rule, not a preference, and `.is-quranic` re-declares the face on the run
 * itself so it survives whatever is chosen here.
 */
export const ARABIC_FACES: readonly ArabicChoice[] = [
  {
    id: "traditional-arabic",
    name: "Traditional Arabic",
    tagline: "Classic naskh, long-document body",
  },
  {
    id: "scheherazade-new",
    name: "Scheherazade New",
    tagline: "Open naskh — default",
  },
  { id: "amiri", name: "Amiri", tagline: "Classical naskh, tighter" },
  // Three modern faces (2026-08-02). Every one is low-contrast and open-
  // countered, which is what keeps a vowelled word legible at text size — the
  // deciding property since the always-vowel rule, for a reader who does not
  // read Arabic unaided.
  { id: "cairo", name: "Cairo", tagline: "Modern, even, very legible" },
  { id: "tajawal", name: "Tajawal", tagline: "Modern, a touch narrower" },
  {
    id: "ibm-plex-sans-arabic",
    name: "IBM Plex Sans Arabic",
    tagline: "Modern, technical, roomy marks",
  },
  // Added 2026-08-14, at Asif's request for a heavier quote-card face. Reuses
  // Amiri's own 700 cut (already self-hosted for headings elsewhere) rather
  // than faux-bolding a face with no real bold — see quote-typography.css
  // `.ar-amiri-bold` / `--q-ar-weight`.
  { id: "amiri-bold", name: "Amiri Bold", tagline: "Amiri's own bold cut" },
];
export const DEFAULT_ARABIC_FACE = "scheherazade-new";

/**
 * How large the book sets ALL its Arabic — display quotations and the terms
 * woven into English sentences move together, because a reader asking for
 * larger Arabic means all of it.
 *
 * Steps rather than a free number: the value has to reach the PDF, where it can
 * only arrive as a stamped class, and a book set to an arbitrary size is a book
 * whose pagination nobody chose. Ordered smallest first — the toolbar's −/+
 * stepper walks this array.
 */
export const ARABIC_SIZES: readonly ArabicChoice[] = [
  { id: "compact", name: "Compact", tagline: "Closer to the English" },
  { id: "standard", name: "Standard", tagline: "Default" },
  { id: "large", name: "Large", tagline: "Marks read without effort" },
  { id: "generous", name: "Generous", tagline: "Largest — the PDF grows" },
];
export const DEFAULT_ARABIC_SIZE = "standard";

/**
 * The ink Arabic is set in. A fixed palette rather than a free picker: every
 * option is measured against the cream, sepia and dark papers and clears WCAG
 * AA, and the likeliest first use of a free picker is a colour that looks
 * pleasant on screen and is unreadable in print.
 */
export const ARABIC_INKS: readonly ArabicChoice[] = [
  { id: "maroon", name: "Maroon", tagline: "Scripture red — default" },
  { id: "ink", name: "Ink", tagline: "Same as the body text" },
  { id: "indigo", name: "Indigo", tagline: "Cool, deep blue" },
  { id: "forest", name: "Forest", tagline: "Deep green" },
  { id: "brown", name: "Brown", tagline: "Warm, close to the page" },
];
export const DEFAULT_ARABIC_INK = "maroon";
