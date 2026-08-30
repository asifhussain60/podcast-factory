#!/usr/bin/env python3
"""Where a transcript comes from, and what it costs to get it.

Three routes reach the same file: one already on disk, one somebody handed us,
one bought from Azure. The tests that matter most here are the ones asserting
that money was NOT spent — a regression in the precedence order is invisible in
the output (the transcript is there either way) and shows up only on a bill.

So the fake transcriber counts its calls, and most tests assert that count.

No network, no Azure, no audio. `load_book` is replaced with a book built in a
tmp_path, the same way `test_listener_book.py` builds one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ensure_transcripts as et  # noqa: E402
from _listener_book import Book  # noqa: E402
from _listener_media import Asset, Episode  # noqa: E402
from _transcript import Cue, from_vtt, read_provenance, to_vtt, vtt_path  # noqa: E402

VTT = """WEBVTT

1
00:00:00.000 --> 00:00:05.000
Bismillah ar-Rahman ar-Rahim

2
00:00:05.000 --> 00:00:10.000
By the blessing of Allah

3
00:00:10.000 --> 00:00:15.000
we were able to go through this text

4
00:00:15.000 --> 00:00:20.000
and complete it.
"""

TURBOSCRIBE_TXT = "(0:01 - 10:51)\nBismillah ar-Rahman ar-Rahim By the blessing of Allah we were able"


class Phrase:
    def __init__(self, offset_ms: int, duration_ms: int, text: str, speaker=None) -> None:
        self.offset_ms, self.duration_ms, self.text, self.speaker = offset_ms, duration_ms, text, speaker


class Result:
    def __init__(self, phrases) -> None:
        self.phrases = phrases
        self.duration_ms = phrases[-1].offset_ms + phrases[-1].duration_ms if phrases else 0


class FakeAzure:
    """Counts what it was asked to do. `calls == 0` is the cost assertion."""

    def __init__(self, *, silent: bool = False) -> None:
        self.calls: list[Path] = []
        self.silent = silent

    def __call__(self, path: Path, locale: str):
        self.calls.append(path)
        if self.silent:
            return Result([])
        return Result([Phrase(i * 5000, 5000, f"azure heard line {i + 1}") for i in range(4)])


def make_book(tmp_path: Path, *, episodes: int = 2, duration_s: int | None = 20) -> Book:
    book = Book(
        slug="test-book",
        bucket="Islamic",
        directory=tmp_path,
        title="Test Book",
        title_arabic=None,
        title_language=None,
        study_track=None,
        blurb=None,
        edition_note=None,
    )
    for n in range(1, episodes + 1):
        audio = tmp_path / "m4a" / f"ep{n:02d}.m4a"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"fake-audio")
        book.episodes.append(
            Episode(
                number=n,
                title=f"Episode {n}",
                blurb=None,
                style=None,
                audio=Asset(
                    key=f"test-book/audio/ep{n:02d}",
                    slug="test-book",
                    kind="audio",
                    content_type="audio/mp4",
                    path=audio,
                ),
                duration_s=duration_s,
            )
        )
    return book


@pytest.fixture()
def book(tmp_path, monkeypatch):
    made = make_book(tmp_path)
    monkeypatch.setattr(et, "load_book", lambda slug: made)
    # Never let a real pronunciations library make the assertions depend on the
    # machine's knowledge-base checkout.
    monkeypatch.setattr(et, "load_pronunciations", lambda: [])
    return made


def drop(book: Book, name: str, text: str = VTT) -> Path:
    folder = et.inbox_path(book.directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def quiet():
    lines: list[str] = []
    return lines, lines.append


# ---------------------------------------------------------------------------
# Sunshine — a supplied transcript is used and nothing is spent
# ---------------------------------------------------------------------------


def test_a_supplied_transcript_is_adopted_and_azure_is_never_called(book) -> None:
    drop(book, "ep01.vtt")
    drop(book, "ep02.vtt")
    azure = FakeAzure()

    written = et.ensure("test-book", transcriber=azure, log=lambda *_: None)

    assert written == 2
    assert azure.calls == []
    assert vtt_path(book.directory, 1).is_file()
    assert len(from_vtt(vtt_path(book.directory, 1).read_text())) == 4


def test_an_adopted_transcript_is_written_in_our_own_canonical_format(book) -> None:
    """Whatever came in, what goes out is the file the reader and the read-along
    already know how to read."""
    drop(book, "ep01.srt", VTT.replace("WEBVTT\n\n", "").replace(".", ","))
    et.ensure("test-book", transcriber=FakeAzure(), log=lambda *_: None)

    text = vtt_path(book.directory, 1).read_text()
    assert text.startswith("WEBVTT")
    assert len(from_vtt(text)) == 4


def test_an_export_named_the_way_the_downloader_names_it_is_matched(book) -> None:
    drop(book, "Sheikh Hamza Yusuf Series [Part 1] Purification.vtt")
    azure = FakeAzure()
    et.ensure("test-book", transcriber=azure, log=lambda *_: None)
    assert vtt_path(book.directory, 1).is_file()
    assert len(azure.calls) == 1  # ep02 still had nothing


def test_a_transcript_already_on_disk_is_neither_re_adopted_nor_re_bought(book) -> None:
    for n in (1, 2):
        path = vtt_path(book.directory, n)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(VTT, encoding="utf-8")
    drop(book, "ep01.vtt")
    azure = FakeAzure()

    assert et.ensure("test-book", transcriber=azure, log=lambda *_: None) == 0
    assert azure.calls == []


def test_force_re_adopts_from_the_supplied_file_rather_than_buying(book) -> None:
    """`--force` means "do it again", not "pay for it"."""
    vtt_path(book.directory, 1).parent.mkdir(parents=True, exist_ok=True)
    vtt_path(book.directory, 1).write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nold\n", encoding="utf-8")
    drop(book, "ep01.vtt")
    azure = FakeAzure()

    et.ensure("test-book", force=True, transcriber=azure, log=lambda *_: None)

    assert azure.calls == [book.episodes[1].audio.path]  # only ep02
    assert len(from_vtt(vtt_path(book.directory, 1).read_text())) == 4


# ---------------------------------------------------------------------------
# Sunshine — Azure still works when nothing was supplied
# ---------------------------------------------------------------------------


def test_azure_is_used_when_nothing_was_supplied(book) -> None:
    azure = FakeAzure()
    assert et.ensure("test-book", transcriber=azure, log=lambda *_: None) == 2
    assert len(azure.calls) == 2


def test_a_mixed_batch_adopts_what_it_can_and_buys_the_rest(book) -> None:
    drop(book, "ep02.vtt")
    azure = FakeAzure()

    assert et.ensure("test-book", transcriber=azure, log=lambda *_: None) == 2
    assert azure.calls == [book.episodes[0].audio.path]
    assert "azure heard" in vtt_path(book.directory, 1).read_text()
    assert "Bismillah" in vtt_path(book.directory, 2).read_text()


def test_silent_audio_still_leaves_the_book_publishable(book) -> None:
    """Publishing must not stop because one recording failed to transcribe."""
    assert et.ensure("test-book", transcriber=FakeAzure(silent=True), log=lambda *_: None) == 0
    assert not vtt_path(book.directory, 1).exists()


# ---------------------------------------------------------------------------
# Rainy — a bad export is named, and never silently becomes a purchase
# ---------------------------------------------------------------------------


def test_a_plain_text_export_is_rejected_by_name_before_the_cost_line(book) -> None:
    """The bill must never be the first time anyone hears the export was bad."""
    drop(book, "ep01.vtt", TURBOSCRIBE_TXT)
    lines, log = quiet()

    et.ensure("test-book", transcriber=FakeAzure(), log=log)

    said = "\n".join(lines)
    assert "REJECTED" in said and "ep01.vtt" in said
    assert said.index("REJECTED") < said.index("audio-hours to transcribe")


def test_a_rejected_export_falls_through_to_azure_by_default(book) -> None:
    """This runs inside the deploy; a bad export must not be able to stop a
    finished book from publishing."""
    drop(book, "ep01.vtt", TURBOSCRIBE_TXT)
    azure = FakeAzure()

    et.ensure("test-book", transcriber=azure, log=lambda *_: None)

    assert len(azure.calls) == 2
    assert "azure heard" in vtt_path(book.directory, 1).read_text()


def test_a_transcript_for_the_wrong_recording_is_refused(book, tmp_path, monkeypatch) -> None:
    """The silent failure this whole feature is guarded against: a 20-second
    transcript against a 10-minute lecture."""
    long_book = make_book(tmp_path, episodes=1, duration_s=600)
    monkeypatch.setattr(et, "load_book", lambda slug: long_book)
    drop(long_book, "ep01.vtt")
    lines, log = quiet()

    et.ensure("test-book", transcriber=FakeAzure(), log=log)

    assert any("covers only" in line for line in lines)


def test_an_unnamed_export_is_complained_about_and_the_episode_is_bought(book) -> None:
    drop(book, "transcript.vtt")
    lines, log = quiet()
    azure = FakeAzure()

    et.ensure("test-book", transcriber=azure, log=log)

    assert any("no episode number" in line for line in lines)
    assert len(azure.calls) == 2


def test_two_exports_claiming_one_episode_are_both_refused(book) -> None:
    drop(book, "ep01.vtt")
    drop(book, "Part 1 rev2.vtt")
    lines, log = quiet()
    azure = FakeAzure()

    et.ensure("test-book", transcriber=azure, log=log)

    assert any("claimed by 2 files" in line for line in lines)
    assert len(azure.calls) == 2


def test_an_export_for_an_episode_this_book_does_not_have_is_reported(book) -> None:
    """Found by an end-to-end run on the real series: `[Part 41]` dropped into a
    two-episode book claimed episode 41, matched nothing, and said NOTHING. The
    operator's only evidence would have been a bill for the episode they thought
    they had just supplied."""
    drop(book, "Sheikh Hamza Yusuf Series [Part 41] Purification.vtt")
    lines, log = quiet()

    et.ensure("test-book", transcriber=FakeAzure(), log=log)

    said = "\n".join(lines)
    assert "claims episode 41" in said
    assert "nothing was done with it" in said


def test_an_export_for_an_episode_already_done_is_ignored_in_silence(book) -> None:
    """Re-dropping the whole folder after one new recording is the normal way to
    use this. Complaining about the twenty already-done files would bury the one
    line that matters."""
    path = vtt_path(book.directory, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(VTT, encoding="utf-8")
    drop(book, "ep01.vtt")
    drop(book, "ep02.vtt")
    lines, log = quiet()

    et.ensure("test-book", transcriber=FakeAzure(), log=log)

    assert not any("ep01" in line and "REJECT" in line for line in lines)


# ---------------------------------------------------------------------------
# --adopt-only — the run that must prove it spent nothing
# ---------------------------------------------------------------------------


def test_adopt_only_never_calls_azure(book) -> None:
    drop(book, "ep01.vtt")
    azure = FakeAzure()

    written = et.ensure("test-book", adopt_only=True, transcriber=azure, log=lambda *_: None)

    assert written == 1
    assert azure.calls == []
    assert not vtt_path(book.directory, 2).exists()


def test_adopt_only_says_which_episodes_it_left_untranscribed(book) -> None:
    drop(book, "ep01.vtt")
    lines, log = quiet()

    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=log)

    said = "\n".join(lines)
    assert "adopt-only" in said and "ep02" in said


def test_adopt_only_with_a_rejected_export_spends_nothing(book) -> None:
    drop(book, "ep01.vtt", TURBOSCRIBE_TXT)
    azure = FakeAzure()

    assert et.ensure("test-book", adopt_only=True, transcriber=azure, log=lambda *_: None) == 0
    assert azure.calls == []


# ---------------------------------------------------------------------------
# --adopt-from — an explicit folder
# ---------------------------------------------------------------------------


def test_an_explicit_folder_is_read_instead_of_the_inbox(book, tmp_path) -> None:
    elsewhere = tmp_path / "exports"
    elsewhere.mkdir()
    (elsewhere / "ep01.vtt").write_text(VTT, encoding="utf-8")
    drop(book, "ep02.vtt")  # in the inbox, must be IGNORED when --adopt-from is given
    azure = FakeAzure()

    et.ensure("test-book", adopt_from=elsewhere, transcriber=azure, log=lambda *_: None)

    assert azure.calls == [book.episodes[1].audio.path]


# ---------------------------------------------------------------------------
# Dry run — reports the decision, writes nothing, spends nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing_and_spends_nothing(book) -> None:
    drop(book, "ep01.vtt")
    azure = FakeAzure()

    assert et.ensure("test-book", dry_run=True, transcriber=azure, log=lambda *_: None) == 0
    assert azure.calls == []
    assert not vtt_path(book.directory, 1).exists()


def test_dry_run_separates_what_it_would_adopt_from_what_it_would_buy(book) -> None:
    drop(book, "ep01.vtt")
    lines, log = quiet()

    et.ensure("test-book", dry_run=True, transcriber=FakeAzure(), log=log)

    said = "\n".join(lines)
    assert "would adopt ep01" in said
    assert "would transcribe ep02" in said


def test_the_estimate_counts_only_what_will_actually_be_bought(book) -> None:
    drop(book, "ep01.vtt")
    lines, log = quiet()

    et.ensure("test-book", dry_run=True, transcriber=FakeAzure(), log=log)

    # One episode of the two, at 20s each.
    assert any(f"{20 / 3600:.2f} audio-hours" in line for line in lines)


# ---------------------------------------------------------------------------
# Provenance — the ledger cannot answer this, so something has to
# ---------------------------------------------------------------------------


def test_an_adopted_transcript_records_where_it_came_from(book) -> None:
    drop(book, "ep01.vtt")
    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    row = read_provenance(book.directory)["01"]
    assert row["source"] == "external"
    assert row["detail"] == "ep01.vtt"
    assert row["coverage"] == 1.0
    assert row["cues"] == 4
    assert "cost_usd" not in row


def test_a_bought_transcript_records_that_it_was_bought(book) -> None:
    et.ensure("test-book", transcriber=FakeAzure(), log=lambda *_: None)

    row = read_provenance(book.directory)["01"]
    assert row["source"] == "azure"
    assert "fast-transcription" in row["detail"]


def test_unverifiable_coverage_is_recorded_as_null_not_omitted(book, tmp_path, monkeypatch) -> None:
    """ "Not checked" has to be visibly different from "checked and fine"."""
    unknown = make_book(tmp_path, episodes=1, duration_s=None)
    monkeypatch.setattr(et, "load_book", lambda slug: unknown)
    drop(unknown, "ep01.vtt")

    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    row = read_provenance(unknown.directory)["01"]
    assert "coverage" in row and row["coverage"] is None


def test_provenance_survives_a_later_run_for_a_different_episode(book) -> None:
    drop(book, "ep01.vtt")
    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)
    drop(book, "ep02.vtt")
    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    assert sorted(read_provenance(book.directory)) == ["01", "02"]


def test_provenance_is_valid_json_with_a_schema(book) -> None:
    drop(book, "ep01.vtt")
    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    data = json.loads((book.directory / "transcripts" / "_provenance.json").read_text())
    assert data["schema"] == "podcast.transcript-provenance/v1"


def test_a_corrupt_provenance_file_does_not_stop_a_publish(book) -> None:
    """It is a record, not a gate."""
    folder = book.directory / "transcripts"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "_provenance.json").write_text("{not json", encoding="utf-8")
    drop(book, "ep01.vtt")

    assert et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None) == 1


# ---------------------------------------------------------------------------
# Parity — both routes get the same treatment
# ---------------------------------------------------------------------------


def test_an_adopted_transcript_gets_the_same_pronunciation_pass_as_a_bought_one(book, monkeypatch) -> None:
    """The only thing standing between a mangled religious term and the printed
    page. A second write path would eventually be added without it."""
    monkeypatch.setattr(
        et,
        "load_pronunciations",
        lambda: [{"term": "taqwa", "mangled_variants": ["takwa"], "source_books": ["test-book"]}],
    )
    drop(book, "ep01.vtt", VTT.replace("and complete it.", "and takwa is vast"))

    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    assert "taqwa is vast" in vtt_path(book.directory, 1).read_text()


def test_the_adopted_cues_keep_their_timings_exactly(book) -> None:
    """Corrections rewrite text. A timing that moved would slide the read-along
    highlight off the words it belongs to."""
    drop(book, "ep01.vtt")
    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    got = from_vtt(vtt_path(book.directory, 1).read_text())
    assert [(c.offset_ms, c.end_ms) for c in got] == [(0, 5000), (5000, 10000), (10000, 15000), (15000, 20000)]


def test_a_speaker_label_in_a_supplied_vtt_survives_adoption(book) -> None:
    drop(book, "ep01.vtt", to_vtt([Cue(i * 5000, 5000, f"line {i}", speaker=1 + i % 2) for i in range(4)]))
    et.ensure("test-book", adopt_only=True, transcriber=FakeAzure(), log=lambda *_: None)

    got = from_vtt(vtt_path(book.directory, 1).read_text())
    assert [c.speaker for c in got] == [1, 2, 1, 2]


# ---------------------------------------------------------------------------
# The book with no audio at all
# ---------------------------------------------------------------------------


def test_a_book_that_ships_no_audio_does_nothing(tmp_path, monkeypatch) -> None:
    empty = make_book(tmp_path, episodes=0)
    monkeypatch.setattr(et, "load_book", lambda slug: empty)
    azure = FakeAzure()

    assert et.ensure("test-book", transcriber=azure, log=lambda *_: None) == 0
    assert azure.calls == []
