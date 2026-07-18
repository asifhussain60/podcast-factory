"""Atom schemas for the knowledge library.

Wave 1: Quran + hadith atoms. Wave B adds doctrine atoms (Kashkole).
Waves 2/3 will add quotes, etymology, definitions.

Authority: `_workspace/plan/architecture.md` (Intelligence Layer section)
           and `_workspace/plan/refactor/plan.md` (Wave B).
"""

from __future__ import annotations

import hashlib
from typing import Literal, TypedDict

# ─── Common envelope (every atom) ─────────────────────────────────────────


class AtomSource(TypedDict):
    book: str
    chapter: str
    locator: str  # heading text or paragraph number


class AtomFirstSeen(TypedDict):
    book: str
    chapter: str
    date: str  # ISO8601


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
    "bukhari",
    "muslim",
    "tirmidhi",
    "abu-dawud",
    "nasai",
    "ibn-majah",
    "other",
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

AtomType = Literal["quran", "hadith", "doctrine", "quote", "term"]  # quote/term added Wave K


class Atom(TypedDict, total=False):
    id: str  # "<type>:<canonical-id>"
    type: AtomType
    first_seen: AtomFirstSeen
    sources: list[AtomSource]
    variants: list[dict]
    body: dict  # QuranBody | HadithBody | DoctrineBody (validated at runtime)


# ─── Doctrine body (Wave B — Kashkole) ───────────────────────────────────

DoctrineGenre = Literal["theological", "ethical", "ritual", "historical", "other"]


class DoctrineBody(TypedDict, total=False):
    text_en: str
    genre: DoctrineGenre
    binder_slug: str
    chapter_slug: str
    chunk_index: int
    quran_refs: list[str]  # e.g. ["2:255", "3:7"]


# ─── Quote body (Wave K) ──────────────────────────────────────────────────


class QuoteBody(TypedDict, total=False):
    speaker: str  # e.g. "Imam Ali", "Imam al-Ghazali", "The Prophet"
    text_en: str  # verbatim English text of the attributed saying
    source: str  # book/chapter origin within the corpus


# ─── Term body (Wave K) ───────────────────────────────────────────────────


class TermBody(TypedDict, total=False):
    term: str  # normalized term name (lowercase transliteration)
    text_en: str  # English definition or context sentence
    arabic: str  # Arabic script (optional)
    source: str  # "doctrine" | "kqur" | etc.


# ─── Canonical id helpers ─────────────────────────────────────────────────


def quran_canonical_id(surah: int, ayah: int) -> str:
    """Return `quran:<surah>:<ayah>`. Validates ranges."""
    if not (1 <= surah <= 114):
        raise ValueError(f"Surah out of range 1–114: {surah}")
    if not (1 <= ayah <= 286):
        raise ValueError(f"Ayah out of range: {ayah}")
    return f"quran:{surah}:{ayah}"


def hadith_canonical_id(collection: HadithCollection, number: int) -> str:
    """Return `hadith:<collection>:<number>`. Falls back to sha256 for `other`."""
    if collection == "other":
        digest = hashlib.sha256(f"hadith:other:{number}".encode()).hexdigest()[:12]
        return f"hadith:other:{digest}"
    return f"hadith:{collection}:{number}"


def doctrine_canonical_id(binder_id: str, chapter_id: str, chunk_index: int) -> str:
    """Return `doctrine:wisdom:<binder_id>:<chapter_id>:<chunk_index>`."""
    return f"doctrine:wisdom:{binder_id}:{chapter_id}:{chunk_index}"


def quote_canonical_id(speaker: str, text_en: str) -> str:
    """Return `quote:<speaker-slug>:<sha256[:10]>`. Stable for the same speaker+text."""
    speaker_slug = speaker.lower().replace(" ", "-").replace("'", "")
    digest = hashlib.sha256(f"{speaker}:{text_en}".encode()).hexdigest()[:10]
    return f"quote:{speaker_slug}:{digest}"


def term_canonical_id(term: str) -> str:
    """Return `term:doctrine:<normalized-term>`. Deduplicates on term name."""
    normalized = term.lower().strip().replace(" ", "-").replace("ʿ", "").replace("ʾ", "")
    return f"term:doctrine:{normalized}"


# ─── Validation ───────────────────────────────────────────────────────────

_REQUIRED_QURAN = {"surah", "ayah"}
_REQUIRED_HADITH = {"collection", "text_en"}
_REQUIRED_DOCTRINE = {"text_en"}
_REQUIRED_QUOTE = {"speaker", "text_en"}
_REQUIRED_TERM = {"term", "text_en"}

_KNOWN_TYPES = {"quran", "hadith", "doctrine", "quote", "term"}


def validate_atom(atom: dict) -> None:
    """Raise ValueError if the atom doesn't conform to the schema for its type."""
    atom_type = atom.get("type")
    if atom_type not in _KNOWN_TYPES:
        raise ValueError(f"Unknown atom type: {atom_type!r}")
    atom_id = atom.get("id", "")
    if not atom_id.startswith(f"{atom_type}:"):
        raise ValueError(f"Atom id {atom_id!r} does not start with '{atom_type}:'")
    body = atom.get("body", {})
    if atom_type == "quran":
        missing = _REQUIRED_QURAN - set(body)
        if missing:
            raise ValueError(f"Quran atom missing body fields: {missing}")
    elif atom_type == "hadith":
        missing = _REQUIRED_HADITH - set(body)
        if missing:
            raise ValueError(f"Hadith atom missing body fields: {missing}")
    elif atom_type == "doctrine":
        missing = _REQUIRED_DOCTRINE - set(body)
        if missing:
            raise ValueError(f"Doctrine atom missing body fields: {missing}")
    elif atom_type == "quote":
        missing = _REQUIRED_QUOTE - set(body)
        if missing:
            raise ValueError(f"Quote atom missing body fields: {missing}")
    elif atom_type == "term":
        missing = _REQUIRED_TERM - set(body)
        if missing:
            raise ValueError(f"Term atom missing body fields: {missing}")
