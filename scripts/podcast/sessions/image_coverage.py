"""Prove every image a Sessions book's reading edition uses is on disk in THIS
repo — before the Drive folder they were copied from is deleted.

`ingest.py` reports `images_missing` at ingest time, against the Drive corpus
that still existed then. That report is stale the moment either thing moves: a
chapter can be re-composed, articulated, or edited in the Book Composer after
ingest, and any of those can add or move an image reference; a Drive file that
was there for that report can be moved or renamed since. Neither is hypothetical
here — Love Of The Prophet's book.md has been rewritten twice since its last
ingest (fluency, then the read-along corrector). So the only report worth
trusting before an irreversible deletion is one taken FRESH, against what the
book actually says NOW, and against nothing but the repo's own disk.

This checks ONE thing: every `![...](images/<sid>/<file>)` reference in
`book/book.md` resolves to a real, non-empty file under `book/`. It does not
re-open the Drive folder at all — the repo is the copy that must outlive it, so
the repo is what gets asked. A reference to anything other than a relative
`images/...` path (an external URL, an absolute path) is flagged rather than
silently passed, because neither survives a Drive deletion either.

Usage:
    python3 scripts/podcast/sessions/image_coverage.py [slug ...]

With no slug, every Sessions-lane book is checked. Exit code is non-zero if any
book is missing an image — the caller (a human, before running `rm` on the
Drive folder) is the one who decides what that means.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _paths import resolve_content  # noqa: E402

from sessions.series import SERIES  # noqa: E402

# A markdown image, matched whole — the same shape `convert.localise_images`
# rewrites into, so this checks what THAT step promised rather than a
# reimplementation of the pattern that could drift from it.
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*(\S+?)\s*\)")


def referenced_images(book_dir: Path) -> list[str]:
    """Every image target `book/book.md` names, in the order it names them."""
    path = book_dir / "book" / "book.md"
    if not path.exists():
        return []
    return _MD_IMAGE_RE.findall(path.read_text(encoding="utf-8"))


def check_book(slug: str) -> dict:
    """Referenced vs. present, for one book. Never touches the Drive."""
    book_dir = resolve_content(slug)
    refs = referenced_images(book_dir)

    missing: list[str] = []
    empty: list[str] = []
    not_relative: list[str] = []

    for ref in refs:
        if ref.startswith(("http://", "https://", "/")):
            not_relative.append(ref)
            continue
        target = book_dir / "book" / ref
        if not target.exists():
            missing.append(ref)
        elif target.stat().st_size == 0:
            empty.append(ref)

    return {
        "slug": slug,
        "referenced": len(refs),
        "missing": missing,
        "empty": empty,
        "not_relative": not_relative,
        "ok": not (missing or empty or not_relative),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slugs", nargs="*")
    args = parser.parse_args(argv)

    slugs = args.slugs or sorted(SERIES)
    unknown = [s for s in slugs if s not in SERIES]
    if unknown:
        parser.error(f"not a Sessions-lane slug: {', '.join(unknown)} (choose from {', '.join(sorted(SERIES))})")

    reports = [check_book(slug) for slug in slugs]
    print(json.dumps(reports, indent=2, ensure_ascii=False))

    for report in reports:
        status = "OK" if report["ok"] else "MISSING IMAGES"
        print(f"  {report['slug']}: {report['referenced']} referenced — {status}", file=sys.stderr)

    return 0 if all(r["ok"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
