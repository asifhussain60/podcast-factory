"""_book_citations.py — how a Qur'anic citation is WRITTEN in a reading edition.

Asif, 2026-08-01: "2:24 should be replaced by (Al-Baqarah: 24). This should be
done for all pdfs moving forward." A bare `(2:24)` is a lookup key, not a
reference: it asks a reader who does not read Arabic to know that surah 2 is
Al-Baqarah before the citation means anything. Every printed translation names
the surah, and so does this edition now.

ONE HOUSE FORM, `(Name: ayah)`. Every shape the corpus uses collapses onto it —
`(2:24)`, `(Quran 21:98)`, `(Qur'an, 35: 45)`, `(Q 53:39)`, `(Quran 14:24-26)` —
because once the surah is named the word "Quran" is saying nothing the name does
not already say. A range keeps both ends: `(Ibrahim: 24-26)`.

WHY THIS MODULE OWNS THE PATTERN. The numeric regex used to live in
`_book_quran_extent`, which reads citations to decide which verse to set in
Arabic. It lives here now with the names, because renaming and parsing are two
sides of one fact and splitting them is how a rename becomes unreadable to the
pass that has to read it back. `_book_quran_extent` imports from here.

IDEMPOTENCY IS THE WHOLE RISK, and it is why `find_citations` reads BOTH forms. A
composed book is re-composed: the Composer replay puts the renamed prose back, and
the Arabic-injection pass then has to recognise `(Al-Baqarah: 24)` as surah 2 ayah
24 or it would report a book with 23 cited verses as citing none, and quietly stop
maintaining their Arabic. A rename that its own pipeline cannot read is a one-way
door.

NAMES ARE PLAIN ASCII, per the house rule, and are the same 114 the site's
companion cards use (`plan-dashboard/src/lib/reader/companion/surah-names.ts`).
The two lists are pinned to one shared fixture rather than trusted to stay equal.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable, Iterator, NamedTuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Surah 1..114 by index+1. Plain ASCII romanization — no macrons, no dots — per
# the standing output rule, and byte-identical to the site's SURAH_NAMES.
SURAH_NAMES: tuple[str, ...] = (
    "Al-Fatihah",
    "Al-Baqarah",
    "Ali 'Imran",
    "An-Nisa",
    "Al-Ma'idah",
    "Al-An'am",
    "Al-A'raf",
    "Al-Anfal",
    "At-Tawbah",
    "Yunus",
    "Hud",
    "Yusuf",
    "Ar-Ra'd",
    "Ibrahim",
    "Al-Hijr",
    "An-Nahl",
    "Al-Isra",
    "Al-Kahf",
    "Maryam",
    "Ta-Ha",
    "Al-Anbiya",
    "Al-Hajj",
    "Al-Mu'minun",
    "An-Nur",
    "Al-Furqan",
    "Ash-Shu'ara",
    "An-Naml",
    "Al-Qasas",
    "Al-'Ankabut",
    "Ar-Rum",
    "Luqman",
    "As-Sajdah",
    "Al-Ahzab",
    "Saba",
    "Fatir",
    "Ya-Sin",
    "As-Saffat",
    "Sad",
    "Az-Zumar",
    "Ghafir",
    "Fussilat",
    "Ash-Shura",
    "Az-Zukhruf",
    "Ad-Dukhan",
    "Al-Jathiyah",
    "Al-Ahqaf",
    "Muhammad",
    "Al-Fath",
    "Al-Hujurat",
    "Qaf",
    "Adh-Dhariyat",
    "At-Tur",
    "An-Najm",
    "Al-Qamar",
    "Ar-Rahman",
    "Al-Waqi'ah",
    "Al-Hadid",
    "Al-Mujadila",
    "Al-Hashr",
    "Al-Mumtahanah",
    "As-Saff",
    "Al-Jumu'ah",
    "Al-Munafiqun",
    "At-Taghabun",
    "At-Talaq",
    "At-Tahrim",
    "Al-Mulk",
    "Al-Qalam",
    "Al-Haqqah",
    "Al-Ma'arij",
    "Nuh",
    "Al-Jinn",
    "Al-Muzzammil",
    "Al-Muddaththir",
    "Al-Qiyamah",
    "Al-Insan",
    "Al-Mursalat",
    "An-Naba",
    "An-Nazi'at",
    "'Abasa",
    "At-Takwir",
    "Al-Infitar",
    "Al-Mutaffifin",
    "Al-Inshiqaq",
    "Al-Buruj",
    "At-Tariq",
    "Al-A'la",
    "Al-Ghashiyah",
    "Al-Fajr",
    "Al-Balad",
    "Ash-Shams",
    "Al-Layl",
    "Ad-Duha",
    "Ash-Sharh",
    "At-Tin",
    "Al-'Alaq",
    "Al-Qadr",
    "Al-Bayyinah",
    "Az-Zalzalah",
    "Al-'Adiyat",
    "Al-Qari'ah",
    "At-Takathur",
    "Al-'Asr",
    "Al-Humazah",
    "Al-Fil",
    "Quraysh",
    "Al-Ma'un",
    "Al-Kawthar",
    "Al-Kafirun",
    "An-Nasr",
    "Al-Masad",
    "Al-Ikhlas",
    "Al-Falaq",
    "An-Nas",
)

# Every NUMERIC citation shape this corpus actually uses, and no more. Anchored on
# the opening parenthesis so a bare `5:13` in running prose — a page range, a
# ratio, a time — cannot match; that is the same hazard
# `_book_compose._QURAN_CITE_RE` guards with its narrower dot-form, recorded in
# its comment as `Q1.20` fiscal quarters. `Quran`/`Qur'an`/`Q`/`Surah` are
# optional because 5 of `degrees-of-excellence`'s 23 citations carry no word at
# all.
# A RANGE (`(Quran 14:24-26)`) is a third of that book's `(Quran …)` citations and
# means the book quotes consecutive ayat as one passage, so the Arabic is their
# concatenation sliced to the quoted extent — not the first verse alone.
CITE_RE = re.compile(
    r"\((?:\s*(?:Qur(?:['’ʾ]?)?an|Qur['’]ān|S[uū]rah?|Sura|Q)\.?\s*,?\s*)?"
    r"(\d{1,3})\s*:\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\s*\)"
)

# The house form, read back. Deliberately NOT a general "word: number" pattern —
# the captured text has to BE one of the 114 names or the match is discarded, so
# an ordinary parenthetical like `(see: 24)` can never be mistaken for scripture.
# The character class is what a romanized surah name is made of and nothing more.
_NAMED_CITE_RE = re.compile(r"\(\s*([A-Za-z'’\- ]{2,20})\s*:\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\s*\)")


def surah_name(n: int) -> str:
    """The surah's name, or "" when the number is outside 1..114."""
    return SURAH_NAMES[n - 1] if 1 <= n <= len(SURAH_NAMES) else ""


