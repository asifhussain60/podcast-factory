#!/usr/bin/env python3
"""student_reader_notes.py — run the student-reader lane over a book's chapters.

Reads each chapter as someone meeting the text cold, finds where a student would
be stopped — a passage they cannot resolve, or an assertion the book offers
nothing behind — and asks the Ismaili Scholar about it. What gets filed is the
Scholar's answer. Asif, 2026-08-06.

TWO MODELS, ONE PERSONA, and the split is deliberate (Asif, 2026-08-06). The
finding is Claude's, on the Max subscription, like every other authoring phase in
this repo. The card is the Scholar's, through the same grounding, the same word
cap and the same citation resolution as the Explain button on the Book Composer —
reached through ``_scholar_bridge``, never reimplemented here. The button stays on
Gemini because it answers while a person waits; ``claude -p`` is tens of seconds
and would make Explain feel broken. Only the writer differs; every step on either
side of it is shared code.

WHERE THE JUDGEMENT LIVES. This file runs the model and touches disk; it decides
nothing. Every rule — which defects count, how they rank, how many a chapter may
carry, what a note is called — is in ``_student_reader``, and the only writer is
``_student_reader_store``, which cannot express the write that destroyed a curated
set on 2026-07-28. A model may notice; it may not select.

AN UNGROUNDED PASSAGE IS RESEARCHED, NOT DROPPED (Asif, 2026-08-06, revising his
own earlier rule the same day). ``prepare`` reports how many knowledge-base atoms
bore on the passage; where that is zero the question goes to Gemini with
Google-Search grounding instead — the only paid call in this lane, and the only
model call behind the bridge, because ``claude -p`` here runs without WebSearch
or WebFetch and cannot do it. Measured on this book: 21 of 23 passages ground, so
this is the exception path by construction. The card opens with a line saying it
was researched outside the library and ends with its sources, because on a
religious text the weight a reader gives an explanation depends on where it came
from. A search that finds nothing to stand on still yields NO card — a best guess
under a scholar's byline is the thing he asked not to have.

WHAT IT NEVER READS. The book's introduction. Asif's rule: notes go on the
chapters, never on the preface or the introduction. The introduction is the one
unnumbered ``##`` section, and it is identified that way rather than by index —
"skip the first" is true of this book today and would silently start skipping
chapter 1 of a book that opens differently.

EVIDENCE the FINDING pass may see: KSESSIONS transcripts (mirror.db
``fts_sessions``, 606) and the Fatimid-Ismaili doctrine atoms (knowledge.db, 93),
as orientation for what the tradition discusses — the Scholar does its own
retrieval afterwards and is the only thing that cites. The Kashkole Wisdom topics
are deliberately absent: all 1,347 are Urdu at source and rendering them into
English is its own queued pass (`kashkole-urdu-to-english` in pending-work), not
something to improvise per note.

Usage:
    python3 scripts/podcast/student_reader_notes.py <slug> [--chapter KEY] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _book_companion import book_chapters  # noqa: E402
from _book_companion_prompts import parse_cards  # noqa: E402
from _paths import resolve_content  # noqa: E402
from _scholar_bridge import ScholarBridgeError, finish, parse, prepare, research  # noqa: E402
from _student_reader import (  # noqa: E402
    chapter_budget,
    dedupe,
    gate_finding,
    select,
    to_companion_note,
)
from _student_reader_prompts import build_prompt, evidence_block  # noqa: E402
from _student_reader_store import already_current, file_notes, owned_notes, section_key  # noqa: E402

_TIMEOUT = 900
#: The tightening pass reads a card that already exists; it needs far less room
#: than authoring one, and a long timeout there only delays a failure.
_TIGHTEN_TIMEOUT = 300
#: Sent to the Scholar as the paragraph around the passage, matching what the
#: Explain button sends from the browser.
_CONTEXT_CHARS = 600

#: A chapter heading the pass never reads. Matched on the RESOLVED key, not on
#: position — see the module docstring.
SKIP_KEYS = frozenset({"introduction to the book", "preface", "introduction"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _book_title(book_dir: Path, slug: str) -> str:
    """The book's own title, for the Scholar's turn. The slug is the fallback —
    a wrong-looking title is better than none, and none is what a missing
    meta.yml would otherwise give the model."""
    meta = book_dir / "meta.yml"
    if meta.exists():
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip("\"'") or slug
    return slug


# ─── asking the Scholar ──────────────────────────────────────────────────────
def _paragraph_around(prose: str, quote: str) -> str:
    """The passage's own paragraph, as the Explain button sends it.

    Same unit and same 600-character cap as the browser: the Scholar's grounding
    retrieval runs on the passage plus this, and widening it to the chapter would
    swamp the query with whatever else the chapter mentions. The chapter still
    reaches the model — as ``chapterContext``, for orientation.
    """
    i = prose.find(quote)
    if i == -1:
        return quote[:_CONTEXT_CHARS]
    start = prose.rfind("\n\n", 0, i)
    end = prose.find("\n\n", i)
    para = prose[(0 if start == -1 else start + 2) : (len(prose) if end == -1 else end)]
    return " ".join(para.split())[:_CONTEXT_CHARS]


def _research_card(
    finding: dict[str, Any],
    prep: dict[str, Any],
    ch: dict[str, str],
    context: str,
    book_title: str,
    log,
) -> dict[str, Any] | None:
    """The paid route, for a passage the knowledge base cannot reach.

    No tightening pass: the grounded reply comes back as plain prose rather than
    the JSON envelope (Google-Search grounding and JSON mode cannot both be on),
    and a second call to polish a card that is already the fallback is spending
    money to gild an exception. `finishCard` still caps it and names its verses.
    """
    quote = str(finding.get("quote") or "").strip()
    question = str(finding.get("question") or "").strip()
    try:
        card = research(
            concept=quote,
            context=context,
            chapter_context=ch["prose"],
            book_title=book_title,
            question=question,
        )
    except ScholarBridgeError as exc:
        # TWO DIFFERENT THINGS, and conflating them is a real error rather than
        # a tidiness point. "researched but unsourced" is a DECISION — the web
        # had nothing to stand on and Asif's rule is no card. Anything else is a
        # FAILURE, and on 2026-08-06 that was a Gemini 503 demand spike recorded
        # as though the search had come back empty: a card silently lost to a
        # busy server, filed in the report as an editorial outcome.
        if "unsourced" in str(exc):
            log(f"      · researched and unsourced, dropped: {quote[:48]}")
            return {"dropped": "unsourced", "quote": quote, "question": question}
        log(f"      · research FAILED (not a verdict) on {quote[:40]!r}: {exc}")
        return None

    sources = list(card.get("sources") or [])
    log(f"      · researched online ({len(sources)} source(s)): {quote[:48]}")
    return {
        "note": to_companion_note(
            finding,
            ch["key"],
            anchor=str(prep.get("anchor") or ""),
            body=str(card.get("body") or ""),
            etymology=list(card.get("etymology") or []),
        ),
        "question": question,
        "grounded": 0,
        "researched": sources,
        "tightened": False,
    }


def ask_scholar(
    finding: dict[str, Any], ch: dict[str, str], book_dir: Path, book_title: str, log
) -> dict[str, Any] | None:
    """One finding, answered — or None, with the reason logged.

    TWO ROUTES, decided by whether the library knows anything about the passage:

      grounded    prepare (free, local SQL) -> claude explain -> claude tighten
                  -> finish (free). No money changes hands.
      ungrounded  prepare -> RESEARCH, which is Gemini with Google-Search
                  grounding and the only paid call in this lane. Asif's decision
                  (2026-08-06): a passage his corpus cannot reach should be
                  looked up rather than skipped, and the card says so at the top.

    The grounding check sits before either model runs, so the choice costs
    nothing to make.
    """
    from _authoring._core import _run_claude_p_with_retry, pure_text_call_options

    quote = str(finding.get("quote") or "").strip()
    question = str(finding.get("question") or "").strip()
    step = f"scholar-{ch['key'][:18]}-{quote[:16]}"
    context = _paragraph_around(ch["prose"], quote)

    try:
        prep = prepare(
            concept=quote,
            context=context,
            chapter_context=ch["prose"],
            book_title=book_title,
            question=question,
        )
    except ScholarBridgeError as exc:
        log(f"      · bridge refused {quote[:40]!r}: {exc}")
        return None

    if not prep.get("grounded") and not prep.get("morphology"):
        return _research_card(finding, prep, ch, context, book_title, log)

    rc, out, err = _run_claude_p_with_retry(
        f"{prep['system']}\n\n---\n\n{prep['user']}",
        timeout=_TIMEOUT,
        book_dir=book_dir,
        phase="0book-student-reader",
        step=step,
        log=log,
        **pure_text_call_options(),
    )
    if rc != 0:
        log(f"      · scholar failed on {quote[:40]!r}: rc={rc} {err[:120]}")
        return None

    # Read the reply BEFORE tightening it. The tightener is asked to return "the
    # same explanation, better articulated" — hand it the JSON envelope instead
    # and it will faithfully rewrite that, so a reply the parser could not read
    # comes back looking like prose and gets filed as a card made of JSON. That
    # shipped once on this book (2026-08-06) before the order was fixed.
    try:
        parsed = parse(raw=out)
    except ScholarBridgeError as exc:
        log(f"      · unreadable answer for {quote[:40]!r}: {exc}")
        return None

    # The tightening pass is an improvement, never a dependency: a failure here
    # leaves the untightened card standing, and the guards on the far side reject
    # a rewrite that lost an Arabic run or a citation.
    body = str(parsed.get("body") or "")
    tightened = ""
    if len(body) >= int(prep.get("tightenMinChars") or 400):
        trc, tout, _ = _run_claude_p_with_retry(
            f"{prep['tightenSystem']}\n\n---\n\n{body}",
            timeout=_TIGHTEN_TIMEOUT,
            book_dir=book_dir,
            phase="0book-student-reader",
            step=f"{step}-tighten",
            log=log,
            **pure_text_call_options(),
        )
        tightened = tout if trc == 0 else ""

    try:
        card = finish(
            body=body,
            etymology=list(parsed.get("etymology") or []),
            tightened_raw=tightened,
        )
    except ScholarBridgeError as exc:
        log(f"      · could not finish the card for {quote[:40]!r}: {exc}")
        return None

    return {
        "note": to_companion_note(
            finding,
            ch["key"],
            anchor=str(prep.get("anchor") or ""),
            body=str(card.get("body") or ""),
            etymology=list(card.get("etymology") or []),
        ),
        "question": question,
        "grounded": prep.get("grounded", 0),
        "tightened": bool(card.get("tightened")),
    }


# ─── the run ─────────────────────────────────────────────────────────────────
def run_chapter(
    book_dir: Path,
    slug: str,
    ch: dict[str, str],
    *,
    dry_run: bool,
    force: bool,
    top_up: bool,
    book_title: str,
    log,
) -> dict[str, Any]:
    from _authoring._core import _run_claude_p_with_retry, pure_text_call_options

    file_key = section_key(ch["title"])
    full_budget = chapter_budget(len(ch["prose"].split()))
    have = owned_notes(book_dir, file_key, slug)

    # TOP UP — fill a chapter that came back under its budget, without disturbing
    # what is already there. Distinct from --force, which re-reads a chapter from
    # scratch: this asks only for the SHORTFALL and tells the model what has
    # already been marked, so it looks for what is still unnoted rather than
    # re-finding the same difficulties. A chapter already at its budget is left
    # alone; asking for zero more would spend a model call to file nothing.
    if top_up:
        budget = full_budget - len(have)
        if budget <= 0:
            log(f"    student-reader: {ch['title'][:44]} — already at its budget of {full_budget}, left as it is")
            return {"chapter": ch["key"], "file": file_key, "title": ch["title"], "skipped": "at-budget", "filed": 0}
    else:
        budget = full_budget
        # Do not ask twice about prose that has not changed. See
        # _student_reader_store.already_current — this, not the merge, is what
        # makes a re-run reproduce its own output instead of accumulating.
        if not force and already_current(book_dir, file_key, slug, ch["prose"]):
            log(f"    student-reader: {ch['title'][:44]} — unchanged since the last read, left as it is")
            return {"chapter": ch["key"], "file": file_key, "title": ch["title"], "skipped": "unchanged", "filed": 0}

    already = [str(n.get("quote") or "") for n in have if n.get("quote")] if top_up else None
    prompt = build_prompt(ch["title"], ch["prose"], evidence_block(ch["title"], ch["prose"]), budget, already)

    rc, out, err = _run_claude_p_with_retry(
        prompt,
        timeout=_TIMEOUT,
        book_dir=book_dir,
        phase="0book-student-reader",
        step=f"student-{ch['key'][:24]}",
        log=log,
        **pure_text_call_options(),
    )
    if rc != 0:
        return {"chapter": ch["key"], "error": f"claude -p rc={rc}: {err[:160]}", "filed": 0}

    candidates = parse_cards(out)
    gated, dropped = [], []
    for c in candidates:
        ok, reasons = gate_finding(c, ch["prose"])
        (gated if ok else dropped).append(c if ok else {"quote": c.get("quote"), "reasons": reasons})

    chosen = select(dedupe(gated), ch["prose"], budget)

    # A DRY RUN STOPS HERE, and that is its whole value: the questions are what
    # this lane decides, and they can be read before a single card is paid for.
    if dry_run:
        log(
            f"    student-reader: {ch['title'][:44]} — budget {budget}, "
            f"{len(candidates)} proposed, {len(dropped)} failed the gate, {len(chosen)} would be asked"
        )
        for c in chosen:
            log(f"      ? [{c.get('defect')}] {c.get('question')}")
            log(f"        on: {str(c.get('quote'))[:70]}")
        return {
            "chapter": ch["key"],
            "file": file_key,
            "title": ch["title"],
            "budget": budget,
            "proposed": len(candidates),
            "gated_out": dropped,
            "filed": 0,
            "questions": [
                {"defect": c.get("defect"), "question": c.get("question"), "quote": c.get("quote")} for c in chosen
            ],
        }

    answered = [ask_scholar(c, ch, book_dir, book_title, log) for c in chosen]
    notes = [a["note"] for a in answered if a and a.get("note")]
    unsourced = [a for a in answered if a and a.get("dropped") == "unsourced"]
    researched = [a for a in answered if a and a.get("researched")]
    unanswered = sum(1 for a in answered if a is None)

    created = refreshed = withdrawn = 0
    if notes or (force and have):
        # Prune only under --force: that is the flag meaning "read this chapter
        # again from scratch", so a finding this pass no longer makes is one it
        # should withdraw. Anything Asif accepted survives regardless — see
        # _student_reader_store.prune_owned.
        created, refreshed, withdrawn = file_notes(
            book_dir, file_key, slug, notes, now=_now(), prose=ch["prose"], prune=force
        )

    log(
        f"    student-reader: {ch['title'][:44]} — "
        f"{'top-up ' + str(budget) + ' of ' + str(full_budget) if top_up else 'budget ' + str(budget)}, "
        f"{len(candidates)} proposed, {len(dropped)} failed the gate, "
        f"{len(researched)} researched online, {len(unsourced)} unsourced and dropped, {len(notes)} filed"
        + (f", {withdrawn} withdrawn" if withdrawn else "")
    )
    return {
        "chapter": ch["key"],
        "file": file_key,
        "title": ch["title"],
        "budget": budget,
        "full_budget": full_budget,
        "already_had": len(have),
        "proposed": len(candidates),
        "gated_out": dropped,
        "unsourced": [{"quote": u["quote"], "question": u["question"]} for u in unsourced],
        "researched": [{"quote": r["note"]["quote"], "sources": r["researched"]} for r in researched],
        "unanswered": unanswered,
        "filed": len(notes),
        "created": created,
        "refreshed": refreshed,
        "withdrawn": withdrawn,
        "notes": [
            {
                "id": a["note"]["id"],
                "defect": a["note"]["source"]["ref"],
                "quote": a["note"]["quote"],
                "question": a["question"],
                "grounded": a["grounded"],
                "researched": bool(a.get("researched")),
            }
            for a in answered
            if a and a.get("note")
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--chapter", help="one chapter key; default is every chapter but the introduction")
    ap.add_argument("--dry-run", action="store_true", help="propose and gate, write nothing")
    ap.add_argument("--force", action="store_true", help="re-read a chapter whose prose has not changed")
    ap.add_argument(
        "--top-up",
        action="store_true",
        help="ask only for the shortfall on a chapter under its budget, keeping what is already filed",
    )
    args = ap.parse_args()

    try:
        book_dir = resolve_content(args.slug)
    except Exception as exc:
        print(f"no such book: {args.slug} ({exc})", file=sys.stderr)
        return 2
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        print(f"no book.md in {book_dir}", file=sys.stderr)
        return 2

    chapters = [c for c in book_chapters(book_md.read_text(encoding="utf-8")) if c["key"] not in SKIP_KEYS]
    if args.chapter:
        chapters = [c for c in chapters if c["key"] == args.chapter]
        if not chapters:
            print(f"no such chapter (or it is skipped by rule): {args.chapter}", file=sys.stderr)
            return 2

    book_title = _book_title(book_dir, args.slug)
    print(f"==> student-reader: {args.slug} — {len(chapters)} chapter(s){' (dry run)' if args.dry_run else ''}")
    results = [
        run_chapter(
            book_dir,
            args.slug,
            c,
            dry_run=args.dry_run,
            force=args.force,
            top_up=args.top_up,
            book_title=book_title,
            log=print,
        )
        for c in chapters
    ]

    report = {
        "schema": "book.student-reader/v1",
        "generated_at": _now(),
        "dry_run": args.dry_run,
        "chapters": results,
        "filed_total": sum(r.get("filed", 0) for r in results),
    }
    if not args.dry_run:
        out = book_dir / "_system" / "student-reader-report.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"    report: {out}")
    print(f"==> {report['filed_total']} note(s) filed across {len(results)} chapter(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
