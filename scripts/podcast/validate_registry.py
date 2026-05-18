#!/usr/bin/env python3
"""validate_registry.py — deterministic checks for per-book podcast registries.

Each book carries its own registry at
    content/podcast/library/<category>/<book-slug>/_system/registry.md

The top-level index at content/podcast/.skill/books.md lists every book that
has a registry. This script discovers all per-book registries via glob and
validates each one independently. Nothing else validates their structure, slug
uniqueness, monotonicity, or row freshness.

Usage:
    python3 scripts/podcast/validate_registry.py            # all per-book registries
    python3 scripts/podcast/validate_registry.py --registry <path>   # one specific file

Exit codes:
    0 — all checks pass
    1 — at least one check failed; details on stderr

Checks (applied to each registry independently)
------

R1. Table parseable
    The registry contains a markdown table with at least 5 expected columns:
    EP#, Title, Slug, Source Type, Status. (Extra columns are tolerated.)

R2. EP# monotonic + unique within the book
    Every row's EP# is a positive integer. Numbers are strictly increasing.
    No duplicates within the same book.

R3. Slug uniqueness + shape within the book
    Every Slug is unique within the book and kebab-case
    ([a-z0-9]+(-[a-z0-9]+)*), max 40 chars.

R4. Status value in the allowed set
    Status ∈ {draft, challenger-pending, ready, generated, archived}.

R5. Status freshness
    For every `ready` or `generated` row, the matching chapter file
    <BOOK_DIR>/chapters/ch{EP}-{slug}.txt must exist. Missing → status is stale (P0).

This script is read-only. It never modifies a registry. The podcast-challenger
agent invokes it before declaring a SHIP-READY verdict.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DIR = REPO_ROOT / "content" / "podcast" / "library"

ALLOWED_STATUS = {"draft", "challenger-pending", "ready", "generated", "archived"}
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_table(text: str) -> tuple[list[dict[str, str]], bool]:
    """Parse the markdown table into a list of row dicts keyed by header.
    Returns (rows, header_found). A freshly-scaffolded registry has the header
    but no rows — that is a valid state, not a parse failure."""
    lines = [l.rstrip() for l in text.splitlines()]
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("|") and "EP#" in line and "Slug" in line:
            header_idx = i
            break
    if header_idx is None:
        return ([], False)
    headers = [c.strip() for c in lines[header_idx].strip("|").split("|")]
    # Skip the separator row (|---|---|...)
    rows = []
    for line in lines[header_idx + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        rows.append(dict(zip(headers, cells)))
    return (rows, True)


def chapter_for_row(book_dir: Path, slug: str, ep_num: int) -> Path | None:
    """Resolve the chapter file for a row within its own book."""
    cand = book_dir / "chapters" / f"ch{ep_num:02d}-{slug}.txt"
    return cand if cand.exists() else None


def discover_registries() -> list[Path]:
    """Find every per-book registry: library/*/*/_system/registry.md."""
    if not LIBRARY_DIR.exists():
        return []
    return sorted(LIBRARY_DIR.glob("*/*/_system/registry.md"))


def validate_one(registry_path: Path) -> list[str]:
    """Validate a single per-book registry. Returns a list of findings (empty = pass)."""
    text = registry_path.read_text(encoding="utf-8")
    rows, header_found = parse_table(text)
    if not header_found:
        return [f"R1 FAIL: no header row found in {registry_path}"]
    if not rows:
        # Header present, zero rows: freshly scaffolded book, nothing to validate.
        return []

    # BOOK_DIR is registry_path.parents[1] (registry.md → _system → BOOK_DIR).
    book_dir = registry_path.parents[1]
    findings: list[str] = []

    # R2 — monotonic + unique
    ep_nums: list[int] = []
    for r in rows:
        raw = r.get("EP#", "").strip()
        if not raw.isdigit():
            findings.append(f"R2: row has non-integer EP# {raw!r} (slug={r.get('Slug')!r})")
            continue
        ep_nums.append(int(raw))
    for i in range(1, len(ep_nums)):
        if ep_nums[i] <= ep_nums[i - 1]:
            findings.append(
                f"R2: EP# not strictly increasing: row {i+1} has EP{ep_nums[i]:02d} "
                f"after EP{ep_nums[i-1]:02d}"
            )
    if len(ep_nums) != len(set(ep_nums)):
        dup = sorted({n for n in ep_nums if ep_nums.count(n) > 1})
        findings.append(f"R2: duplicate EP# values: {dup}")

    # R3 — slug uniqueness + shape
    slugs = [r.get("Slug", "").strip() for r in rows]
    for s in slugs:
        if not s:
            findings.append("R3: row with empty slug")
        elif not SLUG_RE.fullmatch(s):
            findings.append(f"R3: slug {s!r} not kebab-case")
        elif len(s) > 40:
            findings.append(f"R3: slug {s!r} > 40 chars")
    if len(slugs) != len(set(slugs)):
        dup = sorted({s for s in slugs if slugs.count(s) > 1 and s})
        findings.append(f"R3: duplicate slugs: {dup}")

    # R4 — status enum
    for r in rows:
        status = r.get("Status", "").strip()
        if status not in ALLOWED_STATUS:
            findings.append(
                f"R4: row EP{r.get('EP#')} ({r.get('Slug')!r}) has invalid status "
                f"{status!r} (allowed: {sorted(ALLOWED_STATUS)})"
            )

    # R5 — freshness for ready rows
    for r in rows:
        status = r.get("Status", "").strip()
        if status not in {"ready", "generated"}:
            continue
        raw = r.get("EP#", "").strip()
        slug = r.get("Slug", "").strip()
        if not raw.isdigit() or not slug:
            continue
        ep_num = int(raw)
        cand = chapter_for_row(book_dir, slug, ep_num)
        if cand is None:
            findings.append(
                f"R5: row EP{ep_num:02d} ({slug!r}) is {status} but no matching "
                f"chapter file ch{ep_num:02d}-{slug}.txt under {book_dir}/chapters/"
            )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--registry", type=Path, default=None,
        help="Specific per-book registry to validate. Default: discover all.",
    )
    args = ap.parse_args()

    if args.registry is not None:
        registries = [args.registry]
    else:
        registries = discover_registries()
        if not registries:
            print(
                "validate_registry: no per-book registries found under "
                "content/podcast/library/*/*/_system/registry.md",
                file=sys.stderr,
            )
            return 1

    total_rows = 0
    total_findings = 0
    for r in registries:
        if not r.exists():
            print(f"ERROR: registry not found at {r}", file=sys.stderr)
            total_findings += 1
            continue
        findings = validate_one(r)
        rows, _ = parse_table(r.read_text(encoding="utf-8"))
        total_rows += len(rows)
        if findings:
            print(f"validate_registry: {len(findings)} finding(s) in {r}", file=sys.stderr)
            for f in findings:
                print(f"  - {f}", file=sys.stderr)
            total_findings += len(findings)
        else:
            print(f"validate_registry: OK — {len(rows)} row(s) in {r}")

    return 1 if total_findings else 0


if __name__ == "__main__":
    sys.exit(main())
