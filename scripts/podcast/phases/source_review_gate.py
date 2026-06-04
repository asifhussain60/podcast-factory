"""source_review_gate.py — Wave I (I4): Phase 06a source review gate.

A lightweight Haiku pass that reviews companion sources for authenticity,
cross-references, and suspicious gaps before the per-chapter LLM budget runs.

Writes _system/review-gate.json. Orchestrator halts with
phase_status="awaiting_human_review" after this phase completes.

The R4 guard in resume_dispatcher.py reads review-gate.json and clears the
halt only when approved=true is set (via approve_book.py or the Astro UI).

CLI usage:
    python3 scripts/podcast/phases/source_review_gate.py <book-dir>
    python3 scripts/podcast/phases/source_review_gate.py <book-dir> --dry-run
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from _paths import REPO_ROOT  # noqa: E402


@dataclass
class ReviewGate:
    phase: str = "06a"
    approved: bool = False
    warnings: list[dict] = field(default_factory=list)
    reviewed_at: str | None = None
    approved_at: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_file(cls, path: Path) -> "ReviewGate":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            phase=data.get("phase", "06a"),
            approved=bool(data.get("approved", False)),
            warnings=list(data.get("warnings", [])),
            reviewed_at=data.get("reviewed_at"),
            approved_at=data.get("approved_at"),
        )


HAIKU_REVIEW_SYSTEM = """\
You are a scholarly source reviewer for an Islamic book podcast pipeline.
Review the source material summary and flag any concerns.

Check for:
1. Suspicious attribution gaps (citations without traceable sources)
2. Anachronistic references (modern concepts in historical text)
3. Doctrinal cross-contamination (Sunni content in Ismaili source or vice versa)
4. Missing companion source material (chapters reference works not in sources)
5. Authenticity signals (translator notes, editorial additions vs original)

Respond with JSON: {"warnings": [{"severity": "P0|P1|P2", "message": "...",
"chapter": "optional"}], "overall_assessment": "PASS|WARN|FAIL",
"notes": "brief prose summary"}

P0 = blocks pipeline (authentication failure, severe cross-contamination)
P1 = notable concern requiring human attention
P2 = informational observation
"""


def _build_source_summary(book_dir: Path) -> str:
    """Build a summary of available source material for Haiku review."""
    system_dir = book_dir / "_system"
    lines = [f"Book: {book_dir.name}", ""]

    # Read meta.yml if present
    meta_path = book_dir / "meta.yml"
    if meta_path.exists():
        lines.append("=== meta.yml ===")
        lines.append(meta_path.read_text(encoding="utf-8")[:500])
        lines.append("")

    # Read series-plan.md summary (first 800 chars)
    series_plan = system_dir / "series-plan.md"
    if series_plan.exists():
        lines.append("=== Series Plan (excerpt) ===")
        lines.append(series_plan.read_text(encoding="utf-8")[:800])
        lines.append("")

    # List chapter files
    chapters_dir = book_dir / "chapters"
    if chapters_dir.exists():
        chapter_files = sorted(chapters_dir.glob("ch*.txt"))
        lines.append(f"=== Chapters ({len(chapter_files)} total) ===")
        for cf in chapter_files[:5]:
            first_line = cf.read_text(encoding="utf-8").split("\n")[0][:120]
            lines.append(f"  {cf.stem}: {first_line}")
        if len(chapter_files) > 5:
            lines.append(f"  … and {len(chapter_files) - 5} more")
        lines.append("")

    # Source files
    source_dir = system_dir / "source" / "text"
    if source_dir.exists():
        source_files = list(source_dir.glob("*.md"))
        lines.append(f"=== Source Files: {[f.name for f in source_files]} ===")

    return "\n".join(lines)


def _call_haiku_review(summary: str) -> dict:
    """Call Haiku to review source material. Returns parsed response dict."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        return {
            "warnings": [{"severity": "P2", "message": "anthropic not installed — review skipped"}],
            "overall_assessment": "WARN",
            "notes": "Source review skipped: anthropic package not available.",
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "warnings": [{"severity": "P2", "message": "ANTHROPIC_API_KEY not set — review skipped"}],
            "overall_assessment": "WARN",
            "notes": "Source review skipped: no API key.",
        }

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            system=HAIKU_REVIEW_SYSTEM,
            messages=[{"role": "user", "content": f"Review this source material:\n\n{summary}"}],
        )
        raw = response.content[0].text if response.content else "{}"
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON in response")
        return json.loads(raw[start:end])
    except Exception as exc:  # noqa: BLE001
        return {
            "warnings": [{"severity": "P1", "message": f"Haiku review error: {exc}"}],
            "overall_assessment": "WARN",
            "notes": f"Review call failed: {exc}",
        }


def run_source_review_gate(book_dir: Path, *, dry_run: bool = False) -> ReviewGate:
    """Run Phase 06a source review gate. Returns a ReviewGate instance."""
    system_dir = book_dir / "_system"
    system_dir.mkdir(parents=True, exist_ok=True)
    gate_path = system_dir / "review-gate.json"

    # If gate already exists and approved, don't re-run
    if gate_path.exists():
        existing = ReviewGate.from_file(gate_path)
        if existing.approved:
            print(f"  Source review gate already approved — skipping re-run.")
            return existing

    summary = _build_source_summary(book_dir)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if dry_run:
        gate = ReviewGate(
            phase="06a",
            approved=False,
            warnings=[{"severity": "P2", "message": "dry-run — no actual review"}],
            reviewed_at=now,
        )
    else:
        review = _call_haiku_review(summary)
        warnings = review.get("warnings", [])
        assessment = review.get("overall_assessment", "WARN")
        notes = review.get("notes", "")

        # P0 warnings = auto-fail
        p0_warnings = [w for w in warnings if w.get("severity") == "P0"]
        if p0_warnings:
            print(f"  REVIEW: {len(p0_warnings)} P0 warning(s) — pipeline blocked.")
        else:
            print(f"  REVIEW: {assessment} — {len(warnings)} warning(s). Notes: {notes[:80]}")

        gate = ReviewGate(
            phase="06a",
            approved=False,  # Always requires human approval
            warnings=warnings,
            reviewed_at=now,
        )

    gate_path.write_text(gate.to_json(), encoding="utf-8")
    print(f"  Wrote review-gate.json ({len(gate.warnings)} warnings).")
    return gate


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Phase 06a source review gate.")
    parser.add_argument("book_dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    gate = run_source_review_gate(args.book_dir, dry_run=args.dry_run)
    print(f"\ngate approved={gate.approved}, warnings={len(gate.warnings)}")
    if gate.warnings:
        for w in gate.warnings[:5]:
            print(f"  [{w.get('severity','?')}] {w.get('message','')}")


if __name__ == "__main__":
    main()
