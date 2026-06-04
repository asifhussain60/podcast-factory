#!/usr/bin/env python3
"""Cost-ledger summary CLI (P6.2).

Reads <book_dir>/_system/cost-ledger.jsonl, sums by phase + model, and emits:
  • Structured human-readable totals to stdout
  • A `<book_dir>/_system/cost-validation.json` snapshot (diffable in PR review)

Usage:
    python3 scripts/podcast/cost_ledger_summary.py <book-slug-or-path>
    python3 scripts/podcast/cost_ledger_summary.py <book> --json
    python3 scripts/podcast/cost_ledger_summary.py <book> --no-write

Exit codes:
    0 — summary written / printed
    1 — ledger file missing or unparseable
    2 — no usable rows (ledger exists but is empty)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from _paths import REPO_ROOT

BOOKS_DIR = REPO_ROOT / "content" / "drafts"


def _resolve_book_dir(book_arg: str) -> Path:
    """Accept either a slug ('ayyuhal-walad') or a full path."""
    p = Path(book_arg)
    if p.is_absolute() and p.exists():
        return p
    p = BOOKS_DIR / book_arg
    if p.exists():
        return p
    # Last-ditch: relative-from-cwd
    if Path(book_arg).exists():
        return Path(book_arg).resolve()
    raise FileNotFoundError(f"book not found: {book_arg!r}")


def load_ledger(ledger_path: Path) -> list[dict]:
    """Read the JSONL ledger; skip blank/malformed lines."""
    rows: list[dict] = []
    for line in ledger_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            sys.stderr.write(f"[cost_ledger_summary] skipped unparseable line: {line[:80]!r}\n")
    return rows


def summarize(rows: list[dict]) -> dict:
    """Compute totals: by phase, by model, grand totals."""
    by_phase: dict[str, dict] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0,
                 "cache_read": 0, "cache_create": 0, "cost_usd": 0.0, "calls": 0}
    )
    by_model: dict[str, dict] = defaultdict(
        lambda: {"input_tokens": 0, "output_tokens": 0,
                 "cache_read": 0, "cache_create": 0, "cost_usd": 0.0, "calls": 0}
    )
    totals = {"input_tokens": 0, "output_tokens": 0,
              "cache_read": 0, "cache_create": 0, "cost_usd": 0.0, "calls": 0}

    for r in rows:
        phase = r.get("phase", "(unknown)")
        model = r.get("model", "(unknown)")
        for d in (by_phase[phase], by_model[model], totals):
            d["input_tokens"]  += int(r.get("input_tokens", 0))
            d["output_tokens"] += int(r.get("output_tokens", 0))
            d["cache_read"]    += int(r.get("cache_read", 0))
            d["cache_create"]  += int(r.get("cache_create", 0))
            d["cost_usd"]      += float(r.get("cost_usd", 0))
            d["calls"]         += 1

    # Round costs for diff-stability
    for d in (totals, *by_phase.values(), *by_model.values()):
        d["cost_usd"] = round(d["cost_usd"], 4)

    return {
        "row_count": len(rows),
        "totals": totals,
        "by_phase": dict(by_phase),
        "by_model": dict(by_model),
    }


def fmt_text(summary: dict, book_slug: str) -> str:
    t = summary["totals"]
    lines = [
        f"Cost ledger summary — {book_slug}",
        f"  Rows:           {summary['row_count']}",
        f"  Total calls:    {t['calls']}",
        f"  Input tokens:   {t['input_tokens']:>12,}",
        f"  Output tokens:  {t['output_tokens']:>12,}",
        f"  Cache read:     {t['cache_read']:>12,}",
        f"  Cache create:   {t['cache_create']:>12,}",
        f"  Total cost:     ${t['cost_usd']:>10.4f}",
        "",
        "By phase:",
    ]
    for phase, d in sorted(summary["by_phase"].items()):
        lines.append(
            f"  {phase:<24}  calls={d['calls']:>3}  "
            f"in={d['input_tokens']:>10,}  out={d['output_tokens']:>10,}  "
            f"cost=${d['cost_usd']:>8.4f}"
        )
    lines.append("")
    lines.append("By model:")
    for model, d in sorted(summary["by_model"].items()):
        lines.append(
            f"  {model:<30}  calls={d['calls']:>3}  cost=${d['cost_usd']:>8.4f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cost_ledger_summary.py",
        description="Sum cost-ledger.jsonl by phase + model; emit cost-validation.json snapshot.",
    )
    parser.add_argument("book", help="Book slug (e.g., 'ayyuhal-walad') or full path to book dir.")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON to stdout instead of human-readable text.")
    parser.add_argument("--no-write", action="store_true",
                        help="Don't write _system/cost-validation.json snapshot.")
    args = parser.parse_args(argv)

    try:
        book_dir = _resolve_book_dir(args.book)
    except FileNotFoundError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1

    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        sys.stderr.write(f"error: cost-ledger.jsonl not found at {ledger}\n")
        return 1

    rows = load_ledger(ledger)
    if not rows:
        sys.stderr.write(f"warning: cost-ledger.jsonl at {ledger} has zero usable rows\n")
        return 2

    summary = summarize(rows)
    book_slug = book_dir.name

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(fmt_text(summary, book_slug))

    if not args.no_write:
        snapshot = book_dir / "_system" / "cost-validation.json"
        snapshot.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
