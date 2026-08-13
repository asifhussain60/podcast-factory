#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _progress  # noqa: E402
import reader_narration as rn  # noqa: E402
from phases import reader_narration_driver  # noqa: E402


def make_book(tmp_path: Path, *, bucket: str = "Islamic", profile: str = "islamic_scholarly") -> Path:
    book = tmp_path / "content" / bucket / "sample-book"
    (book / "_system").mkdir(parents=True)
    (book / "book").mkdir()
    (book / "_system" / "series-config.yaml").write_text(
        f"content_profile: {profile}\nreader_narration:\n  voice: jenny\n",
        encoding="utf-8",
    )
    (book / "book" / "book.md").write_text(
        "# Sample Book\n\n"
        "## 1. Opening\n\n"
        "This is the first paragraph (الإمامة).\n\n"
        "### A Teaching\n\n"
        "This is the second paragraph with *emphasis* and [a link](https://example.com).\n",
        encoding="utf-8",
    )
    return book


def test_scope_excludes_sessions_lane(tmp_path: Path) -> None:
    book = make_book(tmp_path, bucket="Sessions", profile="islamic_session")

    enabled, reason = rn.narration_enabled(book)

    assert not enabled
    assert "Islamic source" in reason


def test_scope_excludes_sessions_path_even_with_islamic_profile(tmp_path: Path) -> None:
    book = make_book(tmp_path, bucket="Sessions", profile="islamic_scholarly")

    enabled, reason = rn.narration_enabled(book)

    assert not enabled
    assert "KSESSIONS" in reason


def test_speech_text_removes_arabic_without_touching_source() -> None:
    text = rn.speech_text("A claim (الإمامة) with **proof** and `term`.")

    assert "الإمامة" not in text
    assert text == "A claim with proof and term."


def test_speech_text_skips_punctuation_only_fragments() -> None:
    assert rn.speech_text("...") == ""
    assert rn.speech_text("(الإمامة)") == ""


def test_synthesize_clip_retries_invalid_audio(tmp_path: Path) -> None:
    attempts = iter([b"BAD", b"MP3"])

    def fake_duration(path: Path) -> float:
        if path.read_bytes() == b"BAD":
            raise ValueError("invalid audio")
        return 1.5

    with (
        mock.patch.object(rn, "synthesize_text", side_effect=lambda *_args: next(attempts)) as synth,
        mock.patch.object(rn, "audio_duration_seconds", side_effect=fake_duration),
    ):
        duration = rn.synthesize_clip("A real sentence.", rn.VOICE_PRESETS["aria"], tmp_path / "clip.mp3")

    assert duration == 1.5
    assert synth.call_count == 2


def test_render_writes_manifest_cues_and_is_idempotent(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    durations = iter([1.2, 0.4, 0.8, 2.4, 2.4])

    def fake_synthesize(text, preset):
        return f"AUDIO:{text}".encode("utf-8")

    def fake_concat(parts, out_path):
        out_path.write_bytes(b"MP3")

    with (
        mock.patch.object(rn, "synthesize_text", side_effect=fake_synthesize) as synth,
        mock.patch.object(rn, "audio_duration_seconds", side_effect=lambda _p: next(durations)),
        mock.patch.object(rn, "concat_audio", side_effect=fake_concat),
        mock.patch.object(rn, "append_azure_speech_cost") as cost,
    ):
        result = rn.render_reader_narration(book)
        again = rn.render_reader_narration(book)

    assert result.outcome == "completed"
    assert result.rendered == ["opening"]
    assert again.rendered == []
    assert again.skipped == ["opening"]
    assert synth.call_count == 3
    cost.assert_called_once()

    manifest = json.loads((book / "book" / "narration" / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["chapters"]["opening"]
    assert entry["voice"] == "jenny"
    assert entry["audio_key"] == "sample-book/narration/opening.mp3"
    assert [cue["blockIndex"] for cue in entry["cues"]] == [0, 1, 2]
    assert (book / "book" / "narration" / "opening.mp3").read_bytes() == b"MP3"


def test_driver_records_phase_and_commits_only_when_audio_changed(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    _progress.write_state(book, _progress.initial_state("sample-book", "books"))
    summary = rn.RenderSummary(outcome="completed", rendered=["opening"], skipped=[], chars=10)

    with (
        mock.patch.object(reader_narration_driver, "render_reader_narration", return_value=summary),
        mock.patch.object(reader_narration_driver, "phase_git_commit") as commit,
    ):
        outcome, rc = reader_narration_driver.drive_reader_narration(book)

    state = _progress.read_state(book)
    assert (outcome, rc) == ("completed", 0)
    assert state["phases"]["reader-narration"]["status"] == "completed"
    assert state["phases"]["reader-narration"]["rendered"] == ["opening"]
    commit.assert_called_once()
