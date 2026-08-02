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

from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: E402

from _arabic_coverage import arabic_run_spans  # noqa: E402
from _paths import content_dir  # noqa: E402
from _vowel_recovery import (  # noqa: E402
    askable as segment_askable,
)
from _vowel_recovery import (  # noqa: E402
    assemble as assemble_recovery,
)
from _vowel_recovery import (  # noqa: E402
    plan as recovery_plan,
)
from _vowel_recovery import segment_answer  # noqa: E402
from _vowelling import (  # noqa: E402
    VOWELLED_DENSITY,
    is_arabic_passage,
    is_vowelling_candidate,
    mark_count,
    mark_density,
    reflow_to_source_whitespace,
    reflow_words_to_source_whitespace,
    rejection_reason,
)
from _vowelling_prompts import CITATION_SYSTEM, SYSTEM  # noqa: E402

# Vocalisation is one independent call per run and the runs do not interact, so
# the whole pass is embarrassingly parallel. It has to be: an Arabic SOURCE
# stream carries 279-1,340 candidate runs where a composed book carries a few
# dozen, and sequentially that is hours of wall clock for one book. Same width
# `vowel_glossary` already uses against the same endpoint.
DEFAULT_WORKERS = 8

MODEL = "gemini-2.5-pro"
"""Vocalisation is a reasoning task, not a lookup: the reading of an ambiguous
verb comes from the surrounding sense. Flash guesses; Pro deliberates."""

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


def _gemini(system: str, user: str, *, model: str = MODEL, max_output_tokens: int = 4000) -> str:
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
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_output_tokens},
        }
    ).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    # 2.5 Pro draws its thinking from the SAME token allowance as the answer, so a
    # long run can return a candidate carrying only thought parts, or no `parts`
    # key at all. Indexing straight into `parts[0]["text"]` raised KeyError on
    # those and they were recorded as "model error: 'parts'" — a spurious refusal
    # of a passage nothing was actually wrong with. Read the first non-thought
    # part instead, and treat an answerless response as empty so the caller can
    # retry it with more room.
    for candidate in data.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            if part.get("thought"):
                continue
            text = part.get("text", "")
            if text.strip():
                return text
    return ""


def _ask_with_headroom(system: str, run: str) -> str:
    """One vocalisation, retried once with a bigger budget if it came back empty.

    An empty answer from 2.5 Pro nearly always means thinking consumed the token
    allowance rather than that the passage is unvowellable, and the runs it
    happens on are the long ones — exactly the passages worth having.
    """
    out = _clean(_gemini(system, run))
    if out:
        return out
    return _clean(_gemini(system, run, max_output_tokens=12000))


def _clean(raw: str) -> str:
    """Models like to wrap a one-line answer in a fence or quotes."""
    text = raw.strip().removeprefix("```").removesuffix("```").strip()
    for line in text.splitlines():
        stripped = line.strip().strip("\"'«»")
        if stripped and any("؀" <= c <= "ۿ" for c in stripped):
            return stripped
    return ""


