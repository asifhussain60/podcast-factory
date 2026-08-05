"""Tests for the morphology.db builder + query API.

Builds a real (tiny) DB from tests/fixtures/morphology-excerpt.txt through the
production build path — schema, inserts, aggregation — with the corpus-shape
assertion monkeypatched down to excerpt scale. Never touches the live DB
(temp files only, per house convention).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import quranic_morphology as qm  # noqa: E402

EXCERPT = REPO / "tests" / "fixtures" / "morphology-excerpt.txt"


@pytest.fixture()
def db_path(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(qm, "_assert_expected", lambda counts: None)
    path = tmp_path / "morphology.db"
    counts = qm.build_db(db_path=path, source_path=EXCERPT)
    assert counts == {"chapters": 2, "verses": 2, "words": 6, "segments": 12, "roots": 5, "lemmas": 6}
    return path


def test_missing_source_prints_download_instructions(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="corpus.quran.com/download"):
        qm.build_db(db_path=tmp_path / "x.db", source_path=tmp_path / "absent.txt")


def test_shape_assertion_rejects_truncated_corpus(tmp_path: Path) -> None:
    # The real guard: excerpt-scale counts must FAIL the documented corpus shape.
    with pytest.raises(RuntimeError, match="corpus shape check failed"):
        qm.build_db(db_path=tmp_path / "x.db", source_path=EXCERPT)


def test_build_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(qm, "_assert_expected", lambda counts: None)
    path = tmp_path / "morphology.db"
    first = qm.build_db(db_path=path, source_path=EXCERPT)
    second = qm.build_db(db_path=path, source_path=EXCERPT)
    assert first == second
    conn = qm.open_db(path)
    assert conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0] == 12
    conn.close()


def test_get_by_root_accepts_buckwalter_and_arabic(db_path: Path) -> None:
    conn = qm.open_db(db_path)
    try:
        by_bw = qm.get_by_root("rHm", conn)
        by_ar = qm.get_by_root("رحم", conn)
        by_dashed = qm.get_by_root("r-H-m", conn)
    finally:
        conn.close()
    assert [r["form_bw"] for r in by_bw] == ["r~aHoma`ni", "r~aHiymi"]
    assert by_ar == by_bw == by_dashed
    assert by_bw[0]["chapter"] == 1 and by_bw[0]["verse"] == 1 and by_bw[0]["word"] == 3


def test_root_summary_family_and_pos(db_path: Path) -> None:
    conn = qm.open_db(db_path)
    try:
        summary = qm.root_summary("rHm", conn)
    finally:
        conn.close()
    assert summary["root_ar"] == "رحم"
    assert summary["occurrences"] == 2 and summary["lemma_count"] == 2
    assert {lem["lemma_bw"] for lem in summary["lemmas"]} == {"r~aHoma`n", "r~aHiym"}
    assert summary["pos_distribution"] == {"ADJ": 2}
    assert summary["sample_locations"] == ["1:1:3", "1:1:4"]


def test_get_word_reassembles_segments(db_path: Path) -> None:
    conn = qm.open_db(db_path)
    try:
        word = qm.get_word(1, 1, 1, conn)
    finally:
        conn.close()
    assert word["form_bw"] == "bisomi"
    assert [s["form_bw"] for s in word["segments"]] == ["bi", "somi"]
    assert word["segments"][1]["root_ar"] == "سمو"


def test_get_verse_and_lists(db_path: Path) -> None:
    conn = qm.open_db(db_path)
    try:
        verse = qm.get_verse(1, 1, conn)
        roots = qm.list_roots(conn)
        lemmas = qm.list_lemmas(conn)
        hits = qm.search_lemma("r~aHiym", conn)
    finally:
        conn.close()
    assert len(verse) == 4 and verse[0]["form_bw"] == "bisomi"
    assert len(roots) == 5 and len(lemmas) == 6
    assert hits and hits[0]["root_bw"] == "rHm"


def test_absent_db_degrades_to_empty() -> None:
    missing = Path(tempfile.gettempdir()) / "no-such-morphology.db"
    assert qm.open_db(missing) is None
    assert qm.get_by_root("rHm", None) == [] or qm.MORPHOLOGY_DB.is_file()


def test_verify_db_roundtrip(monkeypatch, db_path: Path) -> None:
    monkeypatch.setattr(qm, "_assert_expected", lambda counts: None)
    counts = qm.verify_db(db_path)
    assert counts["segments"] == 12 and counts["roots"] == 5
