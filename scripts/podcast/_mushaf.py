"""_mushaf.py — canonical Quran lookup for Arabic provenance checks.

The corpus was already in the repo and simply never wired to verification:
``content/knowledge-base/mirror.db`` carries all 6,236 ayat as fully-vowelled
Uthmani text in ``fts_quran`` (tracked in git, ~30 MB, so it is present on every
checkout). ``source_library_mirror.quran_ayat_lookup`` reads single verses from
it for the compose-time anchor block; nothing verified AGAINST it.

Why that matters (2026-07-20): a run reached the printed edition fully vowelled
while the scan carried it bare. Three attempts at a scan-grounded guard were
abandoned because the review list came back dominated by canonical Quran, which
is LEGITIMATELY vowelled — and the checks had no way to tell canonical from
fabricated. This module is that missing discriminator, so the guard becomes
possible:

  * a span that IS canonical Quran may carry vowels the scan lacks;
  * a span that is NOT canonical Quran must match the scan's own vowelling.

Degrades silently: if the mirror is absent, ``is_quranic`` returns False for
everything, which makes callers MORE conservative (more spans flagged for review)
rather than silently passing.
"""

from __future__ import annotations

from functools import lru_cache

from _arabic_coverage import normalize_arabic

# Skeleton floor for the UNALIGNED path. 10 letters is about three short words --
# `ليس كمثله شيء` (Q 42:11) is ELEVEN, so a floor of 12 silently rejected one of
# the most frequently quoted phrases in the corpus. Below ~10 a hit is coincidence.
_MIN_SKELETON = 10

# Floor for the WORD-ALIGNED path, which can go far lower because alignment, not
# length, is what rules out coincidence: the span must begin and end on ayah word
# boundaries, so `كن فيكون` (skeleton of 7) is checked as the two whole words it
# is rather than as a letter run that might land mid-word somewhere in 6,236
# verses. Without this, the single most-quoted formula in the corpus -- Q 2:117,
# 3:47, 16:40, 36:82 -- was reported as NON-canonical, which put it on the
# fabricated-vowelling review list: exactly the false positive this module exists
# to remove, and the reason three earlier guard attempts were abandoned.
_MIN_ALIGNED_SKELETON = 5


@lru_cache(maxsize=1)
def _mushaf_haystack() -> str:
    """Every ayah's consonantal skeleton, concatenated. Empty if unavailable."""
    try:
        from source_library_mirror import open_mirror
    except Exception:
        return ""
    conn = open_mirror()
    if conn is None:
        return ""
    try:
        rows = conn.execute("SELECT arabic FROM fts_quran").fetchall()
    except Exception:
        return ""
    finally:
        conn.close()
    return "\n".join(normalize_arabic(r[0] or "") for r in rows)


def _defective(skeleton: str) -> str:
    """Fold Uthmani alif-hazf away by dropping every alif.

    The mushaf writes many long /aa/ vowels without the alif that modern imla'i
    spelling supplies: Q 1:2 is stored `ٱلْعَلَمِينَ`, skeleton `العلمين`, while a
    modern typesetter -- or a model -- produces `العالمين`. As plain strings those
    never match, so the opening chapter of the Quran failed the check.

    Dropping alif ENTIRELY, on both sides, is deliberate: it collapses the two
    orthographies onto one form without needing to know which words are affected.
    Alif is common enough that this alone would be too loose, which is why it is
    only ever used on the word-aligned path -- the boundary requirement is what
    keeps the looser comparison honest.
    """
    return skeleton.replace("ا", "")


@lru_cache(maxsize=1)
def _mushaf_word_haystack() -> str:
    """Every ayah as space-delimited defective skeletons, one verse per line.

    ``normalize_arabic`` strips spaces, so the plain haystack cannot express
    "this is a whole word". This one normalizes word by word and pads each verse
    with spaces, which makes ` needle ` a boundary-anchored search. Verses are
    newline-separated and a needle never contains a newline, so a match can never
    straddle two ayat.
    """
    try:
        from source_library_mirror import open_mirror
    except Exception:
        return ""
    conn = open_mirror()
    if conn is None:
        return ""
    try:
        rows = conn.execute("SELECT arabic FROM fts_quran").fetchall()
    except Exception:
        return ""
    finally:
        conn.close()
    lines = []
    for row in rows:
        words = [_defective(normalize_arabic(w)) for w in (row[0] or "").split()]
        words = [w for w in words if w]
        if words:
            lines.append(" " + " ".join(words) + " ")
    return "\n".join(lines)


def mushaf_available() -> bool:
    return bool(_mushaf_haystack())


def is_quranic(span: str) -> bool:
    """True when ``span`` appears in the canonical mushaf.

    Two independent paths, and either one is enough. The first is a plain
    substring of the consonantal skeleton -- a book quotes a clause of an ayah far
    more often than a whole one, so this is substring rather than equality, and
    the ``_MIN_SKELETON`` floor keeps a two-word fragment from matching by
    accident somewhere in 6,236 verses. The second requires the span to align to
    ayah word boundaries and compares defective skeletons, which recognises both
    short formulas and Uthmani spelling that the first path cannot see.

    The paths are ORed rather than replaced so the change is strictly additive:
    nothing the old check accepted can start being rejected.
    """
    skeleton = normalize_arabic(span or "")
    if not skeleton:
        return False

    if len(skeleton) >= _MIN_SKELETON:
        haystack = _mushaf_haystack()
        if haystack and skeleton in haystack:
            return True
        # Same test on the defective form, which folds Uthmani spelling away AND
        # is immune to word-segmentation differences -- the mushaf sets Q 7:26 as
        # `يَٰبَنِىٓ ءَادَمَ`, one word where modern text has two, so the aligned path
        # below cannot see it. At this length, length alone rules out coincidence,
        # which is the premise the original substring check was already built on.
        if haystack and _defective(skeleton) in _defective(haystack):
            return True

    if len(skeleton) < _MIN_ALIGNED_SKELETON:
        return False
    words = [_defective(normalize_arabic(w)) for w in (span or "").split()]
    words = [w for w in words if w]
    if not words:
        return False
    # A ONE-word span carries no internal alignment evidence -- only the two ends,
    # which every word in the mushaf satisfies trivially. Short common words then
    # match by coincidence: `بلغنا`, this book's own transmitter formula and the
    # thing its whole narrative frame rests on, resolved as scripture on a
    # four-letter defective skeleton. Require a longer word before believing a
    # lone one, which still admits `فَيَكُونُ` -- the case that matters, since the
    # book sets it as a run of its own.
    if len(words) == 1 and len(_defective(skeleton)) < _MIN_ALIGNED_SKELETON:
        return False

    word_haystack = _mushaf_word_haystack()
    if not word_haystack:
        return False
    if " " + " ".join(words) + " " in word_haystack:
        return True

    # A quotation very often picks up a connective the mushaf does not carry:
    # the book sets `فَسُبْحَانَ الَّذِي خَلَقَ` where Q 36:36 reads `سُبْحَانَ الَّذِي خَلَقَ`.
    # That single proclitic letter breaks alignment on the first word and nothing
    # else, so retry once without it. Everything after it must still align, which
    # is what keeps this from loosening the check in any other direction.
    if words[0][:1] in ("و", "ف") and len(words[0]) > 1:
        retry = [words[0][1:]] + words[1:]
        if " " + " ".join(retry) + " " in word_haystack:
            return True
    return False
