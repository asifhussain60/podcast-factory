#!/usr/bin/env python3
"""Cross-book phonetic Arabic pronunciation library.

The canonical, append-only store of VALIDATED Arabic pronunciations that the
pipeline reuses across every book. One JSON object per line at
``content/knowledge-base/pronunciations.jsonl`` (git-diffable, mergeable).

Trust model — the library holds only FINALIZED entries:
  - status="confirmed"  : heard in NotebookLM audio and pronounced correctly
                          with this phonetic. Safe to reuse verbatim.
  - status="unfixable"  : NotebookLM cannot pronounce this term no matter the
                          respelling. Consumers MUST substitute ``gloss``.

Unverified LLM candidates do NOT live here — they stay in a book's
``_phonetics.md`` until phase 0probe validates them by ear and promotes the
result into this library. That keeps the library high-trust: a lookup hit is a
pronunciation a human has actually heard come out correct.

Read side (phase 0c, framing authoring): ``lookup(term)`` / ``load()``.
Write side (phase 0probe applier): ``record(...)`` then ``save()``.

House style for the ``phonetic`` field (enforced by ``is_house_style``):
ALL lowercase, syllables hyphen-separated, the stressed syllable in CAPITALS,
no Arabic script, no spelled-out letters. e.g. al-Ghazali -> gha-zaa-lee.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path

# content/knowledge-base/pronunciations.jsonl — sibling to hadith.jsonl / quran.jsonl
_REPO_ROOT = Path(__file__).resolve().parents[3]
LIBRARY_PATH = _REPO_ROOT / "content" / "knowledge-base" / "pronunciations.jsonl"

VALID_STATUS = ("confirmed", "unfixable")


def normalize_key(term: str) -> str:
    """Diacritic- and case-insensitive lookup key.

    Strips combining marks (so ``al-Ghazālī`` and ``al-Ghazali`` collide),
    folds the Arabic hamza/ayn transliteration glyphs (ʿ ʾ ' ‘ ’) away,
    lowercases, and collapses whitespace. Preserves the ``al-`` article and
    internal hyphens — they are part of the term, not noise.
    """
    s = unicodedata.normalize("NFKD", term)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[ʿʾ'‘’`]", "", s)
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


# Markers that signal a NON-spoken form (IPA transcription) we must reject:
# slashes/brackets delimiters + IPA-only phonetic letters and suprasegmentals.
_IPA_MARKERS = re.compile(r"[/\[\]ˈˌːʔʕɣħʃʒθðɸβχŋɑɒɛɪʊəɜɔæ]")
_ARABIC_SCRIPT = re.compile(r"[؀-ۿݐ-ݿ]")


def is_house_style(phonetic: str) -> bool:
    """True if ``phonetic`` is a usable SPOKEN respelling (not IPA / not raw script).

    Deliberately permissive: a human-confirmed respelling is authoritative, so we
    accept any mix of latin letters, hyphens, spaces and the apostrophe (a common
    glottal-stop / ayn marker, e.g. ``bait al-ma'a-MOOR``). The house ideal is
    still lowercase-hyphen-syllables with CAPS stress, but we only REJECT input
    that is clearly the wrong KIND of string:
      - empty / whitespace
      - IPA (``/al ʔiˈmaːm.../`` — slashes, stress marks, IPA letters)
      - raw Arabic script or leftover transliteration diacritics (ā, ṣ, ...)
      - strings with no latin letter at all
    """
    if not phonetic or not phonetic.strip():
        return False
    s = phonetic.strip()
    if _IPA_MARKERS.search(s):
        return False
    if _ARABIC_SCRIPT.search(s):
        return False
    # Leftover combining diacritics (macrons/dots) mean a raw translit slipped in.
    if any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", s)):
        return False
    if not re.search(r"[A-Za-z]", s):
        return False
    return True


@dataclass
class PronEntry:
    key: str                                   # normalize_key(term)
    term: str                                  # plain display transliteration
    phonetic: str                              # house-style spoken form (the value)
    status: str = "confirmed"                  # confirmed | unfixable
    transliteration: str = ""                  # diacritic transliteration
    arabic_script: str = ""
    gloss: str = ""                            # English substitute (required if unfixable)
    mangled_variants: list[str] = field(default_factory=list)
    source_books: list[str] = field(default_factory=list)
    confirmed_date: str = ""                   # caller-stamped (scripts cannot call Date.now)
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class PronunciationLibrary:
    """In-memory view of the jsonl library, keyed by ``normalize_key``."""

    def __init__(self, entries: dict[str, PronEntry], path: Path):
        self._entries = entries
        self._path = path

    # ---- read side -------------------------------------------------------
    def lookup(self, term: str) -> PronEntry | None:
        return self._entries.get(normalize_key(term))

    def __contains__(self, term: str) -> bool:
        return normalize_key(term) in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def all(self) -> list[PronEntry]:
        return list(self._entries.values())

    # ---- write side ------------------------------------------------------
    def record(
        self,
        term: str,
        phonetic: str,
        *,
        status: str = "confirmed",
        transliteration: str = "",
        arabic_script: str = "",
        gloss: str = "",
        mangled_variants: list[str] | None = None,
        source_book: str = "",
        confirmed_date: str = "",
        notes: str = "",
    ) -> PronEntry:
        """Upsert an entry. Merges ``source_books`` and ``mangled_variants``.

        Raises ValueError on an invalid status, a non-house-style phonetic for a
        ``confirmed`` entry, or an ``unfixable`` entry missing its ``gloss``.
        """
        if status not in VALID_STATUS:
            raise ValueError(f"status must be one of {VALID_STATUS}, got {status!r}")
        if status == "confirmed" and not is_house_style(phonetic):
            raise ValueError(
                f"confirmed phonetic {phonetic!r} for {term!r} violates house style "
                "(expected lowercase hyphen-syllables, CAPS stress)"
            )
        if status == "unfixable" and not gloss.strip():
            raise ValueError(f"unfixable entry {term!r} requires a non-empty gloss substitute")

        key = normalize_key(term)
        existing = self._entries.get(key)
        new_variants = sorted({*(mangled_variants or []), *(existing.mangled_variants if existing else [])})
        new_books = sorted({*( [source_book] if source_book else [] ), *(existing.source_books if existing else [])})
        entry = PronEntry(
            key=key,
            term=term or (existing.term if existing else term),
            phonetic=phonetic,
            status=status,
            transliteration=transliteration or (existing.transliteration if existing else ""),
            arabic_script=arabic_script or (existing.arabic_script if existing else ""),
            gloss=gloss or (existing.gloss if existing else ""),
            mangled_variants=new_variants,
            source_books=new_books,
            confirmed_date=confirmed_date or (existing.confirmed_date if existing else ""),
            notes=notes or (existing.notes if existing else ""),
        )
        self._entries[key] = entry
        return entry

    def save(self) -> int:
        """Atomically rewrite the jsonl, sorted by key. Returns entry count."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = [self._entries[k].to_json() for k in sorted(self._entries)]
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        tmp.replace(self._path)
        return len(lines)


def load(path: Path | None = None) -> PronunciationLibrary:
    """Load the library. A missing file is an empty (not error) library."""
    p = path or LIBRARY_PATH
    entries: dict[str, PronEntry] = {}
    if p.exists():
        for ln, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"{p}:{ln}: malformed JSON line: {e}") from e
            obj.setdefault("key", normalize_key(obj.get("term", "")))
            known = PronEntry.__dataclass_fields__.keys()
            entry = PronEntry(**{k: v for k, v in obj.items() if k in known})
            entries[entry.key] = entry
    return PronunciationLibrary(entries, p)


if __name__ == "__main__":  # pragma: no cover - tiny CLI for inspection
    import sys
    lib = load()
    if len(sys.argv) > 1:
        hit = lib.lookup(sys.argv[1])
        print(hit.to_json() if hit else f"(miss) {sys.argv[1]!r}")
    else:
        print(f"{len(lib)} entries in {LIBRARY_PATH}")
        for e in lib.all():
            print(f"  [{e.status:9}] {e.term:30} -> {e.phonetic or '(gloss: '+e.gloss+')'}")
