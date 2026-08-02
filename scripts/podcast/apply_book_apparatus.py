#!/usr/bin/env python3
"""apply_book_apparatus.py — bring an existing book's apparatus up to current rules.

Runs the DETERMINISTIC TAIL of a compose over a `book/book.md` already on disk:
the Composer-edit replay, the transliteration fold, the Qur'anic Arabic, the
surah-named citations, the glossary overlay, the vowelling, American spelling,
the introduction, the audits, the comprehension bridges, the honorific convention
and the paragraph alignment. It is the same code `compose_book_v2` runs as its own
tail — `_book_apparatus.apply_book_apparatus`, imported, never copied — so the two
paths cannot drift.

WHAT IT DOES NOT DO is re-run the model passes over the prose. That is the whole
point. A rule that changes how Arabic reaches the page (2026-08-02: "there should
be zero English transliteration of Arabic terms ... in book.md") applies to every
book already written, and reaching them through a full re-compose would mean:

  * rewriting eight of nine chapters of `the-master-and-the-disciple`, an approved
    reference edition, to change bracket contents;
  * running the fluency pass over `al-anwaar-al-lateefah` and `asaas-al-taveel`,
    neither of which DECLARES a narrative_frame, so both would resolve to the
    conservative default and be rewritten into the wrong grammatical person;
  * hours of model time on the two Mukhtasar volumes (206k words) to change none
    of their prose.

Every step is idempotent, so running this twice changes nothing the first run did
not. A step that fails is recorded to `_system/compose-skips.json` and read back
by gate B8 — this path is not a way around the ship gates.

USAGE

    python3 scripts/podcast/apply_book_apparatus.py <slug-or-BOOK_DIR>
    python3 scripts/podcast/apply_book_apparatus.py <slug> --force
    python3 scripts/podcast/apply_book_apparatus.py <slug> --json

EXIT CODES

    0  — the apparatus ran (check compose-skips.json / B8 for step-level failures)
    1  — no book.md to work on, or the apparatus raised
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
    ap.add_argument(
        "--force",
        action="store_true",
        help="pass force through to the Composer-edit replay (reports conflicts rather than skipping)",
    )
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

    # Run-scoped, exactly as compose treats it: this file answers "what went wrong
    # THIS run", so a skip fixed three runs ago must not still read as current.
    (book_dir / "_system" / "compose-skips.json").unlink(missing_ok=True)

    before = book_md.read_text(encoding="utf-8")
    print(f"  apparatus: {book_dir.name} · {len(before.split()):,} words")

    from _book_apparatus import apply_book_apparatus

    try:
        apply_book_apparatus(book_dir, log=print, force=args.force)
    except Exception as exc:  # noqa: BLE001 - report it, never a traceback at the CLI
        print(f"ERROR: apparatus raised: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    after = book_md.read_text(encoding="utf-8")
    changed = after != before

    from _compose_skips import verdict

    ok, note = verdict(book_dir)
    result = {
        "slug": book_dir.name,
        "changed": changed,
        "words_before": len(before.split()),
        "words_after": len(after.split()),
        "steps_ok": ok,
        "steps_note": note,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"  apparatus: book.md {'CHANGED' if changed else 'unchanged'}")
        print(f"  apparatus: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
