#!/usr/bin/env python3
"""vowel_glossary.py — put the vowel marks on a book's glossary terms.

THE LAYER `vowel_book.py` CANNOT REACH. That pass vowels Arabic RUNS in the
prose — quoted verses, hadith, sayings. The Arabic woven INTO the English
sentences is not in book.md at all when it runs: `_book_inline_arabic.py` inserts
it from `_system/glossary.yml`, so a bare glossary prints bare terms however well
the quotations are marked. On `the-master-and-the-disciple` that was 65 of 68
terms — `سيدنا`, `الطور`, `جعفر بن منصور اليمن` — every name in the book,
unreadable, beside quotations that had just been vowelled. They are bare for a
good reason: `fill_glossary_arabic.py` takes each term from the OCR of a bare
critical edition. That is where they come from, not where they must stay.

CITATION FORM, NOT THE MUSHAF'S FORM, and this is the one real judgment here.
Several terms are Qur'anic words — `الطور`, `البيت المعمور` — so it is tempting to
take the canonical vocalisation the way `vowel_book.py` does for verses. That
would be WRONG at this size. The mushaf's marks include the final case ending the
verse's own syntax demands: Q 52:1 sets `وَٱلطُّورِ` in the genitive because an oath
particle governs it. A glossary term appears in the reading edition as a
parenthetical beside its English — "Mount Tur (الطور)" — where no such syntax
governs anything, so the correct form is the one a dictionary prints: fully
marked internally, final letter left in pause. That is also what the book's own
romanisation already shows (`Ṭūr`, not `Ṭūri`), so the two halves of the gloss
agree instead of quietly disagreeing about case.

SAME GATE, no exception. `_vowelling.rejection_reason` refuses any answer whose
consonantal skeleton is not byte-identical to the term it replaces. What differs
from the prose pass is only the CANDIDATE rule: `is_vowelling_candidate` floors a
run at eight skeleton characters because a two-word Arabic fragment in running
prose is usually a stray, but a glossary term is a deliberate lexical unit and
`الله` is four. The floor does not apply here; "has Arabic and is not already
marked" does.

WRITES SURGICALLY. Only the `arabic_script:` values change, by line, leaving the
rest of the file byte-identical. Deliberately NOT a YAML round-trip through
`fill_glossary_arabic.emit_glossary_yml`: that writer emits five fields and the
live glossaries carry more (`annotation_class`, `annotation_reason`,
`english_equivalent`), so round-tripping would silently delete the annotation
policy's own decisions.

    python3 scripts/podcast/vowel_glossary.py --slug the-master-and-the-disciple
    python3 scripts/podcast/vowel_glossary.py --slug <slug> --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import content_dir  # noqa: E402
from _vowelling import ARABIC_RE, VOWELLED_DENSITY, mark_count, mark_density, rejection_reason  # noqa: E402
from vowel_book import CITATION_SYSTEM, _clean, _gemini  # noqa: E402

# The prompt lives in vowel_book.py, shared with the lexical-token sweep there:
# both jobs ask for the same thing (a citation form for one term), and two copies
# of it is how the two would drift apart on the next refinement.
SYSTEM = CITATION_SYSTEM

#: Terms between durable writes. Small enough that a kill costs seconds of work,
#: large enough that a 177-term run does not rewrite the file 177 times.
_FLUSH_EVERY = 20

_LINE_RE = re.compile(r"^(?P<indent>\s*)arabic_script:\s*(?P<value>.*?)\s*$")


def _unquote(raw: str) -> tuple[str, bool]:
    """The value, and whether the file had it quoted."""
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\"), True
    return raw, False


def needs_marks(term: str) -> bool:
    """Arabic, and not already marked. No length floor — see the module docstring."""
    t = (term or "").strip()
    return bool(t) and bool(ARABIC_RE.search(t)) and mark_density(t) < VOWELLED_DENSITY


def vowel_glossary(
    book_dir: Path,
    *,
    log: Callable[[str], None] = print,
    dry_run: bool = False,
    call: Callable[[str, str], str] | None = None,
) -> dict:
    """Vowel `_system/glossary.yml` in place. Returns the run's stats."""
    path = book_dir / "_system" / "glossary.yml"
    if not path.exists():
        log("glossary vowelling: no glossary.yml - skipped")
        return {"vowelled": 0}

    text = path.read_text(encoding="utf-8")
    # The romanisation for each term, so the model is told the intended reading
    # rather than guessing it. Read from the SAME lines the values live on, by
    # walking the file, so no YAML parser and no round-trip is involved.
    lines = text.split("\n")
    translit_by_term: dict[str, str] = {}
    pending = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("transliteration:"):
            pending = _unquote(stripped[len("transliteration:") :].strip())[0]
        elif stripped.startswith("arabic_script:"):
            value = _unquote(stripped[len("arabic_script:") :].strip())[0]
            if value:
                translit_by_term.setdefault(value, pending)
            pending = ""

    ask = call or (lambda term, translit: _clean(_gemini(SYSTEM, f"{term}\n\nromanisation: {translit}")))
    stats = {"vowelled": 0, "marks_added": 0, "already": 0, "refused": 0}
    refusals: list[dict] = []
    resolved: dict[str, str] = {}

    todo = [(t, r) for t, r in translit_by_term.items() if needs_marks(t)]
    stats["already"] = len(translit_by_term) - len(todo)
    if dry_run:
        stats["vowelled"] = len(todo)
        todo = []

    def one(pair: tuple[str, str]) -> tuple[str, str | None, str | None]:
        """(term, vowelled, refusal) — never raises, so one bad term costs one term."""
        term, translit = pair
        try:
            candidate = ask(term, translit)
        except Exception as e:
            return term, None, f"model error: {e}"
        reason = rejection_reason(term, candidate)
        return (term, None, reason) if reason else (term, candidate, None)

    # In parallel, because these are 60-odd independent one-word calls and doing
    # them in sequence took longer than ten minutes — long enough that the run was
    # killed before it wrote anything. Eight at a time: enough to make the wall
    # clock reasonable, few enough not to trip the API's rate limiting, which
    # would turn a slow run into a refused one.
    def flush() -> None:
        """Write what has been resolved so far, in place, line by line.

        Called every `_FLUSH_EVERY` completions rather than once at the end
        (2026-08-02). The pass used to write only after `pool.map` had drained,
        so a run killed part-way — the exact failure the parallelism was added to
        avoid — lost every term it had already paid for. `needs_marks` makes the
        next run skip whatever landed, so flushing turns a kill from "start
        again" into "carry on". Rewriting the same lines twice is idempotent.
        """
        if not resolved or dry_run:
            return
        current = path.read_text(encoding="utf-8").split("\n")
        out: list[str] = []
        for line in current:
            m = _LINE_RE.match(line)
            if m:
                value, was_quoted = _unquote(m.group("value"))
                if value in resolved:
                    new = resolved[value]
                    line = f"{m.group('indent')}arabic_script: " + (f'"{new}"' if was_quoted else new)
            out.append(line)
        path.write_text("\n".join(out), encoding="utf-8")

    if todo:
        done = 0
        with ThreadPoolExecutor(max_workers=8) as pool:
            for term, candidate, refusal in pool.map(one, todo):
                done += 1
                if refusal:
                    stats["refused"] += 1
                    refusals.append({"term": term, "reason": refusal})
                    continue
                resolved[term] = candidate or ""
                stats["vowelled"] += 1
                stats["marks_added"] += mark_count(candidate or "") - mark_count(term)
                if done % _FLUSH_EVERY == 0:
                    flush()
                    log(f"    glossary vowelling: {done}/{len(todo)} terms")

    flush()

    stats["refusals"] = refusals
    report = book_dir / "_system" / "glossary-vowelling.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(
        f"glossary vowelling: {stats['vowelled']} term(s) marked (+{stats['marks_added']} marks), "
        f"{stats['already']} already vowelled, {stats['refused']} refused"
    )
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Vowel every bare Arabic term in a book's glossary.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true", help="report what would be vowelled; spend nothing")
    a = ap.parse_args()
    book_dir = content_dir(a.slug)
    if not book_dir or not book_dir.exists():
        print(f"Book not found: {a.slug}", file=sys.stderr)
        return 1
    vowel_glossary(book_dir, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
