"""_book_work_titles.py — a cited book prints under the name a reader can read.

THE RULE (Asif, 2026-08-05). Where the prose already supplies an English
translation of a work title, the edition prints THAT and nothing else:

    Ihya al-Ulum ad-Din (Revival of the Knowledge of the Path to God)
    -> Revival of the Knowledge of the Path to God

Only where the English is already there. A title the author names bare — "look
into the Ihya and the others of my writings" — is his own sentence and is left
exactly as he wrote it. Supplying a translation there would be putting words in
his mouth, and this pass is deliberately incapable of it: the English it prints
is lifted from the bracket beside the title, never from the glossary and never
from a model.

WHY A SEPARATE CLASS RATHER THAN `silent`. `silent` says "annotate nothing",
which would stop the Arabic being added and still leave `Ihya al-Ulum ad-Din
(Revival of …)` — two names for one book, the romanised one first. A work title
is its own kind of thing: not a person whose romanisation is how you say them
(`name`), not vocabulary the book teaches (`teach`). So `work_title` joins the
registry in `_annotation_policy`, and `_book_inline_arabic` reads it as "never
annotate" — which also means the strip pass REMOVES script an earlier run added
under the old class, rather than fossilising it.

WHAT IT UNDOES, and why that is the same job. Chapter 1 of `ayyuhal-walad`
printed this, and every bracket in it is a separate fault:

    Arbaeen (أَرْبَعُون) (Forty Steps)
    Minhaj ul-Abideen ila Jannatu Rabbul Alamin
      (*Minhaj ul-Abideen ila Jannatu Rabbul 'Alamin* (منهاج …)) (The Best Way …)

The compose said the second title twice, once italicised in its own bracket; the
Arabic overlay then annotated the INNER copy, because it walks past a closing
`*` and appends there. So between a work title and its English translation there
can be brackets that are neither — a repeat of the title, or script. This pass
walks them: a bracket holding only script, or holding the title again, is
DROPPED; the first bracket holding English is the translation and becomes the
sentence. A title with no English bracket after it keeps its romanisation and
merely loses the script.

Deterministic, glossary-driven, no model, no cost. Idempotent by construction —
after a run the title is gone, so nothing matches on the next one.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _arabic_coverage import normalize_arabic
from _book_inline_arabic import _ARABIC, _SKIP_LINE, _term_re
from _translit import simplify_transliteration

#: The annotation class this pass acts on. Registered in `_annotation_policy`.
WORK_TITLE_CLASS = "work_title"

_EMPHASIS = "*_"
#: A bracket must hold this many Latin letters before it counts as an English
#: translation. One or two is an initial, a footnote marker or a stray letter
#: inside a mostly-Arabic bracket — not a title anybody could read.
_MIN_ENGLISH = 3


def _spellings(phonetic: str) -> list[str]:
    """The glossary's spelling, and the same with its remaining ayns dropped.

    `simplify_transliteration` drops an ayn-apostrophe INSIDE a word but keeps
    one at the start of a word: `Minhaj ul-'Abideen ila Jannatu Rabbul 'Alamin`
    simplifies to `Minhaj ul-Abideen ila Jannatu Rabbul 'Alamin`, and the prose
    writes it with neither. That single surviving apostrophe is why chapter 1
    printed the title nested inside itself — the glossary form matched the
    italic DUPLICATE, which had kept its ayns, and never the running title.

    Handled here rather than in `_translit`, deliberately. That module is one
    half of a fixture-pinned TS/Python pair and every book's transliteration
    runs through it; widening its apostrophe rule to fix one title is a change
    with a blast radius nobody asked for. This is a local widening of what
    counts as the same title, and it can only ever match MORE spellings of a
    term the glossary already names.
    """
    simplified = simplify_transliteration(phonetic)
    bare = re.sub(r"['’ʿʾ]", "", simplified)
    return [simplified] if bare == simplified else [simplified, bare]


def work_title_terms(book_dir: Path) -> list[str]:
    """Romanised work titles from the glossary, longest first.

    Longest-first for the same reason the overlay sorts that way: `Minhaj
    ul-Abideen ila Jannatu Rabbul Alamin` must be matched before a shorter entry
    could claim its opening word. Phonetics are simplified exactly as
    `_book_inline_arabic` simplifies them, or a glossary that still writes
    `Minhaj ul-'Abideen` would never match a body that says `Minhaj ul-Abideen`.
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
    out: list[str] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if str(e.get("annotation_class") or "").strip() != WORK_TITLE_CLASS:
            continue
        raw = str(e.get("phonetic") or "").strip()
        if raw:
            out.extend(s for s in _spellings(raw) if s)
    out.sort(key=len, reverse=True)
    return out


