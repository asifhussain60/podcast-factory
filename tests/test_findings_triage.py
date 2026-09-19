"""The findings ledger must be a ledger, not a write-only sink.

_learning/findings.jsonl had ~740 top-severity findings still 'flagged' (85.7% never resolved, oldest
2026-05-24) with no triage, so nobody could tell the few that matter from the ghosts: complaints about files
that were since deleted or moved, and older copies of a complaint that a later run re-reported. Asif approved an
auto-close-by-rule policy (2026-09-18): close only when the evidence says the complaint no longer describes
anything live, record WHY on the row, and never delete a row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import findings_triage as ft  # noqa: E402

T1, T2, T3 = "2026-06-01T00:00:00Z", "2026-07-01T00:00:00Z", "2026-08-01T00:00:00Z"


def row(**kw):
    base = {
        "book": "b",
        "source": "podcast-challenger",
        "severity": "P0",
        "resolution": "flagged",
        "file": "content/x/b/ch1.txt",
        "ts": T1,
        "signature": "sig-a",
        "check_id": "N1",
    }
    base.update(kw)
    return base


def classify(rows, exists=True, changed=None):
    return ft.classify(
        rows,
        resolve=lambda r: (Path("/repo") / r["file"]) if exists else None,
        changed_at=lambda p: changed,
    )


def test_a_finding_about_a_file_that_no_longer_exists_is_superseded():
    verdicts = classify([row()], exists=False)
    assert verdicts[0].startswith("artifact no longer exists")


def test_an_older_copy_of_a_complaint_a_later_run_repeated_is_superseded_by_the_latest():
    rows = [row(ts=T1), row(ts=T3)]
    verdicts = classify(rows)
    assert 0 in verdicts and "re-reported" in verdicts[0]
    assert 1 not in verdicts, "the most recent report is the live one"


def test_a_file_changed_after_the_finding_closes_it_only_if_the_same_source_reran_later():
    rerun = row(ts=T3, signature="other", file="content/x/b/ch2.txt")
    changed_after = ft.parse_ts(T2)
    assert 0 in classify([row(ts=T1), rerun], changed=changed_after)
    assert 0 not in classify([row(ts=T1)], changed=changed_after), "no later run = nobody re-checked it"


def test_a_file_unchanged_since_the_finding_stays_open():
    assert classify([row(ts=T2), row(ts=T3, signature="other")], changed=ft.parse_ts(T1)) == {}


def test_rows_already_resolved_are_never_touched():
    assert classify([row(resolution="fixed"), row(resolution="auto-fixed")], exists=False) == {}


def test_rows_without_a_file_or_timestamp_are_left_alone():
    assert classify([row(file=None), row(ts=None)], exists=False) == {}


def test_apply_records_the_reason_keeps_the_old_status_and_deletes_nothing():
    rows = [row(), row(ts=T3)]
    out = ft.apply(rows, {0: "re-reported by a later run"}, today="2026-09-19")
    assert len(out) == 2
    assert out[0]["resolution"] == "superseded" and out[0]["resolution_before"] == "flagged"
    assert out[0]["superseded_reason"] == "re-reported by a later run" and out[0]["superseded_on"] == "2026-09-19"
    assert out[1] == rows[1]


def test_apply_is_idempotent():
    rows = [row(), row(ts=T3)]
    once = ft.apply(rows, classify(rows), today="d")
    assert classify(once) == {}, "an already-superseded row is not classified again"


def test_the_file_round_trips_line_for_line(tmp_path):
    p = tmp_path / "f.jsonl"
    rows = [row(), {"finding_id": "PR1", "source": "postprod-review", "severity": "P1"}]
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    loaded = ft.load(p)
    ft.save(p, loaded)
    assert p.read_text(encoding="utf-8").splitlines() == [json.dumps(r, ensure_ascii=False) for r in rows]


def test_legacy_and_foreign_paths_resolve_to_the_live_location(tmp_path):
    book = tmp_path / "content" / "Islamic" / "b"
    (book / "chapters").mkdir(parents=True)
    (book / "chapters" / "ch1.txt").write_text("x")
    resolve = ft.make_resolver(tmp_path)
    for path in (
        "content/Islamic/b/chapters/ch1.txt",
        "content/drafts/b/chapters/ch1.txt",  # the retired layout
        "/Users/someone/Code/podcast-factory/content/Islamic/b/chapters/ch1.txt",  # another machine's checkout
        "chapters/ch1.txt",  # relative to the book dir
    ):
        assert resolve({"file": path, "book": "b"}) == book / "chapters" / "ch1.txt", path
    assert resolve({"file": "content/Islamic/b/chapters/gone.txt", "book": "b"}) is None
