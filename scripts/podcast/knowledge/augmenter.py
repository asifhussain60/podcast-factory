"""Augmenter — query helper for future-book prompts.

# DEPRECATED — superseded by intelligence/augmenter.py (Wave B DB-backed).
# No production callers. Retained for reference only; delete in a future cleanup.

Wave-B baseline implementation:
- Scans chapter text for Quran/hadith citation patterns.
- Looks up matching atoms from the local JSONL knowledge library.
- Builds a bounded prior-treatment context block for prompt injection.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = REPO_ROOT / "content" / "knowledge-base"

QURAN_RE = re.compile(r"(?:\bQ(?:uran)?\s*)(\d+):(\d+)\b", re.IGNORECASE)
HADITH_RE = re.compile(
    r"\b(Bukhari|Muslim|Tirmidhi|Abu\s*Dawud|Nasai|Ibn\s*Majah)\s*(\d+)\b",
    re.IGNORECASE,
)

COLLECTION_MAP = {
    "bukhari": "bukhari",
    "muslim": "muslim",
    "tirmidhi": "tirmidhi",
    "abudawud": "abu-dawud",
    "nasai": "nasai",
    "ibnmajah": "ibn-majah",
}


def _iter_library_atoms(library_root: Path, atom_type: str) -> list[dict]:
    path = library_root / f"{atom_type}.jsonl"
    if not path.exists():
        return []

    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            atom = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(atom, dict):
            out.append(atom)
    return out


def _extract_citation_ids(chapter_text: str) -> tuple[list[str], dict[str, int]]:
    ids: list[str] = []
    counts: dict[str, int] = {}

    for surah, ayah in QURAN_RE.findall(chapter_text):
        atom_id = f"quran:{int(surah)}:{int(ayah)}"
        ids.append(atom_id)
        counts[atom_id] = counts.get(atom_id, 0) + 1

    for raw_collection, number in HADITH_RE.findall(chapter_text):
        key = re.sub(r"\s+", "", raw_collection.lower())
        collection = COLLECTION_MAP.get(key)
        if not collection:
            continue
        atom_id = f"hadith:{collection}:{int(number)}"
        ids.append(atom_id)
        counts[atom_id] = counts.get(atom_id, 0) + 1

    unique: list[str] = []
    seen: set[str] = set()
    for atom_id in ids:
        if atom_id in seen:
            continue
        seen.add(atom_id)
        unique.append(atom_id)
    return unique, counts


def _atom_text(atom: dict) -> str:
    body = atom.get("body")
    if isinstance(body, dict):
        val = body.get("text_en") or body.get("text") or ""
        return str(val).strip()
    return ""


def _is_self_only(atom: dict, book_slug: str) -> bool:
    sources = atom.get("sources")
    if not isinstance(sources, list) or not sources:
        return False
    seen_books = {
        str(src.get("book", "")).strip().lower()
        for src in sources
        if isinstance(src, dict)
    }
    seen_books.discard("")
    return bool(seen_books) and seen_books == {book_slug.lower()}


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip() + " ..."


def augment_for_chapter(
    book_slug: str,
    chapter_id: str,
    chapter_text: str,
    *,
    types: tuple[str, ...] = ("quran", "hadith"),
    max_atoms: int = 5,
    max_tokens: int = 800,
) -> str:
    """Return a prompt-ready string of prior atoms relevant to this chapter.

    Wave 1 selection: regex-scans `chapter_text` for canonical citations
    (e.g. "Quran 2:255", "Bukhari 1234"), looks them up in the library, returns
    formatted context. No semantic ranking.

    Default-disabled per spec §2.3: returns empty string immediately if the
    book's series-config has `enable_knowledge_augmenter` unset or false.
    Operator flips per-book during A/B rollout. Default flips only after the
    Gate I A/B acceptance check (spec §11.I) passes on at least one book pair.

    Args:
        book_slug: slug of the CURRENT book (excluded from "prior" treatments).
        chapter_id: chapter identifier (e.g. "ch01-prologue").
        chapter_text: raw chapter text to scan for citations.
        types: atom types to consider (Wave 1: only quran + hadith available).
        max_atoms: top-K cap (default 5 per R_KNOWLEDGE_AUGMENT_MAX_ATOMS).
        max_tokens: token-budget cap (default 800 per R_KNOWLEDGE_AUGMENT_MAX_TOKENS).

    Returns:
        Formatted prompt string per spec §6.2; empty string if no matches.
        Always returns within max_tokens budget (truncate cleanly at atom boundary).

    Implementation contract (per spec §2.3, §6):
        1. Load library shards for requested types.
        2. Regex-scan chapter_text using citation patterns from
           `_citation_patterns.py` (Wave 1 deliverable).
        3. Look up matched canonical IDs in the library.
        4. Filter out atoms whose only `source` is `book_slug` (no self-citation).
        5. Sort by citation-count desc; take top max_atoms.
        6. Format per spec §6.2 template.
        7. Truncate at atom boundary if total tokens > max_tokens.
    """
    library_root = KNOWLEDGE_ROOT
    citation_ids, citation_counts = _extract_citation_ids(chapter_text)
    if not citation_ids:
        return ""

    all_atoms: dict[str, dict] = {}
    for atom_type in types:
        for atom in _iter_library_atoms(library_root, atom_type):
            atom_id = str(atom.get("id", "")).strip()
            if atom_id:
                all_atoms[atom_id] = atom

    matched = []
    for atom_id in citation_ids:
        atom = all_atoms.get(atom_id)
        if not atom:
            continue
        if _is_self_only(atom, book_slug):
            continue
        txt = _atom_text(atom)
        if not txt:
            continue
        matched.append((atom_id, atom, citation_counts.get(atom_id, 0)))

    if not matched:
        return ""

    matched.sort(key=lambda row: (-row[2], row[0]))
    matched = matched[:max_atoms]

    # Simple budget approximation: 0.75 words/token.
    max_words = max(80, int(max_tokens * 0.75))
    used_words = 0
    lines = ["[PRIOR TREATMENT CONTEXT]"]

    for atom_id, atom, _score in matched:
        first_seen = atom.get("first_seen") if isinstance(atom.get("first_seen"), dict) else {}
        first_book = str(first_seen.get("book", "unknown")).strip() if isinstance(first_seen, dict) else "unknown"
        first_chapter = str(first_seen.get("chapter", "unknown")).strip() if isinstance(first_seen, dict) else "unknown"
        payload = f"- {atom_id} | source={first_book}/{first_chapter} | {_atom_text(atom)}"
        payload_words = len(payload.split())
        if used_words + payload_words > max_words:
            remaining = max_words - used_words
            if remaining < 12:
                break
            payload = _truncate_words(payload, remaining)
            payload_words = len(payload.split())
        lines.append(payload)
        used_words += payload_words

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def lookup_atom(atom_id: str, library_root: Path | None = None) -> dict | None:
    """Lookup a single atom by canonical id. Returns None if not in library."""
    if library_root is None:
        library_root = KNOWLEDGE_ROOT
    for atom_type in ("quran", "hadith"):
        for atom in _iter_library_atoms(library_root, atom_type):
            if str(atom.get("id", "")).strip() == atom_id:
                return atom
    return None
