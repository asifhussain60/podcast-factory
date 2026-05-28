"""test_wisdom_quality_gate.py — Unit tests for the wisdom pipeline quality gate
(tools/content_translator/stages/seal.py).

Tests cover: valid stage transitions, PEQ gate enforcement on 'challenged' seal,
force-override, missing files, and backward transitions.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from tools.content_translator.stages.seal import seal_stage, _read_stage  # noqa: E402


# ---------------------------------------------------------------------------
# Bundle fixture helpers
# ---------------------------------------------------------------------------

def _make_bundle(tmp_path: Path, stage: str = "reviewed") -> Path:
    """Create a minimal bundle root with bundle.yml at the given stage."""
    bundle_root = tmp_path / "test-bundle"
    text_dir = bundle_root / "_system" / "source" / "text"
    text_dir.mkdir(parents=True)

    bundle_yml = bundle_root / "bundle.yml"
    bundle_yml.write_text(
        f"stage: {stage}\nsuggested_slug: wisdom-test\n",
        encoding="utf-8",
    )
    return bundle_root


def _add_files(bundle_root: Path, *filenames: str, content: str = "content") -> None:
    """Create named files in the bundle's text dir."""
    text_dir = bundle_root / "_system" / "source" / "text"
    for fn in filenames:
        (text_dir / fn).write_text(content, encoding="utf-8")


def _add_peq_report(bundle_root: Path, peq_total: float) -> None:
    """Write a wisdom-challenger-report.md with a PEQ table at the given total."""
    text_dir = bundle_root / "_system" / "source" / "text"
    report = text_dir / "wisdom-challenger-report.md"
    report.write_text(
        textwrap.dedent(f"""\
            ## Challenge Report

            Verdict: PASS

            ## PEQ Score

            | Axis | Weight | Score | Weighted |
            |---|---|---|---|
            | Fidelity   | 35% | 90.0 | 31.5 |
            | Voice      | 25% | 0.0 | 0.0 |
            | Structure  | 20% | 100.0 | 20.0 |
            | Enrichment | 20% | 80.0 | 16.0 |
            | **Total**  | 100% | — | **{peq_total:.1f}** |

            **Verdict: {'PASS' if peq_total >= 85 else 'WARN' if peq_total >= 70 else 'FAIL'}** — total {peq_total:.1f}
        """),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Stage transitions
# ---------------------------------------------------------------------------

class TestStageTransitions:
    def test_reviewed_to_translated(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "reviewed")
        _add_files(bundle, "raw-extract.en.md")
        result = seal_stage(bundle, "translated")
        assert result["sealed"] is True
        assert _read_stage(bundle / "bundle.yml") == "translated"

    def test_translated_to_adapted(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "translated")
        _add_files(bundle, "raw-extract.en.md", "adapted-extract.en.md", "adaptation-citations.jsonl")
        result = seal_stage(bundle, "adapted")
        assert result["sealed"] is True

    def test_already_sealed_skips(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "translated")
        _add_files(bundle, "raw-extract.en.md")
        result = seal_stage(bundle, "translated")
        assert result.get("skipped") is True

    def test_backward_transition_raises(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        with pytest.raises(RuntimeError, match="backwards"):
            seal_stage(bundle, "translated")

    def test_unknown_stage_raises(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "reviewed")
        with pytest.raises(ValueError, match="Unknown stage"):
            seal_stage(bundle, "nonexistent")

    def test_missing_bundle_yml_raises(self, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="bundle.yml"):
            seal_stage(empty_dir, "translated")


# ---------------------------------------------------------------------------
# Required files validation
# ---------------------------------------------------------------------------

class TestRequiredFiles:
    def test_missing_raw_extract_blocks_translated(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "reviewed")
        # Do not create raw-extract.en.md
        with pytest.raises(FileNotFoundError, match="raw-extract.en.md"):
            seal_stage(bundle, "translated")

    def test_missing_adapted_extract_blocks_adapted(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "translated")
        _add_files(bundle, "raw-extract.en.md")
        # Missing adapted-extract.en.md and adaptation-citations.jsonl
        with pytest.raises(FileNotFoundError):
            seal_stage(bundle, "adapted")

    def test_missing_report_blocks_challenged(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        # Missing wisdom-challenger-report.md
        with pytest.raises(FileNotFoundError):
            seal_stage(bundle, "challenged")


# ---------------------------------------------------------------------------
# PEQ gate on 'challenged' seal
# ---------------------------------------------------------------------------

class TestPeqGate:
    def test_peq_pass_seals(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        _add_peq_report(bundle, peq_total=88.0)
        result = seal_stage(bundle, "challenged")
        assert result["sealed"] is True

    def test_peq_warn_seals(self, tmp_path: Path):
        """70–84 is WARN but not a gate failure — should seal."""
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        _add_peq_report(bundle, peq_total=75.0)
        result = seal_stage(bundle, "challenged")
        assert result["sealed"] is True

    def test_peq_exactly_70_seals(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        _add_peq_report(bundle, peq_total=70.0)
        result = seal_stage(bundle, "challenged")
        assert result["sealed"] is True

    def test_peq_below_70_blocks(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        _add_peq_report(bundle, peq_total=65.0)
        with pytest.raises(RuntimeError, match="PEQ gate FAIL"):
            seal_stage(bundle, "challenged")

    def test_peq_below_70_force_override(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        _add_peq_report(bundle, peq_total=55.0)
        result = seal_stage(bundle, "challenged", force=True)
        assert result["sealed"] is True

    def test_no_peq_report_seals_without_gate(self, tmp_path: Path):
        """If no PEQ section in the report, gate is skipped (backward compat)."""
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        # Create a report WITHOUT a PEQ table
        text_dir = bundle / "_system" / "source" / "text"
        report = text_dir / "wisdom-challenger-report.md"
        report.write_text("## Challenge Report\n\nVerdict: PASS\n", encoding="utf-8")
        result = seal_stage(bundle, "challenged")
        assert result["sealed"] is True

    def test_seal_writes_completed_at(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, "adapted")
        _add_files(bundle, "adapted-extract.en.md", "adaptation-citations.jsonl")
        _add_peq_report(bundle, peq_total=80.0)
        result = seal_stage(bundle, "challenged")
        assert "completed_at" in result
        assert "2026" in result["completed_at"] or "T" in result["completed_at"]
