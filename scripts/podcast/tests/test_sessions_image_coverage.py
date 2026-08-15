#!/usr/bin/env python3
"""Coverage check for Sessions-book images, run once before the Drive
"Resources Images" folder they were copied from is deleted. Pins the three ways
a reference can fail the check, and that a clean book passes it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sessions.image_coverage import check_book, referenced_images  # noqa: E402


def _book(tmp_path: Path, body: str) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "book.md").write_text(body, encoding="utf-8")
    return tmp_path


def test_referenced_images_reads_the_markdown_targets_in_order(tmp_path: Path) -> None:
    book_dir = _book(
        tmp_path,
        "First.\n\n![](images/213/a.jpg)\n\nSecond.\n\n![alt text](images/213/b.jpg)\n",
    )

    assert referenced_images(book_dir) == ["images/213/a.jpg", "images/213/b.jpg"]


def test_a_book_with_every_image_present_passes(tmp_path: Path, monkeypatch) -> None:
    book_dir = _book(tmp_path, "![](images/213/a.jpg)\n")
    (book_dir / "book" / "images" / "213").mkdir(parents=True)
    (book_dir / "book" / "images" / "213" / "a.jpg").write_bytes(b"\xff\xd8\xff")

    monkeypatch.setattr("sessions.image_coverage.resolve_content", lambda slug: book_dir)

    report = check_book("love-of-the-prophet")

    assert report["ok"] is True
    assert report["referenced"] == 1
    assert report["missing"] == []


def test_a_reference_naming_no_file_is_reported_missing(tmp_path: Path, monkeypatch) -> None:
    book_dir = _book(tmp_path, "![](images/213/gone.jpg)\n")

    monkeypatch.setattr("sessions.image_coverage.resolve_content", lambda slug: book_dir)

    report = check_book("love-of-the-prophet")

    assert report["ok"] is False
    assert report["missing"] == ["images/213/gone.jpg"]


def test_a_zero_byte_file_is_reported_separately_from_missing(tmp_path: Path, monkeypatch) -> None:
    """A path that exists but was never actually written (a failed copy that
    still created the file) is not the same defect as no file at all, and a
    caller deciding whether to re-ingest needs to tell them apart."""
    book_dir = _book(tmp_path, "![](images/213/empty.jpg)\n")
    (book_dir / "book" / "images" / "213").mkdir(parents=True)
    (book_dir / "book" / "images" / "213" / "empty.jpg").touch()

    monkeypatch.setattr("sessions.image_coverage.resolve_content", lambda slug: book_dir)

    report = check_book("love-of-the-prophet")

    assert report["ok"] is False
    assert report["missing"] == []
    assert report["empty"] == ["images/213/empty.jpg"]


def test_an_external_or_absolute_reference_is_flagged_not_silently_passed(tmp_path: Path, monkeypatch) -> None:
    """Neither kind of reference is a repo asset, and neither survives the Drive
    folder disappearing — an absolute path breaks the moment the book is opened
    from a different machine, and an external URL breaks the moment that host
    goes away. A coverage check that only asked "does the relative path exist"
    would report both as fine."""
    book_dir = _book(
        tmp_path,
        "![](https://session.kashkole.com/Resources/IMAGES/87/x.jpg)\n\n![](/Users/asif/x.jpg)\n",
    )

    monkeypatch.setattr("sessions.image_coverage.resolve_content", lambda slug: book_dir)

    report = check_book("love-of-the-prophet")

    assert report["ok"] is False
    assert len(report["not_relative"]) == 2


def test_a_book_with_no_images_at_all_passes_trivially(tmp_path: Path, monkeypatch) -> None:
    book_dir = _book(tmp_path, "Plain prose, no illustrations.\n")

    monkeypatch.setattr("sessions.image_coverage.resolve_content", lambda slug: book_dir)

    report = check_book("love-of-the-prophet")

    assert report["ok"] is True
    assert report["referenced"] == 0
