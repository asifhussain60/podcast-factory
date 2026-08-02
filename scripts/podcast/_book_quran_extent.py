"""_book_quran_extent.py — WHICH canonical words a passage quotes.

Split out of ``_book_quran.py`` on 2026-08-01 under the DR-005 line-count gate,
along the seam the module already had: this half answers *what verse is this, and
how much of it does the book quote*; ``_book_quran`` answers *where on the page
does it go*. Nothing here reads or writes `book.md`, and nothing here knows what a
blockquote is — it is pure resolution over a citation, the OCR scan, and the
canonical mushaf.

The reasoning behind the two-source design (extent from the scan, letters from the
mirror), the fuzzy alignment and why it is safe, and the two-signal rule for
uncited quotations are all written out in ``_book_quran``'s module docstring. Read
that first; this file is its machinery.
"""

from __future__ import annotations

import bisect
import difflib
import re
import sys
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _book_citations import find_citations  # noqa: E402,F401  (re-exported for callers)
from _mushaf import normalize_arabic  # noqa: E402
from source_library_mirror import quran_ayat_lookup  # noqa: E402

# Arabic, Arabic-Supplement, Extended-A, presentation forms. Same class the rest
# of the pipeline uses (`restore_arabic._ARABIC_RE`, `book-html.mjs ARABIC_RE`).
ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")

# The ornate brackets a scholarly Arabic text puts around scripture and nothing
# else. That is what makes them usable as the second signal: they are the source
# ITSELF saying "this is Qur'an", not our inference about it. U+FD3F is the
# ORNATE LEFT PARENTHESIS, which in an RTL run OPENS the quotation.
_ORNATE_OPEN, _ORNATE_CLOSE = "﴿", "﴾"

# What a citation looks like — numeric AND in the house `(Al-Baqarah: 24)` form —
# is owned by `_book_citations`, which also does the renaming. The two belong
# together: a rename its own pipeline cannot read back is a one-way door.

# Ayah counts per surah — the cheap half of validating a reference. `(2:282)` is a
# verse; `(3:400)` is not, and neither is `(0:1)`. Without this the parser would
# happily look up nonsense and quietly find nothing, which reads as "no Arabic
# available" rather than "that was never a citation".
SURAH_AYAH_COUNTS = (
    7,
    286,
    200,
    176,
    120,
    165,
    206,
    75,
    129,
    109,
    123,
    111,
    43,
    52,
    99,
    128,
    111,
    110,
    98,
    135,
    112,
    78,
    118,
    64,
    77,
    227,
    93,
    88,
    69,
    60,
    34,
    30,
    73,
    54,
    45,
    83,
    182,
    88,
    75,
    85,
    54,
    53,
    89,
    59,
    37,
    35,
    38,
    29,
    18,
    45,
    60,
    49,
    62,
    55,
    78,
    96,
    29,
    22,
    24,
    13,
    14,
    11,
    11,
    18,
    12,
    12,
    30,
    52,
    52,
    44,
    28,
    28,
    20,
    56,
    40,
    31,
    50,
    40,
    46,
    42,
    29,
    19,
    36,
    25,
    22,
    17,
    19,
    26,
    30,
    20,
    15,
    21,
    11,
    8,
    8,
    19,
    5,
    8,
    8,
    11,
    11,
    8,
    3,
    9,
    5,
    4,
    7,
    3,
    6,
    3,
    5,
    4,
    5,
    6,
)

