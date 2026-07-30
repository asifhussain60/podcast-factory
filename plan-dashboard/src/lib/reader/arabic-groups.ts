/**
 * arabic-groups.ts — pairing composed English paragraphs with their Arabic source.
 *
 * SEPARATE FROM arabic-source.ts, which reads files and hashes them and therefore
 * imports `node:fs` and `node:crypto`. This half is pure and runs in the BROWSER —
 * the Book Composer's read view calls it on every render — so it must not drag a
 * Node built-in into the client bundle. The type import below is erased at compile
 * time and costs nothing at runtime.
 */
import type { AlignmentPair } from "./arabic-source";

export interface AlignmentGroup {
  /** Index of the first composed paragraph in the group. */
  start: number;
  /** Index of the last — the same as `start` for a plain 1:1 pairing. */
  end: number;
  /** The pair every paragraph in the group shares. */
  pair: AlignmentPair;
}

/**
 * The runs of composed paragraphs that share one source paragraph.
 *
 * TWO DEFECTS LIVE HERE, both found on 2026-07-30, and the signature of this
 * function is the fix for the first of them.
 *
 * IT TAKES `keys` AND INDEXES `pairs` BY POSITION. The Composer used to build a
 * `Map` from `pair.fp`, and a Map keeps one entry per key. A book of dialogue
 * repeats its speech tags — "The Master replied:", "The boy said:", "The narrator
 * continued:" — so every occurrence of a line shares a fingerprint and all of them
 * collapsed onto whichever pair was inserted last. One fingerprint in a single
 * chapter occurs THIRTEEN times against thirteen different source paragraphs; all
 * thirteen rendered the last one's Arabic. Book-wide it pointed 37 paragraphs at
 * Arabic they did not come from. The alignment is written one entry per composed
 * paragraph in order, so POSITION is the key; the fingerprint reverts to being the
 * edit guard it was documented as — a paragraph whose text has changed no longer
 * matches, so it is dropped rather than pointed at Arabic it may no longer share.
 *
 * IT GROUPS. Articulation splits one Arabic paragraph into several English ones —
 * 696 English from 528 Arabic in one book, up to nine from a single source — and
 * showing the whole source above each of them printed the same block nine times,
 * every copy set against a fraction of its own translation. A run becomes one
 * group, so the Arabic appears once at the head of the English it produced.
 */
export function alignmentGroups(
  pairs: readonly AlignmentPair[],
  keys: readonly string[],
): AlignmentGroup[] {
  const groups: AlignmentGroup[] = [];
  // A length disagreement means the two sides are describing different texts, and
  // a positional index would then be worse than useless — it would be confidently
  // wrong. Say nothing instead.
  if (pairs.length !== keys.length) return groups;
  const at = (i: number): AlignmentPair | undefined =>
    pairs[i]?.fp === keys[i] ? pairs[i] : undefined;
  for (let i = 0; i < keys.length; i++) {
    const pair = at(i);
    if (!pair) continue;
    const signature = pair.source_paras.join(",");
    const last = groups[groups.length - 1];
    const prev = last && last.end === i - 1 ? at(i - 1) : undefined;
    if (last && prev && prev.source_paras.join(",") === signature) {
      last.end = i; // same source paragraph, still running — extend the group
      continue;
    }
    groups.push({ start: i, end: i, pair });
  }
  return groups;
}
