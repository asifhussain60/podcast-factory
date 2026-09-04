#!/usr/bin/env python3
"""The real-money cap is checked inside a lane, not only between phases.

`cost_ceiling_check` existed and was called in exactly three places: the resume
dispatcher, the run supervisor, and each convergence iteration. All three are
phase-or-iteration boundaries, so a lane that fans out hundreds of PAID calls
inside one phase could run straight past the cap and only be noticed when the
phase ended -- vowelling at eight concurrent threads over every Arabic run in a
book, narration buying a clip per paragraph, the video layer generating an image
per slide. The cap says "no more real money on this book"; it now means that
while a lane is running, and the check is one pass over one JSONL file, which is
nothing beside the calls it guards.

Each case seeds the book's own ledger above the hard cap and asserts the lane
refuses before it buys anything.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reader_narration as rn  # noqa: E402
import vowel_book  # noqa: E402
from cost_guard import CostCeilingReached  # noqa: E402
from test_reader_narration import make_book  # noqa: E402
from vowel_glossary import vowel_glossary  # noqa: E402

RUN = "قال العالم"


def _overspent(book_dir: Path) -> Path:
    """A ledger carrying more real money than any book's hard cap allows."""
    (book_dir / "_system").mkdir(parents=True, exist_ok=True)
    (book_dir / "_system" / "cost-ledger.jsonl").write_text(
        json.dumps(
            {
                "ts": "2026-09-04T00:00:00Z",
                "phase": "0book-compose",
                "step": "5a-vowelling",
                "model": "gemini-2.5-pro",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 9_999.0,
                "engine": "gemini",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return book_dir


def _never_called(*_a, **_k):
    raise AssertionError("a paid call was made after the hard cap was reached")


def test_the_vowelling_sweep_refuses_once_the_cap_is_reached(tmp_path: Path) -> None:
    book = _overspent(tmp_path)
    with pytest.raises(CostCeilingReached):
        vowel_book.vowel_runs(f"He said: {RUN} today.", log=lambda _m: None, call=_never_called, book_dir=book)


def test_the_lexical_sweep_refuses_once_the_cap_is_reached(tmp_path: Path) -> None:
    book = _overspent(tmp_path)
    with mock.patch.object(vowel_book, "_gemini", _never_called), pytest.raises(CostCeilingReached):
        vowel_book.vowel_lexical(f'The word ("{RUN}") means something.', book_dir=book)


def test_the_glossary_pass_refuses_once_the_cap_is_reached(tmp_path: Path) -> None:
    book = _overspent(tmp_path)
    (book / "_system" / "glossary.yml").write_text(
        f'- term: scholar\n  transliteration: "qala al-alim"\n  arabic_script: "{RUN}"\n',
        encoding="utf-8",
    )
    with pytest.raises(CostCeilingReached):
        vowel_glossary(book, log=lambda _m: None, call=_never_called)


def test_narration_refuses_once_the_cap_is_reached(tmp_path: Path) -> None:
    book = _overspent(make_book(tmp_path))
    with (
        mock.patch.object(rn, "synthesize_text", _never_called),
        pytest.raises(CostCeilingReached),
    ):
        rn.render_reader_narration(book)


def test_the_video_layer_refuses_once_the_cap_is_reached(tmp_path: Path) -> None:
    # Every image is real money at a fixed price and a whole episode's worth is
    # generated inside one run, so the check belongs per image.
    import generate_video_layer as gvl

    book = _overspent(tmp_path)
    with (
        mock.patch.object(gvl, "_gemini_client", return_value=(_never_called, None)),
        pytest.raises(CostCeilingReached),
    ):
        gvl._generate_background_images(
            {"backgrounds": [{"bg_id": "bg01", "theme": "dawn", "prompt": "x"}]},
            tmp_path / "images",
            book,
            "EP01-x",
        )


def test_a_book_under_the_cap_is_not_disturbed(tmp_path: Path) -> None:
    # The guard must be invisible in the ordinary case, or a lane that reads the
    # ledger once per batch becomes a new way for a run to fail.
    book = make_book(tmp_path)
    durations = iter([1.2, 0.4, 0.8, 2.4, 2.4])
    with (
        mock.patch.object(rn, "synthesize_text", side_effect=lambda t, p: b"AUDIO"),
        mock.patch.object(rn, "audio_duration_seconds", side_effect=lambda _p: next(durations)),
        mock.patch.object(rn, "concat_audio", side_effect=lambda parts, out: out.write_bytes(b"MP3")),
        mock.patch.object(rn, "append_azure_speech_cost"),
    ):
        assert rn.render_reader_narration(book).outcome == "completed"
