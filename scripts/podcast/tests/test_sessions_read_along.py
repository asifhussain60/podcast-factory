#!/usr/bin/env python3
"""The read-along lane: what may change in a spoken chapter, and what may not.

A Sessions chapter taken off the tape is the one place in this repo where the
prose must NOT be improved — the reader highlights it paragraph by paragraph as
Asif's own recording plays, so a rewritten sentence silently breaks the pairing
while leaving a book that still reads well. Every case here pins a way that
could happen without anyone noticing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _transcript import Cue  # noqa: E402
from sessions.read_along import cue_map, retention  # noqa: E402
from sessions.series import SERIES  # noqa: E402
from sessions.spoken import _carry_images, spoken_chapters, write_spoken_chapters  # noqa: E402

# ---------------------------------------------------------------------------
# The retention gate
# ---------------------------------------------------------------------------

SPOKEN = "so the prophet naturally is filled with all those human emotions fear shock horror"


def test_proofreading_passes_the_gate() -> None:
    """Punctuation, capitalisation and paragraphing are exactly what the pass is
    for, and none of them touch the words."""
    corrected = "So the Prophet, naturally, is filled with all those human emotions: fear, shock, horror."

    assert retention(SPOKEN, corrected) >= 0.9


def test_a_rewrite_fails_the_gate() -> None:
    """The failure mode this lane exists to prevent, in its mildest form: prose
    that is better English and no longer the sentence on the recording."""
    rewritten = "The Prophet experienced the full range of human feeling in that moment."

    assert retention(SPOKEN, rewritten) < 0.9


def test_a_summary_fails_the_gate_even_though_every_word_it_kept_is_real() -> None:
    """A shortened window keeps only true words, so a gate that asked 'is this
    text drawn from the source' would pass it. The question is how much of the
    source SURVIVED, which is why the ratio is over the base, not the candidate.
    """
    assert retention(SPOKEN, "fear shock horror") < 0.5


def test_the_gate_ignores_word_order() -> None:
    """A corrector is allowed to move a word across a paragraph break it inserts.
    Order is not evidence of rewriting; vocabulary is."""
    shuffled = " ".join(reversed(SPOKEN.split()))

    assert retention(SPOKEN, shuffled) == 1.0


# ---------------------------------------------------------------------------
# Arabic: scripture comes from the mushaf, never from a rendering
# ---------------------------------------------------------------------------


def test_a_verse_is_taken_from_the_mushaf_not_from_the_reconstruction() -> None:
    """The defect this exists for, in the text that produced it. Rung 3 of the
    romanization ladder renders what the transliteration spells, which for
    Fussilat 53 gave `آيَاتِنَا ... فِي الْآفَاقِ` — close enough to look right and
    not the verse. The ladder's own library rung searches by skeleton overlap and
    missed it, along with 80 of 83 runs in one chapter.
    """
    from sessions.read_along import _mushaf_wording

    reconstructed = "سَنُرِيهِمْ آيَاتِنَا فِي الْآفَاقِ وَفِي أَنْفُسِهِمْ حَتَّى يَتَبَيَّنَ لَهُمْ أَنَّهُ الْحَقُّ"

    canonical = _mushaf_wording(reconstructed)

    assert canonical is not None
    assert canonical != reconstructed
    assert "ٱلْءَافَاقِ" in canonical or "ٱلأٓفَاقِ" in canonical


def test_a_saying_that_is_not_scripture_is_left_to_the_ladder() -> None:
    """The mushaf rule may only claim Qur'an. A hadith or a line of poetry that
    it answered would be published as scripture, which is a worse error than the
    one it fixes."""
    from sessions.read_along import _mushaf_wording

    assert _mushaf_wording("أَمُرُّ عَلَى الدِّيَارِ دِيَارِ لَيْلَى") is None


# ---------------------------------------------------------------------------
# Timing the paragraphs
# ---------------------------------------------------------------------------


def _cues(*pairs: tuple[int, str]) -> list[Cue]:
    return [Cue(offset_ms=at, duration_ms=4000, text=text) for at, text in pairs]


def test_each_paragraph_takes_the_span_of_every_cue_that_landed_on_it() -> None:
    """One paragraph is many cues long, so its span runs from the first of them
    to the last. Getting this backwards — one cue per paragraph — would end every
    highlight four seconds after it began."""
    markdown = (
        "The angel appeared to him and he turned his face away in fear.\n\n"
        "Then Jibreel wrapped his wings around him and squeezed him three times."
    )
    cues = _cues(
        (0, "The angel appeared to him"),
        (4000, "and he turned his face away in fear"),
        (8000, "Then Jibreel wrapped his wings around him"),
        (12000, "and squeezed him three times"),
    )

    mapped, confidence = cue_map(markdown, cues)

    assert [c["startS"] for c in mapped] == [0.0, 8.0]
    assert [c["endS"] for c in mapped] == [8.0, 16.0]
    assert confidence > 0


def test_timings_never_run_backwards() -> None:
    markdown = "First he spoke of mercy.\n\nThen he spoke of judgment.\n\nFinally he spoke of guidance."
    cues = _cues(
        (0, "First he spoke of mercy"),
        (5000, "Then he spoke of judgment"),
        (9000, "Finally he spoke of guidance"),
    )

    mapped, _ = cue_map(markdown, cues)

    assert all(mapped[i]["endS"] <= mapped[i + 1]["endS"] for i in range(len(mapped) - 1))
    assert all(mapped[i]["startS"] <= mapped[i + 1]["startS"] for i in range(len(mapped) - 1))


def test_a_chapter_with_no_transcript_is_reported_unconfident_rather_than_timed() -> None:
    """No cues is not zero-length cues. The caller publishes the recording with
    no highlighting on this signal; a silent empty list would look identical to
    a chapter that legitimately timed to nothing."""
    mapped, confidence = cue_map("A paragraph nobody recorded.", [])

    assert mapped == []
    assert confidence == 0.0


def test_the_block_index_is_the_rendered_block_not_the_paragraph_count() -> None:
    """The reader highlights by position in the RENDERED chapter, and an image is
    a block there while carrying nothing to say. Counting only speakable
    paragraphs would light up the wrong element in every chapter with a figure.
    """
    markdown = "He began with the opening prayer.\n\n![](images/213/plate.jpg)\n\nThen he turned to the verse itself."
    cues = _cues((0, "He began with the opening prayer"), (6000, "Then he turned to the verse itself"))

    mapped, _ = cue_map(markdown, cues)

    assert [c["blockIndex"] for c in mapped] == [0, 2]


# ---------------------------------------------------------------------------
# The illustrations survive the switch to the tape
# ---------------------------------------------------------------------------


def test_an_illustration_follows_the_passage_it_illustrated_in_the_notes() -> None:
    """A transcription has no pictures in it. The notes' own ordering is the only
    evidence of where a figure belongs, and it is carried across rather than
    dropped or piled at the end."""
    notes = (
        "The first point concerns the covenant and its witnesses.\n\n"
        "![](images/213/plate.jpg)\n\n"
        "The second point concerns the seal of the prophets."
    )
    heard = (
        "So the first point I want to make concerns the covenant and its witnesses.\n\n"
        "And the second point concerns the seal of the prophets."
    )

    out = _carry_images(heard, notes)

    blocks = out.split("\n\n")
    assert blocks[1] == "![](images/213/plate.jpg)"
    assert len(blocks) == 3


def test_a_chapter_with_no_illustrations_is_returned_untouched() -> None:
    heard = "One paragraph.\n\nAnother paragraph."

    assert _carry_images(heard, "Some notes with no pictures at all.") == heard


# ---------------------------------------------------------------------------
# Which chapters this applies to
# ---------------------------------------------------------------------------


def test_every_recorded_love_of_the_prophet_session_takes_its_text_from_the_tape() -> None:
    """The measurement behind the decision: the stored notes hold 31-43% of the
    spoken vocabulary of this series, so a chapter built from them cannot be
    mapped to the recording however the mapping is attempted."""
    series = SERIES["love-of-the-prophet"]

    assert set(series.audio_map.values()) == series.transcript_from_audio


def test_a_session_with_no_recording_is_not_claimed_as_spoken() -> None:
    """Surah Al-Fateha has twelve recordings against twenty-three sessions.
    Listing a session with no tape would have the ingest fall back to the notes
    while every later step believed it had a transcription to time against."""
    series = SERIES["surah-al-fateha"]

    assert series.transcript_from_audio <= set(series.audio_map.values())


def test_a_book_that_was_never_a_lecture_series_reports_no_spoken_chapters(tmp_path: Path) -> None:
    (tmp_path / "_system").mkdir(parents=True)

    assert spoken_chapters(tmp_path) == {}


def test_the_spoken_record_round_trips(tmp_path: Path) -> None:
    (tmp_path / "_system").mkdir(parents=True)
    entry = {"title": "Love Based Religion", "sequence": 2, "episode": 1, "base": "what he said"}

    write_spoken_chapters(tmp_path, {"love based religion": entry})

    assert spoken_chapters(tmp_path)["love based religion"] == entry


def test_an_unreadable_record_reads_as_empty_rather_than_raising(tmp_path: Path) -> None:
    """The file is derived and regenerable. A corrupt one must not take down the
    articulation pass, which asks this question only to decide what to skip."""
    (tmp_path / "_system").mkdir(parents=True)
    (tmp_path / "_system" / "sessions-spoken-chapters.json").write_text("{ truncated", encoding="utf-8")

    assert spoken_chapters(tmp_path) == {}


def test_the_manifest_a_spoken_chapter_writes_points_at_the_episode_recording(tmp_path: Path) -> None:
    """Not at a second copy under a narration key. The recording is already in
    the bucket serving the episode player, and two objects for one lecture can
    disagree."""
    from sessions.read_along import read_manifest, write_manifest

    (tmp_path / "book").mkdir(parents=True)
    write_manifest(
        tmp_path,
        {
            "schema": 1,
            "engine": "author-recording",
            "chapters": {"love based religion": {"audio_key": "love-of-the-prophet/audio/ep01.mp3"}},
        },
    )

    manifest = read_manifest(tmp_path)
    key = manifest["chapters"]["love based religion"]["audio_key"]
    assert key == "love-of-the-prophet/audio/ep01.mp3"
    assert "/narration/" not in key
    assert json.loads((tmp_path / "book" / "narration" / "manifest.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The state write that is supposed to mark this step done
# ---------------------------------------------------------------------------


def test_finishing_read_along_actually_records_it_as_completed(tmp_path: Path) -> None:
    """The bug this pins: `_write_state`'s carry-over logic reads the PRIOR
    file's `sessions-read-along` status and writes that back verbatim — so a
    call made to report read-along AS the step that just finished
    (`done_through=READ_ALONG_STEP`, exactly what `read_along.py main()` does)
    could never actually leave `completed` behind, because the "prior" value
    it carries forward is always the pre-completion one. Found 2026-08-15: the
    CLI printed success on every run and the state file never once agreed."""
    from sessions.ingest import READ_ALONG_STEP, _write_state

    (tmp_path / "_system").mkdir()
    series = SERIES["love-of-the-prophet"]

    _write_state(tmp_path, series, done_through="sessions-articulate")
    _write_state(tmp_path, series, done_through=READ_ALONG_STEP)

    state = json.loads((tmp_path / "_system" / "orchestrator-state.json").read_text(encoding="utf-8"))
    assert state["phases"][READ_ALONG_STEP]["status"] == "completed"


def test_a_later_step_finishing_still_carries_read_along_forward(tmp_path: Path) -> None:
    """The other half of the same fix: once read-along genuinely is done, a
    LATER call that does not mention it by name (apparatus finishing, or a
    re-ingest) must not derive its status from position alone — `_write_state`
    still has to remember what read-along itself last reported."""
    from sessions.ingest import LANE_STEPS, READ_ALONG_STEP, _write_state

    (tmp_path / "_system").mkdir()
    series = SERIES["love-of-the-prophet"]

    _write_state(tmp_path, series, done_through="sessions-articulate")
    _write_state(tmp_path, series, done_through=READ_ALONG_STEP)
    _write_state(tmp_path, series, done_through=LANE_STEPS[-1])

    state = json.loads((tmp_path / "_system" / "orchestrator-state.json").read_text(encoding="utf-8"))
    assert state["phases"][READ_ALONG_STEP]["status"] == "completed"
