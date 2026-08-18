"""_islamic_names.py — a curated, deterministic lexicon of proper names for the
glossary harvester.

THE GAP THIS CLOSES. `harvest_gloss_terms.py` finds new glossary candidates by
one method only: a term the SOURCE ITSELF glosses parenthetically in the
English prose — "the ranks (hudud)". That method structurally cannot find a
bare proper name, because a translator almost never glosses a well-known name
that way; the prose just writes "Ali" or "al-Husayn" directly. The result,
confirmed live on `sharh-al-masail-ghulam-hussain` (2026-08-18): a glossary
with thirteen fiqh terms and not one Ahl al-Bayt or Companion name, so
"al-Husayn ibn 'Ali" never carried Arabic script anywhere in the book, while
its own honorific "(ع)" sat right beside it in full script.

WHY A CURATED TABLE, not a general name-detection heuristic. This repo's
standing rule is canonical-provenance-first, never-fabricate-from-memory for
Arabic script — the corpus-fill pass in `fill_glossary_arabic.py` exists
precisely so a term's script comes from the Qur'anic morphology corpus or the
book's own OCR, never a model's recall. A short list of the household of the
Prophet and the best-known Companions carries the same certainty as a mushaf
lookup — these are among the most attested proper names in the entire Islamic
corpus — so hand-curating them here is the deterministic-provenance choice,
not a shortcut around it. This is NOT a general-purpose name lexicon and is
not meant to grow large; it exists to close the specific, recurring gap of
"a major named figure with no glossary entry at all".

Matched as a WHOLE TOKEN, case-sensitive on the capitalized form only (a
lowercase "ali" is an English word in some contexts and is never a false
positive worth risking), with an optional lowercase "al-"/"Al-" prefix
carried into the recorded phonetic so the harvest matches whatever the prose
actually wrote — exactly the existing harvester's own rule ("phonetic is the
form that actually appears in the prose").
"""

from __future__ import annotations

import re

#: root (capitalized, as it appears WITHOUT the definite article) -> canonical
#: Arabic script, unvowelled letters only (vowelling is a later, separate pass
#: — `vowel_glossary.py` — exactly as it is for every other glossary entry).
#: Deliberately short: the household of the Prophet and the Companions named
#: often enough in a scholarly fiqh/hadith text to need no per-book curation.
NAME_ROOTS: dict[str, str] = {
    "Muhammad": "محمد",
    "Ali": "علي",
    "Fatima": "فاطمة",
    "Hasan": "حسن",
    "Husayn": "حسين",
    "Hussain": "حسين",
    "Hussein": "حسين",
    "Jafar": "جعفر",
    "Ja'far": "جعفر",
    "Zaynab": "زينب",
    "Umm Kulthum": "أم كلثوم",
    "Abu Bakr": "أبو بكر",
    "Umar": "عمر",
    "Uthman": "عثمان",
    "Aisha": "عائشة",
    "A'isha": "عائشة",
    "Khadija": "خديجة",
    "Abu Talib": "أبو طالب",
    "Abbas": "عباس",
    "Zayd": "زيد",
    "Salman": "سلمان",
    "Ammar": "عمار",
    "Bilal": "بلال",
    "Ibrahim": "إبراهيم",
    "Ismail": "إسماعيل",
    "Isma'il": "إسماعيل",
    "Musa": "موسى",
    "Isa": "عيسى",
    "Maryam": "مريم",
    "Adam": "آدم",
    "Nuh": "نوح",
    "Yusuf": "يوسف",
    "Dawud": "داود",
    "Sulayman": "سليمان",
    "Zakariyya": "زكريا",
    "Yahya": "يحيى",
    "Yaqub": "يعقوب",
    "Ishaq": "إسحاق",
}

#: Longest-root-first, so "Abu Bakr"/"Umm Kulthum" (two tokens) claim their
#: span before a shorter single-token root inside a different name could.
_ROOTS_BY_LENGTH = sorted(NAME_ROOTS, key=len, reverse=True)

_AL_PREFIX = re.compile(r"^(al-|Al-)")


def _root_pattern(root: str) -> re.Pattern[str]:
    """Match ``root`` as a whole token, optionally preceded by ``al-``/``Al-``,
    never inside a longer word or a possessive."""
    return re.compile(rf"(?<![\w-])((?:al-|Al-)?{re.escape(root)})(?![\w'’-])")


def name_candidates(book_md: str) -> list[dict[str, object]]:
    """Every curated proper name found in ``book_md``, in the harvester's own
    candidate shape: ``{term, count, confidence, first_seen_snippet}``.

    ``term`` is recorded EXACTLY as the prose spells it (with or without
    ``al-``), matching how every other harvested term is anchored. Confidence
    is always "strong" — a curated match carries more certainty than the
    parenthetical-gloss heuristic ever claims for itself.
    """
    if not book_md:
        return []
    seen: dict[str, dict[str, object]] = {}
    claimed: list[tuple[int, int]] = []
    for root in _ROOTS_BY_LENGTH:
        pattern = _root_pattern(root)
        for m in pattern.finditer(book_md):
            if any(s < m.end() and m.start() < e for s, e in claimed):
                continue
            claimed.append((m.start(), m.end()))
            spelling = m.group(1)
            key = spelling.lower()
            hit = seen.get(key)
            if hit:
                hit["count"] = int(hit["count"]) + 1
                continue
            start = max(0, m.start() - 40)
            seen[key] = {
                "term": spelling,
                "count": 1,
                "confidence": "strong",
                "first_seen_snippet": book_md[start : m.end() + 10].strip(),
                "arabic_script": NAME_ROOTS[_AL_PREFIX.sub("", spelling)],
            }
    return sorted(seen.values(), key=lambda c: (-int(c["count"]), str(c["term"]).lower()))