def vowel_runs(
    text: str,
    *,
    log: Callable[[str], None] = print,
    dry_run: bool = False,
    call: Callable[[str], str] | None = None,
    workers: int = DEFAULT_WORKERS,
) -> tuple[str, dict]:
    """Return ``text`` with every bare non-Qur'anic Arabic RUN vowelled.

    Layers one and two only — the run sweep and the mushaf. The third layer, the
    lexical sweep in `vowel_lexical`, is deliberately NOT here: it looks for bare
    Arabic quoted inside ENGLISH prose, and on an Arabic-only source stream its
    delimiters match footnote apparatus rather than words under discussion. A
    caller with English prose (`vowel_text`) wants both; a caller holding an OCR
    of an Arabic book wants only this.

    Replacement is by exact string, run by run, so nothing outside an Arabic run
    can be touched -- the English prose the runs sit in is never sent anywhere.
    A run that occurs several times is vowelled once and replaced everywhere,
    which is correct: the same sentence has the same reading.
    """
    from _mushaf import is_quranic, mushaf_available, mushaf_vocalisation

    ask = call or (lambda run: _ask_with_headroom(SYSTEM, run))
    have_mushaf = mushaf_available()
    if not have_mushaf:
        # Degrade LOUDLY, not silently: without the mushaf every Qur'anic run
        # reads as ordinary Arabic and would be re-vowelled from a model, which
        # is the one case where the canonical text is strictly better.
        log("vowelling: canonical mushaf unavailable - Qur'anic runs cannot be identified; skipping")
        return text, {"skipped": "no mushaf", "vowelled": 0}

    stats = {
        "vowelled": 0,
        "marks_added": 0,
        "already": 0,
        "quranic": 0,
        "from_mushaf": 0,
        "refused": 0,
        # Runs that a refusal would have left completely bare and the salvage pass
        # got most of the marks onto anyway.
        "recovered": 0,
        "in_chars": 0,
        "out_chars": 0,
    }
    refusals: list[dict] = []
    refused_runs: list[tuple[str, str]] = []

    # ── Sort each distinct run into what will answer for it ───────────────────
    pending: list[str] = []
    replacements: list[tuple[str, str]] = []
    from_mushaf: set[str] = set()
    for run in dict.fromkeys(arabic_run_spans(text)):
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
                # The mushaf joins a verse's words with single spaces, so a verse
                # the book prints across two lines comes back as one. Lay it back
                # onto the source's own whitespace — by WORD, since the Uthmani
                # letters differ and the character-level reflow cannot align them.
                canonical = reflow_words_to_source_whitespace(run, canonical)
                replacements.append((run, canonical))
                from_mushaf.add(run)
            else:
                stats["quranic"] += 1
            continue
        if dry_run:
            stats["vowelled"] += 1
            continue
        pending.append(run)

    # ── Ask for all of them at once ───────────────────────────────────────────
    if pending:
        from _engine import ENGINE_GEMINI, TASK_VOWEL, engine_guard

        engine_guard(TASK_VOWEL, ENGINE_GEMINI)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {pool.submit(ask, run): run for run in pending}
            for future in as_completed(futures):
                run = futures[future]
                try:
                    candidate = future.result()
                except Exception as e:  # one bad run must never cost the whole book
                    stats["refused"] += 1
                    refusals.append({"run": run[:60], "reason": f"model error: {e}"})
                    continue
                stats["in_chars"] += len(run)
                stats["out_chars"] += len(candidate or "")
                # The model answers on one line however many the run occupied, and
                # `skeleton` normalises whitespace, so the collapse would sail
                # through the gate. Put the source's own whitespace back first.
                candidate = reflow_to_source_whitespace(run, candidate)
                reason = rejection_reason(run, candidate)
                if reason:
                    # Refusals are RECORDED, not swallowed. A passage the model keeps
                    # failing on is a passage a human should look at directly — but
                    # the whole run no longer goes bare over it. See the salvage pass
                    # below; this list is what it works from.
                    refused_runs.append((run, reason))
                    continue
                replacements.append((run, candidate))

    # ── Salvage: the same gate, on smaller pieces ─────────────────────────────
    # A refusal used to cost the entire run. On the first real source pass that was
    # 94 runs, 92 of them refused over a SINGLE changed letter, leaving bare holes in
    # the middle of otherwise-marked paragraphs. Cut each refused run at its sentence
    # boundaries and re-ask piece by piece: only the fragment actually holding the
    # disputed letter stays bare. The gate is untouched — `_vowel_recovery` calls the
    # same `rejection_reason` on each piece and again on the assembly, and fails
    # closed to the original run if either says no. See that module's header.
    if refused_runs and not dry_run:
        jobs: list[tuple[int, int, str]] = []
        plans: dict[int, list[str]] = {}
        for idx, (run, _reason) in enumerate(refused_runs):
            parts = recovery_plan(run)
            if parts is None:
                continue
            plans[idx] = parts
            jobs += [(idx, i, part) for i, part in enumerate(parts) if segment_askable(part)]
        answers: dict[int, dict[int, str]] = {}
        if jobs:
            log(f"vowelling: retrying {len(plans)} refused run(s) as {len(jobs)} fragment(s)")
            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = {pool.submit(ask, part): (idx, i, part) for idx, i, part in jobs}
                for future in as_completed(futures):
                    idx, i, part = futures[future]
                    try:
                        marked = segment_answer(part, future.result())
                    except Exception:
                        continue  # one bad fragment must not cost its neighbours
                    if marked:
                        answers.setdefault(idx, {})[i] = marked
        for idx, (run, reason) in enumerate(refused_runs):
            got = answers.get(idx)
            if not got:
                stats["refused"] += 1
                refusals.append({"run": run[:60], "reason": reason})
                continue
            rebuilt, still_bare = assemble_recovery(run, plans[idx], got)
            if rebuilt == run:
                stats["refused"] += 1
                refusals.append({"run": run[:60], "reason": reason})
                continue
            replacements.append((run, rebuilt))
            stats["recovered"] += 1
            # The fragment is what a human should look at, not the paragraph it sits
            # in — so the refusal we keep is narrowed to it, with the reason that
            # explains why this much of the run is still bare.
            for fragment in still_bare:
                stats["refused"] += 1
                refusals.append({"run": fragment[:60], "reason": reason, "partial": True})
    elif refused_runs:
        for run, reason in refused_runs:
            stats["refused"] += 1
            refusals.append({"run": run[:60], "reason": reason})

    # ── Apply LONGEST RUN FIRST ───────────────────────────────────────────────
    # Two distinct runs can stand in a substring relation — `قال العالم` occurs on
    # its own and inside `قال العالم، ودموعه تنحدر`, 37 such pairs in one book's
    # OCR. Replacing the short one first rewrites the long one's opening, after
    # which the long run's own `str.replace` matches nothing and silently no-ops
    # while still being counted. Longest-first leaves no shorter run able to eat
    # a longer one's prefix. Sorting also makes the output independent of the
    # order the concurrent calls happened to finish in.
    for run, replacement in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        text = text.replace(run, replacement)
        if run in from_mushaf:
            stats["from_mushaf"] += 1
        else:
            stats["vowelled"] += 1
        stats["marks_added"] += mark_count(replacement) - mark_count(run)

    # The mushaf substitutions are the ONE place where letters legitimately change
    # — the canonical text is Uthmani. Recording each pair lets a caller checking
    # the whole file's skeleton account for them instead of reading a correct
    # verse replacement as the file having been corrupted.
    stats["mushaf_pairs"] = [[run, rep] for run, rep in replacements if run in from_mushaf]
    stats["refusals"] = refusals
    return text, stats


