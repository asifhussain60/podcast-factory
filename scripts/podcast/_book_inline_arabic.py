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


def _gloss_span(line: str, start: int, end: int) -> tuple[int, int] | None:
    """If the term at [start,end) IS a parenthetical transliteration gloss, return
    the span of the whole `(*term*)`.

    The author's convention puts the romanisation in brackets after the English:
    `his gate (*bab*)`. The term therefore sits INSIDE the parentheses, not
    before them — so the script must REPLACE that bracket, not open a second one
    inside it.
    """
    a = start
    while a > 0 and line[a - 1] in "*_":
        a -= 1
    if a == 0 or line[a - 1] != "(":
        return None
    b = end
    while b < len(line) and line[b] in "*_":
        b += 1
    if b >= len(line) or line[b] != ")":
        return None
    # Absorb one leading space so "gate (bab)" -> "gate (script)", not "gate  (…)".
    open_at = a - 1
    if open_at > 0 and line[open_at - 1] == " ":
        open_at -= 1
    return (open_at, b + 1)


def _is_person(phonetic: str) -> bool:
    """True for a personal name, where the transliteration IS the English.

    A reader needs "Jafar ibn Mansur al-Yaman" romanised; they do not need
    "bab" romanised once the script is beside it. Detected by a standalone name
    particle, so "al-Imam al-Natiq" (a title, hyphen-prefixed) is NOT a person
    while "Jafar ibn Mansur al-Yaman" is.
    """
    return any(w.lower() in _NAME_PARTICLES for w in phonetic.split())


def _script_already_near(line: str, at: int, script: str) -> bool:
    """Is this concept already carrying script in the immediate vicinity?

    Containment both ways, because the glossary holds overlapping entries: the
    bare "Imam" (\u0627\u0644\u0625\u0645\u0627\u0645) sits inside "al-Imam al-Natiq"
    (\u0627\u0644\u0625\u0645\u0627\u0645 \u0627\u0644\u0646\u0627\u0637\u0642), and annotating both
    printed the same idea twice in one breath.
    """
    window = line[at : at + len(script) + _ANNOTATED_WINDOW + 24]
    for run in re.findall(rf"[{_ARABIC}][^()]*", window):
        run = run.strip()
        if run and (run in script or script in run):
            return True
    return False


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

        edits: list[tuple[int, int, str]] = []
        queued: list[tuple[int, str]] = []  # (position, script) already decided
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
            # The line still holds its ORIGINAL text while we decide, so a script
            # queued earlier in this pass is invisible to a text scan. Check both.
            near_queued = any(
                abs(pos - m.end()) < _ANNOTATED_WINDOW + 40 and (q in script or script in q) for pos, q in queued
            )
            if near_queued or _script_already_near(line, m.end(), script):
                del pending[phonetic]
                continue

            # Walk past any emphasis closing the term. Landing inside it put the
            # Arabic in an <em>, where a browser synthesizes a slant — a thing
            # Arabic script does not have.
            at = m.end()
            while at < len(line) and line[at] in "*_":
                at += 1

            # THE GLOSS RULE. Where the book already glosses the term with its
            # transliteration — the author's own convention, `his gate (*bab*)`
            # — the script REPLACES that transliteration rather than nesting
            # inside it. Nesting produced `his gate (*bab* (باب))`: the same
            # word three ways, two parentheses deep. Once the script is there
            # the romanisation earns nothing, because the English meaning is
            # already the running prose.
            #
            # A personal name is the exception: its transliteration IS how an
            # English reader says it, so the script is appended beside it.
            gloss = None if _is_person(phonetic) else _gloss_span(line, m.start(), m.end())
            if gloss:
                edits.append((gloss[0], gloss[1], f" ({script})"))
                queued.append((gloss[0], script))
                del pending[phonetic]
                added += 1
                continue

            edits.append((at, at, f" ({script})"))
            queued.append((at, script))
            del pending[phonetic]
            added += 1
        # Right-to-left so no earlier offset shifts under a later edit.
        for start, end, text in sorted(edits, reverse=True):
            lines[i] = lines[i][:start] + text + lines[i][end:]

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
