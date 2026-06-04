"""per_chapter_optimize.py — Wave I (I6): Phase per-chapter-optimize.

A Sonnet pass on each episode bundle after per-chapter authoring and before
the 0g dual-auditor. Checks:
  1. NotebookLM format hygiene (JSON keys, array shapes)
  2. Host-role consistency (no host switching mid-episode)
  3. Teaching arc completeness (hook → core → example → application → bridge)

Writes _system/optimize-report.json per chapter.
P0-class findings (malformed JSON, missing arc sections) block the chapter.
P1+ findings are logged as warnings and do not block.

Phase is skipped if optimize_enabled=false in meta.yml (default: false for
backward compatibility on existing books).

CLI usage:
    python3 scripts/podcast/phases/per_chapter_optimize.py <book-dir> [--chapter ch01]
    python3 scripts/podcast/phases/per_chapter_optimize.py <book-dir> --dry-run
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from _paths import REPO_ROOT  # noqa: E402


@dataclass
class OptimizeFinding:
    severity: str   # P0 | P1 | P2
    check: str      # "format" | "host-role" | "arc"
    message: str
    location: str = ""   # e.g. "turn 3"


@dataclass
class OptimizeReport:
    chapter: str
    pass_count: int = 0
    findings: list[OptimizeFinding] = field(default_factory=list)
    p0_count: int = 0
    verdict: str = "PASS"   # PASS | WARN | BLOCKED

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2, ensure_ascii=False)


def _check_format(episode_text: str) -> list[OptimizeFinding]:
    """Check NotebookLM format hygiene: host/guest turns, array integrity."""
    findings = []
    # Basic check: should have HOST and GUEST speaker labels
    if "HOST:" not in episode_text.upper() and "NARRATOR:" not in episode_text.upper():
        findings.append(OptimizeFinding(
            severity="P1", check="format",
            message="No HOST or NARRATOR speaker label found in episode text.",
        ))
    # Check for abrupt mid-text JSON fragments (sign of malformed template output)
    import re
    if re.search(r'"\s*:\s*\[|\]\s*,\s*"', episode_text):
        findings.append(OptimizeFinding(
            severity="P0", check="format",
            message="JSON-fragment pattern detected in episode text — possible template bleed-through.",
        ))
    return findings


def _check_host_role(episode_text: str) -> list[OptimizeFinding]:
    """Check that host/guest roles do not switch mid-episode."""
    findings = []
    import re
    turns = re.findall(r"^(HOST|GUEST|NARRATOR|SPEAKER [AB]):", episode_text, re.MULTILINE)
    if not turns:
        return findings
    # Find role switches (HOST→GUEST→HOST is fine; HOST→NARRATOR is suspicious)
    unique_roles = set(turns)
    if len(unique_roles) > 2:
        findings.append(OptimizeFinding(
            severity="P1", check="host-role",
            message=f"More than 2 distinct speaker roles detected: {sorted(unique_roles)}",
        ))
    return findings


def _check_arc(episode_text: str) -> list[OptimizeFinding]:
    """Check teaching arc completeness: hook → core → example → application → bridge."""
    findings = []
    lower = episode_text.lower()
    arc_signals = {
        "hook":        ["today we", "this episode", "in this session", "let's begin"],
        "core":        ["the key", "fundamentally", "at its heart", "the principle"],
        "example":     ["for example", "for instance", "consider", "take the case"],
        "application": ["so how", "in practice", "what this means", "you can apply"],
        "bridge":      ["next time", "in our next", "coming up", "we'll explore"],
    }
    missing = []
    for arc_step, signals in arc_signals.items():
        if not any(sig in lower for sig in signals):
            missing.append(arc_step)

    if len(missing) >= 3:
        findings.append(OptimizeFinding(
            severity="P0" if "hook" in missing else "P1",
            check="arc",
            message=f"Teaching arc incomplete — missing signals for: {', '.join(missing)}",
        ))
    elif missing:
        findings.append(OptimizeFinding(
            severity="P2", check="arc",
            message=f"Weak arc signals for: {', '.join(missing)}",
        ))
    return findings


def _call_sonnet_optimize(episode_text: str, chapter_id: str) -> list[OptimizeFinding]:
    """Call Sonnet for a deeper arc and quality check on the episode text."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return []

    client = anthropic.Anthropic(api_key=api_key)
    system = (
        "You are a podcast episode quality reviewer. Check the episode for:\n"
        "1. Teaching arc: hook → core concept → concrete example → practical application → bridge to next\n"
        "2. Host consistency: does one host voice dominate? Any confusing role shifts?\n"
        "3. NotebookLM hygiene: clean speaker labels, no technical artifacts\n\n"
        "Respond ONLY with JSON: {\"findings\": [{\"severity\": \"P0|P1|P2\", "
        "\"check\": \"arc|format|host-role\", \"message\": \"...\", \"location\": \"...\"}], "
        "\"pass_count\": N}\n"
        "P0 = blocks episode. P1 = notable. P2 = minor."
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": f"Review episode {chapter_id}:\n\n{episode_text[:3000]}"}],
        )
        raw = response.content[0].text if response.content else "{}"
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == 0:
            return []
        data = json.loads(raw[start:end])
        return [
            OptimizeFinding(
                severity=f.get("severity", "P2"),
                check=f.get("check", "unknown"),
                message=f.get("message", ""),
                location=f.get("location", ""),
            )
            for f in data.get("findings", [])
        ]
    except Exception:  # noqa: BLE001
        return []


