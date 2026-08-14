/**
 * book-style-settings.mjs — the book-level display choices book-html.mjs and
 * the reader/PDF renderers read: author display name, citation-style family,
 * translation face, Arabic face/size/ink.
 *
 * Split out of book-html.mjs (DR-005, 2026-08-14) — a pure settings-reader
 * cluster with no dependency on markdown parsing, distinct from the HTML
 * assembly it was living beside. Re-exported from book-html.mjs so every
 * existing import path keeps working unchanged.
 */

import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

/** ASCII-fold a display name (meta.yml authors carry diacritics). */
export function asciiFold(s) {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[ʻʿ‘’ʼ]/g, "'");
}
/** Read the author display name from the book's meta.yml (best effort). */
export function readAuthor(bookContentDir) {
  const metaPath = path.join(bookContentDir, "meta.yml");
  if (!existsSync(metaPath)) return "";
  const line = readFileSync(metaPath, "utf-8")
    .split(/\r?\n/)
    .find((l) => /^\s*author:\s*/.test(l));
  if (!line) return "";
  let value = line.replace(/^\s*author:\s*/, "").trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return asciiFold(value.trim());
}
/** The style families and translation faces a book may choose. Duplicated as
 *  typed constants in the API route (citation-style.ts) because this is a
 *  plain-.mjs module the Astro route cannot import types from; the two lists must
 *  change together. `plain` leads because it is the default (locked 2026-07-21). */
export const CITATION_FAMILIES = ["plain", "scholarly", "elegant"];
export const TRANSLATION_FONTS = [
  "eb-garamond",
  "cormorant-garamond",
  "crimson-pro",
  "lora",
];
/** The NON-Qur'anic Arabic face. Scripture is not in this list and never will
 *  be: a run the audit resolved against the canonical mushaf is set in the KFGQPC
 *  Uthmanic script because that is the orthography the text is written in, which
 *  is a correctness rule, not a preference. This choice covers everything else —
 *  hadith, sayings, poetry, the book's own Arabic phrases. */
export const ARABIC_FONTS = [
  "traditional-arabic",
  "scheherazade-new",
  "amiri",
  // Three modern faces added 2026-08-02. Declaring one here is only a third of
  // the job: it must also carry an @font-face in BOTH book-print.css and
  // theme-tokens.css, and a `.ar-<id>` stack in quote-typography.css.
  "cairo",
  "tajawal",
  "ibm-plex-sans-arabic",
  // Added 2026-08-14. No new @font-face needed — Amiri/AmiriSized already carry
  // a real 700 cut (book-print.css, theme-tokens.css), so this reuses the
  // regular Amiri stack and sets --q-ar-weight: 700 in quote-typography.css.
  "amiri-bold",
];

/** How large the book sets its Arabic — display quotations AND terms woven into
 *  prose, which move together (quote-typography.css `.ars-*`). `standard` is the
 *  default and stamps no class: it IS the :root value, so an unset book and one
 *  explicitly set to standard render through the same declaration. */
export const ARABIC_SIZES = ["compact", "standard", "large", "generous"];
export const DEFAULT_ARABIC_SIZE = "standard";

/** The colour Arabic is set in (quote-typography.css `.ari-*`). `maroon` is the
 *  default and stamps no class, for the same reason `standard` does not. Every
 *  option is measured to clear WCAG AA on all three papers — see that file. */
export const ARABIC_INKS = ["maroon", "ink", "indigo", "forest", "brown"];
export const DEFAULT_ARABIC_INK = "maroon";

/** Read the per-book citation-style family from book/citation-style.json.
 *  Returns 'plain' | 'scholarly' | 'elegant', or '' when the file is absent or
 *  the value is unknown (renderer then leaves the body unstyled = default look). */
export function readCitationFamily(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const family = JSON.parse(readFileSync(p, "utf-8"))?.family;
    return CITATION_FAMILIES.includes(family) ? family : "";
  } catch {
    return "";
  }
}
/** Read the per-book translation face from the same file. The field is OPTIONAL
 *  and was added after the first books shipped, so an absent or unknown value
 *  reads as '' and every consumer falls back to the --q-tr-face default (EB
 *  Garamond) — an older book gains the face without its artifact being rewritten. */
export function readTranslationFont(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const font = JSON.parse(readFileSync(p, "utf-8"))?.translation_font;
    return TRANSLATION_FONTS.includes(font) ? font : "";
  } catch {
    return "";
  }
}
/** The book's non-Qur'anic Arabic face, from the same file. Optional in exactly
 *  the way translation_font is: absent or unknown reads as '' and every surface
 *  falls back to the --q-ar-face default (Scheherazade New), so no shipped book's
 *  artifact needed rewriting to gain the setting. */
export function readArabicFont(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const font = JSON.parse(readFileSync(p, "utf-8"))?.arabic_font;
    return ARABIC_FONTS.includes(font) ? font : "";
  } catch {
    return "";
  }
}
/** The book's Arabic size and ink, from the same file.
 *
 *  Both return '' for the DEFAULT as well as for absent/unknown, and that is
 *  deliberate rather than lossy: the default is the `:root` declaration in
 *  quote-typography.css, so stamping `.ars-standard` would mean maintaining a
 *  second declaration that has to agree with it forever. '' means "the class is
 *  not needed", which is the truth. */
export function readArabicSize(bookDir) {
  return readOptionalChoice(
    bookDir,
    "arabic_size",
    ARABIC_SIZES,
    DEFAULT_ARABIC_SIZE,
  );
}
export function readArabicInk(bookDir) {
  return readOptionalChoice(
    bookDir,
    "arabic_ink",
    ARABIC_INKS,
    DEFAULT_ARABIC_INK,
  );
}
function readOptionalChoice(bookDir, key, allowed, fallback) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const v = JSON.parse(readFileSync(p, "utf-8"))?.[key];
    return allowed.includes(v) && v !== fallback ? v : "";
  } catch {
    return "";
  }
}
