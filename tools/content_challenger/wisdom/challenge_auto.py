"""challenge_auto.py — LLM challenger for an adapted KAHSKOLE bundle.

Runs the deterministic validator first. If P0 failures exist, halts with error.
Then calls the Anthropic API (claude-haiku-4-5-20251001) for a semantic quality
review and writes wisdom-challenger-report.md.

Stage transition: adapted → challenged.
Idempotent: skips if already challenged.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
CHALLENGE_COST_LEDGER = REPO_ROOT / "_workspace" / "plan" / "wisdom-challenge-cost-ledger.jsonl"

MODEL = "claude-haiku-4-5-20251001"

_INPUT_COST_PER_M = 0.80
_OUTPUT_COST_PER_M = 4.00

CHALLENGE_SYSTEM_PROMPT = """\
You are the KAHSKOLE chapter challenger. Review an adapted chapter for the \
following quality criteria and produce a concise report.

Report format (markdown, under 400 words):

## Challenge Report — [Chapter Title]
**Date:** [today]
**Verdict:** PASS | WARN | FAIL

### Checks
- **Prose quality**: Is the English scholarly, varied, and readable? \
  Mark FAIL if it reads as raw machine translation.
- **Terminology**: Are key Ismaili terms correctly transliterated with first-occurrence glosses?
- **Faithfulness**: Does the adapted content faithfully convey the doctrinal content \
  of the source? Note any additions or omissions.
- **Citations**: Are the [^cite-N] augmentations relevant and high-confidence?
- **Section structure**: Are all section headings meaningful and appropriate?

### Findings
List any P0 (critical) or P1 (warning) findings, or write "None found."

