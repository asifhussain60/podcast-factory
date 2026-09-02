"""The audio profile is applied automatically and deletes the only other copy.

That combination is why these exist. `normalise` runs inside `publish_to_listener`
on every book it publishes, and it removes the masters — so a mistake here is not
a file that ships at the wrong bitrate, it is audio that no longer exists at any
other bitrate. Each test below pins one thing that must stay true for that to be
safe.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from downsize_audio import (  # noqa: E402
    ABSOLUTE_FLOOR_KBPS,
    DEFAULT_FLOOR_KBPS,
    KEEP_BELOW_KBPS,
    MIN_SIZE_BYTES,
    master_dirs,
    normalise,
    plan_for,
    prune_masters,
    shippable_audio,
)

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def tone(path: Path, *, seconds: int = 3, kbps: int, channels: int = 2, rate: int = 44100) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-ac",
            str(channels),
            "-ar",
            str(rate),
            "-c:a",
            "aac",
            "-b:a",
            f"{kbps}k",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def book(tmp_path: Path) -> Path:
    (tmp_path / "m4a" / "Episodes").mkdir(parents=True)
    return tmp_path


# ── what the profile does and does not touch ────────────────────────────────


def test_masters_are_not_shippable(book: Path) -> None:
    """`Audio/` never appears in the set that gets re-encoded or uploaded."""
    ship = book / "m4a" / "Episodes" / "ep01.m4a"
    ship.write_bytes(b"x" * 10)
    master = book / "m4a" / "Episodes" / "Audio" / "ep01.m4a"
    master.parent.mkdir()
    master.write_bytes(b"x" * 10)
    assert shippable_audio(book) == [ship]


def test_master_dirs_finds_both_layouts(book: Path) -> None:
    """A flat book keeps masters at `m4a/Audio/`, a grouped one a level deeper.

    Looking in only one place is how a flat book silently keeps a gigabyte.
    """
    flat = book / "m4a" / "Audio"
    grouped = book / "m4a" / "Episodes" / "Audio"
    flat.mkdir(parents=True)
    grouped.mkdir(parents=True)
    assert set(master_dirs(book)) == {flat, grouped}


def test_prune_never_reaches_source(book: Path) -> None:
    """`source/` is the provenance record and is not under `m4a/`."""
    keep = book / "_system" / "source" / "Audio" / "raw.m4a"
    keep.parent.mkdir(parents=True)
    keep.write_bytes(b"x" * 100)
    prune_masters(book, apply=True, log=lambda _m: None)
    assert keep.exists()


def test_prune_reports_without_deleting_when_not_applying(book: Path) -> None:
    master = book / "m4a" / "Episodes" / "Audio" / "ep01.m4a"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"x" * 2048)
    files, freed = prune_masters(book, apply=False, log=lambda _m: None)
    assert (files, freed) == (1, 2048)
    assert master.exists(), "a dry run must not delete"


# ── the planner's exclusions ────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_already_efficient_files_are_left_alone(book: Path) -> None:
    """A file at or below 64 kbps keeps its generation, whatever the floor says."""
    tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=60, kbps=KEEP_BELOW_KBPS - 16, channels=1)
    planned, skipped = plan_for(book, DEFAULT_FLOOR_KBPS * 1000, log=lambda _m: None)
    assert planned == []
    assert skipped == 1


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_tiny_files_are_left_alone(book: Path) -> None:
    """The credits clip at the head of every audiobook is not worth a generation."""
    small = tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=3, kbps=192)
    assert small.stat().st_size < MIN_SIZE_BYTES
    planned, skipped = plan_for(book, DEFAULT_FLOOR_KBPS * 1000, log=lambda _m: None)
    assert planned == []
    assert skipped == 1


# ── the safety ordering ─────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_masters_are_kept_when_a_file_did_not_reach_the_profile(book: Path, monkeypatch) -> None:
    """A failed encode means the master is the only copy of the better audio.

    Deleting it because the sweep reached that line would throw away the one
    thing a retry could use.
    """
    tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=120, kbps=192)
    master = book / "m4a" / "Episodes" / "Audio" / "ep01.m4a"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"x" * 4096)

    import downsize_audio

    monkeypatch.setattr(downsize_audio, "reencode", lambda *_a, **_k: (False, "ffmpeg failed"))
    report = normalise(book, apply=True, log=lambda _m: None)

    assert report["encoded"] == 0
    assert report["masters"] == 0
    assert master.exists(), "a book that did not reach the profile keeps its masters"


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_a_clean_run_leaves_exactly_one_copy(book: Path) -> None:
    """The whole point: one file per recording, at the profile, masters gone."""
    ship = tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=120, kbps=192)
    before = ship.stat().st_size
    master = book / "m4a" / "Episodes" / "Audio" / "ep01.m4a"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"x" * 4096)

    report = normalise(book, apply=True, log=lambda _m: None)

    assert report["encoded"] == 1
    assert report["masters"] == 1
    assert not master.parent.exists()
    assert ship.exists() and ship.stat().st_size < before


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_keep_masters_opts_out(book: Path) -> None:
    tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=120, kbps=192)
    master = book / "m4a" / "Episodes" / "Audio" / "ep01.m4a"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"x" * 4096)
    normalise(book, apply=True, keep_masters=True, log=lambda _m: None)
    assert master.exists()


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_a_dry_run_changes_nothing(book: Path) -> None:
    ship = tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=120, kbps=192)
    master = book / "m4a" / "Episodes" / "Audio" / "ep01.m4a"
    master.parent.mkdir(parents=True)
    master.write_bytes(b"x" * 4096)
    size = ship.stat().st_size

    report = normalise(book, apply=False, log=lambda _m: None)

    assert report["planned"] == 1
    # The PREVIEW must still name the deletion it would make — understating a
    # destructive step is the one direction a dry run must never err in.
    assert report["masters"] == 1
    assert ship.stat().st_size == size
    assert master.exists()


@pytest.mark.skipif(not HAS_FFMPEG, reason="needs ffmpeg")
def test_the_encode_preserves_duration(book: Path) -> None:
    """Read-along cues are absolute seconds into the file, so length must hold."""
    from downsize_audio import probe_duration

    ship = tone(book / "m4a" / "Episodes" / "ep01.m4a", seconds=120, kbps=192)
    was = probe_duration(ship)
    normalise(book, apply=True, log=lambda _m: None)
    assert abs(probe_duration(ship) - was) < 0.25


def test_the_absolute_floor_is_below_the_profile() -> None:
    """The flag can go lower than the default, but not into artefact territory."""
    assert ABSOLUTE_FLOOR_KBPS < DEFAULT_FLOOR_KBPS <= KEEP_BELOW_KBPS


def test_reading_a_book_is_read_only_unless_asked() -> None:
    """`load_book` re-encodes and deletes; that must never be the default.

    Many callers read a book to inspect it. If normalising were on by default,
    an audit, a dry run or a report would silently rewrite the recordings and
    delete the masters — so the default is pinned here rather than left to
    whoever next edits the signature.
    """
    import inspect

    from _listener_book import load_book

    parameter = inspect.signature(load_book).parameters["normalise_audio"]
    assert parameter.default is False
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, "must be named at the call site"
