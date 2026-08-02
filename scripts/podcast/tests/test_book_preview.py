#!/usr/bin/env python3
"""The reading edition is built at the finalize halt, and paid for once.

Two properties, and the second is the one that costs real money if it breaks:

1. The lane runs early ONLY when it can complete without a human artifact. Under
   `book_visuals=manual_only` it has no halt in it. Under an explicit `pipeline`
   it stops for dropped NotebookLM decks, so the early call declines and leaves
   the lane where it always was.
2. The publish-time call must not re-run it. That call re-composes the whole book
   — hours of model time — to arrive at the PDF the human has already reviewed.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _book_preview import (
    can_build_without_human_artifact,
    maybe_build_reading_edition_early,
    reading_edition_is_built,
)


def _book(tmp: Path, *, config: str = "", state: dict | None = None, pdf: bool = False) -> Path:
    bd = tmp / "a-book"
    (bd / "_system").mkdir(parents=True, exist_ok=True)
    (bd / "book").mkdir(parents=True, exist_ok=True)
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    (bd / "_system" / "orchestrator-state.json").write_text(json.dumps(state or {}), encoding="utf-8")
    if pdf:
        (bd / "book" / "book.pdf").write_bytes(b"%PDF-1.4 stub")
    return bd


_RENDERED = {"phases": {"0book-render": {"status": "completed"}}}


class EligibilityTests(unittest.TestCase):
    def test_the_default_book_can_build_early(self) -> None:
        with TemporaryDirectory() as td:
            self.assertTrue(can_build_without_human_artifact(_book(Path(td))))

    def test_an_explicit_pipeline_book_cannot(self) -> None:
        with TemporaryDirectory() as td:
            bd = _book(Path(td), config="book_visuals: pipeline\n")
            self.assertFalse(can_build_without_human_artifact(bd))

    def test_a_bad_knob_declines_rather_than_guessing(self) -> None:
        with TemporaryDirectory() as td:
            bd = _book(Path(td), config="book_visuals: whatever\n")
            self.assertFalse(can_build_without_human_artifact(bd))


class IdempotenceTests(unittest.TestCase):
    def test_a_rendered_book_is_recognised(self) -> None:
        with TemporaryDirectory() as td:
            self.assertTrue(reading_edition_is_built(_book(Path(td), state=_RENDERED, pdf=True)))

    def test_completed_status_without_a_pdf_is_NOT_built(self) -> None:
        # The status can outlive the artifact — a stale state must not convince
        # publish to skip the only chance to produce the deliverable.
        with TemporaryDirectory() as td:
            self.assertFalse(reading_edition_is_built(_book(Path(td), state=_RENDERED, pdf=False)))

    def test_a_pdf_without_a_completed_render_is_NOT_built(self) -> None:
        with TemporaryDirectory() as td:
            self.assertFalse(reading_edition_is_built(_book(Path(td), state={}, pdf=True)))

    def test_the_early_call_declines_when_already_built(self) -> None:
        with TemporaryDirectory() as td:
            bd = _book(Path(td), state=_RENDERED, pdf=True)
            self.assertFalse(maybe_build_reading_edition_early(bd, log=lambda _m: None))

    def test_the_early_call_declines_for_a_pipeline_book(self) -> None:
        with TemporaryDirectory() as td:
            bd = _book(Path(td), config="book_visuals: pipeline\n")
            self.assertFalse(maybe_build_reading_edition_early(bd, log=lambda _m: None))


class WiringTests(unittest.TestCase):
    def test_the_finalize_halt_calls_it(self) -> None:
        text = (SCRIPTS_PODCAST / "phases" / "chapter_driver.py").read_text(encoding="utf-8")
        self.assertIn("maybe_build_reading_edition_early", text)

    def test_publish_skips_a_book_already_built(self) -> None:
        text = (SCRIPTS_PODCAST / "phases" / "publish_driver.py").read_text(encoding="utf-8")
        self.assertIn("reading_edition_is_built", text)

    def test_a_lane_failure_never_raises_into_the_halt_card(self) -> None:
        # The reading edition is a companion deliverable; it must never cost the
        # podcast its halt, which is where the NotebookLM upload table is printed.
        with TemporaryDirectory() as td:
            bd = _book(Path(td))
            (bd / "_system" / "series-config.yaml").unlink()
            try:
                maybe_build_reading_edition_early(bd, log=lambda _m: None)
            except Exception as exc:  # pragma: no cover
                self.fail(f"early build raised into the caller: {exc!r}")


if __name__ == "__main__":
    unittest.main()
