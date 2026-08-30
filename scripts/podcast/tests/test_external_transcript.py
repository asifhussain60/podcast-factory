#!/usr/bin/env python3
"""Reading a timed transcript somebody else produced, and refusing a bad one.

The failure this whole module exists to prevent is SILENT: a transcript that
belongs to a different recording reads perfectly well and is wrong. So most of
what follows is rainy-path — a check that cannot fail is not a check, and every
rule in `problems()` has a test here that fails without it.

No network, no Azure, no audio. Everything is text in a tmp_path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _external_transcript import (  # noqa: E402
    COVERAGE_CEILING,
    COVERAGE_FLOOR,
    MIN_CUES,
    UnreadableTranscript,
    coverage,
    discover,
    episode_number_from,
    from_srt,
    parse_timed,
    problems,
    read_candidate,
)
from _transcript import Cue, from_vtt  # noqa: E402

VTT = """WEBVTT

1
00:00:00.000 --> 00:00:05.000
Bismillah ar-Rahman ar-Rahim

2
00:00:05.000 --> 00:00:10.000
By the blessing of Allah subhanahu wa ta'ala

3
00:00:10.000 --> 00:00:15.000
we were able to go through this text

4
00:00:15.000 --> 00:00:20.000
and complete it.
"""

SRT = """1
00:00:00,000 --> 00:00:05,000
Bismillah ar-Rahman ar-Rahim

2
00:00:05,000 --> 00:00:10,000
By the blessing of Allah subhanahu wa ta'ala

3
00:00:10,000 --> 00:00:15,000
we were able to go through this text