def work_title_scripts(book_dir: Path) -> list[str]:
    """The Arabic script of every work title, for the orphan rule below."""
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
    return [
        str(e.get("arabic_script") or "").strip()
        for e in entries
        if isinstance(e, dict)
        and str(e.get("annotation_class") or "").strip() == WORK_TITLE_CLASS
        and str(e.get("arabic_script") or "").strip()
    ]


def _balanced_bracket(line: str, at: int) -> tuple[int, int, str] | None:
    """The `(…)` starting at or just after ``at``, with nesting respected.

    Nesting is not hypothetical here — `(*Title* (منهاج …))` is the exact shape
    this pass exists to unpick, and a non-greedy `\\([^)]*\\)` stops at the inner
    close, leaving a stranded `)` in the prose.
    """
    i = at
    while i < len(line) and line[i].isspace():
        i += 1
    if i >= len(line) or line[i] != "(":
        return None
    depth = 0
    for j in range(i, len(line)):
        if line[j] == "(":
            depth += 1
        elif line[j] == ")":
            depth -= 1
            if depth == 0:
                return i, j + 1, line[i + 1 : j]
    return None


def _is_script_only(inner: str) -> bool:
    """A bracket the overlay wrote: script, and nothing a reader reads as words."""
    return bool(re.search(rf"[{_ARABIC}]", inner)) and len(re.findall(r"[A-Za-z]", inner)) < _MIN_ENGLISH


def _fold(s: str) -> str:
    """Letters and single spaces only, casefolded.

    Punctuation is noise for the one question asked here — is this bracket the
    title over again? — and the punctuation is exactly what differs: the
    duplicate arrives italicised and with the ayns the running title dropped.
    """
    return " ".join(re.sub(r"[^0-9A-Za-z ]+", " ", s).split()).casefold()


def _repeats(inner: str, phonetic: str) -> bool:
    """Is this bracket the title over again, rather than its translation?

    Nested script is removed first: the duplicate arrives as `*Minhaj …*
    (منهاج …)`, so comparing the raw inner text never matches. `startswith`
    rather than containment — a bracket that merely MENTIONS the title inside a
    longer English sentence is a note about the book, not a second copy of its
    name, and must not be deleted.
    """
    stripped = re.sub(rf"\([^()]*[{_ARABIC}][^()]*\)", "", inner)
    bare, target = _fold(stripped), _fold(phonetic)
    return bool(bare) and bool(target) and (bare.startswith(target) or target.startswith(bare))


def _is_english(inner: str) -> bool:
    return len(re.findall(r"[A-Za-z]", inner)) >= _MIN_ENGLISH and not re.search(rf"[{_ARABIC}]", inner)


