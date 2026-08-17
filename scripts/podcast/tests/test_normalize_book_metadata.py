#!/usr/bin/env python3
"""normalize_book_metadata.py — the rules that decide what a book is.

This script writes into `content/`, which is the pipeline's own data and the one
tree the audit contract marks protected. So the tests that matter most are not
the ones proving it writes; they are the ones proving what it REFUSES to write:

  * it never overwrites a value the book already states,
  * it never invents an author,
  * it never promotes the long title-page form into a card heading,
  * it never records a respelling as if it were a translation,

and that running it twice changes nothing the first run did not — which is what
makes it safe to leave in the pipeline rather than a one-off migration.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import normalize_book_metadata as nbm  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Folding — the difference between a translation and a respelling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b",
    [
        ("Mukhtasar ul Asar 2", "Mukhtasar-ul-Asaar 2"),  # the live case
        ("al-Nu'man", "al Numan"),
        ("Kitab al-Riyad", "kitab   al riyad"),
        ("Asaar", "Asar"),
    ],
)
def test_a_respelling_is_recognised(a: str, b: str) -> None:
    assert nbm._is_respelling(a, b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("The Book of Gardens", "Kitab al-Riyad"),  # a real translation
        ("O My Beloved Son", "Ayyuha al-Walad"),
        ("The Scholar and the Disciple", "The Master and the Disciple"),
    ],
)
def test_a_translation_is_not_mistaken_for_one(a: str, b: str) -> None:
    assert not nbm._is_respelling(a, b)


def test_a_missing_side_is_never_a_respelling() -> None:
    # Otherwise a book with no title recorded would silently lose its English
    # name to a comparison against nothing.
    assert not nbm._is_respelling("Anything", None)
    assert not nbm._is_respelling(None, "Anything")


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def make_book(tmp_path: Path, meta: dict, *, system: dict | None = None, work: dict | None = None) -> Path:
    book = tmp_path / "a-book"
    book.mkdir(parents=True, exist_ok=True)
    (book / "meta.yml").write_text(yaml.safe_dump(meta, allow_unicode=True), encoding="utf-8")
    if system is not None:
        (book / "_system").mkdir(exist_ok=True)
        (book / "_system" / "meta.yml").write_text(yaml.safe_dump(system, allow_unicode=True), encoding="utf-8")
    if work is not None:
        (book.parent / "work.yml").write_text(yaml.safe_dump(work, allow_unicode=True), encoding="utf-8")
    return book


def test_the_books_own_file_beats_every_other_source(tmp_path: Path) -> None:
    book = make_book(tmp_path, {"title": "T", "author": "The Book's Own Answer"}, system={"author": "Somewhere Else"})
    identity = nbm.resolve("a-book", book, {"a-book": {"author": "The Dictionary"}})
    assert identity.author.value == "The Book's Own Answer"
    assert identity.author.source == "meta"
    # And because it came from `meta`, there is nothing to write.
    assert nbm.KEY_AUTHOR not in identity.writes()


def test_an_author_only_the_dictionary_knows_is_scheduled_for_the_book(tmp_path: Path) -> None:
    book = make_book(tmp_path, {"title": "T"})
    identity = nbm.resolve("a-book", book, {"a-book": {"author": "The Dictionary"}})
    assert identity.writes()[nbm.KEY_AUTHOR] == "The Dictionary"


def test_the_author_is_found_wherever_the_pipeline_actually_put_it(tmp_path: Path) -> None:
    """Three different keys are in use on disk today. A normalizer that knew
    only one would 'discover' an author was missing and write a worse one."""
    book = make_book(tmp_path, {"title": "T", "doctrinal_context": {"author": "From Doctrinal"}})
    assert nbm.resolve("a-book", book, {}).author.value == "From Doctrinal"

    book = make_book(tmp_path, {"title": "T"}, system={"author": "From System"})
    assert nbm.resolve("a-book", book, {}).author.value == "From System"


def test_no_source_means_no_author_rather_than_a_guess(tmp_path: Path) -> None:
    book = make_book(tmp_path, {"title": "T"})
    identity = nbm.resolve("a-book", book, {})
    assert identity.author.value is None
    assert nbm.KEY_AUTHOR not in identity.writes()
    assert "author" in identity.unknown()


def test_the_title_page_form_is_never_promoted_to_a_card_heading(tmp_path: Path) -> None:
    """`publication.english_title` carries the subtitle — 64 characters that wrap
    to four lines in a card meant to look like its neighbours."""
    book = make_book(
        tmp_path,
        {
            "title": "Degrees of Excellence",
            "publication": {"english_title": "Degrees of Excellence: A Fatimid Treatise on Leadership in Islam"},
        },
    )
    identity = nbm.resolve("a-book", book, {})
    assert identity.english.value is None
    assert nbm.KEY_ENGLISH not in identity.writes()


def test_a_respelling_is_dropped_and_reported(tmp_path: Path) -> None:
    book = make_book(tmp_path, {"title": "Mukhtasar-ul-Asaar 2"})
    identity = nbm.resolve("a-book", book, {"a-book": {"displayTitle": "Mukhtasar ul Asar 2"}})
    assert nbm.KEY_ENGLISH not in identity.writes()
    assert identity.respelling == "Mukhtasar ul Asar 2"


def test_a_urdu_title_is_filed_under_its_own_key(tmp_path: Path) -> None:
    """`_listener_book.py` reads the two keys separately to decide which script a
    title is set in; a Urdu title under `title_arabic` is typeset in the wrong
    face."""
    book = make_book(tmp_path, {"title": "T", "original_title_language": "ur"})
    identity = nbm.resolve("a-book", book, {"a-book": {"nativeTitle": "قافلے", "nativeLang": "ur"}})
    assert identity.native_key == nbm.KEY_URDU
    assert identity.writes()[nbm.KEY_URDU] == "قافلے"


# ---------------------------------------------------------------------------
# Siblings
# ---------------------------------------------------------------------------


def test_a_volume_takes_its_author_from_the_volumes_that_state_one() -> None:
    books = {
        "vol-a": nbm.BookIdentity(slug="vol-a", meta_path=Path("x")),
        "vol-b": nbm.BookIdentity(slug="vol-b", meta_path=Path("y"), author=nbm.Resolution("The Author", "meta")),
    }
    nbm.fill_from_siblings(books, {"vol-a": ["vol-b"], "vol-b": ["vol-a"]})
    assert books["vol-a"].author.value == "The Author"
    assert books["vol-a"].author.source == "sibling volume"


def test_siblings_that_disagree_settle_nothing() -> None:
    """Two names across one work is a question about the work, not a default."""
    books = {
        "vol-a": nbm.BookIdentity(slug="vol-a", meta_path=Path("x")),
        "vol-b": nbm.BookIdentity(slug="vol-b", meta_path=Path("y"), author=nbm.Resolution("One", "meta")),
        "vol-c": nbm.BookIdentity(slug="vol-c", meta_path=Path("z"), author=nbm.Resolution("Another", "meta")),
    }
    nbm.fill_from_siblings(books, {"vol-a": ["vol-b", "vol-c"]})
    assert books["vol-a"].author.value is None


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def test_writing_keeps_every_comment_in_the_file(tmp_path: Path) -> None:
    """A YAML round-trip would drop them, and these files carry comments that
    explain real decisions — one records why five phases were stamped skipped."""
    book = tmp_path / "a-book"
    book.mkdir()
    original = "slug: a-book\ntitle: T\n\n# This comment explains a real decision.\nseries:\n  enabled: true\n"
    (book / "meta.yml").write_text(original, encoding="utf-8")
    identity = nbm.resolve("a-book", book, {"a-book": {"author": "Someone"}})
    written = nbm.apply_writes(identity, identity.writes())
    assert "# This comment explains a real decision." in written
    assert "author: Someone" in written
    assert yaml.safe_load(written)["series"] == {"enabled": True}


def test_the_new_key_lands_beside_the_others_not_at_the_end(tmp_path: Path) -> None:
    book = tmp_path / "a-book"
    book.mkdir()
    (book / "meta.yml").write_text("slug: a-book\ntitle: T\n\nprovenance:\n  note: long\n", encoding="utf-8")
    identity = nbm.resolve("a-book", book, {"a-book": {"author": "Someone"}})
    lines = nbm.apply_writes(identity, identity.writes()).splitlines()
    assert lines.index("author: Someone") < lines.index("provenance:")


def test_a_second_run_changes_nothing(tmp_path: Path) -> None:
    """Idempotence is what makes this safe to leave in the pipeline rather than
    run once and delete."""
    book = tmp_path / "a-book"
    book.mkdir()
    (book / "meta.yml").write_text("slug: a-book\ntitle: T\n", encoding="utf-8")
    card = {"a-book": {"author": "Someone", "displayTitle": "An English Name"}}

    first = nbm.resolve("a-book", book, card)
    (book / "meta.yml").write_text(nbm.apply_writes(first, first.writes()), encoding="utf-8")
    after_one = (book / "meta.yml").read_text(encoding="utf-8")

    second = nbm.resolve("a-book", book, card)
    assert second.writes() == {}
    assert second.author.source == "meta"
    assert (book / "meta.yml").read_text(encoding="utf-8") == after_one


def test_written_arabic_survives_the_round_trip(tmp_path: Path) -> None:
    """`allow_unicode` is load-bearing: without it the script would write
    \\u-escapes into a file a human reads and a book's own title would become
    unreadable in its own file."""
    book = tmp_path / "a-book"
    book.mkdir()
    (book / "meta.yml").write_text("slug: a-book\ntitle: T\n", encoding="utf-8")
    identity = nbm.resolve("a-book", book, {"a-book": {"nativeTitle": "أساس التأويل"}})
    written = nbm.apply_writes(identity, identity.writes())
    assert "أساس التأويل" in written
    assert yaml.safe_load(written)["title_arabic"] == "أساس التأويل"
