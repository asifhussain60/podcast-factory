#!/usr/bin/env python3
"""A session illustration reaches the page, or nothing anywhere says it did not.

WHY THIS FILE EXISTS SEPARATELY

An illustration in a delivered lecture travels through four modules that never
import one another, and the picture appears on the page only if all four agree
about one string:

    sessions/convert    `Resources/IMAGES/<sid>/<guid>.jpg` -> `images/<sid>/<file>`
    sessions/ingest     copies the file to `book/images/<sid>/<file>`
    _listener_media     inventories it as media_asset key `<slug>/image/<sid>/<file>`
    _listener_book      rewrites the rendered src to `/media/<slug>/image/<sid>/<file>`

Each half is reasonable read on its own, and each has looked right while being
wrong. THE FAILURE IS SILENT IN BOTH DIRECTIONS, which is the whole reason for
pinning it here rather than trusting a reading:

  * a src the inventory does not match -> the file is copied, uploaded to R2,
    given a database row, and pointed at by nothing. Every step reports success;
    the reader sees a broken picture.
  * a key the src does not match -> the media route answers 404 for a file that
    is present in the bucket. Same outcome, opposite cause.

So the assertions below are deliberately about AGREEMENT rather than about
either format: they compose the two constructions and require the result to be
one URL. Change either side alone and this fails, which is the point — the
format itself is free to change, as long as both halves change together.

No network, no database, no node: `_media_image_srcs` is pure and `collect_media`
reads a tmp_path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _listener_book import Book, _media_image_srcs  # noqa: E402
from _listener_media import collect_media  # noqa: E402
from sessions.convert import convert, corpus_ref, localise_images  # noqa: E402

SLUG = "surah-al-fateha"
GUID = "21ac5722-564f-4aed-beeb-4f61c600508f"


def make_book(tmp_path: Path) -> Book:
    return Book(
        slug=SLUG,
        bucket="Sessions",
        directory=tmp_path,
        title="Surah Al-Fateha",
        title_arabic=None,
        blurb=None,
        edition_note=None,
    )


def put_image(tmp_path: Path, relative: str) -> Path:
    path = tmp_path / "book" / "images" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff")  # enough to be a file; nothing reads the pixels
    return path


def image_assets(book: Book) -> list:
    return [asset for asset in book.assets if asset.kind == "session-image"]


# ---------------------------------------------------------------------------
# The two constructions, composed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative", [f"87/{GUID}.jpg", f"213/{GUID}.png", f"1278/{GUID}.jpeg"])
def test_the_src_on_the_page_is_the_key_in_the_database(tmp_path: Path, relative: str) -> None:
    """The one assertion this whole file exists for.

    Two modules build this URL from opposite ends — one from a path on disk, one
    from a path in the prose — and neither can see the other's answer.
    """
    put_image(tmp_path, relative)
    book = make_book(tmp_path)
    collect_media(book)

    (asset,) = image_assets(book)
    rendered = _media_image_srcs(f'<img src="images/{relative}" alt="" />', SLUG)

    assert f'src="/media/{asset.key}"' in rendered


def test_the_whole_journey_from_authored_html_to_the_finished_src(tmp_path: Path) -> None:
    """Every module in the chain, in order, on the reference shape that was broken.

    The host-prefixed src is used deliberately: it is the one that travelled the
    entire way and still arrived pointing at somebody else's server.
    """
    converted = convert(f"<p><img src='https://session.kashkole.com/Resources/IMAGES/87/{GUID}.jpg'></p>")
    markdown, wanted = localise_images(converted.markdown)

    # what the ingest would copy, laid down where the ingest lays it down
    for session_id, filename in wanted:
        put_image(tmp_path, f"{session_id}/{filename}")

    book = make_book(tmp_path)
    collect_media(book)
    (asset,) = image_assets(book)

    # what the renderer would produce from that markdown, then site-rewritten
    src = markdown.split("](", 1)[1].rstrip(")")
    rendered = _media_image_srcs(f'<img src="{src}" />', SLUG)

    assert rendered == f'<img src="/media/{SLUG}/image/87/{GUID}.jpg" />'
    assert asset.key == f"{SLUG}/image/87/{GUID}.jpg"


def test_a_nested_session_folder_is_carried_through_rather_than_flattened(tmp_path: Path) -> None:
    """The session id is part of the key, and it is what stops two lectures'
    pictures colliding — the same collision migration 0010 had to repair for
    decks, where every deck's `page-01.jpg` overwrote the last one."""
    put_image(tmp_path, f"87/{GUID}.jpg")
    put_image(tmp_path, f"152/{GUID}.jpg")
    book = make_book(tmp_path)
    collect_media(book)

    assert len({asset.key for asset in image_assets(book)}) == 2


