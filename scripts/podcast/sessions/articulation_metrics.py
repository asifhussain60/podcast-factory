#!/usr/bin/env python3
"""Summarize Sessions articulation throughput and failure patterns."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _paths import resolve_content  # noqa: E402


def _gate_family(gate: str) -> str:
    if "Arabic" in gate or "[[ARABIC_" in gate:
        return "arabic"
    if "near-identical" in gate:
        return "near-identical"
    if "no candidate" in gate:
        return "no-candidate"
    if "assembled chapter" in gate:
        return "assembly"
    if "abridged" in gate:
        return "abridged"
    if "runaway" in gate:
        return "runaway"
    return "other"


def summarize(book_dir: Path) -> dict:
    path = book_dir / "_system" / "sessions-articulation.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    families: Counter[str] = Counter()
    for key, entry in sorted((data.get("chapters") or {}).items()):
        usage = entry.get("usage") or {}
        quality = entry.get("quality") or {}
        gates = list(quality.get("gates") or [])
        gates.extend(quality.get("assembly_gates") or [])
        for gate in gates:
            families[_gate_family(str(gate))] += 1
        duration = float(entry.get("duration_seconds") or 0)
        tokens = int(usage.get("total_tokens") or 0)
        windows = int(quality.get("windows") or usage.get("rows") or 0)
        cached = int(quality.get("windows_cached") or 0)
        repaired = int(quality.get("windows_repaired") or 0)
        source_preserved = int(quality.get("windows_source_preserved") or 0)
        model_failures = int(quality.get("model_failures") or 0)
        rows.append(
            {
                "key": key,
                "title": entry.get("title") or key,
                "status": entry.get("status"),
                "duration_seconds": round(duration, 3),
                "total_tokens": tokens,
                "windows": windows,
                "windows_cached": cached,
                "windows_repaired": repaired,
                "windows_source_preserved": source_preserved,
                "model_failures": model_failures,
                "tokens_per_second": round(tokens / duration, 2) if duration else None,
                "seconds_per_window": round(duration / windows, 2) if windows else None,
                "window_keep_rate": quality.get("window_keep_rate"),
            }
        )
    measured = [r for r in rows if r["duration_seconds"]]
    total_seconds = sum(r["duration_seconds"] for r in measured)
    total_tokens = sum(r["total_tokens"] for r in measured)
    total_windows = sum(r["windows"] for r in rows)
    cached_windows = sum(r["windows_cached"] for r in rows)
    repaired_windows = sum(r["windows_repaired"] for r in rows)
    source_preserved_windows = sum(r["windows_source_preserved"] for r in rows)
    model_failures = sum(r["model_failures"] for r in rows)
    adapted = sum(1 for r in rows if r["status"] == "adapted")
    partial = sum(1 for r in rows if r["status"] == "partial")
    return {
        "book": book_dir.name,
        "chapters_total": len(rows),
        "chapters_measured": len(measured),
        "adapted": adapted,
        "partial": partial,
        "measured_seconds": round(total_seconds, 3),
        "measured_tokens": total_tokens,
        "windows": total_windows,
        "windows_cached": cached_windows,
        "windows_repaired": repaired_windows,
        "windows_source_preserved": source_preserved_windows,
        "model_failures": model_failures,
        "cache_hit_rate": round(cached_windows / total_windows, 4) if total_windows else None,
        "tokens_per_second": round(total_tokens / total_seconds, 2) if total_seconds else None,
        "seconds_per_measured_chapter": round(total_seconds / len(measured), 2) if measured else None,
        "failure_families": dict(families),
        "chapters": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    book_dir = resolve_content(args.slug)
    if book_dir is None:
        print(f"no book found for slug {args.slug!r}", file=sys.stderr)
        return 2
    summary = summarize(Path(book_dir))
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(
            f"{summary['book']}: {summary['adapted']} adapted, {summary['partial']} partial, "
            f"{summary['chapters_measured']} measured chapter(s), "
            f"{summary['seconds_per_measured_chapter']} sec/chapter"
        )
        print(f"tokens: {summary['measured_tokens']} total, {summary['tokens_per_second']} tokens/sec")
        print(
            f"windows: {summary['windows']} total, {summary['windows_cached']} cached, "
            f"{summary['windows_repaired']} repaired, "
            f"{summary['windows_source_preserved']} source-preserved, "
            f"{summary['model_failures']} model failures, "
            f"cache hit rate={summary['cache_hit_rate']}"
        )
        if summary["failure_families"]:
            print("failure families: " + ", ".join(f"{k}={v}" for k, v in summary["failure_families"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
