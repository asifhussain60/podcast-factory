#!/usr/bin/env python3
"""Cross-book phonetic-PATTERN layer — the second pronunciation brain.

The exact-term library (``pronunciation_ledger.py``) stops you re-correcting the
SAME word across books. This module stops you re-correcting the same KIND of
word: it turns a clean transliteration (the diacritic column of ``_phonetics.md``)
into a house-style *baseline spoken form* using tunable character/affix rules, so
an unseen term arrives PRE-FILLED with a suggested respelling you only confirm.

Two pieces:
  - char/affix RULES (seeded, stored in content/knowledge-base/pronunciation-patterns.jsonl)
    map recurring transliteration motifs (ʿayn, emphatics, qaf, digraphs, the
    ``al-`` article, ...) to how they are spoken. Seeded with a sane Arabic map;
    extensible as books teach new motifs.
  - a deterministic ``baseline_phonetic(translit)`` that applies the rules and
    syllabifies into the lowercase-hyphen house style (UNSTRESSED — the human
    adds CAPS stress when confirming; that is the one thing a rule can't infer).

Suggestion precedence (``suggest_phonetic``):
  1. exact-term library hit  -> authoritative (heard-correct)        [confidence=confirmed]
  2. baseline from patterns  -> a strong starting respelling          [confidence=baseline]

This is also the fix for IPA-contaminated _phonetics.md rows: their translit
column is clean, so the baseline regenerates a usable spoken form for them.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
PATTERNS_PATH = _REPO_ROOT / "content" / "knowledge-base" / "pronunciation-patterns.jsonl"

# ── seeded character / digraph / affix rules ────────────────────────────────
# Applied longest-motif-first over a lowercased transliteration. Spoken outputs
# use only plain ascii so they never re-trigger another motif. ʿayn/hamza drop
# to nothing (TTS cannot voice them and a dropped glottal reads cleaner than a
# hard 'g'); qaf -> k; emphatics -> their plain counterparts.
DEFAULT_CHAR_RULES: list[dict] = [
    # long vowels
    {"kind": "char", "motif": "ā", "spoken": "aa", "note": "long a"},
    {"kind": "char", "motif": "ī", "spoken": "ee", "note": "long i"},
    {"kind": "char", "motif": "ū", "spoken": "oo", "note": "long u"},
    {"kind": "char", "motif": "ē", "spoken": "ay", "note": "long e"},
    {"kind": "char", "motif": "ō", "spoken": "oh", "note": "long o"},
    # digraphs (identity, but pinned so single-letter rules can't split them)
    {"kind": "char", "motif": "kh", "spoken": "kh", "note": "khaa"},
    {"kind": "char", "motif": "gh", "spoken": "gh", "note": "ghayn"},
    {"kind": "char", "motif": "sh", "spoken": "sh", "note": "sheen"},
    {"kind": "char", "motif": "th", "spoken": "th", "note": "thaa"},
    {"kind": "char", "motif": "dh", "spoken": "dh", "note": "dhaal"},
    # emphatic / dotted consonants -> plain spoken counterpart
    {"kind": "char", "motif": "ṣ", "spoken": "s", "note": "saad"},
    {"kind": "char", "motif": "ḍ", "spoken": "d", "note": "daad"},
    {"kind": "char", "motif": "ṭ", "spoken": "t", "note": "taa (emphatic)"},
    {"kind": "char", "motif": "ẓ", "spoken": "z", "note": "zaa (emphatic)"},
    {"kind": "char", "motif": "ḥ", "spoken": "h", "note": "haa (emphatic)"},
    {"kind": "char", "motif": "ḫ", "spoken": "kh", "note": "khaa variant"},
    {"kind": "char", "motif": "ġ", "spoken": "gh", "note": "ghayn variant"},
    {"kind": "char", "motif": "ṯ", "spoken": "th", "note": "thaa variant"},
    {"kind": "char", "motif": "ḏ", "spoken": "dh", "note": "dhaal variant"},
    {"kind": "char", "motif": "š", "spoken": "sh", "note": "sheen variant"},
    {"kind": "char", "motif": "ḳ", "spoken": "k", "note": "qaf variant"},
    {"kind": "char", "motif": "q", "spoken": "k", "note": "qaf -> k (TTS-friendly)"},
    # glottals drop
    {"kind": "char", "motif": "ʿ", "spoken": "", "note": "ayn -> dropped"},
    {"kind": "char", "motif": "ʾ", "spoken": "", "note": "hamza -> dropped"},
    {"kind": "char", "motif": "'", "spoken": "", "note": "apostrophe glottal -> dropped"},
    {"kind": "char", "motif": "ʼ", "spoken": "", "note": "modifier apostrophe -> dropped"},
]

_VOWELS = set("aeiou")


@dataclass
class Suggestion:
    phonetic: str
    confidence: str  # confirmed | baseline | none
    source: str  # "library" | "patterns" | ""


def _strip_combining_keep_special(s: str) -> str:
    """Lowercase; drop combining marks NOT already covered by a motif rule.

    Motif rules consume the precomposed/diacritic glyphs (ā, ṣ, ʿ ...). Anything
    left after the rules that is still a combining mark is dropped so stray marks
    never leak into the spoken form.
    """
    out = []
    for ch in unicodedata.normalize("NFC", s):
        if unicodedata.combining(ch):
            continue
        out.append(ch)
    return "".join(out)


def _syllabify(token: str) -> str:
    """Insert house-style hyphens: split into ``[consonants][vowels]`` chunks.

    Unstressed by design. e.g. 'shareea' -> 'sha-ree-a', 'ghazaalee' ->
    'gha-zaa-lee'. Trailing consonants attach to the final chunk.
    """
    if not token:
        return token
    # Break a long vowel (aa/ee/oo/ay/oh) from a following vowel — they belong to
    # different syllables (e.g. sharee+a -> sha-ree-a, not sha-reea).
    token = re.sub(r"(aa|ee|oo|ay|oh)(?=[aeiou])", r"\1|", token)
    out_syls: list[str] = []
    for sub in token.split("|"):
        chunks = re.findall(r"[^aeiou]*[aeiou]+", sub)
        consumed = "".join(chunks)
        tail = sub[len(consumed) :]
        if not chunks:
            out_syls.append(sub)
            continue
        if tail:
            chunks[-1] += tail
        out_syls.extend(chunks)
    return "-".join(out_syls)


class PronunciationPatterns:
    def __init__(self, rules: list[dict], path: Path):
        # char rules sorted longest-motif-first for greedy, unambiguous application
        self._char_rules = sorted(
            [r for r in rules if r.get("kind") == "char"],
            key=lambda r: -len(r.get("motif", "")),
        )
        self._all = rules
        self._path = path

    def baseline_phonetic(self, translit: str) -> str:
        """Deterministic house-style baseline (lowercase, hyphenated, unstressed)."""
        if not translit or not translit.strip():
            return ""
        s = translit.strip().lower()
        for rule in self._char_rules:
            if rule["motif"]:
                s = s.replace(rule["motif"].lower(), rule["spoken"])
        s = _strip_combining_keep_special(s)
        # keep only spoken-safe chars: letters, space, hyphen
        s = re.sub(r"[^a-z \-]", "", s)
        # syllabify each space/hyphen separated token, preserving the separators
        parts = re.split(r"([ \-])", s)
        out = "".join(p if p in (" ", "-") else _syllabify(p) for p in parts)
        out = re.sub(r"-{2,}", "-", out).strip("-")
        return out

    def suggest(self, term: str, translit: str, library=None) -> Suggestion:
        """Best suggested phonetic: library hit first, else pattern baseline."""
        if library is not None:
            hit = library.lookup(term)
            if hit and hit.status == "confirmed" and hit.phonetic:
                return Suggestion(hit.phonetic, "confirmed", "library")
            if hit and hit.status == "unfixable":
                return Suggestion(hit.gloss, "confirmed", "library")
        base = self.baseline_phonetic(translit or term)
        return Suggestion(base, "baseline" if base else "none", "patterns" if base else "")

    def char_rules(self) -> list[dict]:
        return list(self._char_rules)

    def add_rule(self, rule: dict) -> None:
        rule.setdefault("kind", "char")
        self._all.append(rule)
        if rule["kind"] == "char":
            self._char_rules = sorted(
                [r for r in self._all if r.get("kind") == "char"],
                key=lambda r: -len(r.get("motif", "")),
            )

    def save(self) -> int:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in self._all]
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        tmp.replace(self._path)
        return len(lines)


def load(path: Path | None = None) -> PronunciationPatterns:
    """Load patterns. A missing file is seeded with DEFAULT_CHAR_RULES."""
    p = path or PATTERNS_PATH
    if not p.exists():
        store = PronunciationPatterns(list(DEFAULT_CHAR_RULES), p)
        store.save()
        return store
    rules: list[dict] = []
    for ln, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rules.append(json.loads(raw))
        except json.JSONDecodeError as e:
            raise ValueError(f"{p}:{ln}: malformed JSON line: {e}") from e
    return PronunciationPatterns(rules, p)


# ── feature signature (shared by the risk scorer + pattern matching) ─────────
def feature_signature(term: str, translit: str = "") -> list[str]:
    """Tag a term's phonetic features — the 'pattern' a word belongs to."""
    t = translit or term
    tags: list[str] = []
    if re.search(r"[ʿʾ'‘’]", t):
        tags.append("ayn-hamza")
    if re.search(r"[ḥḍṣṭẓḏṯġḫ]", t):
        tags.append("emphatic")
    if re.search(r"q", term, re.IGNORECASE):
        tags.append("qaf")
    if re.search(r"\b(al-| al )", t, re.IGNORECASE) or t.lower().startswith("al-"):
        tags.append("article-al")
    if re.search(r"\b(ibn|bin|bint|abu|abi|umm)\b", t, re.IGNORECASE):
        tags.append("lineage")
    for end in ("iyya", "iyyah", "ah", "a", "i", "u"):
        if t.lower().endswith(end):
            tags.append(f"ending-{end}")
            break
    return tags


if __name__ == "__main__":  # pragma: no cover - inspection CLI
    import sys

    store = load()
    if len(sys.argv) > 1:
        term = sys.argv[1]
        print(f"baseline({term!r}) -> {store.baseline_phonetic(term)!r}")
        print(f"signature -> {feature_signature(term, term)}")
    else:
        print(f"{len(store.char_rules())} char rules in {PATTERNS_PATH}")
        for tr in ("al-Ghazālī", "sharīʿa", "daʿwa", "nuqabāʾ", "ḥawl", "quwwa", "al-Khiḍr", "ʿabd allāh"):
            print(f"  {tr:16} -> {store.baseline_phonetic(tr)}")
