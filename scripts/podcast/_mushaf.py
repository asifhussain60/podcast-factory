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

# Skeleton floor. 10 letters is about three short words -- `ليس كمثله شيء`
# (Q 42:11) is ELEVEN, so a floor of 12 silently rejected one of the most
# frequently quoted phrases in the corpus. Below ~10 a hit is coincidence.
_MIN_SKELETON = 10


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


def mushaf_available() -> bool:
    return bool(_mushaf_haystack())


def is_quranic(span: str) -> bool:
    """True when ``span``'s skeleton appears in the canonical mushaf.

    Substring, not equality: a book quotes a clause of an ayah far more often
    than a whole one. The ``_MIN_SKELETON`` floor keeps a two-word fragment from
    matching by accident somewhere in 6,236 verses.
    """
    skeleton = normalize_arabic(span or "")
    if len(skeleton) < _MIN_SKELETON:
        return False
    haystack = _mushaf_haystack()
    return bool(haystack) and skeleton in haystack
