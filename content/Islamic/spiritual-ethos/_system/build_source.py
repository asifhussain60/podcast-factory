#!/usr/bin/env python3
"""build_source.py — assemble the OCR'd screenshots into the book's Phase 0a source.

Kept inside the book because it encodes THIS capture's shape: four screenshot
groups, each ending in its own endnote pages, and an appendix folder holding two
complete primary texts rather than reference matter.

What it does, in order:

  1. Splits each OCR group at its standalone `NOTES` line — prose one way,
     endnotes the other. Chapter 1 alone carries 117 notes; left attached they
     read as body text, and stripped wholesale they take the substantive ones
     with them.
  2. Rebuilds paragraphs. The OCR emits one line per PRINTED line, so a
     paragraph is a run of full-width lines; a short line ends it. Words
     hyphenated across a line break are rejoined.
  3. Removes the flattened footnote superscripts. In the screenshots these are
     raised digits; OCR lands them against the preceding punctuation
     (`soul.4`, `(68: 4).3`), where they read as stray numbers.
  4. Applies the naming convention: he is Ali (ع) throughout. OCR misreads
     ('Alr) are folded in here too.
  5. Writes the five-chapter source, plus the endnotes as their own files.

Re-runnable: reads only from `_system/source/ocr/`, writes only the outputs.

    python3 content/Islamic/spiritual-ethos/_system/build_source.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parent.parent
OCR = BOOK / "_system/source/ocr"
TEXT = BOOK / "_system/source/text"
NOTES_DIR = BOOK / "_system/source/notes"

# (ocr group, marker that opens the section or None, printed chapter title)
SECTIONS = [
    ("ch01", None, "Introducing Ali (ع) and his Spiritual Ethos"),
    ("ch02", None, "A Sacred Conception of Justice in the Letter of Ali (ع) to Malik al-Ashtar"),
    ("ch03", None, "Realization through Remembrance: Ali (ع) and the Mystical Tradition of Islam"),
    ("appx", "APPENDIX I", "The First Sermon of Nahj al-Balagha"),
    ("appx", "APPENDIX II", "The Letter of Ali (ع) to Malik al-Ashtar"),
]

PAGE_MARKER = re.compile(r"^<!--\s*page\s+\d+\s*-->$")
FOOTNOTE_MARK = re.compile(r"(?<=[.,;:!?'’\)\]])(\d{1,3})(?=[\s“'\"]|$)")

# Longest first, so the patronymic wins before the bare name matches inside it.
NAME_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![\w])(?:Imam\s+)?['’]?Al[iīr]\s+b\.\s+Ab[iī]\s+[ṬT][aā]lib\b"), "Ali ibn Abi Talib (ع)"),
    (re.compile(r"\bImam\s+['’]?Al[iīr]\b"), "Ali (ع)"),
    (re.compile(r"(?<![\w-])['’]Al[iīr]\b"), "Ali (ع)"),
    (re.compile(r"(?<![\w'’(-])Al[īr]\b"), "Ali (ع)"),
]


def read_group(group: str) -> list[str]:
    return (OCR / group / "raw-extract.md").read_text(encoding="utf-8").split("\n")


def slice_section(lines: list[str], marker: str | None) -> tuple[list[str], list[str]]:
    """Return (prose_lines, note_lines) for one section of a group."""
    start = 0
    if marker is not None:
        for i, ln in enumerate(lines):
            if ln.strip() == marker:
                start = i + 1
                break
        else:
            raise SystemExit(f"marker not found: {marker}")

    end = len(lines)
    notes_at = None
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s == "NOTES":
            notes_at = i
            break
        if marker is not None and s.startswith("APPENDIX") and i > start:
            end = i
            break

    if notes_at is not None:
        prose = lines[start:notes_at]
        note_end = len(lines)
        for j in range(notes_at + 1, len(lines)):
            if lines[j].strip().startswith("APPENDIX"):
                note_end = j
                break
        return prose, lines[notes_at + 1:note_end]
    return lines[start:end], []


def to_paragraphs(lines: list[str]) -> list[str]:
    """Join printed lines back into paragraphs.

    A paragraph continues while lines run the full measure; a short line ends
    it. The threshold is derived from the block itself rather than hardcoded,
    because the appendix pages set to a different measure than the chapters.
    """
    lines = [ln for ln in lines if not PAGE_MARKER.match(ln.strip())]
    widths = [len(ln) for ln in lines if len(ln) > 60]
    if not widths:
        return [ln.strip() for ln in lines if ln.strip()]
    full = sorted(widths)[int(len(widths) * 0.9)]
    cutoff = full * 0.80

    paras: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        text = ""
        for part in buf:
            if text.endswith("-") and not text.endswith("--"):
                text = text[:-1] + part.lstrip()
            elif text:
                text += " " + part.strip()
            else:
                text = part.strip()
        if text.strip():
            paras.append(text.strip())
        buf.clear()

    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            flush()
            continue
        buf.append(s)
        if len(s) < cutoff:
            flush()
    flush()
    return paras


# A transliterated Arabic phrase is NOT a reference to him in English prose —
# it is the Arabic itself, spelled in Latin letters. Renaming inside one
# corrupts the quotation ("la fata illa Ali (ع)"), so those spans are held out.
TRANSLIT_PAREN = re.compile(
    r"\([^()]{0,200}?(?:'l-|\bal-|\billa\b|\bminn[iī]\b|\bmawlahu\b|\bibada\b|\bfa-)"
    r"[^()]{0,200}?\)"
)


# English prose always carries these; a run of transliteration never does.
ENGLISH_TELLS = re.compile(
    r"\b(the|and|of|is|was|were|to|in|that|which|for|with|his|her|from|"
    r"this|are|as|but|not|who|had|have|been)\b", re.I
)


def _is_translit_line(text: str) -> bool:
    """A paragraph that is itself transliteration — the epigraph's two lines."""
    return "'l-" in text and len(text) < 220 and not ENGLISH_TELLS.search(text)