# A word matches when its normalized skeletons are this similar. 0.72 was chosen
# against this book's 44 spans: it carries `إِنْرَاهِيمَ`→`إِبْرَاهِيمَ` (one letter
# wrong in eight) while refusing to pair short function words with each other.
_WORD_SIM = 0.72
# A span must be this much *itself* the verse before it is accepted as that
# verse's quotation — aligned words over the span's own length. Precision, not
# recall: a long span that happens to share `الله` with the ayah scores low, which
# is the point.
_SPAN_PRECISION = 0.6
# and this many words, so a two-word coincidence is never an extent.
_MIN_ALIGNED_WORDS = 3
# Consecutive matches may skip this many ayah words and still count as the same
# quotation — enough to ride over what OCR drops, short enough that a coincidence
# across a long verse starts a new segment instead of widening this one.
_AYAH_GAP_SLACK = 6
# The claimed extent must be this well evidenced: aligned words over the WIDTH of
# the window they span. Claiming the book quotes 98 words of Q 2:282 on the
# strength of 3 matches is not a reading of the source, it is a guess with a
# citation attached — and the Arabic that guess puts on the page would say things
# the English beside it does not.
_MIN_EXTENT_SUPPORT = 0.4
# The word-stream fallback has no bracket vouching for it, so it carries two extra
# burdens: more matched words, and a real share of the verse. Q 6:149 is nowhere in
# this book's scan, and three common words in unrelated prose were enough to look
# like it until these applied.
_STREAM_MIN_ALIGNED = 4
_STREAM_MIN_AYAH_SHARE = 0.5
# Share of a passage's content words that the translation must also carry before
# it even counts as the first of the two signals.
#
# LOW ON PURPOSE, and only safe because it is one of two. The book renders its own
# translation: against Pickthall, its Q 9:103 shares four content words of eleven —
# 0.36 — and is unmistakably the same verse. A threshold strict enough to call that
# a match on the English alone would be far too strict to find anything, and a
# threshold loose enough to find it would, on its own, also "find" the discussion
# of Malik on divorce that this book's L398 proposes as Q 65:6. Neither is a
# problem here because a proposal is not a decision: the scan has to name the same
# verse independently before a single character is written.
_EN_SIM = 0.33
# Words too common to identify a verse. Scripture in translation is dense with
# `god`, `lord`, `unto` and `they`, so leaving them in lets any two verses look
# alike and the containment score stops discriminating.
_STOPWORDS = frozenset(
    """the and for that with them they their you your our his her its who whom
    which what when where this these those from into unto upon out off not nor
    but are was were will shall have has had been being does did done any all
    such than then there here about above after before among against
    god lord allah say said says one two indeed only own may might must can
    should would could""".split()
)


