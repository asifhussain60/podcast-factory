"""`enable_slide_decks: false` must be honoured by EVERY path, not just the driver.

isaf-al-talib authored 27 unwanted decks before the driver read the flag (fixed in 02424296, tested in
test_slide_decks_opt_out.py). That covers the phase that AUTHORS decks. This pins the consumers: the
reviews, the recheck gates, and any future caller that might quietly demand decks for a book that opted
out. A deck requirement should only ever apply to a phase that actually completed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import _phase_review as pr  # noqa: E402
import _progress  # noqa: E402


@pytest.fixture
def opted_out_book(tmp_path: Path) -> Path:
    d = tmp_path / "opted-out"
    (d / "_system").mkdir(parents=True)
    (d / "_system" / "series-config.yaml").write_text("enable_slide_decks: false\n", encoding="utf-8")
    state = {
        "slug": "opted-out",
        "phases": {
            "per-chapter-slides": {"status": "skipped", "reason": "enable_slide_decks=false"},
            "per-chapter": {"status": "completed"},
        },
    }
    (d / "_system" / "orchestrator-state.json").write_text(json.dumps(state), encoding="utf-8")
    return d


def test_a_skipped_slide_phase_is_never_reviewed(opted_out_book):
    assert _progress._phase_review_for(opted_out_book, "per-chapter-slides", "skipped") is None


def test_no_later_review_rechecks_the_slide_gate_for_a_book_that_skipped_the_phase(opted_out_book):
    for later in ("per-chapter", "finalize"):
        if not pr.phase_has_gates(later):
            continue
        report = pr.review_phase(opted_out_book, later)
        assert "PPS1" not in [g["gate"] for g in report["gates"]], (
            f"reviewing {later!r} demanded slide decks from a book that opted out"
        )


def test_only_the_review_registry_may_require_decks():
    """A new caller of gate_slide_decks_present would silently re-impose decks. Keep the surface at two files."""
    callers = []
    for path in sorted(SCRIPTS.rglob("*.py")):
        rel = path.relative_to(SCRIPTS).as_posix()
        if "/tests/" in f"/{rel}" or "__pycache__" in rel:
            continue
        if re.search(r"gate_slide_decks_present", path.read_text(encoding="utf-8")):
            callers.append(rel)
    assert set(callers) == {"_phase_gates.py", "_phase_review.py"}, callers
