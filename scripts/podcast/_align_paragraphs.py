"""_align_paragraphs.py — which source paragraph is this composed paragraph from?

The edition is a faithful translation, so its paragraphs follow the source's ORDER
even though they do not follow its shape: articulation split 61 source paragraphs
into 133 in one chapter, breaking long narrative blocks into short turns. The
mapping is therefore monotonic and many-to-one, which is exactly what dynamic
programming is for.

WHY NOT SCORE EACH PARAGRAPH INDEPENDENTLY, which was the first attempt: a greedy
best-match scored 75% on one chapter and 7% on another. The 7% was not ambiguity in
the data, it was the metric. A composed paragraph reading `The Master replied:` has
no content words to match on, so scored alone it is noise — but scored as part of a
path it simply shares its neighbours' source paragraph, which is the correct answer.
The same measurement with the DP below: 51% self-supported on that chapter, 96% on
another, monotonic on all eight, and 88% of the book's genuine Arabic quotations
land in exactly the right source paragraph.

ANCHORS ARE HARD CONSTRAINTS. Where a composed paragraph carries an Arabic
quotation that also appears in the source, we do not have to guess: the path is
pinned there, which also pins its neighbours. Glossary terms are excluded from this
— the inline-Arabic overlay places those at first mention in the ENGLISH, so they
anchor nothing and would drag the path to the wrong place.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

# Words too common to carry alignment signal. Deliberately small: over-pruning
# strips the proper nouns and doctrinal vocabulary that do the real work here.
_STOP = set(
    """the a an and or of to in is was were be been that this those these he she it they them his her
    its their with for on at by as from not no but which who whom what when where how all any some are
    do did done have has had will would shall should may might can could i you we us our your my me him
    so then there said say says upon into out over under than too very such been being""".split()
)

_WORD_RE = re.compile(r"[a-z]+")

# Below this a paragraph's own evidence is too thin to call the pairing verified on
# its own; it may still be carried by the path between two confident neighbours.
SELF_SUPPORT = 0.18


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOP and len(w) > 3]


@dataclass
class Alignment:
    """One composed paragraph's placement in the source."""

    index: int
    source_index: int
    score: float
    anchored: bool


def _similarity_fn(source_blocks: list[str], composed_blocks: list[str]):
    """IDF-weighted cosine between a composed paragraph and a source paragraph.

    IDF over THIS chapter, not the book: within one chapter the words that
    distinguish paragraphs are the rare ones, and a book-wide IDF would flatten
    exactly those.
    """
    df: Counter = Counter()
    for block in source_blocks:
        df.update(set(_tokens(block)))
    n = max(len(source_blocks), 1)
    idf = {w: math.log(1 + n / (1 + c)) for w, c in df.items()}
    src = [Counter(_tokens(b)) for b in source_blocks]
    cmp_ = [Counter(_tokens(b)) for b in composed_blocks]

    def sim(i: int, j: int) -> float:
        a, b = cmp_[i], src[j]
        if not a or not b:
            return 0.0
        inter = sum(idf.get(w, 0.6) for w in a if w in b)
        norm = math.sqrt(sum(idf.get(w, 0.6) for w in a) * sum(idf.get(w, 0.6) for w in b))
        return inter / norm if norm else 0.0

    return sim


def align(
    source_blocks: list[str],
    composed_blocks: list[str],
    anchors: dict[int, int] | None = None,
) -> list[Alignment]:
    """Assign every composed paragraph a source paragraph, monotonically.

    `anchors` maps a composed index to the source index it is KNOWN to belong to;
    the path is forced through those. Returns one Alignment per composed paragraph.
    """
    anchors = anchors or {}
    n, m = len(composed_blocks), len(source_blocks)
    if not n or not m:
        return []
    sim = _similarity_fn(source_blocks, composed_blocks)
    neg = float("-inf")

    def allowed(i: int, j: int) -> bool:
        a = anchors.get(i)
        return a is None or a == j

    dp: list[list[float]] = [[neg] * m for _ in range(n)]
    back: list[list[int]] = [[0] * m for _ in range(n)]

    for j in range(m):
        # A mild pull toward starting early: without it a first paragraph with no
        # distinctive vocabulary can be parked arbitrarily far in, and the whole
        # path follows it.
        dp[0][j] = (sim(0, j) - 0.03 * j) if allowed(0, j) else neg

    for i in range(1, n):
        best_prev, best_j = neg, 0
        for j in range(m):
            if not allowed(i, j):
                dp[i][j] = neg
                if dp[i - 1][j] > best_prev:
                    best_prev, best_j = dp[i - 1][j], j
                continue
            # Either this paragraph continues in the same source paragraph as the
            # last one (many-to-one, the common case when one long block was split
            # into turns) or it advances to a later one. Never backwards.
            stay, advance = dp[i - 1][j], best_prev
            if advance > stay:
                dp[i][j], back[i][j] = advance + sim(i, j), best_j
            else:
                dp[i][j], back[i][j] = stay + sim(i, j), j
            if dp[i - 1][j] > best_prev:
                best_prev, best_j = dp[i - 1][j], j

    end = max(range(m), key=lambda j: dp[n - 1][j])
    path = [0] * n
    j = end
    for i in range(n - 1, -1, -1):
        path[i] = j
        if i:
            j = back[i][j]

    return [Alignment(index=i, source_index=path[i], score=sim(i, path[i]), anchored=i in anchors) for i in range(n)]


def is_monotonic(alignments: list[Alignment]) -> bool:
    return all(alignments[i].source_index <= alignments[i + 1].source_index for i in range(len(alignments) - 1))


def bracket(alignments: list[Alignment], i: int) -> tuple[int, int]:
    """The source-index span a paragraph is pinned within by its confident neighbours.

    A paragraph whose own evidence is thin is not unknown: the path is monotonic, so
    it lies between the nearest confident paragraph before it and the nearest after.
    That span is usually one to three paragraphs — a far more useful answer than
    handing back the whole chapter, which is just the chapter toggle with extra steps.
    """
    lo = hi = alignments[i].source_index
    for k in range(i - 1, -1, -1):
        if alignments[k].anchored or alignments[k].score >= SELF_SUPPORT:
            lo = alignments[k].source_index
            break
    else:
        lo = alignments[0].source_index
    for k in range(i + 1, len(alignments)):
        if alignments[k].anchored or alignments[k].score >= SELF_SUPPORT:
            hi = alignments[k].source_index
            break
    else:
        hi = alignments[-1].source_index
    return (min(lo, alignments[i].source_index), max(hi, alignments[i].source_index))
