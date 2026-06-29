#!/usr/bin/env python3
"""Unit tests for phases/audio_ingest_driver.drive_audio_ingest.

The self-correcting INPUT side of the NotebookLM audio loop. Every Azure/git
boundary is mocked (no spend, no repo mutation). Covers the contract:

  - skip (autonomous/ElevenLabs book — no NotebookLM episodes)
  - halt while the operator is still working (no audio dropped)
  - complete with already-canonical audio
  - deterministic filename-drift repair (normalize_m4a) then complete
  - idempotent second pass (already completed -> immediate skip)
  - ambiguous drop left untouched + re-halt
  - ordering guard: publish driver halts at audio-ingest BEFORE the book branch
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))
sys.path.insert(0, str(SCRIPTS_PODCAST / "phases"))

import _progress  # noqa: E402
from phases import audio_ingest_driver as aid  # noqa: E402

CH_STEM = "ch01-the-lamp-and-the-wick"
EP_ID = "EP01-the-lamp-and-the-wick"
_CANON = re.compile(r"^ch\d{2}[a-z]?-")


def _make_book(tmp: str, *, engine: str | None = None,
               overrides: dict | None = None) -> Path:
    book = Path(tmp)
    (book / "_system").mkdir(parents=True, exist_ok=True)
    _progress.write_state(book, _progress.initial_state(book.name, "books"))
    cfg_lines: list[str] = []
    if engine:
        cfg_lines.append(f"audio_engine: {engine}")
    if overrides:
        cfg_lines.append("episode_engine_overrides:")
        cfg_lines += [f"  {k}: {v}" for k, v in overrides.items()]
    (book / "_system" / "series-config.yaml").write_text(
        ("\n".join(cfg_lines) + "\n") if cfg_lines else "", encoding="utf-8")
    (book / "chapters").mkdir(exist_ok=True)
    (book / "episodes").mkdir(exist_ok=True)
    (book / "chapters" / f"{CH_STEM}.txt").write_text(
        "The lamp and the wick. A lamp consumes itself to give light. The wick "
        "burns while the flame teaches the seeker about sacrifice and the self.\n",
        encoding="utf-8")
    (book / "episodes" / f"{EP_ID}.txt").write_text(
        "Welcome to the teaching on the lamp and the wick. The flame, the wick, "
        "and the sacrifice of the self that carries the light.\n", encoding="utf-8")
    return book


def _fake_transcribe(book_dir, **kw):
    """Stand-in for Azure: write a transcript for every canonical m4a missing one."""
    m4a = Path(book_dir) / "m4a"
    tx = m4a / "transcripts"
    tx.mkdir(parents=True, exist_ok=True)
    written = []
    for p in sorted(m4a.glob("*.m4a")):
        if _CANON.match(p.stem):
            t = tx / f"{p.stem}.transcript.txt"
            if not t.exists():
                t.write_text("transcript text\n", encoding="utf-8")
                written.append(t)
    return written


class AudioIngestDriverTests(unittest.TestCase):
    maxDiff = None

    def _status(self, book):
        return (_progress.read_state(book) or {})["phases"]["audio-ingest"]["status"]

    def test_skip_for_autonomous_engine(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d, engine="elevenlabs")
            outcome, rc = aid.drive_audio_ingest(book)
            self.assertEqual((outcome, rc), ("skipped", 0))
            self.assertEqual(self._status(book), "skipped")

    def test_halt_when_no_audio_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)  # default = notebooklm
            outcome, rc = aid.drive_audio_ingest(book)
            self.assertEqual((outcome, rc), ("halted", 3))
            self.assertEqual(self._status(book), "halted")

    def test_complete_with_canonical_audio(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            (book / "m4a").mkdir()
            (book / "m4a" / f"{CH_STEM}.m4a").write_bytes(b"AUDIO")
            with mock.patch("transcribe_notebooklm.transcribe_book",
                            side_effect=_fake_transcribe), \
                 mock.patch("phases.scaffold.phase_git_commit"):
                outcome, rc = aid.drive_audio_ingest(book)
            self.assertEqual((outcome, rc), ("ingested", 0))
            self.assertEqual(self._status(book), "completed")
            self.assertTrue(
                (book / "m4a" / "transcripts" / f"{CH_STEM}.transcript.txt").exists())

    def test_drift_repair_renames_then_completes(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            (book / "m4a").mkdir()
            # NotebookLM creative title — non-canonical, but its tokens fingerprint ch01.
            dropped = book / "m4a" / "The_Lamp_And_The_Wick_Why_Light_Costs.m4a"
            dropped.write_bytes(b"AUDIO")
            with mock.patch("transcribe_notebooklm.transcribe_book",
                            side_effect=_fake_transcribe), \
                 mock.patch("phases.scaffold.phase_git_commit"):
                outcome, rc = aid.drive_audio_ingest(book)
            self.assertEqual((outcome, rc), ("ingested", 0))
            # Renamed to canonical; the creative-titled drop is gone.
            self.assertTrue((book / "m4a" / f"{CH_STEM}.m4a").exists())
            self.assertFalse(dropped.exists())
            # The decision is recorded in the verification ledger as a confident MATCH.
            import json
            ledger = json.loads(
                (book / "m4a" / "_review" / "prefix-verification.json").read_text())
            self.assertTrue(any(e.get("verdict") == "MATCH" and e.get("kind") == "audio"
                                for e in ledger))

    def test_idempotent_second_pass_skips(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            (book / "m4a").mkdir()
            (book / "m4a" / f"{CH_STEM}.m4a").write_bytes(b"AUDIO")
            with mock.patch("transcribe_notebooklm.transcribe_book",
                            side_effect=_fake_transcribe), \
                 mock.patch("phases.scaffold.phase_git_commit"):
                first = aid.drive_audio_ingest(book)
                # Second call: already completed -> immediate skip, no re-work.
                with mock.patch("transcribe_notebooklm.transcribe_book") as t2:
                    second = aid.drive_audio_ingest(book)
                    t2.assert_not_called()
            self.assertEqual(first, ("ingested", 0))
            self.assertEqual(second, ("skipped", 0))

    def test_ambiguous_drop_left_untouched_and_rehalts(self):
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            (book / "m4a").mkdir()
            # No token overlap with the only chapter -> AMBIGUOUS, never renamed.
            junk = book / "m4a" / "unrelated_random_xyzzy_recording.m4a"
            junk.write_bytes(b"AUDIO")
            with mock.patch("transcribe_notebooklm.transcribe_book",
                            side_effect=_fake_transcribe), \
                 mock.patch("phases.scaffold.phase_git_commit"):
                outcome, rc = aid.drive_audio_ingest(book)
            self.assertEqual((outcome, rc), ("halted", 3))
            self.assertEqual(self._status(book), "halted")
            self.assertTrue(junk.exists())  # untouched — never guessed
            self.assertFalse((book / "m4a" / f"{CH_STEM}.m4a").exists())

    def test_publish_driver_halts_before_book_branch_when_audio_missing(self):
        """Ordering guard: audio-ingest gates the book branch — a NotebookLM book
        with no dropped audio halts at audio-ingest and never reaches 0book/publish."""
        from phases import publish_driver
        with tempfile.TemporaryDirectory() as d:
            book = _make_book(d)
            with mock.patch.object(publish_driver, "_drive_book_branch") as bb:
                rc = publish_driver._drive_publish_through_done(book)
                bb.assert_not_called()
            self.assertEqual(rc, 0)  # clean stop, not an error
            self.assertEqual(self._status(book), "halted")


if __name__ == "__main__":
    unittest.main()
