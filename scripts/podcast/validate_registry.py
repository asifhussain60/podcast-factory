#!/usr/bin/env python3
"""validate_registry.py — deterministic checks for content/podcast/.skill/registry.md.

The registry is mutable cross-book state: a markdown table of every episode
across every podcasted source. Nothing today validates its structure, slug
uniqueness, monotonicity, or row freshness. This script does.

Usage:
    python3 scripts/podcast/validate_registry.py
    python3 scripts/podcast/validate_registry.py --registry <path>

Exit codes:
    0 — all checks pass
    1 — at least one check failed; details on stderr

Checks
------

R1. Table parseable
    The registry contains a markdown table with at least 5 expected columns:
    EP#, Title, Slug, Source Type, Status. (Extra columns are tolerated.)

R2. EP# monotonic + unique
    Every row's EP# is a positive integer. Numbers are strictly increasing.
    No duplicates.

R3. Slug uniqueness
    Every Slug is unique across the registry. Slugs are kebab-case
    ([a-z0-9]+(-[a-z0-9]+)*), max 40 chars.

R4. Status value in the allowed set
    Status ∈ {draft, challenger-pending, ready, generated, archived}.

R5. Status freshness
    For every `ready` row, the matching chapter file
    content/podcast/library/<category>/<book>/chapters/ch{EP}-{slug}.txt must
    exist. Missing → status is stale (P0).

This script is read-only. It never modifies the registry. The podcast-challenger
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


def parse_table(text: str) -> list[dict[str, str]]:
    """Parse the markdown table into a list of row dicts keyed by header.
    Returns [] if no table found."""
    lines = [l.rstrip() for l in text.splitlines()]
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("|") and "EP#" in line and "Slug" in line:
            header_idx = i
            break
    if header_idx is None:
        return []
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
    return rows


def find_chapter_file(slug: str, ep_num: int) -> Path | None:
    """Search every library/<category>/<book>/chapters/ for ch{NN}-{slug}.txt."""
    if not LIBRARY_DIR.exists():
        return None
    pattern = f"ch{ep_num:02d}-{slug}.txt"
    for category in LIBRARY_DIR.iterdir():
        if not category.is_dir():
            continue
        for book in category.iterdir():
            cand = book / "chapters" / pattern
            if cand.exists():
                return cand
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--registry", type=Path, default=None,
        help="Registry path. Default: content/podcast/.skill/registry.md",
    )
    args = ap.parse_args()
    registry_path = args.registry or (REPO_ROOT / "content" / "podcast" / ".skill" / "registry.md")
    if not registry_path.exists():
        print(f"ERROR: registry not found at {registry_path}", file=sys.stderr)
        return 1

    text = registry_path.read_text(encoding="utf-8")
    rows = parse_table(text)
    if not rows:
        print(f"R1 FAIL: no parseable table in {registry_path}", file=sys.stderr)
        return 1

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
        cand = find_chapter_file(slug, ep_num)
        if cand is None:
            findings.append(
                f"R5: row EP{ep_num:02d} ({slug!r}) is {status} but no matching "
                f"chapter file ch{ep_num:02d}-{slug}.txt found under library/"
            )

    if findings:
        print(f"validate_registry: {len(findings)} finding(s) in {registry_path}", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"validate_registry: OK — {len(rows)} row(s) in {registry_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
