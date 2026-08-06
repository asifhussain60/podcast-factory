#!/usr/bin/env python3
"""student_reader_notes.py — run the student-reader lane over a book's chapters.

Reads each chapter as someone meeting the text cold, and files a Companion note
wherever a student would be stopped: a passage they cannot resolve, or an
assertion the book offers nothing behind. Asif, 2026-08-06.

WHERE THE JUDGEMENT LIVES. This file runs the model and touches disk; it decides
nothing. Every rule — which defects count, how they rank, how many a chapter may
carry, what a note is called, what it may claim — is in ``_student_reader``, and
the only writer is ``_student_reader_store``, which cannot express the write that
destroyed a curated set on 2026-07-28. A model may notice; it may not select.

WHAT IT NEVER READS. The book's introduction. Asif's rule: notes go on the
chapters, never on the preface or the introduction. The introduction is the one
unnumbered ``##`` section, and it is identified that way rather than by index —
"skip the first" is true of this book today and would silently start skipping
chapter 1 of a book that opens differently.

EVIDENCE. Three English sources, in this order, all already in the repo:
KSESSIONS transcripts (mirror.db ``fts_sessions``, 606 of them), the Fatimid-
Ismaili doctrine atoms (knowledge.db, 93), and the canonical mushaf. The Kashkole
Wisdom topics are deliberately absent: all 1,347 are Urdu at source and rendering
them into English is its own queued pass (`kashkole-urdu-to-english` in
pending-work), not something to improvise per note.

Usage:
    python3 scripts/podcast/student_reader_notes.py <slug> [--chapter KEY] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _book_companion import book_chapters  # noqa: E402
from _book_companion_prompts import parse_cards  # noqa: E402
from _paths import REPO_ROOT, resolve_content  # noqa: E402
from _student_reader import (  # noqa: E402
    DEFECT_KINDS,
    chapter_budget,
    dedupe,
    gate_note,
    select,
    to_companion_note,
)
from _student_reader_store import file_notes  # noqa: E402

_TIMEOUT = 900
_KB = REPO_ROOT / "content" / "knowledge-base"

#: A chapter heading the pass never reads. Matched on the RESOLVED key, not on
#: position — see the module docstring.
SKIP_KEYS = frozenset({"introduction to the book", "preface", "introduction"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── evidence ────────────────────────────────────────────────────────────────
def _fts_sessions(terms: str, limit: int = 4) -> list[dict[str, str]]:
    """Session transcripts that mention the chapter's own vocabulary."""
    db = _KB / "mirror.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT session_name, snippet(fts_sessions, 1, '', '', '…', 40) "
            "FROM fts_sessions WHERE fts_sessions MATCH ? LIMIT ?",
            (terms, limit),
        ).fetchall()
        conn.close()
    except Exception:
        # An unusable corpus must leave the pass grounded in the chapter alone,
        # never stop it: a missing session index is not a reason to skip a book.
        return []
    return [{"corpus": "ksessions", "ref": r[0], "text": r[1]} for r in rows]


def _doctrine_atoms(limit: int = 40) -> list[dict[str, str]]:
    db = _KB / "knowledge.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT id, body FROM atoms WHERE type='doctrine' AND tradition='fatimid-ismaili' LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception:
        return []
    out = []
    for aid, body in rows:
        try:
            parsed = json.loads(body) if isinstance(body, str) else body
            text = parsed.get("statement") or parsed.get("text") or str(parsed)
        except Exception:
            text = str(body)
        out.append({"corpus": "doctrine", "ref": str(aid), "text": str(text)[:400]})
    return out


def _evidence_block(title: str, prose: str) -> str:
    """What the model is allowed to cite, and nothing else."""
    # Chapter vocabulary as the retrieval query: the longest words the chapter
    # actually uses. Deterministic — same chapter, same query, same rows.
    words = sorted({w.strip(".,;:—\"'()").lower() for w in prose.split() if len(w) > 7})[:8]
    query = " OR ".join(w for w in words if w.isalpha()) or title
    rows = _fts_sessions(query) + _doctrine_atoms()
    if not rows:
        return "(no corroborating material was located — say so rather than supplying any)"
    return "\n".join(f"[{r['corpus']}:{r['ref']}] {r['text']}" for r in rows)


