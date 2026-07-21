"""_book_inline_arabic.py — put the Arabic script back beside inline terms.

The problem this solves. The composer reads ``_system/source/text/refined-english.md``,
which carries no Arabic at all, so a term the source names in Arabic reaches
``book/book.md`` as bare transliteration — "Bayt al-Mamur" where the book means
البيت المعمور. Block quotations keep their script (they are transcribed from the
OCR ground-truth pages that the compose prompt is given); inline terms had no
such channel. R-ARABIC-SCRIPT-RETAINED says transliteration sits BESIDE the
script, never in place of it, so the edition was quietly breaking the rule its
own preface states.

Why this is deterministic and not a model pass. Every script it writes comes from
the curated ``arabic_script`` field in ``_system/glossary.yml``. Nothing is
recalled, so this cannot fabricate a spelling or invent vowel marks — the failure
mode that ``_book_arabic_audit`` exists to catch. It costs nothing to run.

House style is ``Transliteration (عربي)``, matching ``_narrative.ARABIC_DIRECTIVE``
("keep the script and add the transliteration beside it") and the skip-guard that
``plan-dashboard/src/lib/reader/glossary.ts`` already applies to the same shape.

FIRST occurrence per chapter only. A reader needs the script where the term is
introduced; repeating it at every mention turns prose into a glossary.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from _arabic_coverage import normalize_arabic
from _book_arabic_audit import _HONORIFIC_FORMULAS
from _translit import simplify_transliteration

# Name connectors and the article. They are grammatical glue inside a name, never
# a term a reader needs glossed: annotating them split "Jafar ibn Mansur al-Yaman"
# into "Jafar ibn (بن) Mansur…" the first time this ran.
_NAME_PARTICLES = frozenset({"ibn", "bin", "ibn.", "bint", "abu", "abi", "umm", "al", "aal"})

# Arabic letter ranges (presentation forms included) — the same span the audit
# and the site's overlay treat as "this is script, not transliteration".
_ARABIC = r"؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿"

# A line we must not touch: a blockquote (the Arabic quotations already carry
# their own script), a heading, a fenced/HTML block, or a machine fence.
#
# Deliberately NOT "any line containing Arabic". A prose line may already hold an
# inline run — including one this pass added on an earlier run — and skipping
# those made the pass non-idempotent: a second run found the annotated line
# invisible and re-annotated the term at its NEXT mention. Re-annotation is
# prevented by the per-match guard in _annotate_chapter instead, which is exact.
# The transliteration patterns are Latin-only, so they can never match inside an
# Arabic run anyway.
_SKIP_LINE = re.compile(r"^\s*(?:[>#]|```|<|\|)")

# How far past a term to look for its script before deciding this mention is
# already annotated. Wide enough to see past a closing quote, comma or footnote
# marker sitting between the term and its parenthetical.
_ANNOTATED_WINDOW = 12


def _term_re(phonetic: str) -> re.Pattern[str]:
    """Whole-token matcher: not inside a longer word, a hyphenated compound, or
    a possessive — "al-Quran" and "Ghazali's" must not fire."""
    return re.compile(rf"(?<![\w-]){re.escape(phonetic)}(?![\w'’-])")


def _glossary_terms(book_dir: Path) -> list[tuple[str, str]]:
    """(phonetic, arabic_script) pairs worth injecting, longest phonetic first.

    Longest-first so "Bayt al-Mamur" is matched before a bare "Bayt" entry could
    claim its opening word.
    """
    path = Path(book_dir) / "_system" / "glossary.yml"
    if not path.exists():
        return []
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []

    out: list[tuple[str, str]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        script = str(e.get("arabic_script") or "").strip()
        # The phonetic is normalised the same way the book body was, or a term
        # the body now spells "Bayt al-Mamur" would never match a glossary that
        # still says "Bayt al-Ma'mur".
        phonetic = simplify_transliteration(str(e.get("phonetic") or "").strip())
        if not script or not phonetic or not re.search(rf"[{_ARABIC}]", script):
            continue
        # An honorific formula ("عليه السلام") is the author's liturgical
        # practice attached to a name, not a rendering OF that name — gluing it
        # to the name produced "Isaac (عليهم السلام)". Same set the Arabic audit
        # uses, so the two agree on what counts as a formula.
        if normalize_arabic(script) in _HONORIFIC_FORMULAS:
            continue
        # A lone honorific letter ("ع" for عليه السلام) is the same thing
        # abbreviated; it is never a term's script.
        if len(script.strip()) <= 2:
            continue
        if phonetic.lower() in _NAME_PARTICLES:
            continue
        out.append((phonetic, script))
    out.sort(key=lambda t: len(t[0]), reverse=True)
    return out


def _annotate_chapter(body: str, terms: list[tuple[str, str]]) -> tuple[str, int]:
    """Add ``(script)`` after the first prose mention of each term in one chapter.

    All matching happens against the ORIGINAL line and insertions are applied
    right-to-left at the end, so no offset ever shifts under a later match. A
    match overlapping a term already claimed on that line is skipped: without
    that, the short entry "ibn" fired inside the long entry
    "Jafar ibn Mansur al-Yaman" and split a proper name in half.
    """
    lines = body.split("\n")
    pending = {p: s for p, s in terms}
    added = 0

    for i, line in enumerate(lines):
        if not pending or not line.strip() or _SKIP_LINE.search(line):
            continue
        # Reserve the span of EVERY glossary term present on this line, whether
        # or not it is still pending. Reserving only pending terms was not
        # enough: once "Abd Allah" had been annotated in an earlier line it left
        # `pending`, so on a later line the standalone "Allah" entry matched the
        # Allah INSIDE "son of Abd Allah" and printed "Abd Allah (الله)" — one
        # name carrying two different scripts in the same chapter.
        claimed: list[tuple[int, int]] = []
        for phonetic, _script in terms:
            for m in _term_re(phonetic).finditer(line):
                if not any(s < m.end() and m.start() < e for s, e in claimed):
                    claimed.append((m.start(), m.end()))
        reserved = list(claimed)

        inserts: list[tuple[int, str]] = []
        # `terms` is longest-phonetic-first, so a compound name claims its span
        # before any of its component words can.
        for phonetic, script in terms:
            if phonetic not in pending:
                continue
            # A term may only annotate at a span reserved for ITSELF — that is,
            # one whose extent matches this term exactly. A span belonging to a
            # longer name is off limits even though the shorter term matches
            # inside it.
            m = next(
                (
                    m
                    for m in _term_re(phonetic).finditer(line)
                    if (m.start(), m.end()) in reserved
                    and not any(s < m.end() and m.start() < e for s, e in claimed if (s, e) != (m.start(), m.end()))
                ),
                None,
            )
            if not m:
                continue
            claimed.append((m.start(), m.end()))
            # Idempotent: if this mention already carries its script, claim the
            # term and leave the text alone. The window is deliberately loose —
            # the approved base wrote one as `"Kab al-Ahbar (كعب الأحبار)"` with
            # the closing quote BETWEEN the term and its parenthetical, which a
            # strict `\s*\(` check walked straight past, producing the script
            # twice eight characters apart.
            if script in line[m.end() : m.end() + len(script) + _ANNOTATED_WINDOW]:
                del pending[phonetic]
                continue
            # Land the annotation OUTSIDE any emphasis the term sits in. The
            # term is often italicised as a gloss (`*al-Imam al-Natiq*`), and
            # inserting before the closing marker put the Arabic inside the
            # emphasis — where a browser synthesizes a slant, a thing Arabic
            # script does not have. Walk past the closing markers first.
            at = m.end()
            while at < len(line) and line[at] in "*_":
                at += 1
            inserts.append((at, f" ({script})"))
            del pending[phonetic]
            added += 1
        for pos, text in sorted(inserts, reverse=True):
            lines[i] = lines[i][:pos] + text + lines[i][pos:]

    return "\n".join(lines), added


def apply_inline_arabic(book_dir: Path, *, log=lambda _m: None) -> int:
    """Rewrite ``book/book.md`` in place. Returns the number of terms annotated.

    Safe to run repeatedly: a term already carrying its script is left alone.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return 0
    terms = _glossary_terms(book_dir)
    if not terms:
        log("inline-arabic: no glossary terms with Arabic script — skipped")
        return 0

    text = book_md.read_text(encoding="utf-8")
    # Split on chapter headings so "first occurrence" is per chapter, keeping the
    # heading text itself in the non-annotated stream.
    parts = re.split(r"(?m)^(##\s+.+)$", text)
    rebuilt: list[str] = [parts[0]]
    total = 0
    if parts[0].strip():
        annotated, n = _annotate_chapter(parts[0], terms)
        rebuilt[0] = annotated
        total += n
    for i in range(1, len(parts), 2):
        heading = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        annotated, n = _annotate_chapter(body, terms)
        total += n
        rebuilt.append(heading)
        rebuilt.append(annotated)

    new_text = "".join(rebuilt)
    if new_text != text:
        book_md.write_text(new_text, encoding="utf-8")
    log(f"inline-arabic: annotated {total} term mention(s)")
    return total
