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

/**
 * A block that is NOTHING BUT a standalone `![alt](src)` line — the same
 * "whole line, nothing else" test markdown.ts's own image branch uses to
 * decide a figure rather than literal text. Added 2026-08-14 alongside the
 * ChapterImage editor node: an image line renders as a `chapterImage` node in
 * the live doc, a type `alignablePositions` (book-composer.ts) deliberately
 * does not count as an alignable paragraph — but this function, reading the
 * SAME markdown independently, was still counting that line as a numbered
 * prose block. The two counts then disagreed by one for every image in the
 * chapter, `alignablePositions` saw `found.length !== keys.length`, and every
 * alignment button in the whole chapter disabled itself rather than risk
 * pointing at the wrong paragraph — found live 2026-08-14 in a chapter with
 * four images, where the align buttons never enabled at all. An image mid-
 * sentence is UNCHANGED by this: it stays literal text in a real paragraph on
 * both sides, exactly as it did before ChapterImage existed.
 */
const IMAGE_ONLY_RE = /^!\[[^\]]*\]\([^)\s]+\)$/;

/** The chapter's prose blocks, in order, trimmed. */
export function proseBlocks(body) {
  return String(body ?? "")
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter((b) => b && !NOT_PROSE_RE.test(b) && !IMAGE_ONLY_RE.test(b));
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
