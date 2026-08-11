"""Every path that rewrites a pass report recomputes EVERY status-derived count.

The pass reports (`_system/book-fluency-report.json`, `book-voice-report.json`)
carry per-chapter records plus a few top-level totals derived from them. Four
places write those files: the pass itself, the post-replay reconcile, the
on-demand rearticulation re-stamp, and the drop-a-section bookkeeping.

Until 2026-08-11 the three re-stamp paths each carried their own copy of the
tally, and all three copies recomputed `adapted`/`revoiced` and
`overwritten_by_replay` while none recomputed `reverted`. Moving a chapter OFF
`reverted` therefore left the summary frozen while the record beside it told the
truth — one file contradicting itself.

It cost a real day. On kitab-al-riyad the fidelity gates reverted three chapters
on 2026-08-08; each was rearticulated over the following two days, each re-stamp
correctly recomputed `adapted`, and `reverted` stayed at 3 throughout. The book
was never damaged — `output_words == base_words` on all three, so the faithful
base is what stood — but `test_articulation_state_is_intact` reads the summary
and reported a regression that had already been repaired.

These tests are written against the OBSERVABLE contract (write a report, mutate
it through the public entry point, read the counts back) rather than against
`restamp_counts` alone, because the defect was never in a tally — each tally was
correct. It was in which tallies a call site remembered to run. Only a test that
goes through the call sites can catch that, which is why the same assertion is
made once per path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PIPELINE = Path(__file__).resolve().parents[1]
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

from _book_edits import anchor_key  # noqa: E402
from _book_pass_reports import (  # noqa: E402
    STATUS_OVERWRITTEN,
    drop_section_from_reports,
    reconcile_reports_after_replay,
    record_rearticulation,
    restamp_counts,
)

REPORTS = (
    ("book-fluency-report.json", "podcast.book-fluency/v5", "adapted"),
    ("book-voice-report.json", "podcast.book-voice/v5", "revoiced"),
)

# Every top-level count the reports carry. A count added to the schema and not to
# this tuple is a count no test proves is maintained.
COUNT_KEYS = ("reverted", "overwritten_by_replay")


def _record(title: str, status: str) -> dict:
    return {"title": title, "status": status, "base_words": 100, "output_words": 100}


def _write(book: Path, name: str, schema: str, count_key: str, records: list[dict]) -> Path:
    path = book / "_system" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema": schema, "narrative_frame": "external_narrator", count_key: 0, "chapters": records}
    restamp_counts(data, records, schema=schema, count_key=count_key)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _counts(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data["chapters"]
    return {
        "declared": {k: data.get(k) for k in COUNT_KEYS},
        "actual": {
            "reverted": sum(1 for r in records if r.get("status") == "reverted"),
            "overwritten_by_replay": sum(1 for r in records if r.get("status") == STATUS_OVERWRITTEN),
        },
    }


def _assert_consistent(path: Path) -> None:
    c = _counts(path)
    assert c["declared"] == c["actual"], (
        f"{path.name} contradicts itself: the summary says {c['declared']} while its own records say {c['actual']}"
    )


@pytest.mark.parametrize(("name", "schema", "count_key"), REPORTS, ids=[r[0] for r in REPORTS])
def test_rearticulation_restamp_brings_the_reverted_count_down(
    tmp_path: Path, name: str, schema: str, count_key: str
) -> None:
    """The kitab-al-riyad case, reduced: fix a reverted chapter, count must follow."""
    book = tmp_path / "book"
    records = [_record("Chapter One", "reverted"), _record("Chapter Two", "adapted")]
    path = _write(book, name, schema, count_key, records)
    assert json.loads(path.read_text())["reverted"] == 1

    assert record_rearticulation(book, "Chapter One", "adapted", log=lambda *_: None) == 1

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["reverted"] == 0, (
        "the chapter was rearticulated and its record says composer-edit, but the summary still reports it reverted"
    )
    _assert_consistent(path)


@pytest.mark.parametrize(("name", "schema", "count_key"), REPORTS, ids=[r[0] for r in REPORTS])
def test_replay_reconcile_keeps_every_count_consistent(tmp_path: Path, name: str, schema: str, count_key: str) -> None:
    book = tmp_path / "book"
    records = [_record("Chapter One", "adapted"), _record("Chapter Two", "reverted")]
    path = _write(book, name, schema, count_key, records)

    # The key is whatever anchor_key() makes of the title — asked for rather than
    # spelled literally, so a change to that normalisation fails the mirror pin
    # that owns it instead of quietly un-targeting this test.
    replay = {"chapters": [{"chapter_key": anchor_key("Chapter One"), "skipped": False}]}
    assert reconcile_reports_after_replay(book, replay, log=lambda *_: None) >= 1

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["overwritten_by_replay"] == 1
    assert data["reverted"] == 1, "an untouched reverted chapter lost its place in the summary"
    _assert_consistent(path)


@pytest.mark.parametrize(("name", "schema", "count_key"), REPORTS, ids=[r[0] for r in REPORTS])
def test_dropping_a_section_recounts_what_remains(tmp_path: Path, name: str, schema: str, count_key: str) -> None:
    """Dropping the only reverted chapter must take it out of the summary too."""
    book = tmp_path / "book"
    records = [_record("Folded Opening", "reverted"), _record("Chapter One", "adapted")]
    path = _write(book, name, schema, count_key, records)
    assert json.loads(path.read_text())["reverted"] == 1

    assert drop_section_from_reports(book, "Folded Opening", log=lambda *_: None) == 1

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["reverted"] == 0, "the dropped section is gone from the records but not the summary"
    assert data[count_key] == 1
    _assert_consistent(path)


def test_restamp_writes_every_declared_count_even_when_zero(tmp_path: Path) -> None:
    """A count must be WRITTEN, not left at whatever the file already said.

    The frozen-counter bug looked like a missing recomputation, but its shape was
    a key that survived a rewrite untouched. Asserting the key is overwritten —
    including down to zero — is what pins that.
    """
    records = [_record("Chapter One", "adapted")]
    data = {"schema": "stale", "adapted": 99, "reverted": 99, "overwritten_by_replay": 99}
    restamp_counts(data, records, schema="podcast.book-fluency/v5", count_key="adapted")
    assert data == {
        "schema": "podcast.book-fluency/v5",
        "adapted": 1,
        "reverted": 0,
        "overwritten_by_replay": 0,
    }