### Verdict rationale
One sentence on why you assigned PASS / WARN / FAIL.\
"""


def _call_claude_p(user_content: str, timeout: int = 300) -> tuple[str, int, int]:
    """Shell out to `claude -p` (Max subscription — no API key, no quota).

    Returns (response_text, 0, 0) — token counts unavailable via claude -p;
    cost is $0.00 (covered by Max subscription).
    """
    full_prompt = CHALLENGE_SYSTEM_PROMPT + "\n\n---\n\n" + user_content
    result = subprocess.run(
        [
            "claude", "-p", full_prompt,
            "--tools", "",
            "--no-session-persistence",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p exited {result.returncode}.\nstderr: {result.stderr[:400]}"
        )
    return result.stdout.strip(), 0, 0


def _read_stage(bundle_yml: Path) -> str:
    for line in bundle_yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("stage:"):
            return line.split(":", 1)[1].strip()
    return ""


def _update_stage(bundle_yml: Path, new_stage: str) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    lines = [
        f"stage: {new_stage}" if l.startswith("stage:") else l
        for l in text.splitlines()
    ]
    bundle_yml.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_challenge_block(bundle_yml: Path, model: str, verdict: str, cost: float, completed_at: str) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    skipping = False
    for line in lines:
        if line.startswith("challenge:"):
            skipping = True
            continue
        if skipping and (not line or line[0] in (" ", "\t")):
            continue
        skipping = False
        out.append(line)
    block = (
        f"\nchallenge:\n"
        f"  engine: {model}\n"
        f"  verdict: {verdict}\n"
        f"  completed_at: {completed_at}\n"
        f"  challenge_cost_usd: {cost:.6f}\n"
    )
    bundle_yml.write_text("\n".join(out).rstrip() + block, encoding="utf-8")


def _append_cost_ledger(binder_id: Optional[int], chapter_id: Optional[int], cost_usd: float, completed_at: str) -> None:
    CHALLENGE_COST_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "binder_id": binder_id,
        "chapter_id": chapter_id,
        "phase": "challenge",
        "cost_usd": round(cost_usd, 6),
        "completed_at": completed_at,
        "model": MODEL,
    }
    with CHALLENGE_COST_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")



def _extract_verdict(report_text: str) -> str:
    m = re.search(r"\*\*Verdict:\*\*\s*(PASS|WARN|FAIL)", report_text)
    if m:
        return m.group(1)
    for line in report_text.splitlines():
        for v in ("PASS", "WARN", "FAIL"):
            if v in line:
                return v
    return "WARN"


def challenge_bundle(
    bundle_root: Path,
    *,
    binder_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """Run deterministic + LLM challenge on an adapted bundle.

    Returns summary dict with verdict, cost_usd.
    Stage transition: adapted → challenged.
    """
    from .validator import validate_bundle

    bundle_yml = bundle_root / "bundle.yml"
    text_dir = bundle_root / "_system" / "source" / "text"
    adapted = text_dir / "adapted-extract.en.md"
    raw_en = text_dir / "raw-extract.en.md"
    citations_file = text_dir / "adaptation-citations.jsonl"
    report_file = text_dir / "wisdom-challenger-report.md"

    if not bundle_yml.exists():
        raise FileNotFoundError(f"bundle.yml not found: {bundle_yml}")

    stage = _read_stage(bundle_yml)
    if stage == "challenged":
        return {"skipped": True, "stage": "challenged"}
    if stage != "adapted":
        raise RuntimeError(f"Stage is '{stage}' — run adapt-auto first.")

    # Run deterministic validator
    val_result = validate_bundle(bundle_root)

    if val_result.p0_count > 0:
        raise RuntimeError(
            f"Validator P0 failures — cannot challenge:\n" +
            "\n".join(val_result.summary_lines())
        )

    if dry_run:
        return {
            "skipped": False,
            "dry_run": True,
            "validator": val_result.summary_lines(),
            "cost_usd": 0.0,
        }

    # Build challenge input: first 8KB of adapted + validator findings
    adapted_text = adapted.read_text(encoding="utf-8") if adapted.exists() else ""
    raw_text = raw_en.read_text(encoding="utf-8") if raw_en.exists() else ""

    # Use a representative sample for the LLM review (first 6KB)
    sample = adapted_text[:6000]
    if len(adapted_text) > 6000:
        sample += f"\n\n[... {len(adapted_text) - 6000:,} chars omitted for challenger review ...]"

    citations_sample = ""
    if citations_file.exists():
        citations_sample = citations_file.read_text(encoding="utf-8")[:1000]

    validator_summary = "\n".join(val_result.summary_lines())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    user_content = (
        f"Date: {today}\n"
        f"Bundle: binder {binder_id}, chapter {chapter_id}\n\n"
        f"DETERMINISTIC VALIDATOR RESULTS:\n{validator_summary}\n\n"
        f"ADAPTED CONTENT SAMPLE:\n{sample}\n\n"
        f"CITATIONS SAMPLE:\n{citations_sample}"
    )

    report_text, in_tok, out_tok = _call_claude_p(user_content)
    verdict = _extract_verdict(report_text)
    cost_usd = (in_tok * _INPUT_COST_PER_M + out_tok * _OUTPUT_COST_PER_M) / 1_000_000
    completed_at = datetime.now(timezone.utc).isoformat()

    # Write report
    full_report = (
        f"# KAHSKOLE Challenger Report\n"
        f"*Generated: {completed_at} | Model: {MODEL}*\n\n"
        f"## Deterministic Validator\n"
        + "\n".join(val_result.summary_lines()) + "\n\n"
        + report_text
    )
    report_file.write_text(full_report, encoding="utf-8")

    # Update bundle.yml and seal
    _append_challenge_block(bundle_yml, MODEL, verdict, cost_usd, completed_at)
    _update_stage(bundle_yml, "challenged")
    _append_cost_ledger(binder_id, chapter_id, cost_usd, completed_at)

    return {
        "skipped": False,
        "verdict": verdict,
        "validator_p0": val_result.p0_count,
        "validator_p1": val_result.p1_count,
        "cost_usd": cost_usd,
        "report_path": str(report_file),
    }