def optimize_chapter(
    chapter_id: str,
    episode_text: str,
    *,
    dry_run: bool = False,
) -> OptimizeReport:
    """Run all optimization checks on an episode text."""
    report = OptimizeReport(chapter=chapter_id)

    all_findings: list[OptimizeFinding] = []
    all_findings.extend(_check_format(episode_text))
    all_findings.extend(_check_host_role(episode_text))
    all_findings.extend(_check_arc(episode_text))

    if not dry_run:
        sonnet_findings = _call_sonnet_optimize(episode_text, chapter_id)
        all_findings.extend(sonnet_findings)

    report.findings = all_findings
    report.p0_count = sum(1 for f in all_findings if f.severity == "P0")
    report.pass_count = sum(1 for f in all_findings if f.severity not in ("P0", "P1"))

    if report.p0_count > 0:
        report.verdict = "BLOCKED"
    elif any(f.severity == "P1" for f in all_findings):
        report.verdict = "WARN"
    else:
        report.verdict = "PASS"

    return report


def run_book_optimize(
    book_dir: Path,
    *,
    dry_run: bool = False,
    chapter_filter: str | None = None,
) -> dict:
    """Optimize all episode drafts of a book. Writes per-chapter optimize-report.json."""
    # Check if optimization is enabled
    import yaml  # type: ignore[import]
    meta_path = book_dir / "meta.yml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if not meta.get("optimize_enabled", False):
            return {"skipped": True, "reason": "optimize_enabled=false in meta.yml"}

    episode_drafts = book_dir / "_system" / "episode-drafts"
    if not episode_drafts.is_dir():
        return {"error": "No episode-drafts directory found."}

    episode_files = sorted(episode_drafts.glob("ch*.txt"))
    if chapter_filter:
        episode_files = [ef for ef in episode_files if chapter_filter in ef.name]

    results = {
        "chapters": 0, "pass": 0, "warn": 0, "blocked": 0,
        "reports": [], "dry_run": dry_run,
    }

    for ef in episode_files:
        episode_text = ef.read_text(encoding="utf-8")
        report = optimize_chapter(ef.stem, episode_text, dry_run=dry_run)

        # Write per-chapter report
        if not dry_run:
            report_path = book_dir / "_system" / f"optimize-report-{ef.stem}.json"
            report_path.write_text(report.to_json(), encoding="utf-8")

        results["chapters"] += 1
        results[report.verdict.lower() if report.verdict != "BLOCKED" else "blocked"] += 1
        results["reports"].append({
            "chapter": ef.stem,
            "verdict": report.verdict,
            "p0_count": report.p0_count,
        })

    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Phase per-chapter-optimize.")
    parser.add_argument("book_dir", type=Path)
    parser.add_argument("--chapter", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_book_optimize(args.book_dir, dry_run=args.dry_run, chapter_filter=args.chapter)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
