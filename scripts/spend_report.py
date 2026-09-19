#!/usr/bin/env python3
"""spend_report.py — what has the pipeline actually spent, and is any of it unpriced?

Reads every book's `_system/cost-ledger.jsonl` (archived books excluded) and reports, for a window:
real money (`engine: api`, actually charged) apart from flat-rate work (`engine: max`, notional), the books that
cost the most, and — first, because it is the one that hides — API rows with tokens but no price, which read as
$0 and are not (2026-09: 91 opus-4-7 rows were logged free because the model had no price on file).

  python3 scripts/spend_report.py            # last 30 days
  python3 scripts/spend_report.py --days 7 --json
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _rows(root: Path):
    for path in sorted((root / "content").glob("*/*/_system/cost-ledger.jsonl")):
        if path.parts[len(root.parts) + 1].startswith("_"):
            continue
        book = path.parents[1].name
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                row = None
            if isinstance(row, dict):
                yield book, row


def _ts(row: dict[str, Any]) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(row.get("ts")).replace("Z", "+00:00"))
    except ValueError:
        return None


def summarise(root: Path, *, now: dt.datetime | None = None, days: int = 30) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=days)
    real = notional = 0.0
    by_book: collections.Counter[str] = collections.Counter()
    by_model: collections.Counter[str] = collections.Counter()
    unpriced: collections.Counter[str] = collections.Counter()
    for book, row in _rows(root):
        when = _ts(row)
        if when is None or when < since:
            continue
        cost = float(row.get("cost_usd") or 0)
        if row.get("engine", "api") == "max":
            notional += cost
            continue
        real += cost
        by_book[book] += cost
        by_model[str(row.get("model"))] += cost
        tokens = int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0)
        if tokens and (row.get("priced") is False or cost == 0):
            unpriced[str(row.get("model"))] += 1
    return {
        "days": days,
        "real_usd": round(real, 2),
        "notional_usd": round(notional, 2),
        "by_book": [(b, round(v, 2)) for b, v in by_book.most_common()],
        "by_model": [(m, round(v, 2)) for m, v in by_model.most_common()],
        "unpriced_rows": sum(unpriced.values()),
        "unpriced_models": dict(unpriced),
    }


def render(rep: dict[str, Any]) -> str:
    lines = [f"Spend, last {rep['days']} days"]
    if rep["unpriced_rows"]:
        models = ", ".join(f"{m} ({n})" for m, n in rep["unpriced_models"].items())
        lines.append(
            f"  ! UNPRICED: {rep['unpriced_rows']} API row(s) with tokens but no cost — {models}. "
            "Add the model to PRICING_USD_PER_MILLION_TOKENS in scripts/podcast/_cost_ledger.py."
        )
    lines.append(f"  real money (charged):  ${rep['real_usd']:.2f}")
    lines.append(f"  flat-rate (notional):  ${rep['notional_usd']:.2f}   — covered by the subscription, not charged")
    if rep["by_book"]:
        lines.append("  by book:  " + "  ".join(f"{b} ${v:.2f}" for b, v in rep["by_book"][:8]))
    if rep["by_model"]:
        lines.append("  by model: " + "  ".join(f"{m} ${v:.2f}" for m, v in rep["by_model"][:6]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = summarise(REPO_ROOT, days=args.days)
    print(json.dumps(rep, indent=2) if args.json else render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
