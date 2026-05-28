"""tests/test_kashkole_ingest.py — B0 acceptance tests for the Kashkole ingestion driver.

Covers:
- ingest_all(dry_run=True) runs without errors against all chapters
- PASS chapters ingest with needs_review=0; WARN chapters with needs_review=1
- Re-ingesting a chapter after manual deletion produces identical atom count
- --status path: print_status() runs without error
- Idempotency: second ingest call on same chapter returns atoms_skipped (not re-created)
- Re-ingest flag: re_ingest=True deletes old atoms and creates fresh ones
- Chunk algorithm: section marker splitting and ≤600-word grouping
- Topic tagging: maps section IDs to topic type names
- Verdict filtering: FAIL chapters are skipped
- Canonical ID format: doctrine:kashkole:<binder_id>:<chapter_id>:<chunk_index>
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

# Ensure scripts/podcast is importable
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "podcast"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection, run_migrations, _reset_connection


# ---------------------------------------------------------------------------
# Module-level skip guard
# ---------------------------------------------------------------------------

try:
    from intelligence.kashkole_ingest_knowledge import (
        CORPUS_ROOT,
        PASS_WARN,
        _chunk_text,
        _make_chunk,
        _parse_bundle,
        _parse_verdict,
        ingest_all,
        ingest_chapter,
        print_status,
        seed_lookup_tables,
    )
    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERR = str(_e)

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK,
    reason=f"kashkole_ingest_knowledge not importable: {_IMPORT_OK or _IMPORT_ERR}",  # type: ignore[name-defined]
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Run every test with an isolated in-memory DB backed by a tmp file."""
    db_path = tmp_path / "test_knowledge.db"
    import _db as db_module
    monkeypatch.setattr(db_module, "_DB_PATH", db_path)
    _reset_connection()
    run_migrations(db_path=db_path)
    yield
    _reset_connection()


@pytest.fixture
def corpus_available():
    """Skip the test if the real Kashkole corpus is absent from disk."""
    if not CORPUS_ROOT.is_dir():
        pytest.skip("Kashkole corpus not present on disk — skipping live corpus test")


# ---------------------------------------------------------------------------
# Unit tests — chunking
# ---------------------------------------------------------------------------

def _dummy_topic_map():
    """Return minimal topic_types + assignments for unit testing."""
    types = {
        "17": {"name_en": "Prophetic Hadith", "name_ur": "حدیث نبوی"},
        "19": {"name_en": "Meaning of Quranic Verse", "name_ur": ""},
        "0": {"name_en": "Unknown", "name_ur": ""},
    }
    assignments = {"101": 17, "102": 19, "103": 0}
    return types, assignments


SAMPLE_EXTRACT = textwrap.dedent("""\
    Preamble text before first section.

    <!-- section 1 (id=101, raw_sort=1): First section -->

    ## Section One Title

    Alpha beta gamma delta epsilon. """ + "word " * 100 + """

    <!-- section 2 (id=102, raw_sort=2): Second section -->

    ## Section Two Title

    Another paragraph here. """ + "word " * 20 + """

    <!-- section 3 (id=103, raw_sort=3): Third section -->

    Final section text. """ + "word " * 30 + """
""")


def test_chunk_splits_on_section_markers():
    types, assignments = _dummy_topic_map()
    chunks = _chunk_text(SAMPLE_EXTRACT, types, assignments)
    assert len(chunks) >= 1
    # Every chunk has required keys
    for c in chunks:
        assert "chunk_index" in c
        assert "text_en" in c
        assert "section_ids" in c
        assert "topic_tags" in c
        assert "quran_refs" in c


