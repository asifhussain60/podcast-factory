"""test_compose_scope.py — pins the guard against re-running compose_book_v2's
model passes (fluency/augment/voice) when only the deterministic apparatus tail
(glossary.yml, vowelling, render templates) actually changed.

Regression test for the spiritual-ethos 2026-08-08 incident: a 21-entry
glossary.yml Arabic-script fix was folded into book.md via a full
`--retry-phase 0book-compose`, which re-ran the fluency + augment model passes
over all 15 chapters of an English-source book to change Arabic annotations
that `apply_book_apparatus.py` alone injects, in seconds, with zero model
calls. See `_compose_scope.py` and `apply_book_apparatus.py`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _compose_scope
from _compose_scope import apparatus_only_retry_advice, needs_model_recompose


def _touch(path: Path, *, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def _isolate_modules_dir(tmp_path, monkeypatch) -> None:
    """Points _HERE at an empty directory so the real repo's own module mtimes
    (always "now") can't leak into a fixture that isn't testing them."""
    empty = tmp_path / "no-modules-here"
    empty.mkdir(exist_ok=True)
    monkeypatch.setattr(_compose_scope, "_HERE", empty)


def test_no_book_md_means_a_full_compose_is_needed(tmp_path, monkeypatch):
    _isolate_modules_dir(tmp_path, monkeypatch)
    book_dir = tmp_path / "some-book"
    (book_dir / "book").mkdir(parents=True)
    assert needs_model_recompose(book_dir) is True
    assert apparatus_only_retry_advice(book_dir) is None


def test_source_text_newer_than_book_md_means_recompose_is_needed(tmp_path, monkeypatch):
    _isolate_modules_dir(tmp_path, monkeypatch)
    book_dir = tmp_path / "some-book"
    _touch(book_dir / "book" / "book.md", mtime=100)
    _touch(book_dir / "_system" / "source" / "text" / "refined-english.md", mtime=200)
    assert needs_model_recompose(book_dir) is True
    assert apparatus_only_retry_advice(book_dir) is None


def test_series_config_newer_than_book_md_means_recompose_is_needed(tmp_path, monkeypatch):
    _isolate_modules_dir(tmp_path, monkeypatch)
    book_dir = tmp_path / "some-book"
    _touch(book_dir / "book" / "book.md", mtime=100)
    _touch(book_dir / "_system" / "series-config.yaml", mtime=200)
    assert needs_model_recompose(book_dir) is True


def test_a_model_governing_module_edit_means_recompose_is_needed(tmp_path, monkeypatch):
    # Simulates editing _narrative.py or _book_voice.py: prose rules changed,
    # so the model passes must see the book again — even though nothing in the
    # book_dir itself moved.
    fake_modules_dir = tmp_path / "fake-scripts"
    fake_modules_dir.mkdir()
    monkeypatch.setattr(_compose_scope, "_HERE", fake_modules_dir)

    book_dir = tmp_path / "some-book"
    _touch(book_dir / "book" / "book.md", mtime=100)
    assert needs_model_recompose(book_dir) is False  # no governing module exists yet

    _touch(fake_modules_dir / "_narrative.py", mtime=200)
    assert needs_model_recompose(book_dir) is True


def test_a_glossary_only_change_does_not_need_a_model_recompose(tmp_path, monkeypatch):
    """The exact spiritual-ethos scenario: glossary.yml is newer than book.md,
    nothing else is — this must never be read as a reason to re-run fluency/augment."""
    _isolate_modules_dir(tmp_path, monkeypatch)
    book_dir = tmp_path / "spiritual-ethos"
    _touch(book_dir / "book" / "book.md", mtime=100)
    _touch(book_dir / "_system" / "glossary.yml", mtime=200)
    assert needs_model_recompose(book_dir) is False
    advice = apparatus_only_retry_advice(book_dir)
    assert advice is not None
    assert "apply_book_apparatus.py" in advice
    assert "spiritual-ethos" in advice


def test_book_md_freshly_composed_needs_no_recompose(tmp_path, monkeypatch):
    _isolate_modules_dir(tmp_path, monkeypatch)
    book_dir = tmp_path / "some-book"
    _touch(book_dir / "_system" / "source" / "text" / "refined-english.md", mtime=100)
    _touch(book_dir / "_system" / "series-config.yaml", mtime=100)
    _touch(book_dir / "book" / "book.md", mtime=200)
    # Nothing model-governing is newer than book.md, so a retry needs no model
    # pass — the advisory correctly fires (it fires whenever a recompose isn't
    # needed, regardless of *why*; a caller only cares "skip the model pass").
    assert needs_model_recompose(book_dir) is False
    assert apparatus_only_retry_advice(book_dir) is not None


def test_book_driver_checks_compose_scope_before_recomposing():
    """Pins the wiring: the advisory check must run BEFORE the expensive
    compose_book_v2 call, not after — a warning that fires after the money is
    already spent is not a guard."""
    src = (Path(__file__).resolve().parents[1] / "phases" / "book_driver.py").read_text(encoding="utf-8")
    assert "apparatus_only_retry_advice" in src
    assert src.index("apparatus_only_retry_advice") < src.index("compose_book_v2(book_dir")
