"""Tests for transcribe_notebooklm — Azure batch path (transcriber injected)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from transcribe_notebooklm import _episode_id, plan_missing, transcribe_book


def _book(tmp_path: Path) -> Path:
    (tmp_path / "m4a" / "transcripts").mkdir(parents=True)
    (tmp_path / "episodes").mkdir()
    (tmp_path / "m4a" / "ch01a-the-garden.m4a").write_bytes(b"a")
    (tmp_path / "m4a" / "ch02b-the-mountain.m4a").write_bytes(b"b")
    (tmp_path / "episodes" / "EP01-the-garden.txt").write_text("f", encoding="utf-8")
    return tmp_path


def _fake_transcriber(audio_path: Path, locale: str) -> str:
    return f"spoken words of {audio_path.stem} in {locale}"


def test_plan_lists_only_missing(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "transcripts" / "ch01a-the-garden.transcript.txt").write_text("done", encoding="utf-8")
    todo, nc = plan_missing(book)
    assert [p.stem for p in todo] == ["ch02b-the-mountain"]
    assert nc == []


def test_plan_flags_non_canonical_for_normalize(tmp_path):
    book = _book(tmp_path)
    (book / "m4a" / "Some_Creative_Title.m4a").write_bytes(b"x")
    todo, nc = plan_missing(book)
    assert [p.name for p in nc] == ["Some_Creative_Title.m4a"]
    assert len(todo) == 2  # canonical pair still planned


def test_transcribe_writes_both_contracts(tmp_path):
    book = _book(tmp_path)
    written = transcribe_book(book, transcriber=_fake_transcriber, log=lambda *_: None)
    # 2 audio files x (m4a/transcripts + transcripts/EP copy) = 4 files
    assert len(written) == 4
    src = book / "m4a" / "transcripts" / "ch01a-the-garden.transcript.txt"
    audit = book / "transcripts" / "EP01-the-garden.transcript.txt"
    assert src.exists() and audit.exists()
    assert src.read_text() == audit.read_text()
    assert "ch01a-the-garden" in src.read_text()


def test_audit_copy_suppressed(tmp_path):
    book = _book(tmp_path)
    written = transcribe_book(book, audit_copy=False, transcriber=_fake_transcriber, log=lambda *_: None)
    assert len(written) == 2
    assert not (book / "transcripts").exists()


def test_idempotent_skip_and_force(tmp_path):
    book = _book(tmp_path)
    transcribe_book(book, transcriber=_fake_transcriber, log=lambda *_: None)
    again = transcribe_book(book, transcriber=_fake_transcriber, log=lambda *_: None)
    assert again == []
    forced = transcribe_book(
        book, force=True, only="ch01a-the-garden", transcriber=_fake_transcriber, log=lambda *_: None
    )
    assert len(forced) == 2


def test_empty_transcript_skipped_not_written(tmp_path):
    book = _book(tmp_path)
    written = transcribe_book(book, transcriber=lambda *_: "   ", log=lambda *_: None)
    assert written == []
    assert list((book / "m4a" / "transcripts").glob("*.txt")) == []


def test_cost_ledger_rows_appended(tmp_path):
    book = _book(tmp_path)
    transcribe_book(book, transcriber=_fake_transcriber, log=lambda *_: None)
    ledger = book / "_system" / "cost-ledger.jsonl"
    assert ledger.exists()
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    stt = [r for r in rows if r.get("model") == "azure-speech-stt-fast"]
    assert len(stt) == 2
    assert all(r["step"].startswith("transcribe-notebooklm/ch") for r in stt)
    assert all(r["cost_usd"] > 0 for r in stt)


def test_episode_id_prefers_real_episode_filename(tmp_path):
    book = _book(tmp_path)
    # EP01 exists on disk; EP02 doesn't -> derived from the chapter stem.
    assert _episode_id(book, "ch01a-the-garden") == "EP01-the-garden"
    assert _episode_id(book, "ch02b-the-mountain") == "EP02-the-mountain"
