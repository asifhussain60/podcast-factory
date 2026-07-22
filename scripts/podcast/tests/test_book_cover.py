"""Tests for _book_cover — theme brief + non-blocking ensure_cover contract."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _book_cover
from _book_cover import _read_theme, ensure_cover


def _write_toc(
    book_dir: Path, title="The Master and the Disciple", chapters=("Opening", "The Covenant", "The Debate")
) -> None:
    toc = book_dir / "book" / "book-toc.json"
    toc.parent.mkdir(parents=True, exist_ok=True)
    toc.write_text(
        json.dumps(
            {
                "book_title": title,
                "chapters": [{"title": c} for c in chapters],
            }
        ),
        encoding="utf-8",
    )


# --- _read_theme -----------------------------------------------------------


def test_read_theme_missing_toc_is_empty(tmp_path):
    assert _read_theme(tmp_path) == ""


def test_read_theme_invalid_json_is_empty(tmp_path):
    toc = tmp_path / "book" / "book-toc.json"
    toc.parent.mkdir(parents=True)
    toc.write_text("{not json", encoding="utf-8")
    assert _read_theme(tmp_path) == ""


def test_read_theme_includes_title_and_chapters(tmp_path):
    _write_toc(tmp_path)
    brief = _read_theme(tmp_path)
    assert "The Master and the Disciple" in brief
    assert "The Covenant" in brief


def test_read_theme_caps_chapter_list_at_six(tmp_path):
    _write_toc(tmp_path, chapters=tuple(f"Chapter {i}" for i in range(1, 11)))
    brief = _read_theme(tmp_path)
    assert "Chapter 6" in brief
    assert "Chapter 7" not in brief


def test_style_prompt_forbids_text():
    # The renderer overlays title/author; the image itself must carry no text.
    assert "no text" in _book_cover._STYLE


# --- ensure_cover ----------------------------------------------------------


def test_existing_cover_is_honored_not_regenerated(tmp_path):
    out = tmp_path / "book" / "cover.png"
    out.parent.mkdir(parents=True)
    out.write_bytes(b"existing")
    calls = []
    assert ensure_cover(tmp_path, log=calls.append) == out
    assert out.read_bytes() == b"existing"
    assert calls == []  # short-circuit: no generation attempted


def test_generation_failure_is_non_blocking(tmp_path, monkeypatch):
    # Force the lazy import inside ensure_cover to blow up: the contract says
    # any failure logs a warning and returns None (renderer falls back).
    class _Boom:
        def __getattr__(self, name):
            raise RuntimeError("no gemini in tests")

    monkeypatch.setitem(sys.modules, "generate_video_layer", _Boom())
    logs = []
    assert ensure_cover(tmp_path, log=logs.append) is None
    assert any("skipped" in line for line in logs)
    assert not (tmp_path / "book" / "cover.png").exists()


def test_force_regenerates_even_when_cover_exists(tmp_path, monkeypatch):
    out = tmp_path / "book" / "cover.png"
    out.parent.mkdir(parents=True)
    out.write_bytes(b"existing")

    class _Boom:
        def __getattr__(self, name):
            raise RuntimeError("no gemini in tests")

    monkeypatch.setitem(sys.modules, "generate_video_layer", _Boom())
    logs = []
    # force=True attempts generation; failure is non-blocking (None) and the
    # human-supplied file is left untouched.
    assert ensure_cover(tmp_path, force=True, log=logs.append) is None
    assert out.read_bytes() == b"existing"
    assert any("skipped" in line for line in logs)
