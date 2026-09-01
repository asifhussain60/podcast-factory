#!/usr/bin/env python3
"""build_book_brief.py — write (or rewrite) a book's "The Book in Brief" section.

The same code path `compose_book_v2` runs as apparatus step 5f —
`_book_brief.apply_brief`, imported, never copied — reachable over a `book/book.md`
already on disk. It exists for the reason `apply_book_apparatus.py` exists: the
alternative way to reach a finished book's apparatus is a full re-compose, which
re-runs model passes over prose nobody asked to change.

It is also the tuning loop. A brief is judged by reading it, and `--force --words`
re-authors one for a few dollars against a cached analysis rather than re-reading
the book.

USAGE

    python3 scripts/podcast/build_book_brief.py <slug-or-BOOK_DIR>
    python3 scripts/podcast/build_book_brief.py <slug> --words 1500
    python3 scripts/podcast/build_book_brief.py <slug> --force        # re-draft, keep the analysis
    python3 scripts/podcast/build_book_brief.py <slug> --reanalyse    # re-read the book too
    python3 scripts/podcast/build_book_brief.py <slug> --plan-only    # rank, allocate, print; no draft
    python3 scripts/podcast/build_book_brief.py <slug> --dry-run      # author, print, do not touch book.md

EXIT CODES

    0  — a brief is in book.md (or was printed, under --dry-run / --plan-only)
    1  — no book.md, or the brief was refused by its gate
    2  — couldn't resolve the book directory
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def _resolve_book_dir(slug_or_dir: str) -> Path | None:
    """Same resolution the ship gate uses — bucket-aware, slug or path."""
    p = Path(slug_or_dir)
    if p.is_dir() and (p / "book").exists():
        return p.resolve()
    try:
        import publish_to_library as P

        ws = P.resolve_workspace(slug_or_dir)
        return ws.resolve() if ws.is_dir() else None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("slug", help="book slug or BOOK_DIR")
    ap.add_argument("--words", type=int, default=None, help="hard maximum, overriding the book's configured preset")
    ap.add_argument("--force", action="store_true", help="re-draft even if a cached brief exists")
    ap.add_argument("--reanalyse", action="store_true", help="re-read every section (implies --force; costs the most)")
    ap.add_argument("--plan-only", action="store_true", help="rank and allocate, print the plan, write nothing")
    ap.add_argument("--dry-run", action="store_true", help="author and print, but leave book.md untouched")
    ap.add_argument("--json", action="store_true", help="emit a JSON result")
    args = ap.parse_args()

    book_dir = _resolve_book_dir(args.slug)
    if book_dir is None:
        print(f"ERROR: could not resolve a book directory for {args.slug!r}", file=sys.stderr)
        return 2
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        print(f"ERROR: {book_md} does not exist — compose the book first", file=sys.stderr)
        return 1

    import _book_brief as B
    from _book_brief_rank import plan as build_plan

    total = B.target_words(book_dir, override=args.words)
    strategy = B.strategy_for(book_dir)
    sections = B.sections_for_brief(book_md.read_text(encoding="utf-8"), exclude=B.excluded_sections(book_dir))
    print(
        f"  brief: {book_dir.name} · {len(book_md.read_text(encoding='utf-8').split()):,} words "
        f"· {len(sections)} sections · strategy={strategy} · budget={total:,} words"
    )

    if args.plan_only:
        analyses = B.analyse_sections(book_dir, force=args.reanalyse)
        plan = build_plan(analyses, total_words=total)
        # Persisted, not only printed. The plan is the artifact worth arguing with,
        # and a `--plan-only` run that left nothing behind meant the only way to
        # look at one again was to pay for a draft.
        out = book_dir / "_system" / "brief"
        out.mkdir(parents=True, exist_ok=True)
        (out / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        # Printed rather than only written, because the plan is the artifact a
        # person actually argues with: it is where "this got 40 words and that got
        # 400" is decided, and reading it is cheaper than reading the draft it
        # produces and inferring the decision backwards.
        for idx in sorted(plan["section_words"]):
            pts = [p for p in plan["retained"] if p["section_index"] == idx]
            title = pts[0]["section_title"] if pts else f"section {idx}"
            print(f"\n  {title} — {plan['section_words'][idx]} words, {len(pts)} points")
            for p in sorted(pts, key=lambda q: -q["score"]):
                print(f"    {p['score']:5.2f} {p['tier']:<11} {p['text'][:96]}")
        print(
            f"\n  {len(plan['points'])} points ranked · {len(plan['retained'])} retained "
            f"· {len(plan['essential_ids'])} essential · {len(plan['dropped'])} dropped"
        )
        if args.json:
            print(json.dumps({"plan": plan["section_words"], "retained": len(plan["retained"])}, indent=2))
        return 0

    if args.dry_run:
        result = B.author_brief(
            book_dir, force=args.force or args.reanalyse, reanalyse=args.reanalyse, words=args.words
        )
        text = result.get("text") or ""
        if not text:
            print(f"  brief: refused — {result.get('reason')}", file=sys.stderr)
            return 1
        print("\n" + B.BRIEF_HEADING + "\n\n" + text + "\n")
        if args.json:
            print(json.dumps(result.get("report") or {}, indent=2))
        return 0

    result = B.apply_brief(book_dir, force=args.force or args.reanalyse, reanalyse=args.reanalyse, words=args.words)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result.get("applied"):
        print(f"  brief: refused — {result.get('reason')}", file=sys.stderr)
        return 1
    print(f"  brief: written into {book_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
