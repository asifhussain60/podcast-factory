/**
 * para-blocks.mjs — the prose blocks of a chapter, and a stable name for each.
 *
 * JAVASCRIPT HALF OF A MIRROR PAIR. The Python half is
 * `scripts/podcast/_para_blocks.py`. Both are pinned to the SAME fixtures at
 * `para-blocks.fixtures.json`, so a change to either that is not matched in the
 * other fails a test rather than letting the aligner and the Composer disagree
 * about which blocks a chapter HAS or what each one is called. A silent
 * disagreement here does not merely degrade the Arabic reveal — it puts the wrong
 * Arabic above the wrong paragraph, which is worse than showing none.
 *
 * WHY FINGERPRINT THE RAW MARKDOWN, not the rendered text: both sides read the
 * same `book/book.md` body, so the raw block is a shared, byte-identical input.
 * Fingerprinting rendered text would drag in `passage-match.foldText`, which
 * exists to reconcile two DIFFERENT renderings of one sentence and is a far
 * heavier fold — a real drift risk to mirror, for no gain here.
 */
import { createHash } from "node:crypto";

/**
 * A block is PROSE unless it opens as a blockquote, heading, or raw HTML block.
 * This is the rule `lib/reader/composer.ts` already applied inline for its
 * `paras` count, which in turn mirrors what `visual-layout.mjs` counts as a
 * paragraph when placing figures — so all three agree on what "paragraph 4 of
 * this chapter" means. Lifted here so there is one copy, not three.
 */
const NOT_PROSE_RE = /^\s*[>#<]/;

/** The chapter's prose blocks, in order, trimmed. */
export function proseBlocks(body) {
  return String(body ?? "")
    .split(/\n\s*\n/)
    .filter((b) => b.trim() && !NOT_PROSE_RE.test(b))
    .map((b) => b.trim());
}

/**
 * A stable short name for one prose block.
 *
 * Whitespace-collapsed and lowercased before hashing, so a re-wrap or a change of
 * indentation does not rename a paragraph a reader would call the same one.
 * Anything more aggressive would start merging paragraphs that genuinely differ.
 */
export function paraFingerprint(block) {
  const norm = String(block ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
  return createHash("sha256").update(norm, "utf8").digest("hex").slice(0, 16);
}

/** `paraFingerprint` of every prose block, in order. */
export function fingerprints(body) {
  return proseBlocks(body).map(paraFingerprint);
}

/**
 * One name for a chapter's WHOLE ordered block list — the incremental key. When
 * this is unchanged the chapter's prose has not moved, so a stored alignment is
 * still valid and re-composing costs nothing.
 */
export function blocksFingerprint(body) {
  return createHash("sha256")
    .update(fingerprints(body).join("\n"), "utf8")
    .digest("hex")
    .slice(0, 16);
}
