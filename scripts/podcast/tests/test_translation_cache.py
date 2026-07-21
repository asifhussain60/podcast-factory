"""When a composed chapter chunk may be reused.

The audit's finding was that this — the single highest-leverage correctness lever
in the compose chain — had no test at all. The permissive failure is silent and
expensive: the pipeline reports "composed" and re-emits prose written before the
rule you just fixed. On the-master-and-the-disciple that meant every chapter of
the shipping book had skipped the narrative-frame gate, because the chunks were
newer than the June source and nothing else counted.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _translation_cache import cache_floor, governing_inputs, make_is_fresh  # noqa: E402

OLD = time.time() - 86_400 * 30
MID = time.time() - 86_400 * 10
NEW = time.time() - 60


def _touch(path: Path, when: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (when, when))
    return path


def _book(tmp_path: Path, *, config_at: float = OLD) -> tuple[Path, Path]:
    bd = tmp_path / "slug"
    refined = _touch(bd / "_system" / "source" / "text" / "refined-english.md", OLD)
    _touch(bd / "_system" / "series-config.yaml", config_at)
    return bd, refined


def test_a_chunk_newer_than_every_input_is_reusable(tmp_path: Path) -> None:
    bd, refined = _book(tmp_path)
    chunk = _touch(bd / "book" / "_chunks" / "translation" / "bk-01.md", NEW)
    assert make_is_fresh(bd, refined)(chunk) is True


def test_a_chunk_older_than_the_source_is_rejected(tmp_path: Path) -> None:
    bd, refined = _book(tmp_path)
    os.utime(refined, (MID, MID))
    chunk = _touch(bd / "book" / "_chunks" / "translation" / "bk-01.md", OLD)
    assert make_is_fresh(bd, refined)(chunk) is False


def test_a_newer_config_invalidates_the_cache(tmp_path: Path) -> None:
    """THE live bug. The source was from June and the chunks from 19 July, so the
    chunks looked fresh — but `narrative_frame` was locked in the config on the
    20th, and every chapter went on being served from a cache written before that
    rule existed."""
    bd, refined = _book(tmp_path, config_at=NEW)
    chunk = _touch(bd / "book" / "_chunks" / "translation" / "bk-01.md", MID)
    assert make_is_fresh(bd, refined)(chunk) is False, "a config change must invalidate the cache"


def test_a_newer_prompt_module_invalidates_the_cache(tmp_path: Path) -> None:
    """A prompt fix that changes what the model is told must not leave the
    pre-fix prose in place, silently, reported as composed."""
    bd, refined = _book(tmp_path)
    chunk = _touch(bd / "book" / "_chunks" / "translation" / "bk-01.md", MID)
    prompts = Path(__file__).resolve().parents[1] / "_translation_prompts.py"
    assert prompts.exists()
    # The real module is newer than a 10-day-old chunk in any working checkout.
    assert cache_floor(bd, refined) >= prompts.stat().st_mtime - 1
    assert make_is_fresh(bd, refined)(chunk) is False


def test_the_governing_set_names_source_config_and_the_rule_modules(tmp_path: Path) -> None:
    bd, refined = _book(tmp_path)
    names = {p.name for p in governing_inputs(bd, refined)}
    assert "refined-english.md" in names
    assert "series-config.yaml" in names, "the frame lives here"
    assert "_translation_prompts.py" in names
    assert "_narrative.py" in names


def test_a_missing_input_does_not_make_the_cache_look_fresher(tmp_path: Path) -> None:
    """Absence must not lower the floor — a deleted config should never license
    reuse of a chunk that the remaining inputs already invalidate."""
    bd, refined = _book(tmp_path)
    (bd / "_system" / "series-config.yaml").unlink()
    floor = cache_floor(bd, refined)
    assert floor > 0
    assert make_is_fresh(bd, refined)(_touch(bd / "c.md", OLD)) is False


def test_a_missing_chunk_is_never_fresh(tmp_path: Path) -> None:
    bd, refined = _book(tmp_path)
    assert make_is_fresh(bd, refined)(bd / "book" / "_chunks" / "translation" / "nope.md") is False
