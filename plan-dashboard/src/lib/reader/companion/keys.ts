/**
 * companion/keys.ts — pure key helpers, safe to import from BOTH the browser and
 * the server (no node:fs). Keeping this dependency-free is what lets the client
 * normalize a chapter key before it ever reaches the disk writer.
 */

/**
 * The ONLY chapter-key shape the on-disk store accepts. No dots and no slashes,
 * so a key can never escape the companion-notes directory (path-traversal guard).
 */
export const CHAPTER_KEY_RE = /^[a-z0-9][a-z0-9-]{0,119}$/;

/**
 * Normalize an arbitrary chapter/section identifier (a TOC anchor id, a chapter
 * slug, a heading) into a filesystem-safe key matching CHAPTER_KEY_RE. Lowercases,
 * collapses any run of non-alphanumerics to a single hyphen, trims stray hyphens.
 */
export function safeChapterKey(raw: string): string {
  const k = String(raw)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120)
    .replace(/-+$/g, "");
  return k || "general";
}

/** True when a raw key is already storage-safe (no normalization needed). */
export function isSafeChapterKey(raw: string): boolean {
  return CHAPTER_KEY_RE.test(raw);
}

/**
 * The ONE chapter-key rule for Companion notes: a book heading -> the section key
 * the LIVE Session reads notes under.
 *
 * This is renderMarkdown's heading-id slug (markdown.ts) and loadBook's TOC id
 * (book.ts), which both import it from here. It is NOT `anchorKey` (composer.ts):
 * anchorKey strips the leading "N." so it can match a heading whose number moved,
 * which is right for replaying a Composer edit and wrong for a note — the LIVE
 * Session keys notes by TOC id, ordinal included. Deriving a note's chapter with
 * anchorKey filed it under `a-stranger-in-the-city` while the reader looked for
 * `2-a-stranger-in-the-city`, so the note existed and was never shown.
 *
 * Accepts either a raw markdown heading ("## 2. A Stranger in the City") or the
 * heading text alone; the `#` prefix is stripped either way.
 */
export function sectionKeyFromHeading(heading: string): string {
  return String(heading ?? "")
    .replace(/^#{1,6}\s+/, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 80);
}
