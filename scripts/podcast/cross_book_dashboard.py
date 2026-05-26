#!/usr/bin/env python3
"""cross_book_dashboard.py — fleet-level view across all in-flight and shipped books.

Walks every BOOK_DIR under content/drafts/ and content/published/books/, reads
each book's _system/orchestrator-state.json (for phase + status) and
_system/cost-ledger.jsonl (for cumulative LLM spend), and emits a single
markdown table summarizing the entire fleet.

This is the single-pane-of-glass that scripts/podcast/cost_ledger_summary.py
deliberately does NOT provide — cost_ledger_summary.py works one book at a
time. When 2+ books are in flight simultaneously (or a mix of in-flight +
shipped is being audited), this script answers "what's the burn rate this
week across everything" without needing to cd through each book.

Born from the F31 forward-looking audit (2026-05-25): identified the cross-
book observability gap as P0 for the "5+ in-flight books" scenario this
repo is designed to scale toward.

USAGE

    python3 scripts/podcast/cross_book_dashboard.py
    python3 scripts/podcast/cross_book_dashboard.py --since 7d
    python3 scripts/podcast/cross_book_dashboard.py --json    # machine-readable
    python3 scripts/podcast/cross_book_dashboard.py --out path.md

EXIT CODES

  0 = dashboard emitted
  1 = no books found (drafts + published both empty)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFTS = REPO_ROOT / "content" / "drafts"
PUBLISHED = REPO_ROOT / "content" / "published" / "books"


def _parse_since(spec: str | None) -> datetime | None:
    """Convert '7d', '30d', '24h' etc. to a UTC cutoff timestamp; None for all-time."""
    if not spec:
        return None
    m = re.match(r"^(\d+)([dhwm])$", spec.strip().lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    deltas = {"d": timedelta(days=n), "h": timedelta(hours=n),
              "w": timedelta(weeks=n), "m": timedelta(days=30 * n)}
    return datetime.now(timezone.utc) - deltas[unit]


def _read_state(book_dir: Path) -> dict:
    state = book_dir / "_system" / "orchestrator-state.json"
    if not state.exists():
        return {}
    try:
        return json.loads(state.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _read_cost_ledger(book_dir: Path, since: datetime | None) -> tuple[float, int, str]:
    """Return (total_usd, row_count, last_ts) summed across rows since cutoff."""
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return (0.0, 0, "")
    total = 0.0
    rows = 0
    last_ts = ""
    try:
        for raw in ledger.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            ts = rec.get("ts", "")
            if since:
                try:
                    rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if rec_dt < since:
                    continue
            total += float(rec.get("cost_usd", 0) or 0)
            rows += 1
            if ts > last_ts:
                last_ts = ts
    except OSError:
        pass
    return (total, rows, last_ts)


def _chapter_progress(book_dir: Path) -> str:
    """Return 'completed/total' for chapter authoring progress."""
    contracts = book_dir / "chapter-contracts"
    if not contracts.is_dir():
        return "—"
    total = sum(1 for _ in contracts.glob("*.yml"))
    state = _read_state(book_dir)
    completed = len(
        state.get("phases", {}).get("per-chapter", {}).get("completed_slugs", [])
    )
    return f"{completed}/{total}"


def _chapter_timing_stats(book_dir: Path) -> str:
    """F37 (2026-05-25): return 'mean Ns / N chapters' from chapter_timings dict.

    Reads orchestrator-state.json's phases.per-chapter.chapter_timings (added in
    F37) and computes the mean duration_sec across completed chapters. Returns
    '—' when no timing data is present (older books pre-F37).
    """
    state = _read_state(book_dir)
    timings = (
        state.get("phases", {}).get("per-chapter", {}).get("chapter_timings", {})
    )
    durations = [
        t["duration_sec"] for t in timings.values()
        if isinstance(t, dict) and t.get("duration_sec") is not None
    ]
    if not durations:
        return "—"
    mean = sum(durations) / len(durations)
    if mean >= 3600:
        return f"{mean / 3600:.1f}h × {len(durations)}"
    return f"{mean / 60:.1f}m × {len(durations)}"


def _category_label(book_dir: Path) -> str:
    """Best-effort: 'in-flight' for drafts/, 'shipped' for published/books/."""
    if str(book_dir).startswith(str(DRAFTS)):
        return "in-flight"
    if str(book_dir).startswith(str(PUBLISHED)):
        return "shipped"
    return "unknown"


def collect_fleet(since: datetime | None) -> list[dict]:
    """Walk both content trees; return one dict per book."""
    fleet: list[dict] = []
    seen: set[str] = set()
    for root in (DRAFTS, PUBLISHED):
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_") or entry.name.startswith("."):
                continue
            if entry.name in seen:
                continue
            seen.add(entry.name)
            state = _read_state(entry)
            phase = state.get("phase", "—")
            status = state.get("phase_status", "—")
            last_phase = state.get("last_completed_phase", "—")
            total, rows, last_ts = _read_cost_ledger(entry, since)
            fleet.append({
                "book": entry.name,
                "category": _category_label(entry),
                "phase": phase,
                "status": status,
                "last_completed": last_phase,
                "chapters": _chapter_progress(entry),
                "ch_mean_time": _chapter_timing_stats(entry),
                "cost_usd": round(total, 2),
                "ledger_rows": rows,
                "last_cost_ts": last_ts,
            })
    return fleet


def render_markdown(fleet: list[dict], since_label: str) -> str:
    lines = [
        f"# Podcast-factory fleet dashboard",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Cost window: {since_label}",
        "",
        f"Books tracked: **{len(fleet)}**.",
        "",
        "| Book | Category | Phase | Status | Last completed | Chapters | Ch time | Cost (USD) | Ledger rows | Last activity |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    total_usd = 0.0
    for b in fleet:
        lines.append(
            f"| `{b['book']}` | {b['category']} | {b['phase']} | {b['status']} | "
            f"{b['last_completed']} | {b['chapters']} | {b.get('ch_mean_time', '—')} | "
            f"${b['cost_usd']:.2f} | {b['ledger_rows']} | {b['last_cost_ts'] or '—'} |"
        )
        total_usd += b['cost_usd']
    lines.append(
        f"| **TOTAL** | — | — | — | — | — | — | **${total_usd:.2f}** | — | — |"
    )
    lines.append("")
    in_flight = [b for b in fleet if b['category'] == 'in-flight']
    shipped = [b for b in fleet if b['category'] == 'shipped']
    lines.append(f"- **In-flight books**: {len(in_flight)} ({', '.join(b['book'] for b in in_flight) or 'none'})")
    lines.append(f"- **Shipped books**: {len(shipped)} ({', '.join(b['book'] for b in shipped) or 'none'})")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cross-book fleet dashboard: phases, statuses, cumulative costs.",
    )
    parser.add_argument("--since", default=None,
                        help="Cost window: 7d / 24h / 4w / 2m. Default: all-time.")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON to stdout instead of markdown.")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write markdown to this path (default: stdout).")
    args = parser.parse_args(argv)

    since = _parse_since(args.since)
    since_label = args.since if args.since else "all-time"
    fleet = collect_fleet(since)
    if not fleet:
        sys.stderr.write("no books found under content/drafts/ or content/published/books/\n")
        return 1

    if args.json:
        sys.stdout.write(json.dumps({"since": since_label, "fleet": fleet}, indent=2) + "\n")
        return 0

    md = render_markdown(fleet, since_label)
    if args.out:
        args.out.write_text(md, encoding="utf-8")
        print(f"wrote dashboard to {args.out}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
