#!/usr/bin/env python3
"""book_cost.py — Summarise cost-ledger.jsonl for a book.

Reads BOOK_DIR/_system/cost-ledger.jsonl and prints a cost breakdown by
phase + model. Also updates state.json's cost.anthropic_usd field so the
orchestrator status command shows live totals.

Usage:
    python3 scripts/podcast/book_cost.py <book-slug>
    python3 scripts/podcast/book_cost.py <book-slug> --update-state
    python3 scripts/podcast/book_cost.py <book-slug> --json

NOTE: Phase 0b costs show $0.00 when run via the claude CLI subprocess.
The CLI does not expose token usage on stdout. Actual subscription charges
are incurred but cannot be reconstructed from the ledger. This gap is
resolved when 0b is migrated to the Anthropic API (see pipeline refactor
backlog). Estimated 0b cost is shown as a separate advisory line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from _paths import REPO_ROOT, find_content  # noqa: E402

# Opus 4.8 pricing (USD per token, as of 2026-06-02)
# Source: anthropic.com/pricing
_OPUS_4_8_IN  = 15.00 / 1_000_000
_OPUS_4_8_OUT = 75.00 / 1_000_000
_OPUS_4_8_CACHE_READ = 1.50 / 1_000_000
_OPUS_4_8_CACHE_WRITE = 18.75 / 1_000_000

# Opus 4.7 pricing (approximately same tier)
_OPUS_4_7_IN  = 15.00 / 1_000_000
_OPUS_4_7_OUT = 75.00 / 1_000_000
_OPUS_4_7_CACHE_READ = 1.50 / 1_000_000
_OPUS_4_7_CACHE_WRITE = 18.75 / 1_000_000


def _load_ledger(book_dir: Path) -> list[dict]:
    ledger_path = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger_path.exists():
        return []
    rows = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def _estimate_0b_cost(book_dir: Path) -> float | None:
    """Estimate 0b cost from chunk file sizes (heuristic, not authoritative).

    Reads 0b input windows and estimates tokens using 4-char-per-token rule.
    Returns None if chunks not found.
    """
    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0b"
    if not chunks_dir.exists():
        return None
    total_chars = 0
    window_count = 0
    for f in sorted(chunks_dir.glob("win-*.in.md")):
        total_chars += len(f.read_text(encoding="utf-8"))
        window_count += 1
    if not window_count:
        return None
    # Input tokens ≈ chars / 4, output tokens ≈ same (refinement produces ~equal length)
    est_tokens = total_chars / 4
    est_cost = (est_tokens * _OPUS_4_7_IN) + (est_tokens * _OPUS_4_7_OUT)
    return round(est_cost, 4)


def summarise(book_slug: str, *, update_state: bool = False, as_json: bool = False) -> dict:
    found = find_content(book_slug)
    if not found:
        print(f"ERROR: book '{book_slug}' not found in content/drafts or content/published",
              file=sys.stderr)
        sys.exit(1)
    _, _, book_dir = found

    rows = _load_ledger(book_dir)

    # Aggregate by phase
    phases: dict[str, dict] = {}
    total_tracked = 0.0

    for r in rows:
        phase = r.get("phase", "unknown")
        cost = r.get("cost_usd", 0.0) or 0.0
        if phase not in phases:
            phases[phase] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_usd": 0.0,
                "models": set(),
            }
        phases[phase]["calls"] += 1
        phases[phase]["input_tokens"] += r.get("input_tokens", 0) or 0
        phases[phase]["output_tokens"] += r.get("output_tokens", 0) or 0
        phases[phase]["cache_read_tokens"] += r.get("cache_read", 0) or 0
        phases[phase]["cache_write_tokens"] += r.get("cache_create", 0) or 0
        phases[phase]["cost_usd"] += cost
        phases[phase]["models"].add(r.get("model", "unknown"))
        total_tracked += cost

    # Convert sets to lists for JSON serialisation
    for p in phases.values():
        p["models"] = sorted(p["models"])

    # 0b estimate
    est_0b = _estimate_0b_cost(book_dir)
    total_with_0b_estimate = total_tracked + (est_0b or 0.0)

    result = {
        "book_slug": book_slug,
        "by_phase": phases,
        "total_tracked_usd": round(total_tracked, 4),
        "0b_untracked_estimate_usd": est_0b,
        "total_with_estimate_usd": round(total_with_0b_estimate, 4),
        "note": (
            "Phase 0b cost is $0.00 in ledger — claude CLI does not expose token counts. "
            "Estimate is based on chunk file sizes using the 4-char/token heuristic."
        ),
    }

    if update_state:
        from _progress import read_state, write_state
        state = read_state(book_dir)
        if state is not None:
            if not isinstance(state.get("cost"), dict):
                state["cost"] = {"azure_usd": 0.0, "anthropic_usd": 0.0, "slide_deck_usd": 0.0}
            state["cost"]["anthropic_usd"] = round(total_tracked, 4)
            write_state(book_dir, state)

    return result


def _print_table(data: dict) -> None:
    slug = data["book_slug"]
    print(f"\n  Cost breakdown — {slug}")
    print(f"  {'Phase':<8} {'Model(s)':<24} {'Calls':>5} {'Output tok':>11} {'Cache read':>12} {'Cost USD':>10}")
    print(f"  {'-'*76}")
    for phase, d in sorted(data["by_phase"].items()):
        models = ", ".join(d["models"])
        tracked = d["cost_usd"]
        flag = "  ⚠️  (untracked — CLI)" if phase == "0b" and tracked == 0 else ""
        print(f"  {phase:<8} {models:<24} {d['calls']:>5} {d['output_tokens']:>11,} {d['cache_read_tokens']:>12,} ${tracked:>9.4f}{flag}")
    print(f"  {'-'*76}")
    print(f"  {'TRACKED TOTAL':<56} ${data['total_tracked_usd']:>9.4f}")
    est = data["0b_untracked_estimate_usd"]
    if est is not None:
        print(f"  {'+ 0b estimate (heuristic)':<56} ${est:>9.4f}")
        print(f"  {'ESTIMATED TOTAL':<56} ${data['total_with_estimate_usd']:>9.4f}")
    print()
    print(f"  ⚠️  {data['note']}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Show cost breakdown for a book pipeline run.")
    parser.add_argument("slug", help="Book slug")
    parser.add_argument("--update-state", action="store_true",
                        help="Write tracked total into orchestrator-state.json cost.anthropic_usd")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    data = summarise(args.slug, update_state=args.update_state, as_json=args.json)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        _print_table(data)


if __name__ == "__main__":
    main()
