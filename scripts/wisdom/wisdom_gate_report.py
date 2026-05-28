#!/usr/bin/env python3
"""Generate GATE summary report for manual review before Phase 4 intake.

Reads all bundle.ymls and challenge reports to produce a concise Markdown
summary for Asif's review.

Usage:
    python scripts/wisdom/wisdom_gate_report.py
    python scripts/wisdom/wisdom_gate_report.py --out _workspace/plan/wisdom-gate-report.md
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EXTRACT_ROOT = REPO / "CONTENT/_shared/source-library/extracted/wisdom"
TRANSLATE_LEDGER = REPO / "_workspace/plan/wisdom-translation-cost-ledger.jsonl"
ADAPT_LEDGER = REPO / "_workspace/plan/wisdom-adapt-cost-ledger.jsonl"
CHALLENGE_LEDGER = REPO / "_workspace/plan/wisdom-challenge-cost-ledger.jsonl"


def _ledger_total(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0.0
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                total += json.loads(line).get("cost_usd", 0.0)
    return total


def _scan_bundles() -> list[dict]:
    chapters = []
    for shelf in sorted(EXTRACT_ROOT.iterdir()):
        if not shelf.is_dir():
            continue
        for book in sorted(shelf.iterdir()):
            yml = book / "bundle.yml"
            if not yml.exists():
                continue
            text = yml.read_text(encoding="utf-8")
            # Extract fields
            stage = ""
            binder_id = chapter_id = 0
            binder_name = chapter_name = ""
            verdict = ""
            in_shelf = in_book = False
            for line in text.splitlines():
                if line.startswith("stage:"):
                    stage = line.split(":", 1)[1].strip()
                if line.startswith("shelf:"):
                    in_shelf = True
                    in_book = False
                if line.startswith("book:"):
                    in_book = True
                    in_shelf = False
                if in_shelf and re.match(r"\s+id:", line):
                    binder_id = int(line.split(":")[1].strip())
                if in_book and re.match(r"\s+id:", line):
                    chapter_id = int(line.split(":")[1].strip())
                if in_shelf and re.match(r"\s+name:", line):
                    binder_name = line.split(":", 1)[1].strip()
                if in_book and re.match(r"\s+name:", line):
                    chapter_name = line.split(":", 1)[1].strip()
                if line.startswith("  verdict:"):
                    verdict = line.split(":", 1)[1].strip()
            chapters.append({
                "binder_id": binder_id,
                "chapter_id": chapter_id,
                "binder_name": binder_name,
                "chapter_name": chapter_name,
                "stage": stage,
                "verdict": verdict,
                "bundle_root": str(book),
            })
    return chapters


def generate_report(out: Path | None = None) -> str:
    chapters = _scan_bundles()
    total = len(chapters)

    stage_counts: dict[str, int] = {}
    verdict_counts: dict[str, int] = {}
    warns: list[dict] = []
    fails: list[dict] = []

    for c in chapters:
        stage_counts[c["stage"]] = stage_counts.get(c["stage"], 0) + 1
        if c["verdict"]:
            verdict_counts[c["verdict"]] = verdict_counts.get(c["verdict"], 0) + 1
        if c["verdict"] == "WARN":
            warns.append(c)
        elif c["verdict"] == "FAIL":
            fails.append(c)

    translate_cost = _ledger_total(TRANSLATE_LEDGER)
    adapt_cost = _ledger_total(ADAPT_LEDGER)
    challenge_cost = _ledger_total(CHALLENGE_LEDGER)
    total_cost = translate_cost + adapt_cost + challenge_cost

    challenged = stage_counts.get("challenged", 0)
    adapted = stage_counts.get("adapted", 0)
    translated = stage_counts.get("translated", 0)
    gate_ready = challenged == total

    lines = [
        f"# KAHSKOLE Pipeline — GATE Report",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        f"",
        f"## At a Glance",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total chapters | {total} |",
        f"| Challenged (Phase 3 complete) | {challenged} |",
        f"| Adapted (Phase 2 complete) | {adapted} |",
        f"| Translated only (Phase 1) | {translated} |",
        f"| GATE ready | {'✅ YES' if gate_ready else '❌ NOT YET'} |",
        f"",
        f"## Challenge Results",
        f"",
        f"| Verdict | Count |",
        f"|---|---|",
    ]
    for v in ("PASS", "WARN", "FAIL"):
        n = verdict_counts.get(v, 0)
        lines.append(f"| {v} | {n} |")
    lines += [
        f"",
        f"## Cost Summary",
        f"",
        f"| Phase | Cost (USD) |",
        f"|---|---|",
        f"| Phase 1 — Azure translate | ${translate_cost:.2f} |",
        f"| Phase 2 — Adaptation (Anthropic) | ${adapt_cost:.2f} |",
        f"| Phase 3 — Challenge (Anthropic) | ${challenge_cost:.2f} |",
        f"| **Total** | **${total_cost:.2f}** |",
        f"",
    ]

    if fails:
        lines += [
            f"## ❌ FAIL — Require Re-adaptation ({len(fails)})",
            f"",
        ]
        for c in fails:
            lines.append(f"- b{c['binder_id']}/c{c['chapter_id']}: {c['chapter_name']}")
        lines.append("")

    if warns:
        lines += [
            f"## ⚠ WARN — Review Before Proceeding ({len(warns)})",
            f"",
            f"These chapters passed validation but the LLM challenger raised concerns.",
            f"Review challenger reports before signing off.",
            f"",
        ]
        for c in warns:
            lines.append(f"- b{c['binder_id']}/c{c['chapter_id']}: {c['chapter_name']}")
        lines.append("")

    lines += [
        f"## Bilingual Reader",
        f"",
        f"Start the Astro dev server:",
        f"```bash",
        f"cd podcast-reader && npm run dev",
        f"```",
        f"Then navigate to `http://localhost:4321/wisdom` to review any chapter.",
        f"",
        f"## Next Step",
        f"",
        f"After review:",
        f"```bash",
        f"# Intake KAHSKOLE into the podcast pipeline",
        f"# python scripts/podcast/intake_book.py --from-bundle <bundle_root>",
        f"```",
    ]

    report = "\n".join(lines)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written: {out}")

    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "_workspace/plan/wisdom-gate-report.md")
    args = ap.parse_args()
    report = generate_report(args.out)
    print(report)


if __name__ == "__main__":
    main()
