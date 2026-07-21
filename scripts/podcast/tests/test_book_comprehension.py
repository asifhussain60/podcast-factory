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


def test_a_glossary_entry_the_book_never_prints_is_not_drift() -> None:
    """The false positive this check exists to avoid: nāṭiq/natiq fold to the SAME
    printed form (BK-A4 plain transliteration), so only "natiq" ever reaches the
    page. Flagging that as "two spellings" would be reporting on the glossary,
    not on the book — this is the exact bug found reviewing the real edition."""
    drift = naming_drift(pages("the natiq and the natiq again"), ["nāṭiq", "natiq"])
    assert drift == []


def test_two_spellings_actually_printed_in_the_book_is_real_drift() -> None:
    """The genuine case: the compose pass printed the term hyphenated in one place
    and closed-up in another. Both survive the transliteration fold unchanged and
    share a skeleton, so both reaching the page is a real inconsistency."""
    drift = naming_drift(pages("the al-Din chapter", "here alDin is invoked"), ["al-Din", "alDin"])
    assert drift and set(drift[0]["variants"]) == {"al-din", "aldin"}


def test_the_apostrophe_variant_is_prevented_rather_than_reported() -> None:
    """Sharia / Shari'a was the live 2026-07-19 drift pair, and it can no longer
    reach the page at all: `simplify_transliteration` now drops an ayn/hamza
    apostrophe outright (it is kept only for an English contraction), so BOTH
    glossary spellings fold to the single printed form "sharia". Reporting drift
    here would be reporting on the glossary, not on the book — the same false
    positive `test_a_glossary_entry_the_book_never_prints_is_not_drift` guards.
    The class of defect moved from detected to impossible; this test is what
    would fail if that fold were ever loosened again."""
    for stored in ("Shari'a", "Shariʿa"):
        drift = naming_drift(
            pages("the Sharia governs this", f"and here {stored} is invoked too"),
            ["Sharia", stored],
        )
        assert drift == [], f"{stored!r} should fold onto 'sharia', not drift"


def test_folding_still_does_not_invent_drift_the_page_never_printed() -> None:
    """A glossary entry stored with a diacritic whose plain form the book never
    actually prints must still not be flagged — folding changes WHAT is searched
    for, not whether a real match is required."""
    drift = naming_drift(pages("only the natiq appears here"), ["natiq", "Shariʿa"])
    assert drift == []


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


def test_a_name_reveal_explains_backwards_and_is_still_recognized() -> None:
    """ "his father's name was al-Bakhtari" — the cue PRECEDES the term. Found
    reviewing the real book: the old forward-only window missed this and reported
    a false gap two chapters deep, when the character is introduced on the spot."""
    assert explanation_page(pages("his father's name was al-bakhtari and they lived well"), "al-bakhtari") == 1


def test_a_preceding_cue_still_requires_the_same_clause() -> None:
    """The short backward window must not become the old unbounded-window bug in
    reverse — a cue several sentences earlier still explains nothing."""
    far = "is the pillar of prayer. " + "filler word " * 20 + "he then invoked batin."
    assert explanation_page(pages(far), "batin") is None


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
    assert report["summary"] == {"never_explained": 0, "explained_late": 1, "referent_collisions": 0}
    assert set(report) >= {
        "prerequisite_gaps",
        "naming_drift",
        "dense_pages",
        "long_sentences",
        "referent_collisions",
    }


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


# ─── the delivered PDF carries the book's name ───────────────────────────────
def test_the_supplication_lane_writes_a_titled_copy(tmp_path: Path) -> None:
    """The artifact a human receives carries the work's name, not its folder id."""
    sys.path.insert(0, str(SCRIPT_DIR / "supplication"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("_sup_driver", SCRIPT_DIR / "supplication" / "driver.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    pdf = tmp_path / "dua-kumayl.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    titled = module._titled_copy(pdf, "Dua Kumayl")

    assert titled is not None and titled.name == "Dua Kumayl.pdf"
    assert titled.read_bytes() == pdf.read_bytes()
    assert pdf.exists(), "the slug-named file stays for pipeline compatibility"


def test_a_title_that_would_escape_the_folder_is_flattened(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("_sup_driver2", SCRIPT_DIR / "supplication" / "driver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")

    titled = module._titled_copy(pdf, "../../etc/passwd")

    assert titled is not None and titled.parent == tmp_path


def test_an_untitled_work_gets_no_copy(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("_sup_driver3", SCRIPT_DIR / "supplication" / "driver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")

    assert module._titled_copy(pdf, "") is None


def test_front_matter_listing_is_not_a_first_use() -> None:
    # The Contents names a chapter title and the crosswalk prints eight of them,
    # both before the book has defined anything. Counting those as first use
    # produced an explained-late gap on two consecutive renders, each one a
    # heuristic artifact a human had to read the PDF to dismiss.
    from _book_comprehension import body_start_page, prerequisite_gaps

    pages = [
        "Title page",
        "Contents\n1. The Long Road to the Shaykh",
        "Source Crosswalk\nThe Long Road to the Shaykh",
        "The boy travelled far to reach the Shaykh, and the Shaykh received him.",
        "The Shaykh is the elder who tests a seeker before teaching him.",
        "The Shaykh spoke again, and the boy listened.",
    ]

    assert body_start_page(pages) == 4
    assert prerequisite_gaps(pages, ["Shaykh"]) == []


def test_a_book_with_no_front_matter_starts_at_page_one() -> None:
    from _book_comprehension import body_start_page

    assert body_start_page(["Chapter one begins here.", "and continues."]) == 1


def test_a_role_word_pointing_at_two_people_is_reported() -> None:
    # The defect a human found by reading: on one page the boy asks for "my
    # father" (the Master) to be sent with him, and the Shaykh charges him with
    # "your father, who raised you when you were small" (al-Bakhtari). Two men,
    # one word, nothing on the page to tell them apart.
    from _book_comprehension import referent_collisions

    pages = [
        "Contents\n1. A Chapter",
        "Ordinary prose with no role words in it at all.",
        'He said, "send my father along with me", and was told to keep your father in mind.',
        "Again: my father would counsel this, yet your father raised you when you were small.",
    ]

    findings = referent_collisions(pages)

    assert [f["role_word"] for f in findings] == ["father"]
    assert findings[0]["pages"] == [3, 4]
    assert findings[0]["first_page"] == 3


def test_two_vantages_on_the_same_man_are_not_a_collision() -> None:
    # A boy is "my son" to his father and "his son" to the narrator. Counting any
    # two frames cried wolf on exactly this, which is why the rule needs a
    # first-person AND a second-person frame.
    from _book_comprehension import referent_collisions

    pages = [
        "Body opens here.",
        'The father said, "my son, hear me." His son heard him.',
        'Again the father said, "my son". His son listened.',
    ]

    assert referent_collisions(pages) == []


def test_one_colliding_page_is_not_enough() -> None:
    from _book_comprehension import referent_collisions

    assert referent_collisions(["Body.", "my father and your father", "nothing here"]) == []