def _key(name: str) -> str:
    """Comparable form: letters only, lowercased — so "Al-Kahf", "al kahf" and
    "AlKahf" are one key. Mirrors the site's `key()` exactly."""
    return re.sub(r"[^a-z]", "", name.lower())


_BY_NAME: dict[str, int] = {_key(n): i + 1 for i, n in enumerate(SURAH_NAMES)}


def surah_number(name: str) -> int:
    """The number behind a written name, or 0 when it is not a surah name."""
    return _BY_NAME.get(_key(name), 0)


class Citation(NamedTuple):
    """One citation found in the text. ``last`` is None unless it is a range."""

    surah: int
    ayah: int
    last: int | None
    start: int
    end: int
    text: str


def find_citations(text: str) -> Iterator[Citation]:
    """Every Qur'anic citation in ``text``, numeric or named, in document order.

    Overlaps are impossible — the two patterns need different first characters
    after the parenthesis — so the two passes are simply merged and sorted.
    """
    found: list[Citation] = []
    for m in CITE_RE.finditer(text):
        found.append(
            Citation(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3)) if m.group(3) else None,
                m.start(),
                m.end(),
                m.group(0),
            )
        )
    for m in _NAMED_CITE_RE.finditer(text):
        n = surah_number(m.group(1))
        if not n:
            continue
        found.append(
            Citation(
                n,
                int(m.group(2)),
                int(m.group(3)) if m.group(3) else None,
                m.start(),
                m.end(),
                m.group(0),
            )
        )
    found.sort(key=lambda c: c.start)
    return iter(found)


def rename_citations(text: str) -> tuple[str, dict]:
    """Rewrite every numeric citation into the house form. Returns (text, stats).

    Idempotent: a citation already written `(Al-Baqarah: 24)` is matched by the
    named pattern, which this pass does not rewrite, so a second run changes
    nothing. A reference outside 1..114 is left exactly as the author wrote it and
    counted — the pass never invents a surah to name.
    """
    stats: dict = {"renamed": 0, "already_named": 0, "unnamed_reference": []}
    stats["already_named"] = sum(1 for m in _NAMED_CITE_RE.finditer(text) if surah_number(m.group(1)))

    def _sub(m: re.Match[str]) -> str:
        surah, ayah, last = int(m.group(1)), int(m.group(2)), m.group(3)
        name = surah_name(surah)
        if not name:
            stats["unnamed_reference"].append(m.group(0))
            return m.group(0)
        stats["renamed"] += 1
        return f"({name}: {ayah}" + (f"-{int(last)}" if last else "") + ")"

    return CITE_RE.sub(_sub, text), stats


def rename_book(book_dir: Path, *, log: Callable[[str], None] = print, dry_run: bool = False) -> dict:
    """Put every citation in `book/book.md` into the house form."""
    md = book_dir / "book" / "book.md"
    if not md.exists():
        log("citations: no book.md - skipped")
        return {"renamed": 0}

    before = md.read_text(encoding="utf-8")
    after, stats = rename_citations(before)
    if not dry_run and after != before:
        md.write_text(after, encoding="utf-8")

    log(
        f"citations: {stats['renamed']} numeric citation(s) given their surah name, "
        f"{stats['already_named']} already named"
    )
    for ref in stats["unnamed_reference"]:
        log(f"  left as written (no such surah): {ref}")
    return stats
