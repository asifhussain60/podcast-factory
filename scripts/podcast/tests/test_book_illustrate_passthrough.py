"""0book-illustrate never writes a second copy of the book.

Placement is a human act in the Astro Book Composer (Asif, 2026-08-06): this
phase may generate and OFFER a diagram, and may not put one on a page. Two of its
routes never generate at all — fiction, which uses scenic rasters instead, and a
book that forbids added content — and both of those used to emit
``book/book-illustrated.md`` as a plain copy of book.md, purely so a downstream
consumer "still finds the expected file name". That consumer was removed when
visuals were decoupled; the renderer reads book.md on every route. What the
copies did instead was leave a second book on disk that nothing refreshed: on
the-master-and-the-disciple, one nine weeks stale and missing the introduction.

These two routes return before any model call, so they are cheap to test and they
are exactly where the regression would reappear.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _book_illustrate import author_phase_book_illustrate  # noqa: E402

BOOK_MD = "# Title\n\n## One\n\nProse the reader will actually see.\n"


def book(tmp_path: Path, config: str) -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(BOOK_MD, encoding="utf-8")
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return bd


def test_fiction_passthrough_returns_book_md_and_writes_no_variant(tmp_path: Path) -> None:
    bd = book(tmp_path, "slug: slug\ncontent_profile: fiction\n")

    out = author_phase_book_illustrate(bd, log=lambda *a: None)

    assert out == bd / "book" / "book.md"
    assert not (bd / "book" / "book-illustrated.md").exists()


def test_no_augmentation_passthrough_returns_book_md_and_writes_no_variant(tmp_path: Path) -> None:
    bd = book(tmp_path, "slug: slug\ncontent_profile: islamic_scholarly\nbook_augmentation: none\n")

    out = author_phase_book_illustrate(bd, log=lambda *a: None)

    assert out == bd / "book" / "book.md"
    assert not (bd / "book" / "book-illustrated.md").exists()


def test_passthrough_leaves_the_real_book_untouched(tmp_path: Path) -> None:
    """The phase returns book.md — it must not have rewritten it on the way out."""
    bd = book(tmp_path, "slug: slug\ncontent_profile: islamic_scholarly\nbook_augmentation: none\n")

    author_phase_book_illustrate(bd, log=lambda *a: None)

    assert (bd / "book" / "book.md").read_text(encoding="utf-8") == BOOK_MD


def test_a_book_with_no_diagrams_still_records_an_empty_manifest(tmp_path: Path) -> None:
    """Removing the copy must not also remove the evidence the phase ran."""
    bd = book(tmp_path, "slug: slug\ncontent_profile: fiction\n")

    author_phase_book_illustrate(bd, log=lambda *a: None)

    assert (bd / "book" / "_diagrams" / "manifest.json").read_text(encoding="utf-8").strip() == "[]"
