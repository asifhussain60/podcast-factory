#!/usr/bin/env python3
"""Cost recording for the operator-run standalone tools.

`augment_book`, `full_book_denoise`, `generate_slide_decks`, `reconcile_book` and
`segment_book` are run by hand, not by the orchestrator. Each priced its own model
call and then kept a PRIVATE `_system/cost-ledger.json` — a dict with its own
`total_usd`, written by five byte-identical copies of the same `_log_cost`. Nothing
read it: `cost_guard.real_spend_usd`, the status card and the cross-book dashboard
all read `cost-ledger.jsonl`, so real Gemini and metered-Anthropic spend recorded
there counted toward no ceiling and appeared in no report.

Lives in its own module rather than in `_cost_ledger` because that module is at 588
of its 600-line limit; adding these two functions there took it to 665 and the
DR-005 gate refused the commit. The seam is honest either way — everything here is
about callers that priced their own call, which is the one thing `_cost_ledger`'s
own `append_*` helpers deliberately do not do.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cost_ledger import CostRow, _now_iso


def append_precomputed_cost(
    book_dir: Path,
    *,
    phase: str,
    step: str,
    model: str,
    cost_usd: float,
    in_units: int = 0,
    out_units: int = 0,
    ts: str | None = None,
    engine: str = "api",
) -> CostRow:
    """Append a row whose cost the CALLER already computed, in real dollars.

    Prefer `_cost_ledger.append_gemini_cost` or `append_cost_row` when raw chars or
    tokens are available — those price from the tables in that module, which is where
    pricing belongs. This entry point exists for callers holding only a final figure.

    `engine="api"` by default because every current caller bills real money (metered
    Gemini, the metered Anthropic SDK). A flat-rate `claude -p` caller must pass
    `engine="max"`, or its notional cost would count against the book's ceiling.
    """
    row = CostRow(
        ts=ts or _now_iso(),
        phase=phase,
        step=step,
        model=model,
        input_tokens=int(in_units),
        output_tokens=int(out_units),
        cache_read=0,
        cache_create=0,
        cost_usd=round(float(cost_usd), 6),
        engine=engine,
    )
    # Mirrors the locked append in `_cost_ledger`'s own `append_*` helpers: parallel
    # tools can target the same book, and a JSON row can exceed PIPE_BUF.
    import fcntl as _fcntl

    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
        try:
            f.write(json.dumps(asdict(row)) + "\n")
            f.flush()
        finally:
            _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)
    return row


def append_tool_cost(book_dir: Path, entry: dict) -> CostRow:
    """Append one standalone tool's ``_log_cost`` entry to the canonical ledger.

    Each tool builds a small dict at the call site — ``op``, ``service``,
    ``cost_usd``, and either char or word counts. This is the ONE mapping from that
    dict to a row: five copies of it is how the private second ledger survived.

    ``phase="standalone"`` because these tools sit outside the orchestrator's phase
    sequence; recording them under a real phase id would put spend the pipeline never
    made into that phase's total.
    """
    return append_precomputed_cost(
        book_dir,
        phase="standalone",
        step=str(entry.get("op") or "unknown"),
        model=str(entry.get("service") or "unknown"),
        cost_usd=float(entry.get("cost_usd") or 0.0),
        in_units=int(entry.get("in_chars") or entry.get("word_count_before") or 0),
        out_units=int(entry.get("out_chars") or entry.get("word_count_after") or 0),
        ts=entry.get("ts"),
    )
