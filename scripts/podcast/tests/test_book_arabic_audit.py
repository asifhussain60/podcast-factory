"""Arabic provenance in the companion book lane.

Covers the identity question the count-based gates cannot answer: is each Arabic
run in the composed edition the source's own words, or the model's recall?
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _arabic_coverage import arabic_span_is_grounded, normalize_arabic
from _book_arabic_audit import (
    RESOLUTION_HONORIFIC,
    RESOLUTION_KB,
    RESOLUTION_OCR,
    RESOLUTION_UNVERIFIED,
    audit_book_arabic,
    run_arabic_audit,
    split_chapters,
)

# A saying as the OCR of the source page renders it — fully vowelled, with the
# connective particle the printed edition carries.
SOURCE_SAYING = "فأما شكر العالم فطاعته وشكر العلم العمل به"
# The same saying re-set with vowel points and spelling variants: same words.
SAME_SAYING_RESET = "فَأَمَّا شُكْرُ الْعَالِمِ فَطَاعَتُهُ وَشُكْرُ الْعِلْمِ الْعَمَلُ بِهِ"
# A different saying entirely — the fabrication case.
FOREIGN_SAYING = "حسبنا الله ونعم الوكيل نعم المولى ونعم النصير"


def test_normalize_folds_vowels_and_spelling_but_not_words() -> None:
    assert normalize_arabic(SOURCE_SAYING) == normalize_arabic(SAME_SAYING_RESET)
    assert normalize_arabic(SOURCE_SAYING) != normalize_arabic(FOREIGN_SAYING)


def test_grounded_run_is_recognized_through_vowelling() -> None:
    assert arabic_span_is_grounded(SAME_SAYING_RESET, f"page text\n{SOURCE_SAYING}\nmore text")


def test_run_absent_from_the_source_is_not_grounded() -> None:
    assert not arabic_span_is_grounded(FOREIGN_SAYING, SOURCE_SAYING)


@pytest.mark.parametrize("span", ["", "   ", "no arabic here"])
def test_empty_or_latin_spans_are_never_grounded(span: str) -> None:
    assert not arabic_span_is_grounded(span, SOURCE_SAYING)


def test_split_chapters_separates_front_matter_from_chapters() -> None:
    md = "# Book\n\npreface prose\n\n## One\n\nbody one\n\n## Two\n\nbody two\n"
    titles = [t for t, _ in split_chapters(md)]
    assert titles == ["(front matter)", "One", "Two"]


def test_audit_reports_resolution_per_chapter() -> None:
    md = f"## Grounded\n\n> {SAME_SAYING_RESET}\n\n## Invented\n\n> {FOREIGN_SAYING}\n"
    report = audit_book_arabic(md, SOURCE_SAYING, kb_arabic="")
    by_title = {c["chapter"]: c for c in report["chapters"]}
    assert by_title["Grounded"]["runs"][0]["resolution"] == RESOLUTION_OCR
    assert by_title["Invented"]["runs"][0]["resolution"] == RESOLUTION_UNVERIFIED
    assert by_title["Invented"]["unverified"] == 1
    assert report["totals"]["arabic_runs"] == 2


def test_knowledge_base_resolves_what_the_source_pages_do_not() -> None:
    md = f"## Quoting elsewhere\n\n> {FOREIGN_SAYING}\n"
    report = audit_book_arabic(md, SOURCE_SAYING, kb_arabic=FOREIGN_SAYING)
    assert report["chapters"][0]["runs"][0]["resolution"] == RESOLUTION_KB
    assert report["totals"][RESOLUTION_UNVERIFIED] == 0


def test_a_standard_honorific_formula_is_not_flagged_unverified() -> None:
    """The false positive found live 2026-07-19 on the-master-and-the-disciple:
    'عليهم السلام' ('peace be upon them') is the author's own liturgical
    practice, not a quoted source — it needs no grounding any more than an
    English writer's 'may he rest in peace' needs a citation."""
    md = "## Prophets\n\nAbraham and Ishmael and Isaac (عليهم السلام) were favoured.\n"
    report = audit_book_arabic(md, arabic_src="", kb_arabic="")
    assert report["chapters"][0]["runs"][0]["resolution"] == RESOLUTION_HONORIFIC
    assert report["totals"][RESOLUTION_UNVERIFIED] == 0


def test_a_diacritic_variant_of_an_honorific_still_matches() -> None:
    """Matched by the same normalized skeleton as every other resolution tier —
    a fully-vowelled or lightly-spelled variant of the same formula is one
    formula, not two different unverified runs."""
    md = "## Prophets\n\nMentioned (عَلَيْهِ السَّلَام) in the text.\n"
    report = audit_book_arabic(md, arabic_src="", kb_arabic="")
    assert report["chapters"][0]["runs"][0]["resolution"] == RESOLUTION_HONORIFIC


def test_a_genuine_quotation_is_never_mistaken_for_an_honorific() -> None:
    """The honorific allowlist must not become a loophole — a real quotation
    (even a short, well-known one) that happens to share no words with the
    allowlist still falls through to unverified when ungrounded."""
    md = f"## Elsewhere\n\n> {FOREIGN_SAYING}\n"
    report = audit_book_arabic(md, arabic_src="", kb_arabic="")
    assert report["chapters"][0]["runs"][0]["resolution"] == RESOLUTION_UNVERIFIED


def test_run_arabic_audit_writes_a_report_beside_the_book(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system" / "source" / "ocr").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(f"## One\n\n> {SAME_SAYING_RESET}\n", encoding="utf-8")
    (bd / "_system" / "source" / "ocr" / "raw-extract.md").write_text(SOURCE_SAYING, encoding="utf-8")

    report = run_arabic_audit(bd, log=lambda *a: None)

    written = json.loads((bd / "_system" / "book-arabic-audit.json").read_text(encoding="utf-8"))
    assert written == report
    assert report["totals"][RESOLUTION_OCR] == 1


def test_audit_without_ocr_ground_truth_says_so(tmp_path: Path) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(f"## One\n\n> {FOREIGN_SAYING}\n", encoding="utf-8")

    report = run_arabic_audit(bd, log=lambda *a: None)

    assert "no OCR ground truth" in report["note"]
    assert report["totals"][RESOLUTION_UNVERIFIED] == 1


def test_stage_losses_name_the_stage_that_dropped_a_quotation() -> None:
    from _book_arabic_audit import stage_losses

    stages = {
        "base": {"One": 16, "Two": 7},
        "augment": {"One": 16, "Two": 7},
        "voice": {"One": 4, "Two": 7},
        "final": {"One": 4, "Two": 7},
    }

    losses = stage_losses(stages)

    assert losses == [{"chapter": "One", "stage": "voice", "before": 16, "after": 4}]


def test_no_loss_reports_nothing() -> None:
    from _book_arabic_audit import stage_losses

    assert stage_losses({"base": {"One": 5}, "final": {"One": 5}}) == []


def test_stage_counts_reads_the_book_as_it_stands(tmp_path: Path) -> None:
    from _book_arabic_audit import stage_counts

    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(f"## One\n\n> {SAME_SAYING_RESET}\n\n## Two\n\nno arabic\n", encoding="utf-8")

    assert stage_counts(bd) == {"One": 1, "Two": 0}


def test_missing_book_is_not_an_error(tmp_path: Path) -> None:
    assert run_arabic_audit(tmp_path, log=lambda *a: None) == {}
