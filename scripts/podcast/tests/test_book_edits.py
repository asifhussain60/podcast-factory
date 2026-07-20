"""Durable Book Composer edits — the sidecar that makes the Composer singular.

The property under test: an edit made in the Composer must still be in book.md
after the pipeline regenerates that file. Before this sidecar, it was not — and
nothing reported the loss.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_edits import (  # noqa: E402
    anchor_key,
    apply_composer_edits,
    fingerprint,
    load_edits,
    record_edit,
)

_BOOK = "# The Book\n\n## 1. On Knowledge\n\nPipeline prose for one.\n\n## 2. On Patience\n\nPipeline prose for two.\n"


def _book(tmp_path: Path, md: str = _BOOK) -> Path:
    bd = tmp_path / "bd"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(md, encoding="utf-8")
    return bd


def _body(bd: Path, heading: str) -> str:
    text = (bd / "book" / "book.md").read_text(encoding="utf-8")
    after = text.split(heading, 1)[1]
    return after.split("## ", 1)[0].strip()


def test_anchor_key_matches_the_typescript_mirror() -> None:
    # Divergence here silently orphans every saved edit — the replay simply
    # finds no matching chapter. Mirror of anchorKey, whose single JS
    # implementation is plan-dashboard/scripts/lib/anchor-key.mjs.
    assert anchor_key("## 1. On Knowledge") == "on knowledge"
    assert anchor_key("## <em>On</em> Patience") == "on patience"


def test_replay_wins_over_regenerated_prose(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="The human's own sentence.")
    # The pipeline regenerates book.md — the edit is gone from the file...
    (bd / "book" / "book.md").write_text(
        "# The Book\n\n## 1. On Knowledge\n\nFRESH pipeline prose.\n\n## 2. On Patience\n\nPipeline prose for two.\n",
        encoding="utf-8",
    )
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["applied"] == 1
    assert _body(bd, "## 1. On Knowledge") == "The human's own sentence."
    assert "Pipeline prose for two." in _body(bd, "## 2. On Patience")  # untouched


def test_replay_is_idempotent(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="The human's own sentence.")
    apply_composer_edits(bd, log=lambda *a: None)
    once = (bd / "book" / "book.md").read_text(encoding="utf-8")
    apply_composer_edits(bd, log=lambda *a: None)
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == once


def test_conflict_is_reported_not_papered_over(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(
        bd,
        chapter_key="on knowledge",
        body_md="The human's own sentence.",
        base_fingerprint=fingerprint("Pipeline prose for one."),
    )
    # Pipeline improved the chapter after the human edited it.
    (bd / "book" / "book.md").write_text(
        "# The Book\n\n## 1. On Knowledge\n\nIMPROVED pipeline prose.\n\n## 2. On Patience\n\nb\n",
        encoding="utf-8",
    )
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["conflicts"] == 1
    # The edit still wins — it is the author's chapter — but they are told.
    assert _body(bd, "## 1. On Knowledge") == "The human's own sentence."
    assert report["chapters"][0]["conflict"] is True


def test_no_conflict_when_the_base_is_unchanged(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(
        bd,
        chapter_key="on knowledge",
        body_md="The human's own sentence.",
        base_fingerprint=fingerprint("Pipeline prose for one."),
    )
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["applied"] == 1 and report["conflicts"] == 0


def test_orphaned_edit_is_reported_never_guessed_at(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="a chapter that was renamed", body_md="orphan text")
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["orphaned"] == 1 and report["applied"] == 0
    # Nothing was guessed into the book.
    assert "orphan text" not in (bd / "book" / "book.md").read_text(encoding="utf-8")


def test_last_write_per_chapter_wins(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="first")
    record_edit(bd, chapter_key="on knowledge", body_md="second")
    edits = load_edits(bd)["edits"]
    assert len(edits) == 1 and edits[0]["body_md"] == "second"


def test_corrupt_sidecar_does_not_break_compose(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    (bd / "_system" / "composer-edits.json").write_text("{not json", encoding="utf-8")
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["applied"] == 0
    assert "Pipeline prose for one." in (bd / "book" / "book.md").read_text(encoding="utf-8")


def test_no_sidecar_is_a_clean_no_op(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    before = (bd / "book" / "book.md").read_text(encoding="utf-8")
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["applied"] == 0
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == before


def test_replay_report_is_written(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="x")
    apply_composer_edits(bd, log=lambda *a: None)
    report = json.loads((bd / "_system" / "composer-edits-replay.json").read_text())
    assert report["applied"] == 1


# ─── mirror pair with the JS anchorKey ────────────────────────────────────────
def test_anchor_key_matches_the_shared_js_fixtures() -> None:
    """The Python half of the anchorKey mirror pair.

    The JS half is `plan-dashboard/scripts/lib/anchor-key.test.mjs`, reading this
    same fixture file. Before 2026-07-20 the function had four byte-identical JS
    copies plus this one, nothing imported a shared module, and the two languages
    disagreed about Arabic-Indic digits — Python's `\\d` is Unicode-aware and
    JavaScript's is ASCII-only, so `## ١. Patience` keyed differently on each side
    and every edit on such a chapter would be silently orphaned on replay.
    """
    fixtures = Path(__file__).resolve().parents[3] / "plan-dashboard" / "scripts" / "lib" / "anchor-key.fixtures.json"
    assert fixtures.is_file(), f"shared fixture file missing: {fixtures}"
    cases = json.loads(fixtures.read_text(encoding="utf-8"))["cases"]
    assert cases, "fixture file is empty"
    for case in cases:
        assert anchor_key(case["in"]) == case["out"], case["in"]
