"""Shared scaffolding for the corrections-workflow tests.

Two things every one of those tests needs and none should re-invent:

  * a tiny book on disk (`make_book`) laid out the way the real ones are, and
  * a fake D1 (`FakeD1`) that is a REAL SQLite database built from the Library's
    own migrations, so the SQL these scripts emit is executed, not merely
    string-matched. A statement that names a column the schema does not have
    fails here the way it would in wrangler.

`FakeD1` refuses `remote=True` outright: no test in this family may ever be able
to reach a deployed database.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MIGRATIONS = REPO / "listener" / "migrations"

_ACCESS_EVENT = """
CREATE TABLE access_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  subject TEXT NOT NULL, scope_type TEXT, scope_id TEXT, detail TEXT
);
"""


class FakeD1:
    """`upload_listener_media.d1` over an in-memory SQLite built from the real migrations."""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_ACCESS_EVENT)
        for name in ("0023_corrections.sql", "0025_corrections_workflow.sql"):
            self.conn.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))
        self.calls: list[str] = []

    def __call__(self, sql: str, *, remote: bool) -> list[dict]:
        assert remote is False, "a test reached for the deployed database"
        self.calls.append(sql)
        if sql.lstrip().upper().startswith("SELECT"):
            return [dict(r) for r in self.conn.execute(sql).fetchall()]
        self.conn.executescript(sql)
        return []

    # -- helpers for tests -------------------------------------------------
    def add_correction(self, **kw) -> dict:
        row = {
            "id": "c1",
            "slug": "demo",
            "anchor_key": "first chapter",
            "block_index": 0,
            "start_offset": 0,
            "end_offset": 5,
            "quote": "x",
            "prefix": "",
            "proposed_text": "y",
            "rationale_html": "",
            "kind": "typo",
            "status": "open",
            "origin": "moderator",
            "certainty": None,
            "batch_id": None,
            "raised_by": "mod@example.com",
            "raised_at": "2026-09-01T10:00:00.000Z",
            "updated_at": "2026-09-01T10:00:00.000Z",
        }
        row.update(kw)
        cols = ", ".join(row)
        self.conn.execute(f"INSERT INTO correction ({cols}) VALUES ({', '.join('?' for _ in row)})", list(row.values()))
        self.conn.commit()
        return row

    def rows(self, sql: str) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql).fetchall()]


DEFAULT_CHAPTERS = {
    "1. First Chapter": (
        "The teacher said that patience is the key to every door. He repeated it to each student.\n\n"
        "A second paragraph speaks of the neighbour who is near and the neighbour who is far.\n\n"
        "The third paragraph closes the chapter with a short reminder."
    ),
    "2. Second Chapter": "Another chapter begins here and it has its own single paragraph of prose.",
}

CONFIG = """slug: demo
title: "Demo"
content_profile: islamic_scholarly
deliverable_mode: translation_edition
book_augmentation: none
book_voice: faithful
narrative_frame: transmitted_report
"""


def make_book(
    tmp_path: Path,
    chapters: dict[str, str] | None = None,
    *,
    bucket: str = "Islamic",
    slug: str = "demo",
    config: str = CONFIG,
) -> Path:
    """A minimal book at tmp/content/<bucket>/<slug>. Returns its directory."""
    book = tmp_path / "content" / bucket / slug
    (book / "book").mkdir(parents=True)
    (book / "_system").mkdir()
    parts = ["# Demo Book\n"]
    for heading, body in (chapters or DEFAULT_CHAPTERS).items():
        parts.append(f"## {heading}\n\n{body}\n")
    (book / "book" / "book.md").write_text("\n".join(parts), encoding="utf-8")
    (book / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return book


def add_source(
    book: Path, *, pages: dict[int, str], crosswalk_pages: dict[int, list[int]], titles: dict[int, str]
) -> None:
    """A scan (`ocr/raw-extract.md`) plus a crosswalk mapping chapters to its pages."""
    ocr = book / "_system" / "source" / "ocr"
    ocr.mkdir(parents=True)
    (ocr / "raw-extract.md").write_text(
        "\n".join(f"<!-- page {n} -->\n{text}\n" for n, text in sorted(pages.items())), encoding="utf-8"
    )
    chapters = [
        {"index": i, "title": titles[i], "source_pages": p, "arabic_source_pages": p}
        for i, p in crosswalk_pages.items()
    ]
    (book / "book" / "source-crosswalk.json").write_text(json.dumps({"chapters": chapters}), encoding="utf-8")


def book_md(book: Path) -> str:
    return (book / "book" / "book.md").read_text(encoding="utf-8")
