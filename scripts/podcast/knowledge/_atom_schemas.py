"""Atom schemas for the knowledge library.

Wave 1: Quran + hadith only. Waves 2/3 add quotes, etymology, definitions.

Authority: `_workspace/plan/architecture.md` (Intelligence Layer section)
           and `_workspace/plan/refactor/plan.md` (Wave B).

Status (2026-05-25): scaffold only. Wave 1 implementation pending.
"""
from __future__ import annotations

from typing import Literal, TypedDict


# ─── Common envelope (every atom) ─────────────────────────────────────────

class AtomSource(TypedDict):
    book: str
    chapter: str
    locator: str   # heading text or paragraph number


class AtomFirstSeen(TypedDict):
    book: str
    chapter: str
    date: str   # ISO8601


# ─── Quran body (Wave 1) ──────────────────────────────────────────────────

class QuranBody(TypedDict, total=False):
    surah: int
    ayah: int
    text_ar: str
    text_en: str
    translator: str | None
    tafsir_refs: list[str]


# ─── Hadith body (Wave 1) ─────────────────────────────────────────────────

HadithCollection = Literal[
    "bukhari", "muslim", "tirmidhi", "abu-dawud",
    "nasai", "ibn-majah", "other",
]
HadithGrade = Literal["sahih", "hasan", "daif", "unknown"]


class HadithBody(TypedDict, total=False):
    collection: HadithCollection
    number: int
    grade: HadithGrade
    text_ar: str
    text_en: str
    chain: str | None
    narrator: str | None


# ─── Top-level atom envelope ──────────────────────────────────────────────

AtomType = Literal["quran", "hadith"]   # Wave 1 only; expand in Wave 2/3


class Atom(TypedDict, total=False):
    id: str                     # "<type>:<canonical-id>"
    type: AtomType
    first_seen: AtomFirstSeen
    sources: list[AtomSource]
    variants: list[dict]
    body: dict                  # QuranBody | HadithBody (validated at runtime)


# ─── Canonical id helpers ─────────────────────────────────────────────────

def quran_canonical_id(surah: int, ayah: int) -> str:
    """Return `quran:<surah>:<ayah>`. Validates ranges."""
    raise NotImplementedError("Wave 1 implementation pending.")


def hadith_canonical_id(collection: HadithCollection, number: int) -> str:
    """Return `hadith:<collection>:<number>`. Falls back to sha256 for `other`."""
    raise NotImplementedError("Wave 1 implementation pending.")


# ─── Validation ───────────────────────────────────────────────────────────

def validate_atom(atom: dict) -> None:
    """Raise ValueError if the atom doesn't conform to the schema for its type."""
    raise NotImplementedError("Wave 1 implementation pending.")
