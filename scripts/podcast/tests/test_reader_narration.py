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


def test_speech_text_drops_scripture_citations() -> None:
    text = rn.speech_text(
        'God Almighty said: "Indeed, Allah loves those who constantly repent and loves '
        'those who purify themselves" [Surah al-Baqarah: 222]. He also said: "Within it '
        'are men who love to purify themselves, and God loves those who purify themselves" '
        "[Surah al-Tawbah: 108]."
    )
    assert "[Surah" not in text
    assert (
        text == 'God Almighty said: "Indeed, Allah loves those who constantly repent and loves '
        'those who purify themselves". He also said: "Within it are men who love to purify '
        'themselves, and God loves those who purify themselves".'
    )


def test_speech_text_drops_citation_without_surah_prefix_and_verse_ranges() -> None:
    assert "[" not in rn.speech_text('"Establish prayer." [Al Imran: 1]')
    assert "[" not in rn.speech_text('"Be just." [al-Hujurat: 11-12]')


def test_speech_text_drops_citations_in_parentheses() -> None:
    # The library is not consistent about brackets vs parens for the same
    # kind of reference — both must be dropped.
    assert "(" not in rn.speech_text('"Do not devour riba." (Al Imran 130)')
    assert "(" not in rn.speech_text('"Sustenance is His." (Quran, Chapter 11, Verse 6)')
    assert "(" not in rn.speech_text('"Exalt Allah." (25: 43; almost identical at 45: 23)')


def test_speech_text_drops_arabic_script_citations_cleanly() -> None:
    """A citation still in Arabic script with Arabic-Indic digits must be
    removed WHOLE, not left as an empty `[: ]` shell.

    Regression: `_ARABIC` alone strips the name and digits inside the
    bracket but not the bracket punctuation, so already-rendered narration
    for mukhtasar-ul-asar-1 spoke a stray "bracket colon bracket" where the
    citation used to be (2026-08-17).
    """
    text = rn.speech_text('Allah Almighty said: "wash your faces" [البقرة: ١٤٤].')
    assert "[" not in text
    assert "]" not in text
    assert text == 'Allah Almighty said: "wash your faces".'


def test_speech_text_keeps_an_ordinary_bracket_that_is_not_a_citation() -> None:
    # Not immediately after a closing quote — must not be swallowed.
    text = rn.speech_text("He gave the ruling [emphasis in the original].")
    assert "[emphasis in the original]" in text


def test_speech_text_keeps_a_date_in_ordinary_prose() -> None:
    # Has a digit but sits mid-sentence, not right after a quotation — a
    # citation-shaped regex keyed on digits alone would wrongly eat this.
    text = rn.speech_text("Ali migrated from Mecca to Medina (622 CE), the start of the calendar.")
    assert "(622 CE)" in text


def test_speech_text_keeps_a_term_gloss_right_after_a_quotation() -> None:
    # Same position as a citation, but no digit — a real editorial aside
    # naming a term, not a reference, and must survive.
    text = rn.speech_text('He sought only "the face of God" (wajh Allah).')
    assert "(wajh Allah)" in text


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


def test_reader_narration_object_keys_are_url_safe() -> None:
    assert (
        rn.narration_object_name("The Persian Who Was Dead and Revived") == "the-persian-who-was-dead-and-revived.mp3"
    )
    assert (
        rn.narration_object_name("The Boy at the Door — Limits and Conditions")
        == "the-boy-at-the-door-limits-and-conditions.mp3"
    )


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


def _with_enabled(book: Path, value: str) -> Path:
    """Rewrite the book's config with an explicit reader_narration.enabled."""
    cfg = book / "_system" / "series-config.yaml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace("reader_narration:\n", f"reader_narration:\n  enabled: {value}\n"),
        encoding="utf-8",
    )
    return book


def test_an_explicit_yes_overrides_the_profile_default(tmp_path: Path) -> None:
    """A lecture-session book is refused by default, but the default is a guess
    about the KIND of book — a person saying yes about THIS book outranks it."""
    book = _with_enabled(make_book(tmp_path, profile="islamic_session"), "true")

    enabled, reason = rn.narration_enabled(book)

    assert enabled
    assert reason is None


def test_an_explicit_yes_also_overrides_the_sessions_lane(tmp_path: Path) -> None:
    book = _with_enabled(make_book(tmp_path, bucket="Sessions", profile="islamic_session"), "true")

    assert rn.narration_enabled(book)[0]


def test_an_explicit_no_still_wins_over_an_eligible_profile(tmp_path: Path) -> None:
    """The refusing half must keep outranking the enabling half — otherwise a
    book turned off on purpose could be turned back on by its profile."""
    book = _with_enabled(make_book(tmp_path, profile="islamic_scholarly"), "false")

    enabled, reason = rn.narration_enabled(book)

    assert not enabled
    assert "disabled" in reason