# ---------------------------------------------------------------------------
# What must NOT be rewritten
# ---------------------------------------------------------------------------


def test_an_absolute_src_is_left_alone_by_the_site_rewrite() -> None:
    """`_media_image_srcs` matches `src="images/…` and nothing else. A src that
    already points somewhere absolute is not a book asset, and prefixing the
    media route onto it would invent a key for a file that was never inventoried.
    """
    for src in ("/media/other-book/image/1/a.jpg", "https://example.com/a.jpg", "/cover.png"):
        html = f'<img src="{src}" />'
        assert _media_image_srcs(html, SLUG) == html


def test_a_cover_is_not_filed_as_a_session_image(tmp_path: Path) -> None:
    """`media_asset.kind` is what the uploader and the site read to decide what a
    file IS. A book with forty covers has the site picking one of them
    arbitrarily to print on its card — migration 0011 says exactly this."""
    (tmp_path / "book").mkdir(parents=True, exist_ok=True)
    (tmp_path / "book" / "cover.jpg").write_bytes(b"\xff\xd8\xff")
    put_image(tmp_path, f"87/{GUID}.jpg")

    book = make_book(tmp_path)
    collect_media(book)

    assert [asset.kind for asset in book.assets if asset.key.endswith("cover.jpg")] == ["cover"]
    assert len(image_assets(book)) == 1


# ---------------------------------------------------------------------------
# The inventory reads the folder, not a list
# ---------------------------------------------------------------------------


def test_a_book_with_no_illustrations_inventories_none(tmp_path: Path) -> None:
    """Every other route puts nothing in `book/images/`, so this branch runs on
    every book in the library and must be a no-op rather than a per-profile
    condition somebody has to remember to add."""
    book = make_book(tmp_path)
    collect_media(book)
    assert image_assets(book) == []


def test_a_stray_non_image_in_the_folder_is_not_shipped(tmp_path: Path) -> None:
    """`.DS_Store` and Drive's own sidecars land in synced folders constantly. An
    asset row for one would be a file the uploader pushes and the site links."""
    put_image(tmp_path, f"87/{GUID}.jpg")
    (tmp_path / "book" / "images" / "87" / ".DS_Store").write_bytes(b"x")
    (tmp_path / "book" / "images" / "87" / "notes.txt").write_text("x", encoding="utf-8")

    book = make_book(tmp_path)
    collect_media(book)

    assert [asset.key for asset in image_assets(book)] == [f"{SLUG}/image/87/{GUID}.jpg"]


@pytest.mark.parametrize(
    ("suffix", "content_type"),
    [(".jpg", "image/jpeg"), (".jpeg", "image/jpeg"), (".png", "image/png"), (".webp", "image/webp")],
)
def test_every_shipped_image_type_carries_its_own_content_type(tmp_path: Path, suffix: str, content_type: str) -> None:
    """The media route serves the row's `content_type` verbatim from the row. A wrong
    one is a picture the browser downloads instead of displaying."""
    put_image(tmp_path, f"87/{GUID}{suffix}")
    book = make_book(tmp_path)
    collect_media(book)

    (asset,) = image_assets(book)
    assert asset.content_type == content_type


# ---------------------------------------------------------------------------
# The reference resolver itself
# ---------------------------------------------------------------------------


def test_a_reference_that_names_no_corpus_file_resolves_to_nothing() -> None:
    """`corpus_ref` returning None is what routes a reference to the report
    instead of onto the page. A shape it wrongly ACCEPTED would ask the ingest to
    copy a file that does not exist; a shape it wrongly REJECTED would drop a
    picture Asif put on the screen."""
    for src in (
        "Resources/IMAGES/1278/01.jpg",  # real folder, filename is not a GUID
        "Resources/IMAGES/abc/" + GUID + ".jpg",  # session id is not a number
        "IMAGES/87/" + GUID + ".jpg",  # not the corpus path
        "data:image/png;base64,iVBORw0KGgo=",
        "",
    ):
        assert corpus_ref(src) is None, src
