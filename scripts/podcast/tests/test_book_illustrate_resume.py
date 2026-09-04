"""0book-illustrate remembers which section failed, and finishes it next time.

A section whose classification raised used to be swallowed with one stderr line
and dropped from the manifest, so the manifest listed successes only. The
"already complete" check then asked whether every LISTED diagram was on disk —
true of an all-successes list, and true of an empty one — and declared the phase
finished. The missing diagram was never drawn again without --force, which
re-buys every diagram in the book to recover one.

No model is called: the classifier is replaced, and the two steps that follow the
manifest (the Mermaid render and the visuals registry) are stubbed out.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _book_illustrate as ill  # noqa: E402
import _visual_candidates  # noqa: E402

_BODY = " ".join(["word"] * 250)  # comfortably past _MIN_SECTION_WORDS
BOOK_MD = f"# Title\n\n## One\n\n{_BODY}\n\n## Two\n\n{_BODY}\n"
CONFIG = "slug: slug\ncontent_profile: islamic_scholarly\n"
SPEC = {"structure_type": "cycle", "anchor_text": "word", "caption": "A cycle.", "parameters": {}}


def _book(tmp_path: Path) -> Path:
    bd = tmp_path / "slug"
    (bd / "book").mkdir(parents=True)
    (bd / "_system").mkdir(parents=True)
    (bd / "book" / "book.md").write_text(BOOK_MD, encoding="utf-8")
    (bd / "_system" / "series-config.yaml").write_text(CONFIG, encoding="utf-8")
    return bd


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ill, "_render_diagrams", lambda *a, **k: None)
    monkeypatch.setattr(_visual_candidates, "merge_entries", lambda *a, **k: None)

    def draw(spec, diagram_id, diagram_dir, book_dir=None):
        path = diagram_dir / f"{diagram_id}.svg"
        path.write_text("<svg/>", encoding="utf-8")
        return str(path)

    monkeypatch.setattr(ill, "_generate_pattern_svg_file", draw)


def _classifier(monkeypatch: pytest.MonkeyPatch, raising: set[str]) -> list[str]:
    """Section "Two" always earns one diagram; the sections named in `raising` blow up."""
    calls: list[str] = []

    def fake(section_title, section_text, content_profile, *, book_dir, model_flag=None):
        calls.append(section_title)
        if section_title in raising:
            raise RuntimeError("model gone")
        return [dict(SPEC)] if section_title == "Two" else []

    monkeypatch.setattr(ill, "_classify_section", fake)
    return calls


def _manifest(bd: Path) -> list[dict]:
    return json.loads((bd / "book" / "_diagrams" / "manifest.json").read_text(encoding="utf-8"))


def test_a_section_that_raised_is_recorded_in_the_manifest(tmp_path: Path, monkeypatch, offline) -> None:
    bd = _book(tmp_path)
    _classifier(monkeypatch, raising={"One"})

    ill.author_phase_book_illustrate(bd, log=lambda *a: None)

    failed = [e for e in _manifest(bd) if e.get("failed")]
    assert failed == [{"section": "One", "failed": "RuntimeError: model gone"}]
    assert any(e.get("section") == "Two" and e.get("svg_path") for e in _manifest(bd)), "the success is still listed"


def test_the_next_run_re_asks_only_the_failed_section(tmp_path: Path, monkeypatch, offline) -> None:
    bd = _book(tmp_path)
    _classifier(monkeypatch, raising={"One"})
    ill.author_phase_book_illustrate(bd, log=lambda *a: None)

    calls = _classifier(monkeypatch, raising=set())
    ill.author_phase_book_illustrate(bd, log=lambda *a: None)

    assert calls == ["One"], "the drawn section must not be re-bought; the failed one must be"
    assert not [e for e in _manifest(bd) if e.get("failed")]
    assert sorted(e["section"] for e in _manifest(bd)) == ["Two"]  # "One" earned no diagram this time


def test_a_finished_manifest_is_still_skipped(tmp_path: Path, monkeypatch, offline) -> None:
    bd = _book(tmp_path)
    _classifier(monkeypatch, raising=set())
    ill.author_phase_book_illustrate(bd, log=lambda *a: None)

    calls = _classifier(monkeypatch, raising=set())
    ill.author_phase_book_illustrate(bd, log=lambda *a: None)

    assert calls == [], "a manifest whose every diagram is on disk is complete"


def test_an_empty_manifest_is_not_taken_as_complete(tmp_path: Path, monkeypatch, offline) -> None:
    """`all([])` is True: an all-failed run wrote `[]` and was never retried."""
    bd = _book(tmp_path)
    (bd / "book" / "_diagrams").mkdir(parents=True)
    (bd / "book" / "_diagrams" / "manifest.json").write_text("[]\n", encoding="utf-8")

    calls = _classifier(monkeypatch, raising=set())
    ill.author_phase_book_illustrate(bd, log=lambda *a: None)

    assert calls == ["One", "Two"]
