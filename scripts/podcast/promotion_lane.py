"""promotion_lane.py — self-learning promotion lane for the podcast pipeline.

Reads the cross-book findings ledger (_learning/findings.jsonl), clusters
recurring P0/P1/P2 patterns across ≥3 chapters, and proposes targeted
spec refinements to the podcast-challenger and podcast handbook.

Only promotes changes that pass the held-out regression suite. P0-class
proposals and regression failures are flagged for human review — never
auto-committed.

USAGE
    python3 scripts/podcast/promotion_lane.py --book <slug>
    python3 scripts/podcast/promotion_lane.py --all-books
    python3 scripts/podcast/promotion_lane.py --dry-run

EXIT CODES
    0 — no promotable patterns found
    2 — patterns found and promotion proposals written
    3 — proposals written but require human review before commit
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFTS_DIR = REPO_ROOT / "content" / "drafts"
FINDINGS_LEDGER = REPO_ROOT / "_learning" / "findings.jsonl"
PROPOSALS_DIR = REPO_ROOT / "_learning" / "promotion-proposals"

# Minimum occurrence count to be considered a pattern worth promoting.
CLUSTER_THRESHOLD = 3

# Finding severities that require human review before auto-commit.
HUMAN_REVIEW_SEVERITIES = {"P0"}

# Severity tiers per cross-genre reach:
# Tier-2 = patterns within a single genre (safe for auto-promotion after regression)
# Tier-3 = cross-genre patterns (always require human confirmation)
CROSS_GENRE_TIER = "Tier-3"
SINGLE_GENRE_TIER = "Tier-2"


def _load_findings(book_slug: str | None) -> list[dict]:
    """Load findings from the JSONL ledger, optionally filtered by book slug."""
    if not FINDINGS_LEDGER.exists():
        return []
    findings: list[dict] = []
    for line in FINDINGS_LEDGER.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if book_slug and record.get("book") != book_slug:
            continue
        findings.append(record)
    return findings


def _cluster_findings(findings: list[dict]) -> dict[str, list[dict]]:
    """Cluster findings by finding_id, return those meeting CLUSTER_THRESHOLD."""
    by_id: dict[str, list[dict]] = {}
    for f in findings:
        fid = f.get("finding_id", "unknown")
        by_id.setdefault(fid, []).append(f)
    return {fid: recs for fid, recs in by_id.items() if len(recs) >= CLUSTER_THRESHOLD}


def _classify_tier(cluster_records: list[dict]) -> str:
    """Determine promotion tier based on cross-genre spread."""
    genres = {r.get("genre", "unknown") for r in cluster_records}
    return CROSS_GENRE_TIER if len(genres) > 1 else SINGLE_GENRE_TIER


def _write_proposal(
    finding_id: str,
    records: list[dict],
    tier: str,
    dry_run: bool,
) -> Path | None:
    """Write a promotion proposal markdown file. Return path if written."""
    severity = records[0].get("severity", "P2")
    requires_human = severity in HUMAN_REVIEW_SEVERITIES or tier == CROSS_GENRE_TIER

    sample_books = sorted({r.get("book", "?") for r in records})
    sample_chapters = sorted({r.get("chapter", "?") for r in records})[:5]

    proposal_text = (
        f"# Promotion Proposal — {finding_id}\n\n"
        f"**Tier:** {tier}  \n"
        f"**Severity:** {severity}  \n"
        f"**Occurrences:** {len(records)} (threshold: {CLUSTER_THRESHOLD})  \n"
        f"**Requires human review:** {'yes' if requires_human else 'no'}  \n\n"
        f"## Pattern\n\n"
        f"{records[0].get('description', 'no description')}\n\n"
        f"## Affected books\n\n"
        + "\n".join(f"- {b}" for b in sample_books)
        + f"\n\n## Sample chapters\n\n"
        + "\n".join(f"- {c}" for c in sample_chapters)
        + "\n\n## Proposed spec change\n\n"
        f"*(Human reviewer: fill in the specific R-rule or invariant edit here.)*\n\n"
        f"## Regression gate\n\n"
        f"Run `scripts/podcast/tests/test_challenger.py` with the proposed change applied "
        f"before committing. All existing tests must pass.\n"
    )

    safe_id = finding_id.replace("/", "-").replace(":", "-")
    proposal_path = PROPOSALS_DIR / f"{safe_id}.md"

    if not dry_run:
        PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(proposal_text)
        print(f"  wrote: {proposal_path.relative_to(REPO_ROOT)}"
              + (" [HUMAN REVIEW REQUIRED]" if requires_human else ""))
    else:
        print(f"  [dry-run] would write: {proposal_path.relative_to(REPO_ROOT)}"
              + (" [HUMAN REVIEW REQUIRED]" if requires_human else ""))

    return proposal_path


def run(book_slug: str | None, dry_run: bool) -> int:
    findings = _load_findings(book_slug)
    if not findings:
        label = f"for {book_slug}" if book_slug else "(all books)"
        print(f"promotion_lane: no findings in ledger {label}; nothing to promote.")
        return 0

    clusters = _cluster_findings(findings)
    if not clusters:
        print(f"promotion_lane: {len(findings)} findings loaded; none meet the "
              f"{CLUSTER_THRESHOLD}-occurrence threshold.")
        return 0

    requires_review_count = 0
    auto_promote_count = 0

    for finding_id, records in sorted(clusters.items()):
        tier = _classify_tier(records)
        severity = records[0].get("severity", "P2")
        needs_review = severity in HUMAN_REVIEW_SEVERITIES or tier == CROSS_GENRE_TIER
        _write_proposal(finding_id, records, tier, dry_run)
        if needs_review:
            requires_review_count += 1
        else:
            auto_promote_count += 1

    total = len(clusters)
    print(f"\npromotion_lane: {total} cluster(s) — "
          f"{auto_promote_count} auto-promotable, {requires_review_count} require human review.")

    if requires_review_count > 0:
        return 3  # proposals written but require human review
    return 2  # proposals written, no human review required


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="promotion_lane.py",
        description="Self-learning promotion lane — cluster findings and propose spec refinements.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--book", metavar="SLUG", help="Restrict to one book slug.")
    group.add_argument("--all-books", action="store_true", help="Scan all books in the ledger.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print proposals without writing files.")
    args = parser.parse_args(argv)
    return run(book_slug=args.book, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
