from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _self_study as S  # noqa: E402


BOOK = """# The Book

## 1. First Chapter

Body of the first chapter, which teaches patience and sincerity at length.

## 2. Second Chapter

Body of the second chapter, on gratitude and its outward turning.
"""


def _book(tmp_path: Path, md: str = BOOK) -> Path:
    bd = tmp_path / "bd"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(md, encoding="utf-8")
    return bd


# ── Study-summary block contract ────────────────────────────────────────────
def test_format_summary_block_is_labeled_and_fenced() -> None:
    blk = S.format_summary_block("The chapter's key teaching in one faithful line.")
    assert blk.startswith(S._SUMMARY_OPEN) and blk.rstrip().endswith(S._SUMMARY_CLOSE)
    assert f"**{S.SUMMARY_LABEL}.**" in blk


def test_gate_summary_accepts_a_clean_summary() -> None:
    ok, reasons = S.gate_summary(
        "Worship is inward surrender, not outward motion, and its measure is the "
        "truthfulness of the heart rather than the length of the act.")
    assert ok, reasons


def test_gate_summary_rejects_empty_none_meta_and_markup() -> None:
    assert not S.gate_summary("")[0]
    assert not S.gate_summary("NONE")[0]
    assert not S.gate_summary("In this chapter the author explains several points about the heart.")[0]
    assert not S.gate_summary("# A heading masquerading as a summary that is long enough to pass length")[0]


# ── Materialization ─────────────────────────────────────────────────────────
def test_build_self_study_injects_labeled_blocks_without_touching_base(tmp_path, monkeypatch) -> None:
    bd = _book(tmp_path)
    monkeypatch.setattr(S, "_generate_summary",
                        lambda title, ct, book_dir, label, log: f"A faithful summary of {title} stating its key teaching plainly and at sufficient length to pass.")
    monkeypatch.setattr(S, "_generate_enrichment",
                        lambda title, ct, atoms, book_dir, label, log: f"A grounding note for {title} that connects it to the wider tradition of the sources.")
    out = S.build_self_study_markdown(bd, log=lambda *a: None)
    md = out.read_text(encoding="utf-8")
    assert out.name == "book-self-study.md"
    assert md.count(S._SUMMARY_OPEN) == 2      # one per chapter
    assert md.count("<!-- editorial:begin -->") == 2
    # base book.md is never mutated
    assert ":begin -->" not in (bd / "book" / "book.md").read_text(encoding="utf-8")


def test_build_self_study_is_idempotent(tmp_path, monkeypatch) -> None:
    bd = _book(tmp_path)
    monkeypatch.setattr(S, "_generate_summary",
                        lambda *a, **k: "A faithful summary that states the chapter's essentials plainly and is quite long enough to pass the gate.")
    monkeypatch.setattr(S, "_generate_enrichment", lambda *a, **k: "")  # notes off
    first = S.build_self_study_markdown(bd, log=lambda *a: None).read_text()
    second = S.build_self_study_markdown(bd, log=lambda *a: None).read_text()
    assert first.count(S._SUMMARY_OPEN) == 2
    assert first == second  # regenerating from the clean base is stable


def test_dropped_summary_is_not_inserted(tmp_path, monkeypatch) -> None:
    bd = _book(tmp_path)
    monkeypatch.setattr(S, "_generate_summary", lambda *a, **k: "NONE")  # nothing to summarize
    monkeypatch.setattr(S, "_generate_enrichment", lambda *a, **k: "")
    md = S.build_self_study_markdown(bd, log=lambda *a: None).read_text()
    assert S._SUMMARY_OPEN not in md
