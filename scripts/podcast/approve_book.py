"""approve_book.py — Wave I (I4): CLI approval for human review gates.

Writes approved=true + approved_at to _system/review-gate.json.
Use when approving via CLI rather than the Astro Book Review UI.

CLI usage:
    python3 scripts/podcast/approve_book.py <slug>
    python3 scripts/podcast/approve_book.py kitab-al-riyad
    python3 scripts/podcast/approve_book.py the-master-and-the-disciple
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _paths import find_content  # bucket-aware resolver (type-first content layout)


def approve_book(slug: str) -> int:
    """Set approved=true on the book's review-gate.json. Returns 0 on success."""
    hit = find_content(slug)
    if not hit:
        print(f"ERROR: Book not found: {slug}", file=sys.stderr)
        print(f"  (searched all buckets via _paths.find_content)", file=sys.stderr)
        return 1
    book_dir = Path(hit[2])

    gate_path = book_dir / "_system" / "review-gate.json"
    if not gate_path.exists():
        print(f"ERROR: No review-gate.json found for {slug}.", file=sys.stderr)
        print(f"  Run Phase 06a first: python3 scripts/podcast/phases/source_review_gate.py <book-dir>", file=sys.stderr)
        return 1

    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    if gate.get("approved"):
        print(f"Book {slug!r} is already approved (approved_at={gate.get('approved_at')}).")
        return 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gate["approved"] = True
    gate["approved_at"] = now

    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Approved: {slug!r} at {now}")
    print(f"  Warnings on file: {len(gate.get('warnings', []))}")
    print(f"  Next: run --resume {slug} to continue the pipeline from Phase 06a.")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/podcast/approve_book.py <book-slug>", file=sys.stderr)
        sys.exit(1)
    slug = sys.argv[1]
    sys.exit(approve_book(slug))


if __name__ == "__main__":
    main()
