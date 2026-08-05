/**
 * block-align.ts — match the paragraphs of an edited document back to the
 * paragraphs of the baseline they started from.
 *
 * Deliberately dependency-free (string[] in, (number|null)[] out, no imports) so
 * Node's built-in type stripping can run it straight from the test file — same
 * arrangement as src/lib/reader/book-fences.ts. Tests: scripts/block-align.test.mjs.
 */

/** Above this block count the alignment table is skipped for positional
 *  indexing — a doc this long is past the point where per-keystroke O(n*m) is
 *  affordable, and track-changes noise is the lesser evil against a frozen tab. */
const MAX_ALIGN_BLOCKS = 1200;

/**
 * Map each CURRENT block to the ORIGINAL block it descends from, or null if it
 * has no counterpart.
 *
 * Why this exists. The diff used to compare current block N against original
 * block N — pure array position. Press Enter once and every block after the
 * caret shifts by one, so each is diffed against its NEIGHBOUR's original: the
 * whole rest of the chapter lights up as changed and the neighbour's text is
 * rendered inline as struck-out deletions. One keystroke produced 138 deletion
 * widgets holding 5,350 characters, which reads as "pressing Enter dumps
 * paragraphs of text into my chapter" (reported 2026-07-21). Splitting,
 * merging, or reordering a paragraph all triggered it.
 *
 * A longest-common-subsequence over exact block text pins every UNCHANGED block
 * to its true original regardless of how many blocks were inserted or removed
 * above it, so a split now marks only the blocks actually touched.
 */
export function alignBlocks(
  original: string[],
  current: string[],
): (number | null)[] {
  const n = original.length;
  const m = current.length;
  if (!n || !m) return new Array(m).fill(null);
  if (n > MAX_ALIGN_BLOCKS || m > MAX_ALIGN_BLOCKS)
    return current.map((_, i) => (i < n ? i : null));

  // lcs[i][j] = length of the LCS of original[i..] and current[j..].
  const width = m + 1;
  const lcs = new Int32Array((n + 1) * width);
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i * width + j] =
        original[i] === current[j]
          ? lcs[(i + 1) * width + j + 1] + 1
          : Math.max(lcs[(i + 1) * width + j], lcs[i * width + j + 1]);
    }
  }

  // Walk the table to collect the ANCHORS — blocks whose text is untouched.
  const anchors: [number, number][] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (original[i] === current[j]) {
      anchors.push([i, j]);
      i++;
      j++;
    } else if (lcs[(i + 1) * width + j] >= lcs[i * width + j + 1]) {
      i++;
    } else {
      j++;
    }
  }

  // Anchors alone are not enough: the moment a block is EDITED it stops matching
  // its own original exactly, so it falls outside every anchor and would lose its
  // word-diff — i.e. typing would silently stop being tracked, which is the whole
  // point of the feature. So pair up the unmatched runs BETWEEN two anchors in
  // order: the k-th edited block in a gap belongs to the k-th original block in
  // the same gap. Anything left over on the current side is genuinely new (the
  // far half of a split, or a freshly typed paragraph) and stays null.
  const out: (number | null)[] = new Array(m).fill(null);
  let prevOrig = -1;
  let prevCur = -1;
  const fillGap = (origEnd: number, curEnd: number): void => {
    for (let k = 1; prevCur + k < curEnd && prevOrig + k < origEnd; k++)
      out[prevCur + k] = prevOrig + k;
  };
  for (const [oi, cj] of anchors) {
    fillGap(oi, cj);
    out[cj] = oi;
    prevOrig = oi;
    prevCur = cj;
  }
  fillGap(n, m); // the tail after the last anchor
  return out;
}
