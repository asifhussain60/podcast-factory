"""One rule for Latin-script text that names or labels a book: plain English letters only.

WHY THIS EXISTS (2026-09-19, isaf-al-talib). The written standard
(`docs/standards/book-articulation.md`, rule 15) bans diacritics in a book's PROSE, and
the prose was clean. Nothing covered the text that NAMES the book: `book-toc.json`
(written by the 0book-design model) carried "Iṣāf al-Ṭālib fī Jamīʿ al-Maṭālib" and
chapter titles like "Rūm", the PDF and Google Drive file names were built from it, and
`meta.yml` carried apostrophe stand-ins for Arabic letters ("Is'af", "Jami'"), which
are ASCII and so invisible to any diacritics check. Three sources, one defect, no gate.

THE RULE. Text in Latin script uses A-Z, digits and ordinary English punctuation.
  * combining marks and dotted/macron letters are folded (ṭ -> t, ā -> a);
  * the ayn/hamza modifier letters (ʿ ʾ) are dropped ("Ali", "Quran", "wudu");
  * in a TITLE an apostrophe survives only where English uses one ("Student's",
    "students'", "don't"); a transliteration apostrophe ("Is'af", "Jami'") is dropped.
  * Arabic-script runs are NEVER touched: the quotations are the book's content.

Deterministic, no model, no per-book exceptions. Prose is CHECKED here, not rewritten:
changing quoted prose belongs to the Composer (the singular path for PDF-bound text).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

_ARABIC_RUN = re.compile("[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿‌-‏]+")
_DROPPED = str.maketrans("", "", "ʿʾʻʼ")  # ʿ ʾ ʻ ʼ
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
# An apostrophe English uses: 's 't 'd 'm 'll 're 've, or a plural possessive (s').
_ENGLISH_APOSTROPHE = re.compile(r"(?<=[A-Za-z])'(?=(?:s|t|d|m|ll|re|ve)\b)|(?<=s)'(?![A-Za-z])", re.I)
_MODIFIER_LETTERS = re.compile("[ʰ-˿]")
_TITLE_OK = re.compile(r"[A-Za-z0-9 .,()&:;/\u2014\u2013\-'\"!?]*")


def _fold_segment(text: str) -> str:
    text = text.translate(_DROPPED).translate(_QUOTES)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def plain_latin(text: str) -> str:
    """Fold diacritics and modifier letters out of the Latin parts of `text`."""
    out: list[str] = []
    last = 0
    for run in _ARABIC_RUN.finditer(text):
        out.append(_fold_segment(text[last : run.start()]))
        out.append(run.group(0))
        last = run.end()
    out.append(_fold_segment(text[last:]))
    return "".join(out)


def _quote_pair_positions(text: str) -> set[int]:
    """Apostrophes that open and close a quotation ('Be'), so they are marks, not letters."""
    keep: set[int] = set()
    opening: int | None = None
    for i, ch in enumerate(text):
        if ch != "'":
            continue
        before = text[i - 1] if i else " "
        after = text[i + 1] if i + 1 < len(text) else " "
        if not before.isalnum() and after.isalnum():
            opening = i
        elif before.isalnum() and not after.isalnum() and opening is not None:
            keep |= {opening, i}
            opening = None
    return keep


def plain_title(text: str) -> str:
    """`plain_latin` plus removal of transliteration apostrophes, for names and titles."""
    folded = plain_latin(text)
    kept = {m.start() for m in _ENGLISH_APOSTROPHE.finditer(folded)} | _quote_pair_positions(folded)
    return "".join(ch for i, ch in enumerate(folded) if ch != "'" or i in kept)


def title_violations(text: str) -> list[str]:
    """What is wrong with a title, in words; empty when it is already plain."""
    if not text:
        return []
    if plain_title(text) != text:
        return [f"{text!r} should read {plain_title(text)!r}"]
    if not _TITLE_OK.fullmatch(text):
        return [f"{text!r} uses characters outside plain English"]
    return []


def prose_violations(text: str) -> list[str]:
    """Latin letters with diacritics or modifier letters outside Arabic-script runs."""
    found: dict[str, int] = {}
    for line in text.splitlines():
        rest = _ARABIC_RUN.sub(" ", line)
        for ch in _fold_segment_marks(rest):
            found[ch] = found.get(ch, 0) + 1
    return [f"{ch!r} x{n}" for ch, n in sorted(found.items())]


def _fold_segment_marks(text: str) -> list[str]:
    bad = []
    for ch in text:
        if _MODIFIER_LETTERS.match(ch):
            bad.append(ch)
        elif ord(ch) > 127 and ch.isalpha() and _fold_segment(ch) != ch:
            bad.append(ch)
    return bad


def _walk_titles(toc: dict[str, Any]) -> list[tuple[str, str]]:
    pairs = [("book_title", toc.get("book_title") or "")]
    for i, ch in enumerate(toc.get("chapters") or []):
        pairs.append((f"chapters[{i}].title", ch.get("title") or ""))
    pf = toc.get("preface") or {}
    if isinstance(pf, dict):
        pairs.append(("preface.title", pf.get("title") or ""))
    return pairs


def sanitize_toc(toc: dict[str, Any]) -> dict[str, Any]:
    """Make a book-toc dict plain: titles by `plain_title`, themes/rationales by `plain_latin`."""
    if toc.get("book_title"):
        toc["book_title"] = plain_title(toc["book_title"])
    holders = list(toc.get("chapters") or [])
    if isinstance(toc.get("preface"), dict):
        holders.append(toc["preface"])
    for ch in holders:
        if ch.get("title"):
            ch["title"] = plain_title(ch["title"])
        for key in ("theme", "rationale"):
            if isinstance(ch.get(key), str):
                ch[key] = plain_latin(ch[key])
    return toc


def book_latin_findings(book_dir: Path) -> list[str]:
    """Every plain-English violation in a book's titles, table of contents and prose."""
    book_dir = Path(book_dir)
    findings: list[str] = []
    toc_path = book_dir / "book" / "book-toc.json"
    if toc_path.exists():
        toc = json.loads(toc_path.read_text(encoding="utf-8"))
        for where, title in _walk_titles(toc):
            findings += [f"book-toc {where}: {v}" for v in title_violations(title)]
    meta = book_dir / "meta.yml"
    if meta.exists():
        for line in meta.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(title|title_english):\s*(.+?)\s*$", line)
            if m:
                value = m.group(2).strip("\"'")
                findings += [f"meta.yml {m.group(1)}: {v}" for v in title_violations(value)]
    book_md = book_dir / "book" / "book.md"
    if book_md.exists():
        text = book_md.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("#"):
                findings += [f"book.md heading: {v}" for v in title_violations(line.lstrip("# ").strip())]
        bad = prose_violations(text)
        if bad:
            findings.append("book.md prose: diacritic letters " + ", ".join(bad[:8]))
    return findings
