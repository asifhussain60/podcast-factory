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


# ── Chapter grouping ────────────────────────────────────────────────────────
def test_iter_chapters_folds_source_subsections_into_the_chapter() -> None:
    text = (
        "# Book\n\n## First Thing\n\nPreface body.\n\n"
        "## 1. Real Chapter\n\nChapter body.\n\n## An Internal Section\n\nMore body.\n\n"
        "## 2. Second Chapter\n\nSecond body.\n"
    )
    pre, chapters = S._iter_chapters(text)
    # preface (first heading) + two numbered chapters == 3 chapters; the unnumbered
    # "An Internal Section" is folded into chapter 1's body, not a 4th chapter.
    assert len(chapters) == 3
    assert "An Internal Section" in chapters[1][1]
    assert "# Book" in pre


# ── Sub-headings (Step 6) ───────────────────────────────────────────────────
def test_insert_subheadings_matches_anchor_and_skips_misses(monkeypatch) -> None:
    body = "Opening paragraph one.\n\nThe seeker walks the road at dawn.\n\nA third paragraph here."
    out = S._insert_subheadings(
        body,
        [("On the Road", "The seeker walks the road"),      # matches para 2
         ("Nowhere", "this phrase is absent entirely")],     # no match -> skipped
        log=lambda *a: None, title="X")
    assert "## On the Road\n\nThe seeker walks the road at dawn." in out
    assert "## Nowhere" not in out
    # never anchors the first paragraph
    assert not out.lstrip().startswith("## ")


def test_long_chapter_gets_ai_subheadings(tmp_path, monkeypatch) -> None:
    long_body = "Intro paragraph that opens the chapter.\n\n" + \
        "\n\n".join(f"Paragraph number {i} with enough words to build length here in the chapter body flow." for i in range(80))
    bd = _book(tmp_path, f"# Book\n\n## 1. Long Chapter\n\n{long_body}\n")
    monkeypatch.setattr(S, "_generate_summary", lambda *a, **k: "A faithful summary long enough to pass the gate cleanly for the reader.")
    monkeypatch.setattr(S, "_generate_enrichment", lambda *a, **k: "")
    monkeypatch.setattr(S, "_generate_subheadings",
                        lambda title, body, book_dir, log: [("A Midpoint", "Paragraph number 40 with enough words")])
    md = S.build_self_study_markdown(bd, log=lambda *a: None).read_text()
    assert "## A Midpoint" in md


def test_short_chapter_gets_no_ai_subheadings(tmp_path, monkeypatch) -> None:
    bd = _book(tmp_path)  # short chapters, below the word threshold
    called = {"n": 0}
    monkeypatch.setattr(S, "_generate_summary", lambda *a, **k: "A faithful summary long enough to pass the gate cleanly for the reader.")
    monkeypatch.setattr(S, "_generate_enrichment", lambda *a, **k: "")
    def _boom(*a, **k):
        called["n"] += 1
        return []
    monkeypatch.setattr(S, "_generate_subheadings", _boom)
    S.build_self_study_markdown(bd, log=lambda *a: None, with_term_defs=False)
    assert called["n"] == 0  # never invoked for short chapters


# ── Inline term definitions (Step 3) ────────────────────────────────────────
def test_is_plain_prose_line_excludes_non_prose() -> None:
    assert S._is_plain_prose_line("The concept of tawhid is central.")
    assert not S._is_plain_prose_line("> a blockquote")
    assert not S._is_plain_prose_line("## a heading")
    assert not S._is_plain_prose_line("- a list item")
    assert not S._is_plain_prose_line("لا إله إلا الله")   # Arabic script line
    assert not S._is_plain_prose_line("<!-- editorial:begin -->")


def test_term_definition_inlined_at_first_use_only(monkeypatch) -> None:
    text = "The idea of tawhid matters here.\n\nLater tawhid returns again.\n\n> tawhid in a quote."
    monkeypatch.setattr(S, "_glossary_terms", lambda bd: ["tawhid"])
    monkeypatch.setattr(S, "_generate_term_defs", lambda items, bd, log: {"tawhid": "divine oneness"})
    out, n = S._apply_term_definitions(text, Path("."), lambda *a: None)
    assert n == 1
    assert "tawhid (divine oneness) matters" in out       # first prose use glossed
    assert out.count("(divine oneness)") == 1             # dedup: only once
    assert "> tawhid in a quote." in out                  # never touches the blockquote


def test_term_definition_respects_skip(monkeypatch) -> None:
    text = "Imam Ghazali wrote about tawhid at length."
    monkeypatch.setattr(S, "_glossary_terms", lambda bd: ["Ghazali", "tawhid"])
    # the model SKIPs the proper name (returned as absent), defines the concept
    monkeypatch.setattr(S, "_generate_term_defs", lambda items, bd, log: {"tawhid": "divine oneness"})
    out, n = S._apply_term_definitions(text, Path("."), lambda *a: None)
    assert n == 1
    assert "Ghazali (" not in out
    assert "tawhid (divine oneness)" in out
