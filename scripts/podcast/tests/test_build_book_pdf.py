"""build_book_pdf's collapse-to-one-file contract.

A book folder used to carry two PDFs after a render: the Playwright working
target (book.pdf) and a copy under the book's own title. Every quality gate
had to know both names existed and pick the right one. build_book now RENAMES
the working file to the titled name — one PDF per book folder — and every
consumer resolves it through deliver_book._find_pdf instead of a hardcoded
path. These tests pin the rename itself; the resolver side is covered in each
consumer's own test file (test_validate_book_ready.py, etc.).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import build_book_pdf as B  # noqa: E402


def _book(tmp_path: Path, *, book_title: str = "The Book of the Road") -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("# The Book of the Road\n\n## One\n\nbody\n", encoding="utf-8")
    (bd / "book" / "book-toc.json").write_text(
        f'{{"book_title": "{book_title}", "chapters": [{{"title": "One"}}]}}', encoding="utf-8"
    )
    return bd


def _stub_pipeline(monkeypatch: pytest.MonkeyPatch, *, render_ok: bool = True) -> None:
    """Stand in for Playwright, the cover generator, and the comprehension pass —
    none of which this test is about, and all of which touch the network or a
    real PDF parser."""

    def fake_run(argv, **kwargs):
        # argv: ["node", RENDER_SCRIPT, book_md, out_pdf, THEME_CSS, "1", self_study_flag]
        out_pdf = Path(argv[3])
        if render_ok:
            out_pdf.write_bytes(b"%PDF-1.4 fake render\n%%EOF\n")
        return type("R", (), {"returncode": 0 if render_ok else 1, "stderr": ""})()

    monkeypatch.setattr(B.subprocess, "run", fake_run)
    monkeypatch.setattr("_book_cover.ensure_cover", lambda *a, **k: None)
    monkeypatch.setattr(B, "_final_comprehension_review", lambda *a, **k: None)
    monkeypatch.setattr(B, "_GDRIVE_LIBRARY", Path("/nonexistent-in-tests"))


def test_render_renames_to_the_titled_pdf_and_deletes_the_working_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bd = _book(tmp_path)
    _stub_pipeline(monkeypatch)

    out = B.build_book(bd, surface_finder=False)

    assert out == bd / "book" / "The Book of the Road.pdf"
    assert out.exists()
    assert not (bd / "book" / "book.pdf").exists(), "one PDF per book folder — the working file must not survive"


def test_a_failed_rename_keeps_the_render_as_the_only_deliverable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the rename itself fails, the render must not be lost — book.pdf stays
    as the deliverable rather than the book folder ending up with nothing."""
    bd = _book(tmp_path)
    _stub_pipeline(monkeypatch)
    monkeypatch.setattr(Path, "replace", lambda self, target: (_ for _ in ()).throw(OSError("locked")))

    out = B.build_book(bd, surface_finder=False)

    assert out == bd / "book" / "book.pdf"
    assert out.exists()


def test_self_study_edition_is_untouched_by_the_titled_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-study returns before the titled-copy step and never touches book.pdf
    at all — a wholly separate filename, book-self-study.pdf."""
    bd = _book(tmp_path)
    (bd / "book" / "book-self-study.md").write_text("# The Book of the Road\n\nbody\n", encoding="utf-8")
    _stub_pipeline(monkeypatch)

    out = B.build_book(bd, surface_finder=False, self_study=True)

    assert out == bd / "book" / "book-self-study.pdf"
    assert not (bd / "book" / "book.pdf").exists()
    assert not (bd / "book" / "The Book of the Road.pdf").exists()


def test_a_missing_book_toc_title_falls_back_to_the_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "book" / "book.md").write_text("# X\n\n## One\n\nbody\n", encoding="utf-8")
    # No book-toc.json and no meta.yml — _edition_title's last resort is the slug.
    _stub_pipeline(monkeypatch)

    out = B.build_book(bd, surface_finder=False)

    assert out == bd / "book" / "slug.pdf"