4
00:00:15,000 --> 00:00:20,000
and complete it.
"""

#: What TurboScribe's plain-text export actually looks like: 1,906 words under a
#: single marker, no line breaks, no sentence punctuation. Abbreviated here.
TURBOSCRIBE_TXT = (
    "(0:01 - 10:51)\nBismillah ar-Rahman ar-Rahim By the blessing of Allah subhanahu "
    "wa ta'ala we were able to go through this text to complete it and we ask Allah"
)


def cues_at(*spans: tuple[int, int]) -> list[Cue]:
    return [Cue(offset_ms=a, duration_ms=b - a, text=f"cue {i}") for i, (a, b) in enumerate(spans, 1)]


# ---------------------------------------------------------------------------
# Formats — sunshine
# ---------------------------------------------------------------------------


def test_webvtt_is_read() -> None:
    cues = parse_timed(VTT, name="ep01.vtt")
    assert len(cues) == 4
    assert cues[0].offset_ms == 0
    assert cues[0].duration_ms == 5000
    assert cues[1].text == "By the blessing of Allah subhanahu wa ta'ala"


def test_subrip_is_read() -> None:
    """SubRip differs from WebVTT by one character — a comma for the decimal
    point — which is exactly why it used to slip past unrecognised."""
    cues = parse_timed(SRT, name="ep01.srt")
    assert len(cues) == 4
    assert cues[0].offset_ms == 0
    assert cues[3].end_ms == 20_000


def test_the_two_formats_produce_identical_cues() -> None:
    assert [(c.offset_ms, c.duration_ms, c.text) for c in parse_timed(VTT)] == [
        (c.offset_ms, c.duration_ms, c.text) for c in parse_timed(SRT)
    ]


def test_a_vtt_header_over_subrip_stamps_is_still_read() -> None:
    """Exporters really do write this. Reading by CONTENT rather than by the file
    extension is what makes it work: the WebVTT reader finds no cues it
    recognises, and the SubRip reader is tried next."""
    assert len(parse_timed("WEBVTT\n\n" + SRT, name="odd.vtt")) == 4


def test_subrip_does_not_invent_a_speaker() -> None:
    """SubRip has no voice span, and the conventions people use instead are
    ambiguous with ordinary dialogue punctuation. A wrong speaker is a claim
    about who said something."""
    assert all(c.speaker is None for c in from_srt(SRT))


# ---------------------------------------------------------------------------
# Formats — rainy
# ---------------------------------------------------------------------------


def test_a_plain_text_export_is_refused_by_name() -> None:
    """The export Asif first sent: one timestamp for a whole 10-minute lecture.
    Adopting it would publish a read-along that highlights everything at once."""
    with pytest.raises(UnreadableTranscript) as exc:
        parse_timed(TURBOSCRIBE_TXT, name="Part 41.txt")
    assert "Part 41.txt" in str(exc.value)
    assert "not a timed transcript" in str(exc.value)


def test_an_empty_file_is_refused_rather_than_read_as_zero_cues() -> None:
    with pytest.raises(UnreadableTranscript):
        parse_timed("", name="empty.vtt")


def test_subrip_used_to_parse_as_nothing_and_now_raises() -> None:
    """The regression guard for the actual defect.

    `from_vtt` returns `[]` for SubRip — it parses our own output and is only as
    tolerant as it needs to be. Downstream, `sessions/spoken.py` turns "no cues"
    into "", so dropping an `.srt` produced an EMPTY CHAPTER and nothing said
    why. `from_vtt` is deliberately left alone; `parse_timed` is what refuses.
    """
    assert from_vtt(SRT) == []
    assert len(parse_timed(SRT)) == 4


def test_prose_with_a_stray_colon_is_not_mistaken_for_a_transcript() -> None:
    with pytest.raises(UnreadableTranscript):
        parse_timed("Chapter 3: the heart\n\nHe said 12:30 was the hour.", name="notes.txt")


# ---------------------------------------------------------------------------
# Trust — a clean transcript passes
# ---------------------------------------------------------------------------


def test_a_good_transcript_has_no_problems() -> None:
    assert problems(parse_timed(VTT), audio_duration_s=20.0) == []


def test_trailing_silence_is_tolerated() -> None:
    """A recording can end with silence, applause, or an unmiked question.
    Refusing a good transcript costs a paid re-run."""
    assert problems(parse_timed(VTT), audio_duration_s=22.0) == []


# ---------------------------------------------------------------------------
# Trust — every check fails when it should
# ---------------------------------------------------------------------------


def test_a_truncated_transcript_is_refused() -> None:
    """The load-bearing check. A 20-second transcript against a 10-minute
    recording is a truncated export or the wrong file."""
    found = problems(parse_timed(VTT), audio_duration_s=600.0)
    assert found and "covers only" in found[0]


def test_a_transcript_longer_than_its_recording_is_refused() -> None:
    """The wrong-file case seen from the other side: an overrun cannot be
    trailing silence."""
    found = problems(parse_timed(VTT), audio_duration_s=5.0)
    assert found and "describes a longer recording" in found[0]


def test_the_coverage_floor_and_ceiling_are_the_boundary() -> None:
    # Four cues, because fewer is its own failure — see MIN_CUES.
    cues = cues_at((0, 25_000), (25_000, 50_000), (50_000, 75_000), (75_000, 100_000))
    assert problems(cues, audio_duration_s=100.0 / COVERAGE_FLOOR * 0.99) == []
    assert problems(cues, audio_duration_s=100.0 / COVERAGE_FLOOR * 1.02) != []
    assert problems(cues, audio_duration_s=100.0 / COVERAGE_CEILING * 1.01) == []
    assert problems(cues, audio_duration_s=100.0 / COVERAGE_CEILING * 0.98) != []


def test_a_wall_of_text_with_one_cue_is_refused() -> None:
    found = problems(cues_at((0, 600_000)), audio_duration_s=600.0)
    assert found and f"at least {MIN_CUES}" in found[0]


def test_cues_that_go_backwards_are_refused() -> None:
    """Two files concatenated, or overlapping speaker tracks. Either way the
    paragraph-to-audio alignment downstream would be nonsense."""
    cues = cues_at((0, 5_000), (5_000, 10_000), (2_000, 7_000), (10_000, 15_000))
    found = problems(cues, audio_duration_s=15.0)
    assert any("start before the cue before them" in f for f in found)


def test_a_cue_that_ends_before_it_starts_is_refused() -> None:
    cues = [Cue(offset_ms=0, duration_ms=-500, text="x")] + cues_at((1, 5_000), (5_000, 9_000), (9_000, 15_000))
    found = problems(cues, audio_duration_s=15.0)
    assert any("end before they start" in f for f in found)


def test_a_transcript_of_only_empty_cues_is_refused() -> None:
    cues = [Cue(offset_ms=i * 1000, duration_ms=1000, text="   ") for i in range(6)]
    assert any("empty of text" in f for f in problems(cues, audio_duration_s=6.0))


def test_every_problem_is_reported_not_only_the_first() -> None:
    """One run should diagnose a bad batch, not one re-run per defect."""
    cues = [Cue(offset_ms=0, duration_ms=1000, text="")]
    assert len(problems(cues, audio_duration_s=600.0)) >= 3


# ---------------------------------------------------------------------------
# Trust — degrading honestly when the recording's length is unknown
# ---------------------------------------------------------------------------


def test_an_unknown_recording_length_skips_coverage_rather_than_failing() -> None:
    """A machine without ffprobe must still be able to adopt."""
    assert problems(parse_timed(VTT), audio_duration_s=None) == []
    assert problems(parse_timed(VTT), audio_duration_s=0) == []


def test_unverifiable_coverage_reads_as_none_not_as_a_number() -> None:
    """ "Not checked" has to be visibly different from "checked and fine"."""
    assert coverage(parse_timed(VTT), None) is None
    assert coverage(parse_timed(VTT), 20.0) == 1.0


# ---------------------------------------------------------------------------
# Which episode is this?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("ep01.vtt", 1),
        ("ep 7.srt", 7),
        ("episode-12.vtt", 12),
        ("Sheikh Hamza Yusuf Series [Part 41] Purification.vtt", 41),
        ("Part 3 - The Heart.srt", 3),
        ("Session 2 — Spiritual Symbols.vtt", 2),
        ("03 - Opening.vtt", 3),
        ("EP09_final.vtt", 9),
    ],
)
def test_an_episode_number_is_read_from_the_filename(name, expected) -> None:
    assert episode_number_from(name) == expected


@pytest.mark.parametrize("name", ["transcript.vtt", "final draft.srt", "purification-of-the-heart.vtt", "ep0.vtt"])
def test_a_filename_claiming_no_episode_returns_none(name) -> None:
    """None is a real answer. Inferring a number from position in a directory
    listing would silently reorder a series the first time an export was
    missing."""
    assert episode_number_from(name) is None


def test_our_own_convention_wins_over_a_number_in_the_title() -> None:
    assert episode_number_from("ep05 - Part 41 of the series.vtt") == 5


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_a_folder_of_exports_maps_onto_episode_numbers(tmp_path) -> None:
    for name in ("ep01.vtt", "ep02.srt", "[Part 3] lecture.vtt"):
        (tmp_path / name).write_text(VTT, encoding="utf-8")
    found = discover(tmp_path)
    assert sorted(found.by_episode) == [1, 2, 3]
    assert found.complaints == []


def test_a_missing_folder_is_empty_rather_than_an_error(tmp_path) -> None:
    found = discover(tmp_path / "nope")
    assert found.by_episode == {} and found.complaints == []


def test_files_that_are_not_transcripts_are_ignored_in_silence(tmp_path) -> None:
    """A `.DS_Store` is not a failed transcript."""
    (tmp_path / ".DS_Store").write_bytes(b"\x00")
    (tmp_path / "notes.md").write_text("hello", encoding="utf-8")
    (tmp_path / "ep01.vtt").write_text(VTT, encoding="utf-8")
    found = discover(tmp_path)
    assert list(found.by_episode) == [1]
    assert found.complaints == []


def test_an_unnamed_export_is_complained_about_not_guessed(tmp_path) -> None:
    (tmp_path / "transcript.vtt").write_text(VTT, encoding="utf-8")
    found = discover(tmp_path)
    assert found.by_episode == {}
    assert len(found.complaints) == 1
    assert "no episode number" in found.complaints[0]


def test_two_files_claiming_one_episode_disqualify_both(tmp_path) -> None:
    """A coin-flip here publishes the wrong lecture under the right title."""
    (tmp_path / "ep03.vtt").write_text(VTT, encoding="utf-8")
    (tmp_path / "Part 3 rev2.srt").write_text(SRT, encoding="utf-8")
    found = discover(tmp_path)
    assert found.by_episode == {}
    assert any("claimed by 2 files" in c for c in found.complaints)


def test_a_collision_does_not_take_the_healthy_files_with_it(tmp_path) -> None:
    (tmp_path / "ep03.vtt").write_text(VTT, encoding="utf-8")
    (tmp_path / "Part 3 rev2.srt").write_text(SRT, encoding="utf-8")
    (tmp_path / "ep04.vtt").write_text(VTT, encoding="utf-8")
    assert list(discover(tmp_path).by_episode) == [4]


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


def test_a_good_candidate_is_adoptable(tmp_path) -> None:
    path = tmp_path / "ep01.vtt"
    path.write_text(VTT, encoding="utf-8")
    candidate = read_candidate(1, path, audio_duration_s=20.0)
    assert candidate.adoptable
    assert candidate.coverage == 1.0
    assert len(candidate.cues) == 4


def test_a_bad_candidate_carries_its_reason_rather_than_raising(tmp_path) -> None:
    """One bad export must not abort a batch of forty-one."""
    path = tmp_path / "ep01.txt.vtt"
    path.write_text(TURBOSCRIBE_TXT, encoding="utf-8")
    candidate = read_candidate(1, path, audio_duration_s=652.0)
    assert not candidate.adoptable
    assert candidate.cues == []
    assert candidate.problems


def test_an_undecodable_file_is_a_reason_not_a_crash(tmp_path) -> None:
    path = tmp_path / "ep01.vtt"
    path.write_bytes(b"\xff\xfe\x00\x01\x02")
    candidate = read_candidate(1, path, audio_duration_s=20.0)
    assert not candidate.adoptable and candidate.problems