def _key(word: str) -> str:
    return normalize_arabic(word)


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _arabic_ratio(text: str) -> float:
    """Share of ``text``'s word-forming characters that are Arabic script.

    Distinguishes an Arabic verse line from an English sentence carrying an
    inline honorific. The book's prose is full of the latter — `the imams
    (عَلَيْهِمُ السَّلَامُ)` — so "contains Arabic" is useless as a test and
    "is mostly Arabic" is the one that works.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if ARABIC_RE.match(c)) / len(letters)


def _longest_increasing(pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """The longest run of ``(span_idx, ayah_idx)`` with ayah_idx strictly rising.

    Word-level similarity alone will pair a common word (`الله`, `من`) with
    whichever occurrence it hit first, which can be at the far end of the ayah and
    would stretch the extent across most of the verse. Requiring the kept matches
    to advance through the ayah in the same order they appear in the quotation
    discards those, because a quotation reads forwards.
    """
    if not pairs:
        return []
    tails: list[int] = []
    tail_idx: list[int] = []
    back: list[int] = []
    for n, (_span_i, ayah_i) in enumerate(pairs):
        i = bisect.bisect_left(tails, ayah_i)
        if i == len(tails):
            tails.append(ayah_i)
            tail_idx.append(n)
        else:
            tails[i] = ayah_i
            tail_idx[i] = n
        back.append(tail_idx[i - 1] if i else -1)
    out: list[tuple[int, int]] = []
    cur = tail_idx[len(tails) - 1]
    while cur != -1:
        out.append(pairs[cur])
        cur = back[cur]
    return out[::-1]


def _align(span_words: list[str], ayah_keys: list[str]) -> tuple[int, int, int, float]:
    """How ``span_words`` maps onto the ayah: ``(lo, hi_exclusive, n, precision)``.

    ``lo``/``hi`` index the AYAH — the window the quotation covers. ``n`` is how
    many words were placed. ``(0, 0, 0, 0.0)`` when none were.

    PRECISION IS MEASURED OVER THE MATCHED SUB-RUN, not over the whole input, and
    that distinction is what makes the scan usable. This book's scan has 45 open
    ornate brackets against 44 closes, so one extracted "span" runs from a verse
    straight through the critical-apparatus footnotes beneath it
    (`١ جائزاً: جائز، ت، ث.`). Scored against its full length that span looked like
    15% verse and was rejected — taking Q 17:77 with it, even though the verse sits
    intact at its head. Scored between the first and last word that actually
    aligned, the footnotes fall outside the measurement and the verse is found.
    The same change is what lets a plain word-stream window be scored at all,
    since such a window has no meaningful "own length".
    """
    # EVERY plausible position for each word, not just its best one. A verse
    # repeats its common words — Q 2:282 has `وَلَا` at ayah word 16 and again at
    # 78 — and picking the highest-scoring match in isolation sends the word to
    # whichever occurrence it met first. Six of that quotation's twelve words
    # landed on earlier duplicates, the chain through them broke, and the span
    # scored below threshold and was thrown away.
    #
    # Sorting candidates by span position ascending and, WITHIN one span word, by
    # ayah position descending is what lets a plain increasing-subsequence pass
    # choose among them: two candidates of the same word can never both be kept,
    # because they descend, so the chain that survives has picked at most one
    # position per word — and it picks the one the surrounding words agree with.
    pairs: list[tuple[int, int]] = []
    for si, w in enumerate(span_words):
        cands = [ai for ai, c in enumerate(ayah_keys) if _sim(w, c) >= _WORD_SIM]
        pairs.extend((si, ai) for ai in sorted(cands, reverse=True))
    kept = _longest_increasing(pairs)
    if not kept:
        return (0, 0, 0, 0.0)

    # Break the chain wherever it JUMPS, and keep the densest piece. Rising order
    # is not enough on its own: one common word (`أَن`, `مِن`) matching early in a
    # long ayah still rises, so it survives the LIS and drags the window back to
    # its own position. On Q 2:282 that turned a 12-word quotation into a claimed
    # 98-word one — the seven real matches sat at ayah words 72-83 and a single
    # stray at word 19 set the start. A quotation is contiguous in its source, so a
    # gap this large is evidence of a coincidence rather than of a skipped word;
    # _AYAH_GAP_SLACK stays generous enough to ride over the words OCR drops.
    segments: list[list[tuple[int, int]]] = [[kept[0]]]
    for prev, cur in zip(kept, kept[1:]):
        if cur[1] - prev[1] > _AYAH_GAP_SLACK:
            segments.append([cur])
        else:
            segments[-1].append(cur)
    seg = max(segments, key=lambda s: (len(s), s[-1][1] - s[0][1]))

    run = seg[-1][0] - seg[0][0] + 1
    return (seg[0][1], seg[-1][1] + 1, len(seg), len(seg) / run)


def ornate_spans(ocr_text: str) -> list[str]:
    """Every ornate-bracketed run in the scan, whitespace-flattened.

    Tolerant of the unbalanced bracket OCR leaves behind (this book's scan has 45
    opens against 44 closes): a run is taken up to the next close mark, and a
    trailing unclosed one is ignored rather than swallowing the rest of the file.
    """
    out: list[str] = []
    for chunk in ocr_text.split(_ORNATE_OPEN)[1:]:
        if _ORNATE_CLOSE not in chunk:
            continue
        body = chunk.split(_ORNATE_CLOSE, 1)[0]
        flat = " ".join(body.split())
        if flat:
            out.append(flat)
    return out


def arabic_word_stream(ocr_text: str) -> list[str]:
    """Every Arabic word in the scan, in order — the fallback search space.

    Used when no ornate span resolves. The brackets are the better signal (the
    source itself marking scripture) but they are OCR output: this book's scan has
    an unbalanced pair, and a book scanned without ornate brackets at all would
    offer none. Falling back to the raw word stream means the pass degrades to
    "search the whole scan" rather than to "find nothing".
    """
    return [w for w in re.findall(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+", ocr_text) if _key(w)]


def _stream_windows(stream_keys: list[str], ayah_keys: list[str]) -> list[list[str]]:
    """Candidate sub-runs of the scan that might be this ayah.

    Anchored on EXACT normalized-key hits so the search stays linear: a fuzzy
    comparison of every scan word against every ayah word would be O(scan x ayah)
    per citation. Anchors only have to be good enough to propose a neighbourhood —
    the fuzzy alignment inside `_align` is what then decides, and it is the step
    allowed to be slow because it runs on a handful of short windows.
    """
    wanted = set(ayah_keys)
    anchors = [i for i, k in enumerate(stream_keys) if k in wanted]
    if not anchors:
        return []
    reach = max(8, len(ayah_keys) * 2)
    windows: list[list[str]] = []
    start = prev = anchors[0]
    for pos in anchors[1:]:
        if pos - prev > reach:
            windows.append(stream_keys[start : prev + 1])
            start = pos
        prev = pos
    windows.append(stream_keys[start : prev + 1])
    # A window covering half the scan is not a quotation; it is the whole book
    # sharing common words with the verse.
    return [w for w in windows if len(w) <= reach * 3]


def valid_reference(surah: int, ayah: int) -> bool:
    if not (1 <= surah <= 114):
        return False
    return 1 <= ayah <= SURAH_AYAH_COUNTS[surah - 1]


def canonical_words(surah: int, ayah: int, last: int | None = None) -> list[str] | None:
    """Canonical vowelled words for an ayah, or for an inclusive range of them.

    Returns ``None`` if ANY ayah in the range is missing from the mirror: a range
    silently short one verse would produce an extent that skips over text the book
    quotes, which is worse than reporting the whole citation as uncovered.
    """
    words: list[str] = []
    for n in range(ayah, (last or ayah) + 1):
        rec = quran_ayat_lookup(surah, n)
        if not rec:
            return None
        text = (rec["arabic"] if isinstance(rec, dict) else rec[2]) or ""
        # The mirror stores some ayat behind a leading bidi mark (U+200E / U+200F).
        # It renders as nothing and means nothing in an already-RTL run, but it is
        # an invisible character that would land in book.md. `mushaf_vocalisation`
        # strips it at its own exit; `quran_ayat_lookup` does not, so it comes off
        # here.
        words.extend(text.strip("‎‏").split())
    return words or None


def verse_extent(
    surah: int,
    ayah: int,
    spans: Iterable[str],
    last: int | None = None,
    stream_keys: list[str] | None = None,
) -> tuple[str | None, dict]:
    """Canonical Arabic for the clause the scan quotes, plus why.

    Returns ``(arabic_or_None, detail)``. ``detail`` always records the reason, so
    an uncovered verse says WHY it is uncovered rather than merely being absent.
    """
    canon = canonical_words(surah, ayah, last)
    if canon is None:
        return None, {"reason": "not-in-mirror"}
    ayah_keys = [_key(w) for w in canon]

    def _best(
        candidates: Iterable[list[str]], *, min_aligned: int, min_share: float
    ) -> tuple[int, float, int, int] | None:
        found = None
        for words in candidates:
            if not words:
                continue
            lo, hi, n, precision = _align(words, ayah_keys)
            if n < min_aligned or precision < _SPAN_PRECISION:
                continue
            if (hi - lo) and n / (hi - lo) < _MIN_EXTENT_SUPPORT:
                continue
            if n / len(ayah_keys) < min_share:
                continue
            cand = (n, precision, lo, hi)
            if found is None or cand[:2] > found[:2]:
                found = cand
        return found

    # Ornate spans first — the source marking its own scripture beats anything
    # inferred from a word stream.
    best = _best(
        ([k for k in (_key(w) for w in span.split()) if k] for span in spans),
        min_aligned=_MIN_ALIGNED_WORDS,
        min_share=0.0,
    )
    basis = "ocr-span"
    if best is None and stream_keys:
        best = _best(
            _stream_windows(stream_keys, ayah_keys),
            min_aligned=_STREAM_MIN_ALIGNED,
            min_share=_STREAM_MIN_AYAH_SHARE,
        )
        basis = "ocr-stream"

    if best is None:
        return None, {"reason": "no-span-in-scan", "ayah_words": len(canon)}

    n, precision, lo, hi = best
    return " ".join(canon[lo:hi]), {
        "reason": basis,
        "ayah_words": len(canon),
        "quoted_words": hi - lo,
        "aligned_words": n,
        "precision": round(precision, 3),
        "whole_ayah": lo == 0 and hi == len(canon),
    }


def _english_proposal(passage: str) -> tuple[tuple[int, int], float] | None:
    """Best (surah, ayah) for an English passage, from the mirror's translations.

    FTS5 narrows the 6,236 candidates; `ORDER BY rank` is load-bearing, not
    tidiness. An unranked `OR` query returns rows in rowid order, so a LIMIT lands
    on the opening of surah 2 every time and never reaches the verse being looked
    for — which is why this returned nothing for Q 9:103 while the mirror held it.

    Scoring is TOKEN CONTAINMENT, not character similarity. The book renders a
    verse in its own words and the mirror's Pickthall carries inline `<i>` markup,
    so a character-level ratio put an obvious match at 0.22 — the two texts say the
    same thing with different letters between the words. What actually identifies a
    verse is which content words it shares, and containment (rather than Jaccard)
    is the right direction because the quotation is usually a FRAGMENT: the verse
    may say much more without that making it a worse match.
    """
    from source_library_mirror import _strip_html, open_mirror

    def _tokens(s: str) -> set[str]:
        return {w for w in re.findall(r"[a-z']{3,}", _strip_html(str(s)).lower()) if w not in _STOPWORDS}

    want = _tokens(passage)
    if len(want) < 4:
        return None
    terms = [w for w in re.findall(r"[A-Za-z']{4,}", passage)][:12]
    if not terms:
        return None
    try:
        conn = open_mirror()
    except Exception:
        return None
    if conn is None:
        return None
    try:
        rows = conn.execute(
            "SELECT surah, ayat, pickthall, asad FROM fts_quran WHERE fts_quran MATCH ? ORDER BY rank LIMIT 40",
            (" OR ".join(terms),),
        ).fetchall()
    except Exception:
        return None
    finally:
        conn.close()

    best = None
    for surah, ayat, pickthall, asad in rows:
        for tr in (pickthall, asad):
            if not tr:
                continue
            score = len(want & _tokens(tr)) / len(want)
            if best is None or score > best[1]:
                best = ((int(surah), int(ayat)), score)
    if best and best[1] >= _EN_SIM:
        return best
    return None
