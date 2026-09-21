#!/usr/bin/env python3
"""build_correction_packets.py -- one self-contained packet per open correction.

    python3 scripts/podcast/build_correction_packets.py <slug> [--correction ID]

Reads the book's `open` and `suggested` corrections from the LOCAL Library
database and writes `content/<Bucket>/<slug>/_system/corrections/packets/<id>.json`.
Everything in a packet comes from disk and that one row; no model is asked for
anything. Useful on its own: the printed gate table says how many corrections
even NEED a model before one is wired in (design 9b, phase 4b).

The database is local unless `--remote` AND `--i-understand-remote` are both
given. Nothing here writes to it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _correction_db import (  # noqa: E402
    REMOTE_CONFIRM_FLAG,
    default_d1,
    fetch_corrections,
    refuse_remote_unless_confirmed,
)
from _correction_packets import (  # noqa: E402
    LIVE_STATUSES,
    build_packet,
    gate_summary,
    gates_of,
    load_context,
    verdict_from_gates,
    write_packet,
)
from _paths import resolve_content  # noqa: E402

REVIEWABLE = ("suggested", "open")


def build_all(
    book_dir: Path, slug: str, *, d1, remote: bool = False, correction_id: str | None = None, write: bool = True
) -> list[dict]:
    """Build (and by default write) the packets. `d1` is injectable for tests."""
    rows = fetch_corrections(d1, slug, REVIEWABLE, remote=remote, correction_id=correction_id)
    # Overlap is judged against every live row, not just the reviewable ones.
    live = fetch_corrections(d1, slug, LIVE_STATUSES, remote=remote)
    ctx = load_context(book_dir, slug)
    packets = [build_packet(ctx, row, live) for row in rows]
    if write:
        for p in packets:
            write_packet(book_dir, p)
    return packets


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--correction", help="build only this correction id")
    ap.add_argument(
        "--remote", action="store_true", help="read the DEPLOYED database (needs " + REMOTE_CONFIRM_FLAG + ")"
    )
    ap.add_argument(REMOTE_CONFIRM_FLAG, dest="confirmed", action="store_true")
    args = ap.parse_args(argv)

    refusal = refuse_remote_unless_confirmed(args.remote, args.confirmed)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2

    book_dir = resolve_content(args.slug)
    if not book_dir.is_dir():
        print(f"no such book: {args.slug}", file=sys.stderr)
        return 2

    packets = build_all(book_dir, args.slug, d1=default_d1(), remote=args.remote, correction_id=args.correction)
    if not packets:
        print("no open or suggested corrections")
        return 0

    decided = 0
    for p in packets:
        gates = gates_of(p)
        verdict = verdict_from_gates(gates)
        decided += verdict is not None
        bad = ",".join(g.id for g in gates if g.result == "no") or "-"
        print(
            f"{p['correction_id']:<40} hash={p['packet_hash'][:10]} gates-failing={bad:<24} -> {verdict or 'ask the AI'}"
        )
        if verdict:
            print(f"    {gate_summary(gates, verdict)}")
    print(
        f"\n{len(packets)} packet(s) written; {decided} decided by the gates alone, {len(packets) - decided} would go to the reviewer"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
