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
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120)
    .replace(/-+$/g, '');
  return k || 'general';
}

/** True when a raw key is already storage-safe (no normalization needed). */
export function isSafeChapterKey(raw: string): boolean {
  return CHAPTER_KEY_RE.test(raw);
}