def apply_names(text: str) -> str:
    """Substitute via placeholders so no replacement can be re-matched."""
    if _is_translit_line(text):
        return text
    held: list[str] = []

    def hold(value: str) -> str:
        held.append(value)
        return f"\x00{len(held) - 1}\x00"

    text = TRANSLIT_PAREN.sub(lambda m: hold(m.group(0)), text)
    for pattern, repl in NAME_RULES:
        text = pattern.sub(lambda m, r=repl: hold(r), text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], text)
    return re.sub(r"\(ع\)(\s*\(ع\))+", "(ع)", text)


# A marker can also land straight against the word ("justice5", "Junayd5").
# Prose only: the endnotes legitimately carry forms like "EI2" and "vol.9".
FOOTNOTE_ON_WORD = re.compile(r"(?<=[a-z])(\d{1,3})(?=[\s'’.,;:)\]]|$)")


def clean(text: str, prose: bool = True) -> str:
    text, n = FOOTNOTE_MARK.subn("", text)
    if prose:
        text, n2 = FOOTNOTE_ON_WORD.subn("", text)
        n += n2
    clean.removed += n  # type: ignore[attr-defined]
    # OCR misreads the final long-i as an r throughout; fix before naming so the
    # held-out transliterations are corrected too.
    text = re.sub(r"(?<![\w])(['’]?)Alr\b", r"\1Ali", text)
    text = apply_names(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


clean.removed = 0  # type: ignore[attr-defined]


def is_heading(p: str) -> bool:
    letters = [c for c in p if c.isalpha()]
    return (
        len(p) < 80
        and bool(letters)
        and sum(c.isupper() for c in letters) / len(letters) > 0.85
        and not p.endswith(".")
    )


def main() -> int:
    TEXT.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    out: list[str] = ["# Spiritual Ethos", ""]
    out.append("*Justice and Remembrance — Reza Shah-Kazemi. "
               "Chapters one to three, with both primary texts from the appendices.*")
    out.append("")

    summary: list[tuple[str, int, int]] = []

    for idx, (group, marker, title) in enumerate(SECTIONS, 1):
        prose_lines, note_lines = slice_section(read_group(group), marker)
        paras = to_paragraphs(prose_lines)

        # Drop the running head and the printed chapter title; we set our own.
        while paras and (
            re.fullmatch(r"CHAPTER (ONE|TWO|THREE)", paras[0].strip())
            or paras[0].strip().startswith("APPENDIX")
            or is_heading(paras[0]) and idx <= 3 and len(paras[0]) < 60
        ):
            paras.pop(0)
        if paras and ("Spiritual Ethos" in paras[0] or "Mystical Tradition" in paras[0]
                      or "Sacred Conception" in paras[0] or "Nahj al-bal" in paras[0]
                      or "Malik al-Ashtar" in paras[0]) and len(paras[0]) < 100:
            paras.pop(0)

        out.append(f"## {title}")
        out.append("")
        for p in paras:
            p = clean(p)
            if is_heading(p):
                out.append(f"### {p.title()}")
            else:
                out.append(p)
            out.append("")

        notes = [clean(p, prose=False) for p in to_paragraphs(note_lines)]
        if notes:
            slug = f"{idx:02d}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]}"
            (NOTES_DIR / f"{slug}-notes.md").write_text(
                f"# Endnotes — {title}\n\n" + "\n\n".join(notes) + "\n", encoding="utf-8"
            )
        summary.append((title, sum(len(p.split()) for p in paras), len(notes)))

    (TEXT / "raw-extract.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")

    print(f"wrote {TEXT / 'raw-extract.md'}")
    for title, words, nnotes in summary:
        print(f"  {words:6,} words  {nnotes:4} notes   {title}")
    print(f"  footnote markers removed: {clean.removed}")  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    sys.exit(main())