def vowel_lexical(
    text: str,
    *,
    dry_run: bool = False,
    stats: dict | None = None,
) -> tuple[str, dict]:
    """The third layer: bare Arabic words that ENGLISH prose discusses AS words.

    Split out of `vowel_text` so a caller holding an Arabic-only source can skip
    it. Its delimiters (quotes, parentheses) mean "the author put this word here
    to be looked at" in English prose; in an Arabic critical edition the same
    brackets hold footnote markers and manuscript-variant apparatus.
    """
    out = text
    stats = stats if stats is not None else {"marks_added": 0, "refused": 0}
    stats.setdefault("marks_added", 0)
    stats.setdefault("refused", 0)
    refusals: list[dict] = stats.setdefault("refusals", [])
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


def vowel_text(
    text: str,
    *,
    log: Callable[[str], None] = print,
    dry_run: bool = False,
    call: Callable[[str], str] | None = None,
    workers: int = DEFAULT_WORKERS,
) -> tuple[str, dict]:
    """All three layers, for text that is ENGLISH prose carrying Arabic.

    The composed book's own path. `vowel_runs` handles the quoted passages and
    scripture; `vowel_lexical` then handles the individual words the prose
    discusses AS words, which fall below the run floor by design.
    """
    out, stats = vowel_runs(text, log=log, dry_run=dry_run, call=call, workers=workers)
    if stats.get("skipped"):  # no mushaf — vowel_runs already said so
        return out, stats
    return vowel_lexical(out, dry_run=dry_run, stats=stats)


def record_spend(book_dir: Path, *, phase: str, step: str, stats: dict) -> None:
    """Put this pass's Gemini spend and model choice on the book's ledgers.

    Neither was recorded before, so a pass that makes hundreds of metered calls
    was invisible in `cost-ledger.jsonl` and in `model-provenance.jsonl` — the two
    files the cost policy and the provenance audit read. Best-effort on both
    counts: a ledger problem must never cost a finished vowelling.
    """
    if not stats.get("in_chars") and not stats.get("out_chars"):
        return
    try:
        from _cost_ledger import append_gemini_cost

        append_gemini_cost(
            book_dir=book_dir,
            phase=phase,
            step=step,
            model=MODEL,
            in_chars=stats.get("in_chars", 0),
            out_chars=stats.get("out_chars", 0),
        )
    except Exception as e:  # pragma: no cover - ledger trouble is never fatal
        print(f"    WARN: cost-ledger append failed: {e}", file=sys.stderr)
    try:
        from _authoring._core import record_model_provenance

        record_model_provenance(book_dir, phase=phase, step=step, model=MODEL)
    except Exception as e:  # pragma: no cover
        print(f"    WARN: provenance append failed: {e}", file=sys.stderr)


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
    if not dry_run:
        record_spend(book_dir, phase="0book-compose", step="5a-vowelling", stats=stats)
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


def _books_with_a_composed_book() -> list[Path]:
    """Every book carrying a `book/book.md`, for the `--all` sweep.

    Walks `content/` directly rather than a slug registry so a nested volume
    (`asaas-al-taveel/vol-01`) is found at whatever depth it sits.
    """
    from _paths import REPO_ROOT

    return sorted({md.parent.parent for md in (REPO_ROOT / "content").glob("*/**/book/book.md")})


def main() -> int:
    ap = argparse.ArgumentParser(description="Vowel every bare non-Qur'anic Arabic run in a book.")
    ap.add_argument("--slug", help="one book; omit and pass --all to sweep every composed book")
    ap.add_argument("--all", action="store_true", help="sweep every book that has a composed book.md")
    ap.add_argument("--dry-run", action="store_true", help="report what would be vowelled; spend nothing")
    a = ap.parse_args()
    if bool(a.slug) == bool(a.all):
        print("Pass exactly one of --slug <slug> or --all.", file=sys.stderr)
        return 2

    if a.all:
        targets = _books_with_a_composed_book()
        if not targets:
            print("No composed books found.", file=sys.stderr)
            return 1
    else:
        book_dir = content_dir(a.slug)
        if not book_dir or not book_dir.exists():
            print(f"Book not found: {a.slug}", file=sys.stderr)
            return 1
        targets = [book_dir]

    for book_dir in targets:
        # Bucket/slug, not just the leaf: two different books both live at a leaf
        # named `vol-01`, so the leaf alone does not say which one this is.
        from _paths import REPO_ROOT

        try:
            label = book_dir.relative_to(REPO_ROOT / "content")
        except ValueError:  # pragma: no cover - a book outside content/
            label = book_dir
        print(f"==> {label}")
        vowel_book(book_dir, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
