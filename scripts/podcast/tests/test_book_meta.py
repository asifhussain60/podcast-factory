"""Every book gets a meta.yml, built only from what is actually known.

isaf-al-talib, 2026-09-18: the scaffold's own docstring says it registers the book "via the per-book
meta.yml", but it never wrote one. The Library loader then crashed on `open(meta.yml)` and a person
hand-wrote the file. `_book_meta` creates it from the scaffold arguments and, when present, the book's
series-config — and never guesses: an author or an Arabic title nobody supplied stays absent (a
plausible guess about who wrote a religious text is the worst thing a metadata file can hold).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _book_meta as bm  # noqa: E402

ISAF = {
    "title": "Is'af al-Talib fi Jami' al-Matalib",
    "author": "Faidh Ali bin Sayyidna Sulaiman (Shams al-Kiyan)",
    "source_language": "ar",
    "deliverable_mode": "translation_edition",
    "study_track": "shariah",
    "title_arabic": "كتاب إسعاف الطالب في جميع المطالب",
}


def test_a_translation_edition_gets_every_field_the_library_needs():
    meta = bm.build_meta("isaf-al-talib", series_config=ISAF)
    assert meta["slug"] == "isaf-al-talib"
    assert meta["title"] == ISAF["title"] and meta["author"] == ISAF["author"]
    assert meta["title_arabic"] == ISAF["title_arabic"]
    assert meta["original_title_language"] == "ar"
    assert meta["study_track"] == "shariah"
    assert meta["series"]["enable_book_branch"] is True
    assert meta["publication"]["status"] == "draft"


def test_nothing_is_invented_when_the_source_of_truth_is_silent():
    meta = bm.build_meta("some-book", title="Some Book")
    assert set(meta) == {"slug", "title", "publication"}, "only what is known; no author, no Arabic title, no track"
    assert "author" not in meta and "title_arabic" not in meta and "series" not in meta


def test_a_book_that_is_not_a_translation_edition_does_not_switch_on_the_reading_edition():
    meta = bm.build_meta("x", title="X", series_config={"deliverable_mode": "augmented_companion"})
    assert "series" not in meta  # off unless declared; a silent default here once cost a run


def test_an_explicit_enable_book_branch_is_honoured():
    meta = bm.build_meta("x", title="X", series_config={"enable_book_branch": True})
    assert meta["series"]["enable_book_branch"] is True


def test_explicit_arguments_win_over_series_config_only_when_given():
    meta = bm.build_meta("x", title="From The Args", author="A. Author", series_config={"title": "From Config"})
    assert meta["title"] == "From The Args" and meta["author"] == "A. Author"


def test_ensure_meta_creates_valid_yaml_that_keeps_arabic(tmp_path):
    path = bm.ensure_meta(tmp_path, "isaf-al-talib", series_config=ISAF)
    assert path == tmp_path / "meta.yml"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert loaded["title_arabic"] == ISAF["title_arabic"]
    assert "\\u" not in path.read_text(encoding="utf-8"), "Arabic must be stored as itself, not escapes"


def test_ensure_meta_never_overwrites_a_book_that_already_has_one(tmp_path):
    (tmp_path / "meta.yml").write_text("slug: x\ntitle: Hand Written\n# a human's comment\n", encoding="utf-8")
    before = (tmp_path / "meta.yml").read_bytes()
    assert bm.ensure_meta(tmp_path, "x", series_config=ISAF) is None
    assert (tmp_path / "meta.yml").read_bytes() == before


def test_ensure_meta_reads_the_books_own_series_config_when_none_is_passed(tmp_path):
    (tmp_path / "_system").mkdir()
    (tmp_path / "_system" / "series-config.yaml").write_text(yaml.safe_dump(ISAF, allow_unicode=True), encoding="utf-8")
    bm.ensure_meta(tmp_path, "isaf-al-talib")
    assert yaml.safe_load((tmp_path / "meta.yml").read_text(encoding="utf-8"))["author"] == ISAF["author"]


def test_a_title_falls_back_to_a_readable_form_of_the_slug_only_as_a_last_resort():
    assert bm.build_meta("white-nights")["title"] == "White Nights"


def test_scaffold_writes_meta_yml(tmp_path, monkeypatch):
    import scaffold_book as sb

    monkeypatch.setattr(sb, "book_dir_for", lambda category, slug: tmp_path / slug)
    monkeypatch.setattr(sb, "REPO_ROOT", tmp_path)
    assert sb.scaffold("books", "new-book", "New Book", "An Author", force=False) == 0
    loaded = yaml.safe_load((tmp_path / "new-book" / "meta.yml").read_text(encoding="utf-8"))
    assert loaded["title"] == "New Book" and loaded["author"] == "An Author"
    assert loaded["publication"]["status"] == "draft"


def test_loading_a_book_without_meta_yml_fails_with_the_command_that_fixes_it(tmp_path, monkeypatch):
    import _listener_book as lb

    (tmp_path / "book").mkdir(parents=True)
    (tmp_path / "book" / "book.md").write_text("# B\n", encoding="utf-8")
    monkeypatch.setattr(lb, "find_content", lambda slug: ("draft", "Islamic", tmp_path))
    with pytest.raises(SystemExit) as exc:
        lb.load_book("isaf-al-talib")
    message = str(exc.value)
    assert "meta.yml" in message and "_book_meta.py isaf-al-talib" in message