def collapse_work_titles(
    body: str, phonetics: list[str], scripts: list[str] | None = None
) -> tuple[str, list[dict[str, str]]]:
    """Replace each glossed work title with its English translation.

    Returns the new body and one record per change, so the caller can report
    what it did rather than leaving a silent rewrite of the author's page.
    """
    if not phonetics and not scripts:
        return body, []
    phonetics = phonetics or []
    records: list[dict[str, str]] = []
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if not line.strip() or _SKIP_LINE.search(line):
            continue
        # THE ORPHANED SCRIPT. Where an earlier pass replaced the romanised
        # title with its script and the English is the running prose — "in the
        # Revival of the Sciences of Religion (إِحْيَاءُ الْعُلُوم), so seek it there" —
        # there is no romanisation left for the rules below to find, and the
        # bracket is still the second name for a book already named in English.
        # Narrow on purpose: it removes a bracket ONLY when its whole content is
        # the script of a term a human classified `work_title`, matched on the
        # consonantal skeleton so a vowelling cannot hide it.
        for script in scripts or []:
            skeleton = normalize_arabic(script)
            if not skeleton:
                continue

            def _drop(m: re.Match[str], _s: str = skeleton) -> str:
                return "" if normalize_arabic(m.group(1)) == _s else m.group(0)

            new_line = re.sub(rf"\s*\(\s*([^()\n]*[{_ARABIC}][^()\n]*?)\s*\)", _drop, line)
            if new_line != line:
                records.append({"title": script, "action": "dropped-orphan-script"})
                line = new_line
        # THE REVERSED SHAPE. Where the author put the English in the
        # running prose and the title in the bracket — "in the Revival of the
        # Sciences of Religion (*Ihya Ulum ad-Din*), so seek it there" — the
        # English is already the sentence and the bracket is the second name the
        # rule exists to remove. Handled before the forward pass because the
        # forward pass would find the term INSIDE that bracket, look for a
        # translation after it, find none, and leave it standing.
        for phonetic in phonetics:
            pattern = re.compile(
                rf"\s*\(\s*[{re.escape(_EMPHASIS)}]*{re.escape(phonetic)}[{re.escape(_EMPHASIS)}]*\s*\)"
            )
            new_line = pattern.sub("", line)
            if new_line != line:
                records.append({"title": phonetic, "action": "dropped-second-name"})
                line = new_line
        lines[i] = line
        for phonetic in phonetics:
            pattern = _term_re(phonetic)
            # Re-scan from the top after every edit: an edit shortens the line,
            # so a cached match offset would point into the middle of a word.
            while True:
                m = pattern.search(line)
                if not m:
                    break
                start, at = m.start(), m.end()
                while start > 0 and line[start - 1] in _EMPHASIS:
                    start -= 1
                while at < len(line) and line[at] in _EMPHASIS:
                    at += 1
                cursor, english = at, None
                while True:
                    found = _balanced_bracket(line, cursor)
                    if not found:
                        break
                    b_start, b_end, inner = found
                    if _is_english(inner):
                        english = (b_end, inner.strip().strip(_EMPHASIS).strip())
                        break
                    if _is_script_only(inner) or _repeats(inner, phonetic):
                        cursor = b_end
                        continue
                    break
                if english is None:
                    # No translation on the page. Drop whatever script or
                    # duplicate stood between (cursor moved past them), keep the
                    # author's own romanisation — the half of the rule that
                    # refuses to invent an English name.
                    if cursor > at:
                        line = line[:at] + line[cursor:]
                        records.append({"title": phonetic, "action": "stripped-brackets"})
                        continue
                    break
                b_end, text = english
                line = line[:start] + text + line[b_end:]
                records.append({"title": phonetic, "action": "englished", "printed": text})
            lines[i] = line
    return "\n".join(lines), records


def apply_work_titles(book_dir: Path, *, log=lambda _m: None) -> int:
    """Run the pass over ``book/book.md``. Returns how many titles changed."""
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return 0
    phonetics = work_title_terms(book_dir)
    scripts = work_title_scripts(book_dir)
    if not phonetics:
        log("work-titles: no work_title terms in the glossary — skipped")
        return 0
    before = book_md.read_text(encoding="utf-8")
    after, records = collapse_work_titles(before, phonetics, scripts)
    report = {
        "schema": "book.work-titles/v1",
        "terms": phonetics,
        "changes": records,
    }
    (book_dir / "_system" / "book-work-titles.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if after != before:
        tmp = book_md.with_suffix(".md.tmp")
        tmp.write_text(after, encoding="utf-8")
        tmp.replace(book_md)
    englished = sum(1 for r in records if r["action"] == "englished")
    stripped = len(records) - englished
    log(f"work-titles: {englished} printed in English, {stripped} left romanised with brackets dropped")
    return len(records)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--book-dir")
    args = ap.parse_args()
    if args.book_dir:
        book_dir = Path(args.book_dir)
    elif args.slug:
        from _paths import resolve_content

        book_dir = resolve_content(args.slug)
    else:
        ap.error("either <slug> or --book-dir is required")
    apply_work_titles(book_dir, log=print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
