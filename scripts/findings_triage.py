#!/usr/bin/env python3
"""findings_triage.py — turn _learning/findings.jsonl back into a ledger.

By 2026-09 the file held ~740 top-severity findings still 'flagged' (85.7% never resolved, oldest 2026-05-24)
with no triage, so the handful that matter could not be told from the ghosts. Asif approved auto-closing by
rule (2026-09-18). A finding is marked `superseded` — never deleted, with its old status and the reason kept on
the row — when the evidence says it no longer describes anything live:

  1. its artifact no longer exists (deleted, or the retired content/drafts layout, or another machine's path);
  2. a LATER run re-reported the same signature, so this row is an older copy of a live complaint;
  3. its artifact changed after the finding AND the same source has run on that book since — somebody re-checked.

Everything else stays open. Rows already resolved (fixed, auto-fixed, accepted-…) are never touched, and
rows without a file or timestamp are left alone.

  python3 scripts/findings_triage.py            # dry run: counts and samples, changes nothing
  python3 scripts/findings_triage.py --apply    # write the superseded marks (atomic rewrite)
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "_learning" / "findings.jsonl"
OPEN = {"flagged", "carried", None}
_ABSOLUTE_MARKER = "/podcast-factory/"


def parse_ts(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def load(path: Path = LEDGER) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def make_resolver(root: Path) -> Callable[[dict[str, Any]], Path | None]:
    """Find a finding's artifact however its path was written: repo-relative, the retired content/drafts
    layout, another machine's absolute path, or relative to the book's own folder. None = truly gone."""

    def candidates(row: dict[str, Any]) -> list[Path]:
        raw = str(row["file"])
        book = row.get("book") or ""
        rel = raw.split(_ABSOLUTE_MARKER, 1)[1] if _ABSOLUTE_MARKER in raw else raw.lstrip("/")
        out = [root / rel]
        if rel.startswith("content/drafts/"):
            tail = rel.removeprefix("content/drafts/").removeprefix("books/")
            out += list(root.glob(f"content/*/{tail}"))
        if book:
            out += [p for p in root.glob(f"content/*/{book}/{rel}")]
            after = rel.split(f"{book}/", 1)[1] if f"{book}/" in rel else ""
            if after:
                out += list(root.glob(f"content/*/{book}/{after}"))
        return out

    def resolve(row: dict[str, Any]) -> Path | None:
        return next((c for c in candidates(row) if c.exists()), None)

    return resolve


def git_changed_at(root: Path) -> Callable[[Path], float | None]:
    cache: dict[Path, float | None] = {}

    def changed_at(path: Path) -> float | None:
        if path not in cache:
            try:
                out = subprocess.run(
                    ["git", "log", "-1", "--format=%ct", "--", str(path)],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout.strip()
                cache[path] = float(out) if out else None
            except (OSError, subprocess.SubprocessError, ValueError):
                cache[path] = None
        return cache[path]

    return changed_at


def classify(
    rows: list[dict[str, Any]],
    *,
    resolve: Callable[[dict[str, Any]], Path | None],
    changed_at: Callable[[Path], float | None],
) -> dict[int, str]:
    """{row index: reason} for every open row the rules close. Pure apart from the two injected lookups."""
    verdicts: dict[int, str] = {}
    candidates = [
        i
        for i, r in enumerate(rows)
        if r.get("resolution") in OPEN and r.get("file") and parse_ts(r.get("ts")) is not None
    ]
    latest_by_sig: dict[tuple, float] = {}
    latest_by_source_book: dict[tuple, float] = {}
    for r in rows:
        ts = parse_ts(r.get("ts"))
        if ts is None:
            continue
        if r.get("signature"):
            key = (r.get("book"), r.get("source"), r["signature"])
            latest_by_sig[key] = max(latest_by_sig.get(key, 0.0), ts)
        latest_by_source_book[(r.get("book"), r.get("source"))] = max(
            latest_by_source_book.get((r.get("book"), r.get("source")), 0.0), ts
        )
    for i in candidates:
        r = rows[i]
        ts = parse_ts(r["ts"]) or 0.0
        path = resolve(r)
        if path is None:
            verdicts[i] = "artifact no longer exists (deleted, moved, or from a retired layout)"
            continue
        sig_key = (r.get("book"), r.get("source"), r.get("signature"))
        if r.get("signature") and latest_by_sig.get(sig_key, 0.0) > ts:
            verdicts[i] = "re-reported by a later run — this is an older copy of the live complaint"
            continue
        changed = changed_at(path)
        if changed and changed > ts and latest_by_source_book.get((r.get("book"), r.get("source")), 0.0) > ts:
            verdicts[i] = "artifact changed after this finding and the same source re-ran on the book since"
    return verdicts


def apply(rows: list[dict[str, Any]], verdicts: dict[int, str], *, today: str) -> list[dict[str, Any]]:
    out = []
    for i, r in enumerate(rows):
        if i in verdicts:
            r = {
                **r,
                "resolution_before": r.get("resolution"),
                "resolution": "superseded",
                "superseded_reason": verdicts[i],
                "superseded_on": today,
            }
        out.append(r)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the superseded marks (default: dry run)")
    args = ap.parse_args(argv)
    rows = load()
    verdicts = classify(rows, resolve=make_resolver(REPO_ROOT), changed_at=git_changed_at(REPO_ROOT))
    open_before = [r for r in rows if r.get("resolution") in OPEN]
    print(f"ledger: {len(rows)} rows, {len(open_before)} open")
    by_reason = collections.Counter(v.split(" — ")[0].split(" (")[0] for v in verdicts.values())
    sev = collections.Counter(rows[i].get("severity") for i in verdicts)
    print(f"would close {len(verdicts)}: " + "; ".join(f"{n} × {reason}" for reason, n in by_reason.most_common()))
    print("by severity: " + ", ".join(f"{k}={v}" for k, v in sorted(sev.items(), key=lambda kv: str(kv[0]))))
    left = collections.Counter(
        r.get("severity") for i, r in enumerate(rows) if r.get("resolution") in OPEN and i not in verdicts
    )
    print("stays open: " + ", ".join(f"{k}={v}" for k, v in sorted(left.items(), key=lambda kv: str(kv[0]))))
    if not args.apply:
        print("dry run — nothing written (use --apply)")
        return 0
    save(LEDGER, apply(rows, verdicts, today=dt.date.today().isoformat()))
    print(f"applied: {len(verdicts)} row(s) marked superseded in {LEDGER.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
