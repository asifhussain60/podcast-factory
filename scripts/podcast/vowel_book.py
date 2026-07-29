#!/usr/bin/env python3
"""vowel_book.py — put the vowel marks on every Arabic run in a book.

WHY THE PIPELINE DOES THIS NOW (Asif, 2026-07-29). Until this pass existed, the
rule was the opposite one: a model must never supply tashkeel, and BK-N5 made a
supplied mark a P0 under the book-challenger's closing gate. The reasoning was
sound in isolation -- on an Arabic verb a wrong vowel flips active to passive, and
this book is largely reported speech -- but it optimised for the wrong reader.
Asif does not read Arabic. To him an unvowelled run is not "unverified", it is
unreadable, so a rule whose whole effect was to keep marks off the page made every
edition worse for the person it is printed for. The rule is reversed: Arabic
always carries its marks, and this pass is what puts them there.

WHAT IS *NOT* RELAXED, and the distinction is the entire safety argument. A
vowelling may differ from its source in MARKS ONLY. `_vowelling.rejection_reason`
refuses any answer whose consonantal skeleton is not byte-identical to the run it
replaces, so a model that adds marks passes and a model that "corrects" a word,
drops a clause, normalises a hamza form or reaches for the mushaf's Uthmani
spelling is refused and never reaches `book.md`. Relaxing the policy on marks was
Asif's call; letting letters move under cover of it was not.

TWO SOURCES OF MARKS, chosen by what the run IS:
  * Ordinary Arabic -- the book's own words -- is vowelled by the model above,
    under the marks-only gate.
  * SCRIPTURE is not. `_mushaf.is_quranic` recognises a Qur'anic run and
    `_mushaf.mushaf_vocalisation` returns the canonical vowelled text for it, out
    of `content/knowledge-base/mirror.db`. For a verse there is a right answer and
    it is in the repo, so no model is asked. That text is UTHMANI, so the letters
    change too -- the one place in this repo where that is right rather than a
    defect, and consistent with the reading edition already setting every
    mushaf-resolved run in the KFGQPC Uthmanic face. A verse that does not align
    word for word is left exactly as the book prints it.

A run already carrying its marks (`is_vowelling_candidate`) is skipped by either
path: there is nothing to add.

IDEMPOTENT. A second run finds every previously-marked passage already vowelled
and does nothing, so re-composing a book costs nothing and cannot double-mark.

Wired into `_book_pipeline_v2` after the inline-Arabic overlay (so glossary script
inserted there is vowelled too) and before the audits (so what they judge is what
prints). Also runnable on its own as a backfill for books composed before the
reversal, in the same shape as `normalize_spelling.py`:

    python3 scripts/podcast/vowel_book.py --slug the-master-and-the-disciple
    python3 scripts/podcast/vowel_book.py --slug <slug> --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _arabic_coverage import arabic_run_spans  # noqa: E402
from _paths import content_dir  # noqa: E402
from _vowelling import (  # noqa: E402
    VOWELLED_DENSITY,
    is_arabic_passage,
    is_vowelling_candidate,
    mark_count,
    mark_density,
    rejection_reason,
)

MODEL = "gemini-2.5-pro"
"""Vocalisation is a reasoning task, not a lookup: the reading of an ambiguous
verb comes from the surrounding sense. Flash guesses; Pro deliberates."""

SYSTEM = """You add Arabic vowel marks (tashkeel) and nothing else.

You will be given one Arabic passage from a classical Ismaili teaching text. Return
the SAME passage with full tashkeel applied.

ABSOLUTE CONSTRAINTS - a response that breaks any of these is discarded:
- Do not add, remove, reorder or change ANY letter. The consonantal skeleton of your
  answer must be byte-identical to the input. This is checked mechanically.
- Do not "correct" spelling, do not substitute Uthmani Qur'anic orthography, do not
  normalise hamza forms, do not change punctuation or word order.
- Write the definite article with a PLAIN alif (\u0627). Never use alif wasla
  (\u0671) - it is a different character, so "\u0671\u0644\u0625\u0631\u0627\u062f\u0629" for "\u0627\u0644\u0625\u0631\u0627\u062f\u0629" is a letter change and the whole
  answer is discarded, however correct the vowelling around it.
- Do not translate, explain, or add commentary. Return only the vowelled Arabic.
- Where the vocalisation is genuinely ambiguous, choose the reading that the
  surrounding sense supports and still return only the passage.

Return the vowelled Arabic on a single line, with no quotes and no preamble."""


CITATION_SYSTEM = """You add Arabic vowel marks (tashkeel) to a single term and nothing else.

You will be given one Arabic term from a classical Ismaili text, and the English
around it. Return the SAME term fully vowelled, as a dictionary citation form.

ABSOLUTE CONSTRAINTS - a response that breaks any of these is discarded:
- Do not add, remove, reorder or change ANY letter. The consonantal skeleton of your
  answer must be byte-identical to the input. This is checked mechanically.
