/**
 * anchor-key.mjs — the ONE implementation of the chapter anchor key.
 *
 * A Composer edit is stored against a chapter's heading, not its offset, and is
 * replayed by matching that key. If two sides of the system normalize a heading
 * differently, the replay finds no chapter and the author's edit is reported as
 * orphaned — the single failure mode that loses human work silently.
 *
 * Until 2026-07-20 this function existed as FOUR byte-identical copies (
 * lib/reader/composer.ts, api/studio/book-md.ts, src/scripts/book-composer.ts,
 * scripts/visual-layout.mjs) with a fifth in Python (`_book_edits.anchor_key`),
 * none importing from a shared module, and the mirror rule in CLAUDE.md named
 * only two of them. Editing one and forgetting the rest is the obvious way to
 * reintroduce the defect, so there is now nothing to forget.
 *
 * Plain .mjs with no dependencies deliberately: it has to be importable from
 * Astro/TS AND from the standalone node build scripts. `scripts/lib/
 * preview-pages.mjs` already establishes that an .astro page can import from
 * here, so this is the existing pattern rather than a new one.
 *
 * The Python mirror is `scripts/podcast/_book_edits.py::anchor_key`. Change one,
 * change the other, in the same commit — and keep the digit class explicit in
 * both: JavaScript's \d is ASCII-only while Python's is Unicode-aware, so a
 * heading numbered with Arabic-Indic digits (`## ١. Patience`) normalized to
 * `patience` in Python and `١. patience` in JS. No book uses those numerals yet,
 * but this is an Arabic-source project, so it is a question of when.
 */

/** Digits that can open a numbered heading: ASCII, Arabic-Indic, Extended Arabic-Indic. */
const HEADING_NUMBER_RE = /^[0-9٠-٩۰-۹]+\.\s*/;

/** Normalize an anchor / heading to a comparable key: strip markup, "N." prefix, case. */
export function anchorKey(s) {
  return String(s ?? "")
    .replace(/<[^>]+>/g, "")
    .replace(/^#{1,6}\s+/, "")
    .replace(HEADING_NUMBER_RE, "")
    .trim()
    .toLowerCase();
}