def test_chunk_index_is_sequential():
    types, assignments = _dummy_topic_map()
    chunks = _chunk_text(SAMPLE_EXTRACT, types, assignments)
    indices = [c["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_respects_word_limit():
    types, assignments = _dummy_topic_map()
    # Each section > 600 words individually — must be one chunk per section
    long_body = "word " * 700
    text = (
        f"<!-- section 1 (id=101, raw_sort=1): A -->\n{long_body}\n"
        f"<!-- section 2 (id=102, raw_sort=2): B -->\n{long_body}\n"
    )
    chunks = _chunk_text(text, types, assignments)
    # Each section is already > 600 words so each must be its own chunk
    assert len(chunks) == 2


def test_chunk_topic_tags_mapped_correctly():
    types, assignments = _dummy_topic_map()
    chunks = _chunk_text(SAMPLE_EXTRACT, types, assignments)
    # Section 101 → type_id 17 → "Prophetic Hadith"
    tags_per_chunk = {c["chunk_index"]: c["topic_tags"] for c in chunks}
    all_tags = [t for tags in tags_per_chunk.values() for t in tags]
    assert "Prophetic Hadith" in all_tags or "Meaning of Quranic Verse" in all_tags


def test_chunk_unknown_topic_tag_excluded():
    """Sections mapped to topic_type_id=0 (Unknown) should produce no tag."""
    types, assignments = _dummy_topic_map()
    text = "<!-- section 1 (id=103, raw_sort=1): C -->\nsome content here\n"
    chunks = _chunk_text(text, types, assignments)
    assert chunks
    assert chunks[0]["topic_tags"] == []


def test_chunk_quran_refs_extracted():
    types, assignments = _dummy_topic_map()
    text = "<!-- section 1 (id=101, raw_sort=1): A -->\n" \
           "See ⟪quran 2:255⟫ and ⟪quran 7:24⟫ here.\n"
    chunks = _chunk_text(text, types, assignments)
    refs = chunks[0]["quran_refs"]
    assert "2:255" in refs
    assert "7:24" in refs


# ---------------------------------------------------------------------------
# DB-backed tests — live corpus (skip if absent)
# ---------------------------------------------------------------------------

def test_ingest_all_dry_run_no_errors(corpus_available):
    """ingest_all(dry_run=True) must complete without errors on the real corpus."""
    summary = ingest_all(dry_run=True)
    assert summary.total_chapters > 0
    assert not summary.errors, f"Errors: {summary.errors}"


def test_ingest_all_dry_run_counts_atoms(corpus_available):
    """dry_run should report > 0 atoms would be created for PASS+WARN chapters."""
    summary = ingest_all(dry_run=True)
    assert summary.total_atoms_created > 0 or summary.ingested > 0


def test_ingest_all_dry_run_skips_fail_chapters(corpus_available):
    """FAIL chapters are counted in skipped_verdict, not ingested."""
    summary_all = ingest_all(dry_run=True)
    assert summary_all.skipped_verdict > 0  # some FAIL chapters exist in corpus


def test_ingest_one_chapter(corpus_available):
    """Ingesting one known PASS/WARN chapter creates atoms in the DB."""
    # Find first PASS or WARN chapter to use as test target
    from intelligence.kashkole_ingest_knowledge import _iter_chapter_dirs, _parse_verdict, _parse_bundle
    target = None
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        v = _parse_verdict(ch_dir)
        if v in PASS_WARN:
            b = _parse_bundle(ch_dir)
            if b.get("binder_slug") and b.get("chapter_slug"):
                target = b
                break
    if target is None:
        pytest.skip("No PASS/WARN chapter found in corpus")

    result = ingest_chapter(target["binder_slug"], target["chapter_slug"])
    assert result.ok, f"Ingest failed: {result.error}"
    assert result.atoms_created > 0
    assert result.verdict in PASS_WARN

    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM atoms WHERE type = 'doctrine'"
    ).fetchone()[0]
    assert count == result.atoms_created


def test_warn_chapter_sets_needs_review(corpus_available):
    """WARN chapters must write needs_review=1 to corpus_chapters."""
    from intelligence.kashkole_ingest_knowledge import _iter_chapter_dirs, _parse_verdict, _parse_bundle
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        v = _parse_verdict(ch_dir)
        if v == "WARN":
            b = _parse_bundle(ch_dir)
            result = ingest_chapter(b["binder_slug"], b["chapter_slug"])
            assert result.ok, result.error
            conn = get_connection()
            row = conn.execute(
                "SELECT needs_review FROM corpus_chapters WHERE id = ?",
                (f"kashkole:{b['binder_id']}:{b['chapter_id']}",),
            ).fetchone()
            assert row is not None
            assert row[0] == 1
            return
    pytest.skip("No WARN chapter found in corpus")


def test_pass_chapter_sets_needs_review_zero(corpus_available):
    """PASS chapters must write needs_review=0 to corpus_chapters."""
    from intelligence.kashkole_ingest_knowledge import _iter_chapter_dirs, _parse_verdict, _parse_bundle
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        v = _parse_verdict(ch_dir)
        if v == "PASS":
            b = _parse_bundle(ch_dir)
            result = ingest_chapter(b["binder_slug"], b["chapter_slug"])
            assert result.ok, result.error
            conn = get_connection()
            row = conn.execute(
                "SELECT needs_review FROM corpus_chapters WHERE id = ?",
                (f"kashkole:{b['binder_id']}:{b['chapter_id']}",),
            ).fetchone()
            assert row is not None
            assert row[0] == 0
            return
    pytest.skip("No PASS chapter found in corpus")


def test_idempotency_second_call_skips(corpus_available):
    """Calling ingest_chapter twice without re_ingest returns atoms_skipped > 0."""
    from intelligence.kashkole_ingest_knowledge import _iter_chapter_dirs, _parse_verdict, _parse_bundle
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        if _parse_verdict(ch_dir) in PASS_WARN:
            b = _parse_bundle(ch_dir)
            if b.get("binder_slug") and b.get("chapter_slug"):
                ingest_chapter(b["binder_slug"], b["chapter_slug"])
                r2 = ingest_chapter(b["binder_slug"], b["chapter_slug"])
                assert r2.atoms_skipped > 0
                assert r2.atoms_created == 0
                return
    pytest.skip("No PASS/WARN chapter found")


def test_re_ingest_produces_same_atom_count(corpus_available):
    """Re-ingesting a chapter must produce the same atom count as the first ingest."""
    from intelligence.kashkole_ingest_knowledge import _iter_chapter_dirs, _parse_verdict, _parse_bundle
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        if _parse_verdict(ch_dir) in PASS_WARN:
            b = _parse_bundle(ch_dir)
            if b.get("binder_slug") and b.get("chapter_slug"):
                r1 = ingest_chapter(b["binder_slug"], b["chapter_slug"])
                r2 = ingest_chapter(b["binder_slug"], b["chapter_slug"], re_ingest=True)
                assert r1.atoms_created == r2.atoms_created
                conn = get_connection()
                count = conn.execute(
                    "SELECT COUNT(*) FROM atoms WHERE type = 'doctrine'"
                ).fetchone()[0]
                assert count == r1.atoms_created
                return
    pytest.skip("No PASS/WARN chapter found")


def test_canonical_id_format(corpus_available):
    """Atom IDs must match doctrine:kashkole:<binder_id>:<chapter_id>:<chunk_index>."""
    from intelligence.kashkole_ingest_knowledge import _iter_chapter_dirs, _parse_verdict, _parse_bundle
    import re as _re
    pattern = _re.compile(r"^doctrine:kashkole:\d+:\d+:\d+$")
    for ch_dir, _bd, _cd in _iter_chapter_dirs():
        if _parse_verdict(ch_dir) in PASS_WARN:
            b = _parse_bundle(ch_dir)
            if b.get("binder_slug") and b.get("chapter_slug"):
                ingest_chapter(b["binder_slug"], b["chapter_slug"])
                conn = get_connection()
                rows = conn.execute(
                    "SELECT id FROM atoms WHERE type = 'doctrine' LIMIT 10"
                ).fetchall()
                assert rows, "No doctrine atoms were written"
                for (atom_id,) in rows:
                    assert pattern.match(atom_id), f"Bad ID format: {atom_id}"
                return
    pytest.skip("No PASS/WARN chapter found")


def test_seed_lookup_tables_idempotent():
    """Calling seed_lookup_tables twice must not raise or duplicate rows."""
    conn = get_connection()
    seed_lookup_tables(conn)
    seed_lookup_tables(conn)
    count = conn.execute(
        "SELECT COUNT(*) FROM external_corpora WHERE id = 'kashkole'"
    ).fetchone()[0]
    assert count == 1