- Do not "correct" spelling, do not substitute Uthmani Qur'anic orthography, do not
  normalise hamza forms. Write the definite article with a PLAIN alif (\u0627),
  never alif wasla (\u0671) - that is a different character and discards the answer.
- Mark the word fully INSIDE, and leave the FINAL letter unmarked (pausal form).
  The term is printed beside its English as a gloss, where no syntax governs its
  case ending; a citation form is what belongs there.
- The English tells you which reading is meant - a noun or a verb, this sense or
  that one. Follow it.
- Return only the vowelled Arabic term: no quotes, no commentary, no translation."""

# Arabic letters, excluding the combining marks themselves — for the length floor
# the lexical sweep in vowel_text applies to a token.
ARABIC_LETTER_RE = re.compile("[\u0620-\u064a\u0660-\u066f\u0671-\u06d3]")

# A short bare Arabic token quoted or bracketed inside English prose: the book
# discussing a word AS a word. `"باطن," "an inward"`, `one (واحد) is four letters`.
# These fall below the run floor by design — a two-letter Arabic fragment loose in
# prose is usually a stray — so they need their own finder, and the delimiter is
# what makes them safe to act on: it says the author put the word there to be
# looked at, which is exactly where a reader needs the marks most.
_LEXICAL_TOKEN_RE = re.compile(r'(?<=[("\u00ab\u201c])([\u0600-\u06ff][\u0600-\u06ff\s]*?)(?=[)"\u00bb\u201d,.:;])')


def _gemini(system: str, user: str, *, model: str = MODEL) -> str:
    """One vocalisation call. Same transport as gemini_refine.py."""
    from _secrets import get_gemini_key

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={get_gemini_key()}"
    body = json.dumps(
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            # Temperature near zero: vocalising a fixed text is not a creative
            # task, and the same passage should come back the same way twice.
            # The token budget is headroom for 2.5 Pro's thinking, which is drawn
            # from this same allowance -- a tight budget returns an empty answer.
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000},
        }
    ).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _clean(raw: str) -> str:
    """Models like to wrap a one-line answer in a fence or quotes."""
    text = raw.strip().removeprefix("```").removesuffix("```").strip()
    for line in text.splitlines():
        stripped = line.strip().strip("\"'«»")
        if stripped and any("؀" <= c <= "ۿ" for c in stripped):
            return stripped
    return ""


def vowel_text(
    text: str,
    *,
    log: Callable[[str], None] = print,
    dry_run: bool = False,
    call: Callable[[str], str] | None = None,
) -> tuple[str, dict]:
    """Return ``text`` with every bare non-Qur'anic Arabic run vowelled.

    Replacement is by exact string, run by run, so nothing outside an Arabic run
    can be touched -- the English prose the runs sit in is never sent anywhere.
    A run that occurs several times is vowelled once and replaced everywhere,
    which is correct: the same sentence has the same reading.
    """
    from _mushaf import is_quranic, mushaf_available, mushaf_vocalisation

    ask = call or (lambda run: _clean(_gemini(SYSTEM, run)))
    have_mushaf = mushaf_available()
    if not have_mushaf:
        # Degrade LOUDLY, not silently: without the mushaf every Qur'anic run
        # reads as ordinary Arabic and would be re-vowelled from a model, which
        # is the one case where the canonical text is strictly better.
        log("vowelling: canonical mushaf unavailable - Qur'anic runs cannot be identified; skipping")
        return text, {"skipped": "no mushaf", "vowelled": 0}

    seen: set[str] = set()
    stats = {
        "vowelled": 0,
        "marks_added": 0,
        "already": 0,
        "quranic": 0,
        "from_mushaf": 0,
        "refused": 0,
    }
    refusals: list[dict] = []
    out = text
    for run in arabic_run_spans(text):
        if run in seen:
            continue
        seen.add(run)
        if not is_vowelling_candidate(run):
            stats["already"] += 1
            continue
        if not is_arabic_passage(run):
            continue
        if is_quranic(run):
            # Scripture the book prints BARE. Skipping it on the assumption that a
            # verse arrives already marked left the most familiar passages in the
            # book — the basmala, `إنا لله وإنا إليه راجعون` — as the only
            # unreadable ones. A model must not supply these marks: for canonical
            # scripture there is a right answer and it is in the repo, so take the
            # mushaf's own vocalisation. Note this returns UTHMANI text, letters
            # and all; see mushaf_vocalisation for why that is right here and
            # nowhere else. A verse that does not align exactly is left alone.
            canonical = mushaf_vocalisation(run) if not dry_run else None
            if canonical and canonical != run:
                out = out.replace(run, canonical)
                stats["from_mushaf"] += 1
                stats["marks_added"] += mark_count(canonical) - mark_count(run)
            else:
                stats["quranic"] += 1
            continue
        if dry_run:
            stats["vowelled"] += 1
            continue
        try:
            candidate = ask(run)
        except Exception as e:  # one bad run must never cost the whole book
            stats["refused"] += 1
            refusals.append({"run": run[:60], "reason": f"model error: {e}"})
            continue
        reason = rejection_reason(run, candidate)
        if reason:
            # Refusals are RECORDED, not swallowed. A passage the model keeps
            # failing on is a passage a human should look at directly.
            stats["refused"] += 1
            refusals.append({"run": run[:60], "reason": reason})
            continue
        out = out.replace(run, candidate)
        stats["vowelled"] += 1
        stats["marks_added"] += mark_count(candidate) - mark_count(run)

    # ── The third layer: words the prose discusses AS words ───────────────────
    # `"باطن," "an inward"` — the book arguing about what a word means, with the
    # word set in quotes. Below the run floor, so the sweep above skipped every
    # one; and belonging to no glossary entry, so `vowel_glossary` never saw them
    # either. They are the passages where marks matter MOST, because the sentence
    # is literally about how the word is read. The English beside each one names
    # the reading — noun or verb, this sense or that — so it goes to the model as
    # context and the answer is a citation form, the same as a glossary term.
    stats["lexical"] = 0
    lexical: dict[str, str] = {}
    for token in dict.fromkeys(m.group(1).strip() for m in _LEXICAL_TOKEN_RE.finditer(out)):
        # THREE Arabic letters minimum, and this floor is not stylistic. The book
        # discusses individual LETTERS as well as words — `(ع)` — and a one-letter
        # token is a substring of half the Arabic in the edition. The first cut had
        # no floor, took `ع`, and the substitution below (then a plain str.replace)
        # put a fatha on every ayn in nine chapters: `جَعَلَ` came out `جَعََلَ`. Reverted;
        # the floor and the anchored substitution below are both that bug's fix.
        letters = [c for c in token if ARABIC_LETTER_RE.match(c)]
        if len(letters) < 3 or mark_density(token) >= VOWELLED_DENSITY:
            continue
        if dry_run:
            stats["lexical"] += 1
            continue
        # A window around the FIRST occurrence: enough English for the gloss that
        # follows the word to be in it, which is what disambiguates the reading.
        at = out.find(token)
        context = out[max(0, at - 90) : at + len(token) + 90].replace("\n", " ")
        try:
            candidate = _clean(_gemini(CITATION_SYSTEM, f"{token}\n\ncontext: {context}"))
        except Exception as e:
            stats["refused"] += 1
            refusals.append({"run": token, "reason": f"model error: {e}"})
            continue
        reason = rejection_reason(token, candidate)
        if reason:
            stats["refused"] += 1
            refusals.append({"run": token, "reason": reason})
            continue
        lexical[token] = candidate
        stats["lexical"] += 1
        stats["marks_added"] += mark_count(candidate) - mark_count(token)

    # ANCHORED substitution, never a free str.replace. `قمر` is a substring of
    # `القمر` and of any number of longer words; replacing it globally would mark
    # the middle of words the sweep never looked at. Rewriting through the same
    # pattern that found each token confines every edit to a delimited position.
    if lexical:
        out = _LEXICAL_TOKEN_RE.sub(lambda m: lexical.get(m.group(1).strip(), m.group(1)), out)

    stats["refusals"] = refusals
    return out, stats


def vowel_book(book_dir: Path, *, log: Callable[[str], None] = print, dry_run: bool = False) -> dict:
    """Vowel `book/book.md` in place. Returns the run's stats."""
    md = book_dir / "book" / "book.md"
    if not md.exists():
        log("vowelling: no book.md - skipped")
        return {"vowelled": 0}
    before = md.read_text(encoding="utf-8")
    after, stats = vowel_text(before, log=log, dry_run=dry_run)
    if not dry_run and after != before:
        md.write_text(after, encoding="utf-8")
    # The refusal list is the human-facing half of this pass: every run the gate
    # turned away, with the reason, so a passage the model cannot vowel is
    # visible rather than quietly left bare.
    report = book_dir / "_system" / "book-vowelling.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(
        f"vowelling: {stats.get('vowelled', 0)} run(s) marked "
        f"(+{stats.get('marks_added', 0)} marks), {stats.get('from_mushaf', 0)} set from the mushaf, "
        f"{stats.get('lexical', 0)} discussed word(s), {stats.get('already', 0)} already vowelled, "
        f"{stats.get('quranic', 0)} Qur'anic left as printed, {stats.get('refused', 0)} refused"
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Vowel every bare non-Qur'anic Arabic run in a book.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true", help="report what would be vowelled; spend nothing")
    a = ap.parse_args()
    book_dir = content_dir(a.slug)
    if not book_dir or not book_dir.exists():
        print(f"Book not found: {a.slug}", file=sys.stderr)
        return 1
    vowel_book(book_dir, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
