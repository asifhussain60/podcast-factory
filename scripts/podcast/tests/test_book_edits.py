"""Durable Book Composer edits — the sidecar that makes the Composer singular.

The property under test: an edit made in the Composer must still be in book.md
after the pipeline regenerates that file. Before this sidecar, it was not — and
nothing reported the loss.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_edits import (  # noqa: E402
    SidecarUnreadable,
    anchor_key,
    apply_composer_edits,
    base_fingerprint_for,
    edited_body,
    edited_chapter_keys,
    fingerprint,
    load_base_stamp,
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


def test_replay_writes_the_body_verbatim(tmp_path: Path) -> None:
    """No normalisation here — the deterministic passes run AFTER the replay.

    This function used to fold transliteration and spelling itself, because it ran
    after those passes. It could not fold in the inline Arabic that way, since that
    pass had already run, so an authored chapter printed with no script beside its
    terms. The replay moved ahead of all of them (compose step 5a-replay); folding
    here as well would mean two places deciding house style.
    """
    bd = _book(tmp_path)
    body = "The colour of honour, and Bayt al-Ma'mur."
    record_edit(bd, chapter_key="on knowledge", body_md=body)
    apply_composer_edits(bd, log=lambda *a: None)
    assert _body(bd, "## 1. On Knowledge") == body


def test_replay_is_idempotent(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="The human's own sentence.")
    apply_composer_edits(bd, log=lambda *a: None)
    once = (bd / "book" / "book.md").read_text(encoding="utf-8")
    apply_composer_edits(bd, log=lambda *a: None)
    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == once


def test_conflict_is_reported_not_papered_over(tmp_path: Path) -> None:
    # Only --force re-composes over an author's chapter, so only --force can
    # produce a true conflict. Everything else is the skip path below.
    bd = _book(tmp_path)
    apply_composer_edits(bd, log=lambda *a: None)  # compose 1: stamps the base
    record_edit(
        bd,
        chapter_key="on knowledge",
        body_md="The human's own sentence.",
        base_fingerprint=base_fingerprint_for(bd, "on knowledge"),
    )
    # Pipeline was forced to re-compose the chapter after the human edited it.
    (bd / "book" / "book.md").write_text(
        "# The Book\n\n## 1. On Knowledge\n\nIMPROVED pipeline prose.\n\n## 2. On Patience\n\nb\n",
        encoding="utf-8",
    )
    report = apply_composer_edits(bd, log=lambda *a: None, force=True)
    assert report["conflicts"] == 1
    # The edit still wins — it is the author's chapter — but they are told.
    assert _body(bd, "## 1. On Knowledge") == "The human's own sentence."
    assert report["chapters"][0]["conflict"] is True


def test_no_conflict_when_the_base_is_unchanged(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    apply_composer_edits(bd, log=lambda *a: None)
    record_edit(
        bd,
        chapter_key="on knowledge",
        body_md="The human's own sentence.",
        base_fingerprint=base_fingerprint_for(bd, "on knowledge"),
    )
    report = apply_composer_edits(bd, log=lambda *a: None, force=True)
    assert report["applied"] == 1 and report["conflicts"] == 0


def test_a_fingerprint_from_before_the_stamp_never_fires_a_conflict(tmp_path: Path) -> None:
    """An edit saved by the retired TS hash carries a number from another
    computation. Comparing across two computations is what made this signal
    meaningless; an unknown is reported as no conflict, and the honest current
    value is stamped so the NEXT compose can tell.
    """
    bd = _book(tmp_path)
    record_edit(
        bd,
        chapter_key="on knowledge",
        body_md="The human's own sentence.",
        base_fingerprint="7f2f42eac1f48af6",  # the shape the deleted TS hash wrote
    )
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["conflicts"] == 0
    assert base_fingerprint_for(bd, "on knowledge") != "7f2f42eac1f48af6"
    assert base_fingerprint_for(bd, "on knowledge") == fingerprint("Pipeline prose for one.")


# ─── the stamp: one number, produced once, quoted by both sides ───────────────
def test_stamp_is_written_for_every_chapter_even_with_no_edits(tmp_path: Path) -> None:
    # A chapter nobody has edited is exactly the one somebody edits next, and the
    # Composer needs a number to quote for it.
    bd = _book(tmp_path)
    apply_composer_edits(bd, log=lambda *a: None)
    stamp = load_base_stamp(bd)
    assert set(stamp) == {"on knowledge", "on patience"}
    assert base_fingerprint_for(bd, "on patience") == fingerprint("Pipeline prose for two.")


def test_the_normal_path_never_manufactures_a_conflict(tmp_path: Path) -> None:
    """The regression this whole change exists for.

    An edited chapter is not regenerated, so the text sitting under its heading at
    replay time is the author's own — fingerprinting THAT and comparing it to the
    stamp would compare the edit against itself and report a conflict on every
    single compose, which is what shipped until 2026-07-21.
    """
    bd = _book(tmp_path)
    apply_composer_edits(bd, log=lambda *a: None)  # compose 1: stamps the base
    record_edit(
        bd,
        chapter_key="on knowledge",
        body_md="The human's own sentence.",
        base_fingerprint=base_fingerprint_for(bd, "on knowledge"),
    )
    # Compose 2: the chapter is skipped upstream, so its body is already the
    # human's text by the time replay sees it.
    (bd / "book" / "book.md").write_text(
        "# The Book\n\n## 1. On Knowledge\n\nThe human's own sentence.\n\n## 2. On Patience\n\nPipeline prose for two.\n",
        encoding="utf-8",
    )
    report = apply_composer_edits(bd, log=lambda *a: None)
    assert report["applied"] == 1 and report["conflicts"] == 0
    # ...and it stays quiet however many times the loop re-enters compose.
    assert apply_composer_edits(bd, log=lambda *a: None)["conflicts"] == 0


def test_skipped_chapter_carries_its_stamp_forward(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    apply_composer_edits(bd, log=lambda *a: None)
    original = base_fingerprint_for(bd, "on knowledge")
    record_edit(bd, chapter_key="on knowledge", body_md="Wholly different words.", base_fingerprint=original)
    apply_composer_edits(bd, log=lambda *a: None)
    assert base_fingerprint_for(bd, "on knowledge") == original


# ─── the sidecar must survive its own failure modes ──────────────────────────
def test_record_edit_refuses_to_overwrite_an_unreadable_sidecar(tmp_path: Path) -> None:
    # Returning "no edits" here and writing that back is how one truncated file
    # used to discard every edit the author had ever made.
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="worth keeping")
    (bd / "_system" / "composer-edits.json").write_text('{"edits": [{"chap', encoding="utf-8")
    with pytest.raises(SidecarUnreadable):
        record_edit(bd, chapter_key="on patience", body_md="new")
    # The damaged file is left exactly as found, for a human to recover from.
    assert (bd / "_system" / "composer-edits.json").read_text(encoding="utf-8") == '{"edits": [{"chap'


def test_sidecar_writes_are_atomic(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="x")
    assert not list((bd / "_system").glob("*.tmp"))


# ─── what the compose stages ask before spending a model call ────────────────
def test_edited_chapters_are_discoverable_by_the_compose_stages(tmp_path: Path) -> None:
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="The human's own sentence.")
    assert edited_chapter_keys(bd) == {"on knowledge"}
    assert edited_body(bd, "on knowledge") == "The human's own sentence."
    assert edited_body(bd, "on patience") is None


def test_an_empty_edit_body_reads_as_no_edit(tmp_path: Path) -> None:
    # Same reason replay refuses to apply one: it would wipe the chapter, and the
    # ship gate counts headings rather than prose, so nothing would notice.
    bd = _book(tmp_path)
    record_edit(bd, chapter_key="on knowledge", body_md="   \n ")
    assert edited_body(bd, "on knowledge") is None


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
