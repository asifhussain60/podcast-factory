"""Glossed-term harvesting, and the terms that reach the page with no script.

Every case is drawn from what the five live editions actually printed on
2026-08-03, when Asif read `al-anwaar-al-lateefah` and asked why the page said
`marifah` instead of Arabic. The harvester had found ONE candidate in a book that
italicises 261 distinct terms, because it only ever looked inside parentheses —
and the articulation pass writes the other shape.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _gloss_terms import (  # noqa: E402
    bare_term_findings,
    gloss_candidates,
    normalize_term,
    scripted_terms,
)

REPO = Path(__file__).resolve().parents[3]
LIVE_BOOKS = (
    "the-master-and-the-disciple",
    "degrees-of-excellence",
    "ayyuhal-walad",
    "asaas-al-taveel/vol-01",
    "al-anwaar-al-lateefah/vol-01",
)


def _terms(rows) -> set[str]:
    return {normalize_term(r["term"]) for r in rows}


# ─── The shape the articulation pass writes ─────────────────────────────────
def test_emphasis_gloss_is_a_candidate() -> None:
    """`the *marifah* — the gnosis` is a gloss, exactly as `the gnosis (marifah)` is."""
    assert "marifah" in _terms(gloss_candidates("It is through the *marifah* — the gnosis — of all things."))


def test_parenthetical_gloss_still_works() -> None:
    assert "hudud" in _terms(gloss_candidates("adherence to their ranks (hudud) as appointed."))


def test_a_term_found_both_ways_is_counted_once() -> None:
    rows = gloss_candidates("The *wilayah* is the bond. Allegiance (wilayah) is the first pillar.")
    hits = [r for r in rows if normalize_term(r["term"]) == "wilayah"]
    assert len(hits) == 1 and hits[0]["count"] == 2


def test_bold_is_emphasis_not_a_foreign_word() -> None:
    assert _terms(gloss_candidates("This is **important** and nothing else.")) == set()


def test_arabic_script_in_emphasis_is_not_a_romanization() -> None:
    assert _terms(gloss_candidates("The line reads *الفصل الأول* here.")) == set()


# ─── The finding: italicised as foreign, never once in script ───────────────
BARE = "It is through the *marifah* — the gnosis — that the road opens, and through *muwalat* also."
SCRIPTED = "It is through the *marifah* (مَعْرِفَة) — the gnosis — that the road opens."


def test_a_term_never_given_in_script_is_reported() -> None:
    found = {r["term"] for r in bare_term_findings(BARE)}
    assert found == {"marifah", "muwalat"}


def test_one_annotation_anywhere_in_the_book_clears_the_term() -> None:
    """The annotation policy introduces a term ONCE per book — that is enough."""
    assert bare_term_findings(SCRIPTED + "\n\nAnd the *marifah* again, and again.") == []


def test_uses_are_counted_so_the_worst_offender_sorts_first() -> None:
    text = "*shariah* here. *shariah* again. *shariah* once more. And *halal* once."
    rows = bare_term_findings(text)
    assert [r["term"] for r in rows] == ["shariah", "halal"]
    assert rows[0]["uses"] == 3


def test_a_work_title_is_not_a_missing_annotation() -> None:
    """`*Kitab al-Anwar*` is a title. A title wants no script beside it."""
    assert bare_term_findings("as *Kitab al-Anwar* records, and *Ihya Ulum al-Din* too.") == []


def test_english_in_italics_is_not_a_missing_annotation() -> None:
    """The gloss half of a pair, and ordinary emphasis, are not Arabic terms."""
    text = "the *batin*, the *inner*; the *zahir*, the *outer*; a *tradition-grounded* claim about *light*."
    assert {r["term"] for r in bare_term_findings(text)} == {"batin", "zahir"}


def test_scripted_terms_reads_every_annotation_shape() -> None:
    have = scripted_terms("the *amal* (عَمَل) and the hudud (حُدُود) and *wilayah* (وِلَايَة, allegiance)")
    assert {"amal", "hudud", "wilayah"} <= have


# ─── The live corpus ────────────────────────────────────────────────────────
def test_no_shipped_edition_regresses_past_its_recorded_bare_count() -> None:
    """A ratchet, not a clean sheet.

    These books have real gaps today — 219 terms on `al-anwaar` alone — and the
    honest guard is one that cannot get WORSE while they are being fixed. Lower
    each ceiling as a book is cured; a compose that reintroduces bare terms fails
    here instead of shipping a page the reader cannot look anything up in.
    """
    ceilings = {
        "the-master-and-the-disciple": 0,
        "degrees-of-excellence": 1,
        "ayyuhal-walad": 0,
        "asaas-al-taveel/vol-01": 6,
        # `al-anwaar-al-lateefah/vol-01` is absent ON PURPOSE. It is not a book
        # with a missing scan; it is 65 Urdu lectures transcribed from mp3, and
        # there is no Arabic page behind its vocabulary to be faithful to. It
        # declares `source_medium: audio_lecture` and REQ-BA-127 scopes itself
        # out — see `_pipeline_flags.source_medium`.
    }
    for slug in LIVE_BOOKS:
        book_dir = REPO / "content" / "Islamic" / slug
        # `al-anwaar` declares `source_medium: audio_lecture` — 65 Urdu lectures
        # transcribed from mp3, no printed Arabic anywhere — so REQ-BA-127 scopes
        # itself out and there is nothing here to ratchet.
        if slug not in ceilings:
            continue
        book_md = book_dir / "book" / "book.md"
        if not book_md.exists():  # the sample books are not in every checkout
            continue
        source = ""
        for rel in ("_system/source/text/refined-english.md", "_system/source/ocr/raw-extract.md"):
            path = book_dir / rel
            if path.exists():
                source += path.read_text(encoding="utf-8", errors="ignore")
        entries = []
        glossary = book_dir / "_system" / "glossary.yml"
        if glossary.exists():
            from _glossary_io import load_glossary

            entries = load_glossary(glossary)[0]
        found = bare_term_findings(book_md.read_text(encoding="utf-8"), source, entries)
        assert len(found) <= ceilings[slug], (
            f"{slug}: {len(found)} terms italicised as foreign but never given in Arabic script "
            f"(ceiling {ceilings[slug]}) — e.g. {', '.join(r['term'] for r in found[:6])}"
        )


def test_the_harvester_sees_what_the_articulated_books_actually_gloss() -> None:
    """The regression that let 239 bare terms ship: one candidate found in the
    whole of `al-anwaar`, because every gloss in it is an italic, not a paren."""
    book_md = REPO / "content" / "Islamic" / "al-anwaar-al-lateefah" / "vol-01" / "book" / "book.md"
    if not book_md.exists():
        return
    text = book_md.read_text(encoding="utf-8")
    assert len(gloss_candidates(text)) > 100
    # And the italic shape really is why: strip the emphasis markers and the
    # candidate list collapses to what the parenthetical scan alone could see.
    assert len(gloss_candidates(re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text))) < 40


def test_a_curated_familiar_or_silent_term_is_not_a_finding() -> None:
    """The annotation policy deciding is not a gap.

    `halal` is classified `familiar` — a recognized English form that takes no
    apparatus — and `hawiya` is `silent`. Reporting either argues with a curated
    decision, which on `ayyuhal-walad` was 3 of its 5 findings.
    """
    text = "the *halal* and the *hawiya* and the *marifah*."
    entries = [
        {"phonetic": "halal", "annotation_class": "familiar"},
        {"phonetic": "hawiya", "annotation_class": "silent"},
        {"phonetic": "marifah", "annotation_class": "teach"},
    ]
    assert {r["term"] for r in bare_term_findings(text, "", entries)} == {"marifah"}


def test_scripted_terms_is_linear_on_prose_without_brackets() -> None:
    """A backwards pattern here hung the whole suite.

    `((?:[A-Za-z][\\w\\-]*[ \\t]*\\*?[ \\t]*){1,4})\\(` nests two unbounded
    quantifiers, so on a long line with no parenthesis to anchor it the engine
    backtracks exponentially. The scan is forward-only now.
    """
    import time

    text = ("the master said that the boy replied that the scholar answered " * 400) + "\n"
    start = time.monotonic()
    scripted_terms(text)
    assert time.monotonic() - start < 1.0


def test_req_ba_127_scopes_itself_out_of_an_audio_sourced_book(tmp_path: Path) -> None:
    """A romanization is not a debt when no printed page stands behind it.

    `al-anwaar-al-lateefah` is 65 mp3 lectures recorded in Urdu, transcribed and
    translated — the pipeline never had the book. Its whole spine carries FORTY
    Arabic runs across 65 transcripts. With no `deliverable_mode` pinned it fell
    to the translation-edition default and was judged by rules written for a book
    rendered from a page: 189 romanized terms reported as a gap to close.
    """
    import yaml

    bd = tmp_path / "book_dir"
    (bd / "_system").mkdir(parents=True)
    text = "the *mawaddah* and the *zahir* and the *taweel*."

    (bd / "_system" / "series-config.yaml").write_text(
        yaml.safe_dump({"content_profile": "islamic_scholarly"}), encoding="utf-8"
    )
    assert len(bare_term_findings(text, "", [], bd)) == 3  # printed_text is the default

    (bd / "_system" / "series-config.yaml").write_text(
        yaml.safe_dump({"content_profile": "islamic_scholarly", "source_medium": "audio_lecture"}),
        encoding="utf-8",
    )
    assert bare_term_findings(text, "", [], bd) == []


def test_a_book_that_declares_nothing_is_still_judged() -> None:
    """Default IN scope: opting out has to be an act, and an unreadable config
    must never quietly disable a check."""
    from _gloss_terms import scoped_out_by_source

    assert scoped_out_by_source(None) is False
    assert scoped_out_by_source("/no/such/book") is False
