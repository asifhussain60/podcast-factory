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

# The WORD-ALIGNED path needs THREE words, and the reason is empirical. Alignment
# alone does not rule out coincidence, because the Quran is Arabic: over 2,000
# random two-word spans of this book's own non-Quranic prose, 17.4% aligned
# somewhere in the 6,236 verses -- `ثم قال`, `قال له`, `من غير`, `هو الذي`. Three
# words drops that to a rate dominated by the book's REAL citations.
#
# Distinctiveness was tried instead and rejected on measurement: `ثم قال` occurs
# in 1 verse and `كن فيكون` in 8, so "how many ayat contain this" ranks the
# connective as MORE distinctive than the citation. Match count cannot separate
# them; word count can.
#
# The cost is that `كن فيكون` and `فَيَكُونُ` no longer resolve as canonical. That
# is correct: a one- or two-word Arabic run carries too little evidence to call
# scripture, and the consumer that cared -- the fabricated-vowelling review --
# now declines to judge such runs at all rather than needing them excused. See
# `_narrative.ocr_vowelling_findings`.
_MIN_ALIGNED_WORDS = 3

# Floor for the defective-substring path. Much higher than the plain one because
# dropping every alif is a lossy comparison that also erases leading particles:
# at the plain floor it accepted `أَتُدْرِكُهُ الْأَبْصَارُ`, the book's INTERROGATIVE
# form, against Q 6:103's negation `لَا تُدْرِكُهُ` -- reading an affirmation as the
# verse that denies it. Only spans long enough that the folding cannot flip their
# sense are compared this way.
_MIN_DEFECTIVE_SKELETON = 18


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

    It is also LOSSY in a way that matters, because alif carries grammatical
    particles as well as long vowels. Folding it away turned the book's
    interrogative `أَتُدْرِكُهُ الْأَبْصَارُ` into a match for Q 6:103's negation
    `لَا تُدْرِكُهُ` — reading an affirmation as the verse that denies it. So each
    caller floors it: the word-aligned path requires three whole words, and the
    substring path requires `_MIN_DEFECTIVE_SKELETON` characters, which is long
    enough that no single folded particle can flip the sense of the match.
    (An earlier version of this docstring claimed folding was used only on the
    aligned path. It never was — the substring path used it too, unfloored.)
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

    Three paths, any one of which is enough, each with its own floor:

    1. Plain substring of the consonantal skeleton, floored at ``_MIN_SKELETON``.
       A book quotes a clause of an ayah far more often than a whole one, so this
       is substring rather than equality.
    2. The same substring on the DEFECTIVE form, floored much higher at
       ``_MIN_DEFECTIVE_SKELETON``. Folds Uthmani spelling and is immune to word
       segmentation -- the mushaf sets Q 7:26 as `يَٰبَنِىٓ ءَادَمَ`, one word where
       modern text has two, which no alignment can see.
    3. Word-ALIGNED against a space-preserving haystack, requiring
       ``_MIN_ALIGNED_WORDS`` whole words. Recognises verses the plain path misses
       on spelling, without letting a short common phrase through.

    Every floor here was set by measuring false positives against this book's own
    non-Quranic prose, not by intuition. The failure mode being defended against
    is asymmetric: a span wrongly called scripture is EXCUSED from the
    fabricated-vowelling check, so a false positive defeats the purpose of the
    module while a false negative merely costs a review-list entry.
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
        defective = _defective(skeleton)
        if len(defective) >= _MIN_DEFECTIVE_SKELETON and defective in _defective(haystack):
            return True

    words = [_defective(normalize_arabic(w)) for w in (span or "").split()]
    words = [w for w in words if w]
    if len(words) < _MIN_ALIGNED_WORDS:
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
