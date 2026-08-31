"""A chapter's recording holds that chapter, and nothing outside it.

Asif, 2026-08-31, having pressed play and heard "Hello, welcome to my lecture"
two and a half hours before the chapter he opened: "can you strip out this noise
from the recording so it only represents what's in the chapter."

What is cut is not a judgement. It is the span the chapter's own text was matched
to — the same spans `_cue_gate` passed — and everything NO chapter accounts for
is what goes. On `purification-of-the-heart` that is 149 of 1,175 minutes.

Half these cases are about the two things that must never happen: an original
recording being modified, and a cut file's timings still measuring the file it
came from.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cut_chapter_audio import LEAD_IN_S, TAIL_S, _span, cut_book, rebase  # noqa: E402


def _book(tmp_path: Path, chapters: dict) -> Path:
    d = tmp_path / "bk"
    (d / "book" / "narration").mkdir(parents=True)
    (d / "m4a" / "Episodes").mkdir(parents=True)
    (d / "m4a" / "Episodes" / "ep01.mp3").write_bytes(b"not really audio")
    (d / "book" / "narration" / "manifest.json").write_text(
        json.dumps({"engine": "author-recording", "chapters": chapters}), encoding="utf-8"
    )
    return d


def _chapter(start: float, end: float, **extra) -> dict:
    entry = {
        "title": "Envy",
        "episode": 1,
        "audio": "m4a/Episodes/ep01.mp3",
        "audio_key": "bk/audio/ep01.mp3",
        "cues": [
            {"idx": 0, "blockIndex": 0, "startS": start, "endS": start + 5, "text": "first"},
            {"idx": 1, "blockIndex": 1, "startS": end - 5, "endS": end, "text": "last"},
        ],
    }
    entry.update(extra)
    return entry


# ── what gets cut ────────────────────────────────────────────────────────────
def test_the_span_runs_from_the_first_cue_to_the_last():
    start, end = _span(_chapter(8885.79, 11889.0))
    assert start == 8885.79 - LEAD_IN_S
    assert end == 11889.0 + TAIL_S


def test_a_lead_in_keeps_the_first_word_off_the_frame_boundary():
    """A stream copy lands on the nearest frame, which can clip an opening
    consonant. Room tone before the first word costs nothing."""
    start, _end = _span(_chapter(100.0, 200.0))
    assert start == 100.0 - LEAD_IN_S


def test_the_lead_in_never_runs_before_the_recording_starts():
    start, _end = _span(_chapter(0.1, 60.0))
    assert start == 0.0


def test_an_untimed_chapter_has_no_span_and_is_left_alone(tmp_path):
    entry = _chapter(1, 2)
    entry["cues"] = []
    d = _book(tmp_path, {"envy": entry})
    report = cut_book(d, log=lambda m: None)
    assert report["cut"] == []
    assert "no timings" in report["skipped"][0]


# ── the timings come with the cut ────────────────────────────────────────────
def test_cues_are_rebased_to_the_new_file():
    """A cue's seconds measure the file it was cut from. Left alone they would
    highlight paragraphs hours away from the audio."""
    out = rebase([{"startS": 8886.0, "endS": 8890.0}], 8885.0)
    assert out[0]["startS"] == 1.0
    assert out[0]["endS"] == 5.0


def test_a_rebased_cue_is_never_negative():
    assert rebase([{"startS": 5.0, "endS": 9.0}], 8.0)[0]["startS"] == 0.0


def test_rebasing_keeps_everything_else_about_a_cue():
    out = rebase([{"startS": 10.0, "endS": 12.0, "blockIndex": 4, "text": "x"}], 10.0)
    assert out[0]["blockIndex"] == 4 and out[0]["text"] == "x"


# ── what must not happen ─────────────────────────────────────────────────────
def test_a_recut_uses_the_recorded_source_span_not_the_rebased_cues(tmp_path):
    """The bug this pins produced a wrong file: after a cut the cues measure the
    CUT, so recomputing the span from them cuts the first fifty minutes of the
    sitting instead of the fifty the chapter occupies. `cut_span` is in the
    source's own coordinates and is the only thing that survives a rebase."""
    d = _book(
        tmp_path,
        {"envy": _chapter(0.35, 3001.5, cut_span=[8885.44, 11889.6], cut_from="m4a/Episodes/ep01.mp3")},
    )
    lines: list[str] = []
    cut_book(d, force=True, dry_run=True, log=lines.append)
    assert "148.1" in lines[0], lines


def test_the_original_recording_is_never_written(tmp_path):
    d = _book(tmp_path, {"envy": _chapter(10.0, 40.0)})
    before = (d / "m4a" / "Episodes" / "ep01.mp3").read_bytes()
    cut_book(d, dry_run=True, log=lambda m: None)
    assert (d / "m4a" / "Episodes" / "ep01.mp3").read_bytes() == before


def test_a_book_with_no_timings_is_not_an_error(tmp_path):
    d = tmp_path / "bare"
    (d / "book").mkdir(parents=True)
    assert cut_book(d, log=lambda m: None)["outcome"] == "skipped"


def test_a_second_run_over_the_same_span_does_nothing(tmp_path):
    """Cutting nineteen hours again to arrive at the same files is the kind of
    no-op that has to actually be a no-op."""
    d = _book(tmp_path, {"envy": _chapter(0.35, 100.0, cut_span=[10.0, 40.0])})
    (d / "book" / "narration" / "envy.mp3").write_bytes(b"already cut")
    report = cut_book(d, log=lambda m: None)
    assert report["cut"] == []
    assert "already cut" in report["skipped"][0]


def test_the_cut_file_stops_pointing_at_the_whole_recording_s_key():
    """`_listener_media` REFERENCES an existing asset when the manifest names its
    key, so a cut chapter that kept `audio_key` would publish the ten-hour
    episode object instead of its own fifty-minute file."""
    import inspect

    import cut_chapter_audio

    src = inspect.getsource(cut_chapter_audio.cut_book)
    assert 'entry.pop("audio_key", None)' in src