# ─── the prompt ──────────────────────────────────────────────────────────────
def build_prompt(title: str, prose: str, evidence: str, budget: int) -> str:
    kinds = "\n".join(f"  - {k}" for k in DEFECT_KINDS)
    return f"""You are reading one chapter of a translated Ismaili teaching text as a STUDENT
meeting it for the first time — not as a teacher explaining it. You are an
intelligent, careful reader: you can tell a passage that is genuinely hard to
resolve from one that is merely unfamiliar, and you do NOT flag the second.

Mark ONLY the places a careful first-time reader is actually stopped. Two kinds
of stop, and nothing else:
  (a) you cannot tell what is meant — the sentence admits more than one reading
      and the chapter never resolves it, or a term or referent is used as if
      already known;
  (b) the chapter asserts something and offers nothing behind it.

Report at most {budget} findings for this chapter. Fewer is correct when fewer
are real — an empty list is a valid answer and is better than a padded one.

Classify each into EXACTLY one of these, using no other word:
{kinds}

EVIDENCE you may cite. These are the only sources that exist for you. Cite one
ONLY if it genuinely bears on the passage. If nothing here bears on it, do not
cite, do not reason from memory, and do not deliver a verdict on whether the
teaching is true — write the question a student would ask instead. You are not
ruling on the tradition; you are recording where the chapter left you.

{evidence}

Return ONLY a JSON array, no preamble and no code fence. Each element:
{{"defect": "<one of the kinds above>",
  "quote": "<a VERBATIM span of at least 4 words copied exactly from the chapter — this is where the note attaches>",
  "anchor": "<a short label, 2-6 words>",
  "body": "<25-220 words: what stopped you, in plain English, addressed to nobody>",
  "claims_support": <true only if you are citing material that bears on it>,
  "citations": [{{"corpus": "ksessions|doctrine|quran|hadith", "ref": "<the reference exactly as given above>"}}]}}

CHAPTER — {title}

{prose}
"""


# ─── the run ─────────────────────────────────────────────────────────────────
def run_chapter(book_dir: Path, slug: str, ch: dict[str, str], *, dry_run: bool, log) -> dict[str, Any]:
    from _authoring._core import _run_claude_p_with_retry

    budget = chapter_budget(len(ch["prose"].split()))
    prompt = build_prompt(ch["title"], ch["prose"], _evidence_block(ch["title"], ch["prose"]), budget)

    rc, out, err = _run_claude_p_with_retry(
        prompt,
        timeout=_TIMEOUT,
        book_dir=book_dir,
        phase="0book-student-reader",
        step=f"student-{ch['key'][:24]}",
        log=log,
    )
    if rc != 0:
        return {"chapter": ch["key"], "error": f"claude -p rc={rc}: {err[:160]}", "filed": 0}

    candidates = parse_cards(out)
    gated, dropped = [], []
    for c in candidates:
        ok, reasons = gate_note(c, ch["prose"])
        (gated if ok else dropped).append(c if ok else {"quote": c.get("quote"), "reasons": reasons})

    chosen = select(dedupe(gated), ch["prose"], budget)
    notes = [to_companion_note(c, ch["key"]) for c in chosen]

    created = refreshed = 0
    if not dry_run and notes:
        created, refreshed = file_notes(book_dir, ch["key"], slug, notes, now=_now())

    log(
        f"    student-reader: {ch['title'][:44]} — budget {budget}, "
        f"{len(candidates)} proposed, {len(dropped)} failed the gate, {len(notes)} filed"
    )
    return {
        "chapter": ch["key"],
        "title": ch["title"],
        "budget": budget,
        "proposed": len(candidates),
        "gated_out": dropped,
        "filed": len(notes),
        "created": created,
        "refreshed": refreshed,
        "notes": [{"id": n["id"], "defect": n["source"]["ref"], "quote": n["quote"]} for n in notes],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--chapter", help="one chapter key; default is every chapter but the introduction")
    ap.add_argument("--dry-run", action="store_true", help="propose and gate, write nothing")
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

    print(f"==> student-reader: {args.slug} — {len(chapters)} chapter(s){' (dry run)' if args.dry_run else ''}")
    results = [run_chapter(book_dir, args.slug, c, dry_run=args.dry_run, log=print) for c in chapters]

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
