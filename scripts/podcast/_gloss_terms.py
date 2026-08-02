"""_gloss_terms.py — find the Arabic terms a composed book GLOSSES in its prose.

The problem this solves. `degrees-of-excellence` prints 266 parenthetical glosses
across 188 distinct terms — `the ranks (hudud)`, `governance (siyasa)`, `the
proofs (hujaj)` — and exactly one of them carries Arabic script. Not because the
overlay is broken: because the glossary that drives it held ELEVEN entries. Its
input, `_system/source/text/_phonetics.md`, has had no writer since 2026-06-08,
and the fallback is a hard-coded 30-term list none of this book's vocabulary is
on. So the pipeline never learned the words the book was already teaching.

The glosses themselves are NOT the model's invention — 181 of 188 appear in the
source, because a critical edition teaches its vocabulary that way. They are kept
and converted, never stripped.

ONE MODULE, TWO CONSUMERS: `harvest_gloss_terms.py` (which adds what it finds to
the glossary) and the compose-time coverage gate. They must agree about what
counts as a gloss, or the gate would fail a book the harvester cannot fix.

CONFIDENCE, and why it can be loose. A candidate is STRONG when the SOURCE spells
the same word with scholarly diacritics that `simplify_transliteration` folds
away — `ḥudūd` -> `hudud`, `taʾwīl` -> `tawil`. That is direct evidence the word
is Arabic rather than English, and it covers 146 of 188 measured. The remaining
42 are WEAK and passed through anyway, because the pipeline already contains the
real arbiter: `fill_glossary_arabic` returns `""` for anything it cannot find in
the OCR, and `_book_inline_arabic._glossary_terms` excludes an entry with empty
script. So `(pole)` — an English word in a parenthesis — costs one lookup that
finds nothing and is never annotated. The filter only has to be good enough to
save spend, not to be correct, which is what makes it safe to be generous.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from _translit import simplify_transliteration

#: Lines that are not running prose: headings, quotes, fences, HTML, tables.
#: Shared shape with `_book_inline_arabic._SKIP_LINE` — a gloss inside a fenced
#: block or a table cell is not a gloss the reader meets in a sentence.
_SKIP_LINE = re.compile(r"^\s*(?:[>#]|```|<|\|)")

#: `(anything)` on one line, with the emphasis markers a source gloss often
#: carries (`(*bab*)`). Bounded length: a parenthesis holding a clause is an
#: aside, not a term.
_PAREN = re.compile(r"\((\*?)([^()\n]{2,45}?)\1\)")

_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")

#: A romanized Arabic term is letters, spaces, hyphens and apostrophes. A digit,
#: a colon or a slash means a citation (`Al-Baqarah: 24`), a date (`d. 381/991`)
#: or a reference — never a term.
_SHAPE = re.compile(r"^[A-Za-z'’ʾʿ\-\s]{2,45}$")

#: Whole-token English that proves the parenthesis is a phrase, not a term.
#: Deliberately small: these are words that cannot appear in a transliterated
#: Arabic noun phrase, so a hit is decisive rather than probabilistic.
_ENGLISH_TOKENS = frozenset(
    """
    a an the and or but of to in on at by for with from as is are was were be been
    this that these those it its he she they we you i not no nor if then than
    may might can could will would shall should must
    see also cf ibid trans ed eds vol p pp n
    god allah lord praise blessing peace upon him her them
    general editor translator translated edited introduction preface note notes
    """.split()
)

#: Terms English has absorbed and the repo already lists as such, plus the
#: prophet exonyms. Both files exist for exactly this question, so the answer is
#: read rather than re-derived.
_KB = Path(__file__).resolve().parents[2] / "content" / "knowledge-base"


def _kb_words(name: str) -> frozenset[str]:
    try:
        data = json.loads((_KB / name).read_text(encoding="utf-8"))
    except Exception:
        return frozenset()
    return frozenset(k.lower() for k in data if not k.startswith("_"))


def absorbed_english() -> frozenset[str]:
    """Words that are English now — `imam`, `quran`, `islam`, plus prophet names.

    OUT OF SCOPE by Asif's rule (2026-08-02): the exclusion is about a term doing
    an ordinary English job in running prose. A parenthesis is the book stopping
    to SHOW the Arabic word, so a gloss of one of these is still a gloss — this
    set is used to judge running prose, never to reject a candidate.
    """
    return _kb_words("loanwords.json") | _kb_words("exonyms.json")


def normalize_term(raw: str) -> str:
    """The comparison form: folded transliteration, collapsed space, lowercased."""
    return " ".join(simplify_transliteration(str(raw or "")).split()).lower()


def _source_diacritic_forms(source_text: str) -> frozenset[str]:
    """Words the SOURCE spells with scholarly diacritics, in folded form.

    `ḥudūd` folds to `hudud` and differs from what it folded FROM, which is the
    evidence: an English word never changes under the fold. Built once per book.
    """
    out: set[str] = set()
    for token in re.findall(r"[^\s—–.,;:()\[\]\"'!?]+", source_text or ""):
        folded = simplify_transliteration(token)
        if folded != token and re.fullmatch(r"[A-Za-z'’\-]{2,}", folded):
            out.add(folded.lower())
    return frozenset(out)


def gloss_candidates(book_md: str, source_text: str = "") -> list[dict[str, Any]]:
    """Every parenthetical gloss of an Arabic term, deduped, strongest first.

    Each entry: ``{term, count, confidence, first_seen_snippet}``.
    """
    diacritic_forms = _source_diacritic_forms(source_text)
    seen: dict[str, dict[str, Any]] = {}

    for line in (book_md or "").splitlines():
        if not line.strip() or _SKIP_LINE.search(line):
            continue
        for match in _PAREN.finditer(line):
            inner = match.group(2).strip()
            if _ARABIC.search(inner) or not _SHAPE.fullmatch(inner):
                continue
            tokens = inner.split()
            if not 1 <= len(tokens) <= 4:
                continue
            if any(t.strip("'’-").lower() in _ENGLISH_TOKENS for t in tokens):
                continue
            key = normalize_term(inner)
            if not key:
                continue
            hit = seen.get(key)
            if hit:
                hit["count"] += 1
                continue
            # STRONG when any word of the term is one the source spells with
            # diacritics. One word is enough for a phrase: `ra's al-ulama` is
            # proved Arabic by `ʿulamāʾ` alone.
            strong = any(t.lower().strip("'’-") in diacritic_forms for t in simplify_transliteration(inner).split())
            start = max(0, match.start() - 40)
            seen[key] = {
                "term": inner,
                "count": 1,
                "confidence": "strong" if strong else "weak",
                "first_seen_snippet": line[start : match.end() + 10].strip(),
            }

    return sorted(
        seen.values(),
        key=lambda c: (c["confidence"] != "strong", -c["count"], c["term"].lower()),
    )


def gloss_coverage(book_md: str, entries: Iterable[dict[str, Any]], source_text: str = "") -> dict[str, Any]:
    """How much of what the book glosses the glossary can actually annotate.

    THE number the pipeline never computed. `_book_arabic_audit` enumerates
    Arabic RUNS first, so a romanized term with no script produces no run and is
    not merely unmeasured — it is invisible to the data structure. This is its
    complement: it starts from the romanization and asks whether script exists.
    """
    known: dict[str, dict[str, Any]] = {}
    for e in entries:
        key = normalize_term(e.get("phonetic") or e.get("transliteration") or "")
        if key:
            known.setdefault(key, e)

    candidates = gloss_candidates(book_md, source_text)
    missing_strong: list[str] = []
    covered = 0
    for c in candidates:
        entry = known.get(normalize_term(c["term"]))
        if entry and str(entry.get("arabic_script") or "").strip():
            covered += 1
        elif c["confidence"] == "strong":
            missing_strong.append(c["term"])

    strong = [c for c in candidates if c["confidence"] == "strong"]
    return {
        "schema": "book.gloss-coverage/v1",
        "candidates": len(candidates),
        "strong": len(strong),
        "covered": covered,
        "missing_strong": sorted(missing_strong),
        "glossary_entries": len(known),
        "coverage": round(covered / len(candidates), 3) if candidates else 1.0,
        "strong_coverage": (round((len(strong) - len(missing_strong)) / len(strong), 3) if strong else 1.0),
    }
