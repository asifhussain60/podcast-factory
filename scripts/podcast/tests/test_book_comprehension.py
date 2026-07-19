"""Can a reader follow the book? — the deterministic half.

The judgment belongs to the reviewing agent; these tests pin the evidence it
reads, above all the one comparison that makes the whole check work: the book's
plain transliteration against the glossary's scholarly diacritics.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_comprehension import (  # noqa: E402
    _is_concept,
    analyze,
    explanation_page,
    glossary_terms,
    naming_drift,
    prerequisite_gaps,
    term_pages,
)


def pages(*texts: str) -> list[str]:
    return list(texts)


# ─── the fold that makes any of this work ────────────────────────────────────
def test_a_diacritic_glossary_term_matches_the_books_plain_spelling() -> None:
    """The glossary stores nāṭiq; the printed book prints natiq. They are one term."""
    assert term_pages(pages("the natiq speaks for his age"), "nāṭiq") == [1]


def test_naming_drift_sees_the_two_spellings_as_one_idea() -> None:
    drift = naming_drift(pages("the natiq and the natiq again"), ["nāṭiq", "natiq"])
    assert drift and set(drift[0]["variants"]) == {"natiq", "nāṭiq"}


# ─── what counts as a concept ────────────────────────────────────────────────
def test_name_particles_and_multiword_names_are_not_concepts() -> None:
    assert not _is_concept("ibn")
    assert not _is_concept("Ja'far ibn Mansur al-Yaman")
    assert not _is_concept("al")


def test_a_single_word_idea_is_a_concept() -> None:
    assert _is_concept("batin")
    assert _is_concept("nāṭiq")


def test_glossary_terms_reads_the_books_own_glossary(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "glossary.yml").write_text(
        "entries:\n- phonetic: batin\n- phonetic: ibn\n- phonetic: Ja'far ibn Mansur\n", encoding="utf-8"
    )
    assert glossary_terms(bd) == ["batin"]


def test_a_missing_glossary_is_not_an_error(tmp_path: Path) -> None:
    assert glossary_terms(tmp_path) == []


# ─── explanation detection ───────────────────────────────────────────────────
def test_an_explanation_trailing_the_term_is_recognized() -> None:
    assert explanation_page(pages("the batin is the inner meaning of the law"), "batin") == 1


def test_a_cue_before_the_term_does_not_count_as_explaining_it() -> None:
    """'is the' in the previous clause belongs to another sentence entirely."""
    assert explanation_page(pages("prayer is the pillar. He then invoked batin."), "batin") is None


def test_a_term_the_book_never_explains_returns_nothing() -> None:
    assert explanation_page(pages("batin. batin. batin."), "batin") is None


# ─── prerequisite gaps ───────────────────────────────────────────────────────
def test_a_term_explained_pages_after_it_is_used_is_a_gap() -> None:
    p = pages("we begin with the natiq", "the natiq again", "more natiq", "the natiq is the speaking prophet")

    gaps = prerequisite_gaps(p, ["natiq"])

    assert gaps[0]["term"] == "natiq"
    assert gaps[0]["first_use_page"] == 1
    assert gaps[0]["explained_page"] == 4
    assert gaps[0]["kind"] == "explained-late"


def test_a_term_explained_where_it_first_lands_is_not_a_gap() -> None:
    p = pages("the natiq is the speaking prophet", "the natiq again", "more natiq")
    assert prerequisite_gaps(p, ["natiq"]) == []


def test_a_term_used_once_or_twice_is_incidental_not_a_gap() -> None:
    assert prerequisite_gaps(pages("a natiq", "nothing", "natiq"), ["natiq"]) == []


def test_a_term_the_book_leans_on_but_never_explains_is_the_worst_case() -> None:
    p = pages("natiq here", "natiq there", "natiq everywhere")
    gaps = prerequisite_gaps(p, ["natiq"])
    assert gaps[0]["kind"] == "never-explained"
    assert gaps[0]["explained_page"] is None


def test_gaps_are_ordered_worst_first() -> None:
    p = pages(
        "the hujja and the natiq begin",
        "hujja natiq",
        "hujja natiq",
        "the hujja is the proof",
        "natiq",
        "the natiq is the speaking prophet",
    )
    gaps = prerequisite_gaps(p, ["hujja", "natiq"])
    assert [g["term"] for g in gaps] == ["natiq", "hujja"], "the longer carry comes first"


# ─── the assembled report ────────────────────────────────────────────────────
def test_analyze_reports_every_lens_and_a_summary() -> None:
    p = pages("the natiq begins", "natiq", "natiq", "the natiq is the speaking prophet")

    report = analyze(p, ["natiq"])

    assert report["pages"] == 4
    assert report["terms_tracked"] == 1
    assert report["summary"] == {"never_explained": 0, "explained_late": 1}
    assert set(report) >= {"prerequisite_gaps", "naming_drift", "dense_pages", "long_sentences"}


def test_a_very_long_sentence_is_surfaced_for_review() -> None:
    report = analyze(pages(" ".join(["word"] * 60) + "."), [])
    assert report["long_sentences"] and report["long_sentences"][0]["words"] >= 45


# ─── wired as the final step of every PDF route ──────────────────────────────
def test_a_route_with_no_pdf_yet_reports_nothing_rather_than_failing(tmp_path: Path) -> None:
    from _book_comprehension import run_comprehension_checks

    assert run_comprehension_checks(tmp_path, log=lambda *a: None) == {}


def test_a_route_can_name_its_own_pdf(tmp_path: Path) -> None:
    """The supplication lane writes book/<slug>.pdf, not book/book.pdf."""
    from _book_comprehension import run_comprehension_checks

    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    named = bd / "book" / "ziyarat.pdf"

    # Absent file: the named path is what gets checked, not the lane default.
    assert run_comprehension_checks(bd, log=lambda *a: None, pdf=named) == {}


def test_every_pdf_route_ends_with_the_review() -> None:
    """The wiring itself — a route that stops calling this stops being reviewed."""
    book_route = (SCRIPT_DIR / "build_book_pdf.py").read_text(encoding="utf-8")
    supplication_route = (SCRIPT_DIR / "supplication" / "driver.py").read_text(encoding="utf-8")

    assert "_final_comprehension_review" in book_route
    assert "_final_comprehension_review" in supplication_route
    # The fiction builder deliberately delegates to build_book rather than
    # duplicating the render plumbing, so it inherits the review.
    assert "from build_book_pdf import build_book" in (SCRIPT_DIR / "build_fiction_book_pdf.py").read_text("utf-8")
